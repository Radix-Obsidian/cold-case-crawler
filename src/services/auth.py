"""
Authentication Service using Supabase Auth

Handles user signup, login, and membership management.
"""

import os
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
import logging

logger = logging.getLogger(__name__)

MembershipTier = Literal["free", "premium", "founding"]


class User(BaseModel):
    """User model."""
    
    id: str
    email: str
    tier: MembershipTier = "free"
    stripe_customer_id: Optional[str] = None
    created_at: datetime


class AuthResult(BaseModel):
    """Result from auth operations."""
    
    success: bool
    user: Optional[User] = None
    session_token: Optional[str] = None
    error: Optional[str] = None


class AuthService:
    """
    Authentication service using Supabase.
    
    Handles:
    - Email/password signup and login
    - Magic link (passwordless) auth
    - Session management
    - Membership tier tracking
    """
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def signup_email(self, email: str, password: str) -> AuthResult:
        """
        Sign up a new user with email and password.
        """
        try:
            result = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            
            if result.user:
                # Create member record in our members table
                await self._create_member_record(result.user.id, email)
                
                return AuthResult(
                    success=True,
                    user=User(
                        id=result.user.id,
                        email=email,
                        tier="free",
                        created_at=datetime.utcnow(),
                    ),
                    session_token=result.session.access_token if result.session else None,
                )
            else:
                return AuthResult(success=False, error="Signup failed")
                
        except Exception as e:
            logger.error(f"Signup error: {e}")
            return AuthResult(success=False, error=str(e))
    
    async def signup_free(self, email: str) -> AuthResult:
        """
        Sign up for free tier with just email (magic link).
        Sends a login link to the email.
        """
        try:
            # Use magic link for passwordless signup
            result = self.supabase.auth.sign_in_with_otp({
                "email": email,
            })
            
            # Create member record (will be linked when they click the link)
            await self._create_member_record_by_email(email)
            
            return AuthResult(
                success=True,
                user=User(
                    id="pending",
                    email=email,
                    tier="free",
                    created_at=datetime.utcnow(),
                ),
                error=None,
            )
            
        except Exception as e:
            logger.error(f"Free signup error: {e}")
            return AuthResult(success=False, error=str(e))
    
    async def login_email(self, email: str, password: str) -> AuthResult:
        """
        Log in with email and password.
        """
        try:
            result = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            
            if result.user and result.session:
                # Get member data
                member = await self._get_member_by_email(email)
                
                return AuthResult(
                    success=True,
                    user=User(
                        id=result.user.id,
                        email=email,
                        tier=member.get("tier", "free") if member else "free",
                        stripe_customer_id=member.get("stripe_customer_id") if member else None,
                        created_at=datetime.fromisoformat(member["created_at"]) if member else datetime.utcnow(),
                    ),
                    session_token=result.session.access_token,
                )
            else:
                return AuthResult(success=False, error="Invalid credentials")
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return AuthResult(success=False, error=str(e))
    
    async def login_magic_link(self, email: str) -> AuthResult:
        """
        Send a magic link for passwordless login.
        """
        try:
            self.supabase.auth.sign_in_with_otp({
                "email": email,
            })
            
            return AuthResult(
                success=True,
                error=None,
            )
            
        except Exception as e:
            logger.error(f"Magic link error: {e}")
            return AuthResult(success=False, error=str(e))
    
    async def verify_session(self, token: str) -> AuthResult:
        """
        Verify a session token and return user data.
        """
        try:
            result = self.supabase.auth.get_user(token)
            
            if result.user:
                member = await self._get_member_by_email(result.user.email)
                
                return AuthResult(
                    success=True,
                    user=User(
                        id=result.user.id,
                        email=result.user.email,
                        tier=member.get("tier", "free") if member else "free",
                        stripe_customer_id=member.get("stripe_customer_id") if member else None,
                        created_at=datetime.fromisoformat(member["created_at"]) if member else datetime.utcnow(),
                    ),
                )
            else:
                return AuthResult(success=False, error="Invalid session")
                
        except Exception as e:
            logger.error(f"Session verify error: {e}")
            return AuthResult(success=False, error=str(e))
    
    async def logout(self, token: str) -> bool:
        """
        Log out and invalidate session.
        """
        try:
            self.supabase.auth.sign_out()
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    async def update_membership(
        self, 
        email: str, 
        tier: MembershipTier,
        stripe_customer_id: Optional[str] = None,
    ) -> bool:
        """
        Update a user's membership tier.
        Called after successful Stripe checkout.
        """
        try:
            update_data = {"tier": tier, "updated_at": datetime.utcnow().isoformat()}
            if stripe_customer_id:
                update_data["stripe_customer_id"] = stripe_customer_id
            
            self.supabase.table("members").update(update_data).eq("email", email).execute()
            logger.info(f"Updated membership for {email} to {tier}")
            return True
            
        except Exception as e:
            logger.error(f"Update membership error: {e}")
            return False
    
    async def get_member_status(self, email: str) -> Optional[dict]:
        """
        Get membership status for an email.
        """
        return await self._get_member_by_email(email)
    
    # ==================== PRIVATE METHODS ====================
    
    async def _create_member_record(self, user_id: str, email: str) -> None:
        """Create a member record linked to auth user."""
        try:
            self.supabase.table("members").insert({
                "user_id": user_id,
                "email": email,
                "tier": "free",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.error(f"Failed to create member record: {e}")
    
    async def _create_member_record_by_email(self, email: str) -> None:
        """Create a member record by email (for magic link signup)."""
        try:
            # Check if already exists
            existing = await self._get_member_by_email(email)
            if existing:
                return
            
            self.supabase.table("members").insert({
                "email": email,
                "tier": "free",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.error(f"Failed to create member record: {e}")
    
    async def _get_member_by_email(self, email: str) -> Optional[dict]:
        """Get member record by email."""
        try:
            result = self.supabase.table("members").select("*").eq("email", email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get member: {e}")
            return None


def create_auth_service() -> AuthService:
    """Create AuthService with Supabase client."""
    from supabase import create_client
    from src.config import get_settings
    
    settings = get_settings()
    supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return AuthService(supabase_client)
