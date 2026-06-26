"""
LAYERS - Admin Panel setup
=========================================
Mounts SQLAdmin at /admin. Called once from main.py after the app is created:

    from app.admin.setup import setup_admin
    setup_admin(app)

Uses the SAME async engine as the app (app.core.database.engine) so the panel
reads/writes the live database. Auth is the JWT/role backend in admin/auth.py,
keyed with settings.jwt_secret_key (also signs the admin session cookie).
"""

import logging

from sqladmin import Admin

from app.core.config import settings
from app.core.database import engine
from app.admin.auth import AdminAuth
from app.admin.views import (
    UserAdmin,
    ArtifactAdmin,
    ReportAdmin,
    ModerationLogAdmin,
)

logger = logging.getLogger(__name__)


def setup_admin(app) -> Admin:
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret_key)
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="LAYERS Admin",
    )
    admin.add_view(UserAdmin)
    admin.add_view(ArtifactAdmin)
    admin.add_view(ReportAdmin)
    admin.add_view(ModerationLogAdmin)
    logger.info("🛠️ Admin panel mounted at /admin")
    return admin
