"""
Stripe Service for Cold Case Crawler Memberships

Handles subscription management, checkout sessions, and member verification.
Uses Stripe Checkout Sessions (recommended approach) for payment flows.
"""

import os
import asyncio
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
import httpx

# Membership tiers
MembershipTier = Literal["free", "premium", "founding"]


class MembershipPlan(BaseModel):
    """Membership plan configuration."""
    
    tier: MembershipTier
    name: str
    price_monthly: float  # USD
    price_yearly: float  # USD (with discount)
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    features: list[str] = Field(default_factory=list)


class Member(BaseModel):
    """Member record."""
    
    member_id: str
    email: str
    tier: MembershipTier = "free"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CheckoutResult(BaseModel):
    """Result from creating a checkout session."""
    
    checkout_url: str
    session_id: str


# Default membership plans
MEMBERSHIP_PLANS: dict[MembershipTier, MembershipPlan] = {
    "free": MembershipPlan(
        tier="free",
        name="Free Listener",
        price_monthly=0.0,
        price_yearly=0.0,
        features=[
            "Access to all public episodes",
            "Basic case summaries",
            "Community discussions",
        ]
    ),
    "premium": MembershipPlan(
        tier="premium",
        name="Case Insider",
        price_monthly=9.99,
        price_yearly=99.99,  # ~17% discount
        features=[
            "Everything in Free",
            "Early access to episodes (48 hours)",
            "Extended evidence files",
            "Ad-free listening",
            "Monthly bonus episodes",
            "Discord access",
        ]
    ),
    "founding": MembershipPlan(
        tier="founding",
        name="Founding Investigator",
        price_monthly=19.99,
        price_yearly=199.99,  # ~17% discount
        features=[
            "Everything in Premium",
            "Vote on case selection",
            "Name in episode credits",
            "Exclusive merchandise",
            "Direct Q&A with hosts",
            "Behind-the-scenes content",
        ]
    ),
}


class StripeService:
    """
    Stripe integration for Cold Case Crawler memberships.
    
    Uses Checkout Sessions for subscription management (Stripe best practice).
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        publishable_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        success_url: str = "http://localhost:8000/membership/success",
        cancel_url: str = "http://localhost:8000/membership/cancel",
    ):
        self.secret_key = secret_key or os.getenv("STRIPE_SECRET_KEY")
        self.publishable_key = publishable_key or os.getenv("STRIPE_PUBLISHABLE_KEY")
        self.webhook_secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET")
        self.success_url = success_url
        self.cancel_url = cancel_url
        self.base_url = "https://api.stripe.com/v1"
        
        if not self.secret_key:
            raise ValueError(
                "Stripe secret key required. Set STRIPE_SECRET_KEY in .env"
            )
    
    @property
    def _headers(self) -> dict[str, str]:
        """Auth headers for Stripe API."""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
    
    async def create_customer(self, email: str, name: Optional[str] = None) -> str:
        """Create a Stripe customer and return customer ID."""
        async with httpx.AsyncClient() as client:
            data = {"email": email}
            if name:
                data["name"] = name
            
            response = await client.post(
                f"{self.base_url}/customers",
                headers=self._headers,
                data=data,
            )
            response.raise_for_status()
            return response.json()["id"]
    
    async def create_product_and_prices(self, plan: MembershipPlan) -> dict[str, str]:
        """
        Create a Stripe product with monthly and yearly prices.
        Returns dict with price IDs.
        """
        async with httpx.AsyncClient() as client:
            # Create product
            product_response = await client.post(
                f"{self.base_url}/products",
                headers=self._headers,
                data={
                    "name": f"Cold Case Crawler - {plan.name}",
                    "description": ", ".join(plan.features[:3]),
                },
            )
            product_response.raise_for_status()
            product_id = product_response.json()["id"]
            
            # Create monthly price
            monthly_response = await client.post(
                f"{self.base_url}/prices",
                headers=self._headers,
                data={
                    "product": product_id,
                    "unit_amount": int(plan.price_monthly * 100),  # cents
                    "currency": "usd",
                    "recurring[interval]": "month",
                },
            )
            monthly_response.raise_for_status()
            monthly_price_id = monthly_response.json()["id"]
            
            # Create yearly price
            yearly_response = await client.post(
                f"{self.base_url}/prices",
                headers=self._headers,
                data={
                    "product": product_id,
                    "unit_amount": int(plan.price_yearly * 100),  # cents
                    "currency": "usd",
                    "recurring[interval]": "year",
                },
            )
            yearly_response.raise_for_status()
            yearly_price_id = yearly_response.json()["id"]
            
            return {
                "product_id": product_id,
                "monthly_price_id": monthly_price_id,
                "yearly_price_id": yearly_price_id,
            }

    async def create_checkout_session(
        self,
        price_id: str,
        customer_email: Optional[str] = None,
        customer_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> CheckoutResult:
        """
        Create a Stripe Checkout Session for subscription.
        
        Returns URL to redirect customer to Stripe's hosted checkout.
        """
        async with httpx.AsyncClient() as client:
            data = {
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "success_url": f"{self.success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": self.cancel_url,
            }
            
            if customer_id:
                data["customer"] = customer_id
            elif customer_email:
                data["customer_email"] = customer_email
            
            if metadata:
                for key, value in metadata.items():
                    data[f"metadata[{key}]"] = value
            
            response = await client.post(
                f"{self.base_url}/checkout/sessions",
                headers=self._headers,
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            
            return CheckoutResult(
                checkout_url=result["url"],
                session_id=result["id"],
            )
    
    async def get_subscription(self, subscription_id: str) -> dict:
        """Get subscription details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def cancel_subscription(
        self, 
        subscription_id: str,
        at_period_end: bool = True,
    ) -> dict:
        """
        Cancel a subscription.
        
        By default, cancels at end of billing period (recommended).
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self._headers,
                data={"cancel_at_period_end": str(at_period_end).lower()},
            )
            response.raise_for_status()
            return response.json()
    
    async def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """
        Create a Stripe Billing Portal session.
        
        Allows customers to manage their subscription, update payment, etc.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/billing_portal/sessions",
                headers=self._headers,
                data={
                    "customer": customer_id,
                    "return_url": return_url,
                },
            )
            response.raise_for_status()
            return response.json()["url"]
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> dict:
        """
        Verify Stripe webhook signature and return event data.
        
        Raises ValueError if signature is invalid.
        """
        import hmac
        import hashlib
        import time
        
        if not self.webhook_secret:
            raise ValueError("Webhook secret not configured")
        
        # Parse signature header
        elements = dict(item.split("=") for item in signature.split(","))
        timestamp = elements.get("t")
        v1_signature = elements.get("v1")
        
        if not timestamp or not v1_signature:
            raise ValueError("Invalid signature format")
        
        # Check timestamp (prevent replay attacks)
        if abs(time.time() - int(timestamp)) > 300:  # 5 min tolerance
            raise ValueError("Timestamp too old")
        
        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode()}"
        expected = hmac.new(
            self.webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        if not hmac.compare_digest(expected, v1_signature):
            raise ValueError("Invalid signature")
        
        import json
        return json.loads(payload)


# Convenience function
def create_stripe_service(**kwargs) -> StripeService:
    """Create a StripeService instance with environment defaults."""
    return StripeService(**kwargs)
