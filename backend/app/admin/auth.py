"""
LAYERS - Admin Authentication Backend
====================================================
Gates the /admin panel. Reuses the SAME primitives as the REST API so there's
no second auth system to keep in sync:
  - bcrypt verify_password (app.core.security)
  - JWT create/verify_access_token (app.core.security)
  - the "ADMIN" role check (mirrors require_admin in anti_cheat.py)

Flow:
  login()        email/username + password → verify → must be ADMIN & not banned
                 → store a fresh JWT in the (signed) admin session cookie
  authenticate() every page load: re-verify the JWT AND re-load the user, so a
                 demoted/banned admin loses access immediately, not at token expiry
  logout()       clear the session

SQLAdmin's AuthenticationBackend installs its own SessionMiddleware using the
secret_key we pass in setup.py (settings.jwt_secret_key).
"""

import logging
import uuid

from sqlalchemy import select, or_
from starlette.requests import Request

from sqladmin.authentication import AuthenticationBackend

from app.admin._helpers import is_admin_role
from app.core.database import AsyncSessionLocal
from app.core.security import (
    verify_password,
    create_access_token,
    verify_access_token,
)
from app.models.user import User

logger = logging.getLogger(__name__)


class AdminAuth(AuthenticationBackend):

    async def login(self, request: Request) -> bool:
        form = await request.form()
        identifier = (form.get("username") or "").strip()
        password = form.get("password") or ""
        if not identifier or not password:
            return False

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(
                    or_(User.email == identifier, User.username == identifier)
                )
            )
            user = result.scalar_one_or_none()

            if not user or not verify_password(password, user.password_hash):
                logger.info("Admin login failed for %r", identifier)
                return False
            if not is_admin_role(user.role):
                logger.warning("Non-admin %r tried to access admin panel", identifier)
                return False
            if getattr(user, "is_banned", False):
                return False

            request.session["token"] = create_access_token(str(user.id))
            request.session["admin_id"] = str(user.id)
            logger.info("Admin %s logged in", user.username)
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        token_data = verify_access_token(token)
        if not token_data:
            request.session.clear()
            return False

        # Re-load the user every request: a revoked admin is locked out NOW.
        try:
            uid = uuid.UUID(str(token_data.user_id))
        except (ValueError, TypeError):
            request.session.clear()
            return False

        async with AsyncSessionLocal() as session:
            user = await session.get(User, uid)
            if (not user
                    or not is_admin_role(user.role)
                    or getattr(user, "is_banned", False)):
                request.session.clear()
                return False
        return True
