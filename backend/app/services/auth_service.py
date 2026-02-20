"""
LAYERS - Authentication Service
================================
Business logic for user registration, login, password management,
and profile updates.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional
import logging

from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenRefresh,
    TokenResponse,
    UserResponse,
    UserProfile,
    MessageResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePassword,
    AuthResponse,
)
from app.core.security import (
    get_password_hash,
    verify_password,
    create_token_pair,
    verify_refresh_token,
)
from app.core.reset_token import (
    generate_reset_token,
    hash_reset_token,
    create_reset_token_expiry,
    is_token_expired,
)
from app.core.config import settings


logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and user management business logic."""

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _build_user_response(user: User) -> UserResponse:
        """Build UserResponse from User model."""
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            bio=user.bio,
            experience_points=user.experience_points,
            level=user.level,
            reputation_score=user.reputation_score,
            is_verified=user.is_verified,
            created_at=user.created_at,
        )

    @staticmethod
    async def _check_email_exists(db: AsyncSession, email: str) -> bool:
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def _check_username_exists(db: AsyncSession, username: str) -> bool:
        result = await db.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalar_one_or_none() is not None

    # ========================================================
    # REGISTRATION
    # ========================================================

    @staticmethod
    async def register_user(
        db: AsyncSession,
        data: UserRegister,
    ) -> AuthResponse:
        """
        Register a new user account.
        Returns user profile and tokens on success.
        """
        if await AuthService._check_email_exists(db, data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        if await AuthService._check_username_exists(db, data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        user = User(
            email=data.email,
            username=data.username,
            password_hash=get_password_hash(data.password),
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"New user registered: {user.username} ({user.email})")

        tokens = create_token_pair(str(user.id))

        return AuthResponse(
            user=AuthService._build_user_response(user),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    # ========================================================
    # LOGIN
    # ========================================================

    @staticmethod
    async def login_user(
        db: AsyncSession,
        data: UserLogin,
    ) -> AuthResponse:
        """
        Login with email and password.
        Returns user profile and tokens on success.
        """
        result = await db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if user.is_banned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been suspended",
            )

        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(f"User logged in: {user.username}")

        tokens = create_token_pair(str(user.id))

        return AuthResponse(
            user=AuthService._build_user_response(user),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    # ========================================================
    # TOKEN REFRESH
    # ========================================================

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession,
        data: TokenRefresh,
    ) -> TokenResponse:
        """Refresh access token using a valid refresh token."""
        token_data = verify_refresh_token(data.refresh_token)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        result = await db.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()

        if not user or user.is_banned or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        tokens = create_token_pair(str(user.id))

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    # ========================================================
    # PASSWORD RESET
    # ========================================================

    @staticmethod
    async def request_password_reset(
        db: AsyncSession,
        data: PasswordResetRequest,
    ) -> MessageResponse:
        """
        Request a password reset token.
        Always returns success to prevent email enumeration.
        In dev mode, returns the plain token in the message.
        """
        result = await db.execute(
            select(User).where(User.email == data.email.lower())
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Password reset requested for unknown email: {data.email}")
            return MessageResponse(
                message="If an account exists with this email, a reset link has been sent."
            )

        plain_token = generate_reset_token()
        hashed_token = hash_reset_token(plain_token)
        expiry = create_reset_token_expiry()

        user.reset_token_hash = hashed_token
        user.reset_token_expiry = expiry
        await db.commit()

        logger.info(f"Password reset requested for: {user.email}")

        if settings.debug:
            return MessageResponse(
                message=f"Reset token (DEV ONLY): {plain_token}",
                success=True,
            )

        return MessageResponse(
            message="If an account exists with this email, a reset link has been sent."
        )

    @staticmethod
    async def confirm_password_reset(
        db: AsyncSession,
        data: PasswordResetConfirm,
    ) -> MessageResponse:
        """Confirm password reset with token and new password."""
        hashed_token = hash_reset_token(data.token)

        result = await db.execute(
            select(User).where(User.reset_token_hash == hashed_token)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        if user.reset_token_expiry and is_token_expired(user.reset_token_expiry):
            user.reset_token_hash = None
            user.reset_token_expiry = None
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

        user.password_hash = get_password_hash(data.new_password)
        user.reset_token_hash = None
        user.reset_token_expiry = None
        await db.commit()

        logger.info(f"Password reset completed for: {user.email}")

        return MessageResponse(
            message="Password has been reset successfully. You can now login."
        )

    # ========================================================
    # CHANGE PASSWORD
    # ========================================================

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        data: ChangePassword,
    ) -> MessageResponse:
        """Change password for a logged-in user. Requires current password."""
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.password_hash = get_password_hash(data.new_password)
        await db.commit()

        logger.info(f"Password changed for: {user.email}")

        return MessageResponse(message="Password has been changed successfully.")

    # ========================================================
    # PROFILE
    # ========================================================

    @staticmethod
    def get_user_profile(user: User) -> UserResponse:
        """Get user profile response."""
        return AuthService._build_user_response(user)

    @staticmethod
    async def update_user_profile(
        db: AsyncSession,
        user: User,
        data: UserProfile,
    ) -> UserResponse:
        """Update user profile (username, bio, avatar_url)."""
        if data.username and data.username != user.username:
            if await AuthService._check_username_exists(db, data.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )
            user.username = data.username

        if data.bio is not None:
            user.bio = data.bio

        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url

        await db.commit()
        await db.refresh(user)

        return AuthService._build_user_response(user)

    @staticmethod
    async def deactivate_account(
        db: AsyncSession,
        user: User,
    ) -> MessageResponse:
        """Deactivate user account (soft delete)."""
        user.is_active = False
        await db.commit()

        logger.info(f"Account deactivated: {user.email}")

        return MessageResponse(message="Account has been deactivated.")

    # ========================================================
    # AVAILABILITY CHECKS
    # ========================================================

    @staticmethod
    async def check_email_availability(
        db: AsyncSession,
        email: str,
    ) -> dict:
        """Check if email is available for registration."""
        exists = await AuthService._check_email_exists(db, email)
        return {"email": email, "available": not exists}

    @staticmethod
    async def check_username_availability(
        db: AsyncSession,
        username: str,
    ) -> dict:
        """Check if username is available for registration."""
        exists = await AuthService._check_username_exists(db, username)
        return {"username": username, "available": not exists}
