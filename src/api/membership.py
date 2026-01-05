"""
Membership API Routes

Handles subscription checkout, webhooks, and member verification.
Uses Supabase for user accounts and Stripe for payments.
"""

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
import os

from src.services.stripe_service import (
    create_stripe_service,
    MEMBERSHIP_PLANS,
    MembershipTier,
)
from src.services.auth import create_auth_service

router = APIRouter(prefix="/membership", tags=["membership"])


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    
    email: EmailStr
    tier: Literal["premium", "founding"]
    billing_cycle: Literal["monthly", "yearly"] = "monthly"


class FreeSignupRequest(BaseModel):
    """Request to sign up for free tier."""
    
    email: EmailStr


class LoginRequest(BaseModel):
    """Request to login."""
    
    email: EmailStr
    password: Optional[str] = None  # None = magic link


class CheckoutResponse(BaseModel):
    """Response with checkout URL."""
    
    checkout_url: str
    session_id: str


class MemberStatusResponse(BaseModel):
    """Member status response."""
    
    email: str
    tier: MembershipTier
    is_active: bool
    features: list[str]


# Price IDs cache
_price_ids: dict[str, dict] = {}


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest):
    """
    Create a Stripe Checkout session for subscription.
    
    Returns URL to redirect user to Stripe's hosted checkout page.
    """
    try:
        stripe = create_stripe_service()
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail="Stripe not configured. Add STRIPE_SECRET_KEY to .env"
        )
    
    plan = MEMBERSHIP_PLANS.get(request.tier)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")
    
    # Get or create price IDs
    if request.tier not in _price_ids:
        # In production, these would be pre-created in Stripe Dashboard
        # For now, create them dynamically
        try:
            prices = await stripe.create_product_and_prices(plan)
            _price_ids[request.tier] = prices
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create Stripe product: {e}"
            )
    
    price_key = "monthly_price_id" if request.billing_cycle == "monthly" else "yearly_price_id"
    price_id = _price_ids[request.tier][price_key]
    
    # Create checkout session
    result = await stripe.create_checkout_session(
        price_id=price_id,
        customer_email=request.email,
        metadata={"tier": request.tier, "billing_cycle": request.billing_cycle},
    )
    
    return CheckoutResponse(
        checkout_url=result.checkout_url,
        session_id=result.session_id,
    )


@router.post("/free-signup")
async def free_signup(request: FreeSignupRequest):
    """
    Sign up for free tier - creates Supabase account with magic link.
    """
    email = request.email
    
    try:
        auth = create_auth_service()
        result = await auth.signup_free(email)
        
        if result.success:
            return {
                "status": "success",
                "message": "Welcome to Cold Case Crawler! Check your email for a login link.",
                "tier": "free",
            }
        else:
            # Check if user already exists
            existing = await auth.get_member_status(email)
            if existing:
                return {
                    "status": "exists",
                    "message": "You're already signed up! Check your email for a login link.",
                    "tier": existing.get("tier", "free"),
                }
            raise HTTPException(status_code=400, detail=result.error)
            
    except Exception as e:
        # Fallback: just store in database without auth
        try:
            auth = create_auth_service()
            await auth._create_member_record_by_email(email)
            return {
                "status": "success",
                "message": "Welcome to Cold Case Crawler!",
                "tier": "free",
            }
        except:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(request: LoginRequest):
    """
    Login with email. If password provided, use password auth.
    Otherwise, send magic link.
    """
    try:
        auth = create_auth_service()
        
        if request.password:
            result = await auth.login_email(request.email, request.password)
        else:
            result = await auth.login_magic_link(request.email)
            return {
                "status": "magic_link_sent",
                "message": "Check your email for a login link!",
            }
        
        if result.success:
            return {
                "status": "success",
                "user": {
                    "email": result.user.email,
                    "tier": result.user.tier,
                },
                "token": result.session_token,
            }
        else:
            raise HTTPException(status_code=401, detail=result.error)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
):
    """
    Handle Stripe webhook events.
    
    Key events:
    - checkout.session.completed: New subscription created
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_failed: Payment failed
    """
    try:
        stripe = create_stripe_service()
    except ValueError:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    payload = await request.body()
    
    try:
        event = stripe.verify_webhook_signature(payload, stripe_signature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    
    auth = create_auth_service()
    
    if event_type == "checkout.session.completed":
        # New subscription created
        email = data.get("customer_email")
        customer_id = data.get("customer")
        metadata = data.get("metadata", {})
        tier = metadata.get("tier", "premium")
        
        # Update member tier in Supabase
        await auth.update_membership(email, tier, customer_id)
        print(f"✅ New {tier} member: {email}")
    
    elif event_type == "customer.subscription.deleted":
        # Subscription cancelled - downgrade to free
        customer_id = data.get("customer")
        # Would need to look up email by customer_id
        print(f"❌ Subscription cancelled for customer: {customer_id}")
    
    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        print(f"⚠️ Payment failed for customer: {customer_id}")
    
    return {"status": "ok"}


@router.get("/status/{email}", response_model=MemberStatusResponse)
async def get_member_status(email: str):
    """Get membership status for an email."""
    try:
        auth = create_auth_service()
        member = await auth.get_member_status(email)
        
        if member:
            tier = member.get("tier", "free")
        else:
            tier = "free"
        
        plan = MEMBERSHIP_PLANS[tier]
        
        return MemberStatusResponse(
            email=email,
            tier=tier,
            is_active=True,
            features=plan.features,
        )
    except Exception as e:
        # Default to free tier on error
        plan = MEMBERSHIP_PLANS["free"]
        return MemberStatusResponse(
            email=email,
            tier="free",
            is_active=True,
            features=plan.features,
        )


@router.get("/portal/{email}")
async def get_billing_portal(email: str, return_url: str = "/"):
    """
    Get Stripe Billing Portal URL for member to manage subscription.
    """
    try:
        auth = create_auth_service()
        member = await auth.get_member_status(email)
        
        if not member or not member.get("stripe_customer_id"):
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        stripe = create_stripe_service()
        portal_url = await stripe.create_billing_portal_session(
            customer_id=member["stripe_customer_id"],
            return_url=return_url,
        )
        return {"portal_url": portal_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def get_plans():
    """Get available membership plans."""
    return {
        tier: {
            "name": plan.name,
            "price_monthly": plan.price_monthly,
            "price_yearly": plan.price_yearly,
            "features": plan.features,
        }
        for tier, plan in MEMBERSHIP_PLANS.items()
    }
