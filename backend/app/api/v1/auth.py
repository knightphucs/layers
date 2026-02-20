"""
LAYERS - Authentication API Routes
Register, login, token refresh, password reset
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
    UserProfile,
    MessageResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePassword,
    AuthResponse,
)
from app.services.auth_service import AuthService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Bearer token security scheme
security = HTTPBearer()


# =============================================================================
# Dependencies
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user.

    Usage:
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    token = credentials.credentials
    token_data = verify_access_token(token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns None if no valid token.
    Useful for endpoints that work differently for logged in/out users.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    Returns user profile and tokens on successful registration.
    """
    return await AuthService.register_user(db, data)


@router.post("/login", response_model=AuthResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    Returns user profile and tokens on successful login.
    """
    return await AuthService.login_user(db, data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    return await AuthService.refresh_access_token(db, data)


# =============================================================================
# Password Reset
# =============================================================================

@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset.
    Generates a reset token (returned in dev mode, would be emailed in production).
    """
    return await AuthService.request_password_reset(db, data)


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with token and new password."""
    return await AuthService.confirm_password_reset(db, data)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePassword,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password for logged-in user. Requires current password."""
    return await AuthService.change_password(db, user, data)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user)
):
    """Get current authenticated user's profile."""
    return AuthService.get_user_profile(user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UserProfile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    return await AuthService.update_user_profile(db, user, data)


@router.delete("/me", response_model=MessageResponse)
async def deactivate_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate current user's account."""
    return await AuthService.deactivate_account(db, user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    user: User = Depends(get_current_user)
):
    """
    Logout current user.

    Note: JWT tokens are stateless, so this just returns success.
    In production, you might want to blacklist the token in Redis.
    """
    logger.info(f"User logged out: {user.username}")
    return MessageResponse(message="Successfully logged out")


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/check-email/{email}")
async def check_email_available(email: str, db: AsyncSession = Depends(get_db)):
    """Check if an email is available for registration."""
    return await AuthService.check_email_availability(db, email)


@router.get("/check-username/{username}")
async def check_username_available(username: str, db: AsyncSession = Depends(get_db)):
    """Check if a username is available for registration."""
    return await AuthService.check_username_availability(db, username)
