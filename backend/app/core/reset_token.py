"""
LAYERS - Password Reset Utilities
Token generation and verification for password reset
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib

from app.core.config import settings


def generate_reset_token() -> str:
    """
    Generate a secure random token for password reset.
    Returns a 32-character hex string.
    """
    return secrets.token_hex(16)


def hash_reset_token(token: str) -> str:
    """
    Hash a reset token for storage.
    We don't store plain tokens in the database.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset_token_expiry() -> datetime:
    """
    Create expiry time for reset token (1 hour from now).
    """
    return datetime.now(timezone.utc) + timedelta(hours=1)


def is_token_expired(expiry: datetime) -> bool:
    """
    Check if a reset token has expired.
    """
    return datetime.now(timezone.utc) > expiry


# For email verification (similar pattern)
def generate_verification_code() -> str:
    """
    Generate a 6-digit verification code for email.
    """
    return str(secrets.randbelow(900000) + 100000)  # 100000-999999
