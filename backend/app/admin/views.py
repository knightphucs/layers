"""
LAYERS - Admin ModelViews
========================================
The actual screens of the panel. Four views, sitting on the Day 1+2 models:

  UserAdmin           manage users; ban/unban actions; edit role & reputation
  ArtifactAdmin       review queue; approve / remove actions; sorted most-reported-first
  ReportAdmin         read-only list of every report (filter by status/reason in search)
  ModerationLogAdmin  read-only audit trail

The approve / remove actions REUSE the exact same service calls as the
Day 1/2 REST endpoints (ModerationService + ReportService), so the panel and
the API can never drift apart:
  approve → status ACTIVE, reports dismissed, ADMIN_APPROVE logged
  remove  → status DELETED, author −30 reputation, reporters rewarded, ADMIN_REMOVE logged

NOTE on SQLAdmin 0.16.x:
  - column_default_sort must use STRING column names, not column attributes.
    sort_query() calls sort_field.split(".") which crashes on InstrumentedAttribute.
  - list_query(self, request) is the override hook (not scaffold_list_query).
  - column_searchable_list works with cast(col, String) so UUID/enum are safe,
    but we still avoid native SQLEnum cols to stay portable.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import noload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from sqladmin import ModelView, action

from app.admin._helpers import parse_pks
from app.core.database import AsyncSessionLocal
from app.models.artifact import Artifact, ArtifactStatus
from app.models.moderation_log import ModerationLog
from app.models.report import Report
from app.models.user import User
from app.services.moderation_service import ModerationService, PENALTY_ADMIN_REMOVE
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


def _admin_id(request: Request):
    """Admin's UUID from the signed session (set in AdminAuth.login)."""
    raw = request.session.get("admin_id")
    try:
        return uuid.UUID(str(raw)) if raw else None
    except (ValueError, TypeError):
        return None


def _back(request: Request) -> RedirectResponse:
    """Return to the page the action was triggered from."""
    return RedirectResponse(request.headers.get("referer") or "/admin")


# ============================================================
# USERS
# ============================================================

class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    category = "People"

    column_list = [
        User.username, User.email, User.role,
        User.reputation_score, User.level, User.is_banned, User.created_at,
    ]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.reputation_score, User.level, User.created_at]
    column_default_sort = [("created_at", True)]   # must be strings in 0.16.x
    column_details_list = [
        User.id, User.username, User.email, User.role,
        User.reputation_score, User.experience_points, User.level,
        User.is_banned, User.ban_reason, User.banned_until,
        User.cheat_strikes, User.bio, User.created_at,
    ]
    form_columns = [User.role, User.is_banned, User.reputation_score, User.ban_reason]
    can_create = False
    can_delete = False
    page_size = 50

    @action(
        name="ban_users",
        label="Ban selected",
        confirmation_message="Ban the selected user(s)? They will be logged out.",
    )
    async def ban_users(self, request: Request) -> RedirectResponse:
        ids = parse_pks(request.query_params.get("pks", ""))
        me = _admin_id(request)
        async with AsyncSessionLocal() as session:
            for raw in ids:
                try:
                    uid = uuid.UUID(raw)
                except ValueError:
                    continue
                if me and uid == me:   # never ban yourself
                    continue
                user = await session.get(User, uid)
                if user:
                    user.is_banned = True
                    user.ban_reason = "Banned via admin panel"
            await session.commit()
        return _back(request)

    @action(
        name="unban_users",
        label="Unban selected",
        confirmation_message="Unban the selected user(s)?",
    )
    async def unban_users(self, request: Request) -> RedirectResponse:
        ids = parse_pks(request.query_params.get("pks", ""))
        async with AsyncSessionLocal() as session:
            for raw in ids:
                try:
                    uid = uuid.UUID(raw)
                except ValueError:
                    continue
                user = await session.get(User, uid)
                if user:
                    user.is_banned = False
                    user.ban_reason = None
                    user.banned_until = None
                    user.cheat_strikes = 0
            await session.commit()
        return _back(request)


# ============================================================
# ARTIFACTS — the review queue
# ============================================================

class ArtifactAdmin(ModelView, model=Artifact):
    name = "Artifact"
    name_plural = "Artifacts"
    icon = "fa-solid fa-map-pin"
    category = "Content"

    column_list = [
        Artifact.content_type, Artifact.status, Artifact.report_count,
        Artifact.layer, Artifact.user_id, Artifact.created_at,
    ]
    column_searchable_list = [Artifact.layer]
    column_sortable_list = [
        Artifact.report_count, Artifact.created_at, Artifact.status,
    ]
    column_default_sort = [("report_count", True)]  # must be strings in 0.16.x
    column_details_list = [
        Artifact.id, Artifact.content_type, Artifact.status, Artifact.layer,
        Artifact.visibility, Artifact.report_count, Artifact.user_id,
        Artifact.payload, Artifact.created_at,
    ]
    form_columns = [Artifact.status]
    can_create = False
    can_delete = False
    page_size = 50

    def list_query(self, request: Request):
        # Prevent lazy="selectin" from loading Location (PostGIS geom/WKBElement
        # can't be serialized by SQLAdmin's Jinja2 context).
        return select(Artifact).options(noload(Artifact.location))

    @action(
        name="approve_publish",
        label="Approve & Publish",
        confirmation_message="Publish the selected artifact(s) and dismiss their reports?",
    )
    async def approve_publish(self, request: Request) -> RedirectResponse:
        ids = parse_pks(request.query_params.get("pks", ""))
        admin_id = _admin_id(request)
        async with AsyncSessionLocal() as session:
            for raw in ids:
                try:
                    aid = uuid.UUID(raw)
                except ValueError:
                    continue
                artifact = await session.get(Artifact, aid)
                if not artifact or artifact.status == ArtifactStatus.DELETED:
                    continue
                artifact.status = ArtifactStatus.ACTIVE
                artifact.report_count = 0
                await ReportService.resolve_for_artifact(session, aid, removed=False)
                await ModerationService.log_admin_action(
                    session, admin_id, aid, "ADMIN_APPROVE"
                )
            await session.commit()
        return _back(request)

    @action(
        name="remove_content",
        label="Remove (delete + penalize author)",
        confirmation_message="Delete the selected artifact(s) and penalize their authors?",
    )
    async def remove_content(self, request: Request) -> RedirectResponse:
        ids = parse_pks(request.query_params.get("pks", ""))
        admin_id = _admin_id(request)
        async with AsyncSessionLocal() as session:
            for raw in ids:
                try:
                    aid = uuid.UUID(raw)
                except ValueError:
                    continue
                artifact = await session.get(Artifact, aid)
                if not artifact or artifact.status == ArtifactStatus.DELETED:
                    continue
                artifact.status = ArtifactStatus.DELETED
                if artifact.user_id:
                    author = await session.get(User, artifact.user_id)
                    if author:
                        author.modify_reputation(PENALTY_ADMIN_REMOVE)
                await ReportService.resolve_for_artifact(session, aid, removed=True)
                await ModerationService.log_admin_action(
                    session, admin_id, aid, "ADMIN_REMOVE", note="removed via admin panel"
                )
            await session.commit()
        return _back(request)


# ============================================================
# REPORTS (read-only)
# ============================================================

class ReportAdmin(ModelView, model=Report):
    name = "Report"
    name_plural = "Reports"
    icon = "fa-solid fa-flag"
    category = "Content"

    column_list = [
        Report.artifact_id, Report.reporter_id, Report.reason,
        Report.status, Report.created_at,
    ]
    column_searchable_list = [Report.reason, Report.status]
    column_sortable_list = [Report.created_at, Report.status]
    column_default_sort = [("created_at", True)]   # must be strings in 0.16.x
    column_details_list = [
        Report.id, Report.artifact_id, Report.reporter_id, Report.reason,
        Report.detail, Report.status, Report.created_at, Report.resolved_at,
    ]
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


# ============================================================
# MODERATION LOG (read-only audit trail)
# ============================================================

class ModerationLogAdmin(ModelView, model=ModerationLog):
    name = "Moderation Log"
    name_plural = "Moderation Logs"
    icon = "fa-solid fa-clipboard-list"
    category = "Audit"

    column_list = [
        ModerationLog.created_at, ModerationLog.context, ModerationLog.decision,
        ModerationLog.user_id, ModerationLog.artifact_id, ModerationLog.excerpt,
    ]
    column_searchable_list = [ModerationLog.decision, ModerationLog.context]
    column_sortable_list = [ModerationLog.created_at, ModerationLog.decision]
    column_default_sort = [("created_at", True)]   # must be strings in 0.16.x
    column_details_list = [
        ModerationLog.id, ModerationLog.user_id, ModerationLog.artifact_id,
        ModerationLog.context, ModerationLog.decision, ModerationLog.reasons,
        ModerationLog.excerpt, ModerationLog.created_at,
    ]
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50
