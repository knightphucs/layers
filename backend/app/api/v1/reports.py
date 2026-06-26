"""
LAYERS - Reports API
  POST /api/v1/reports/{artifact_id}  — authenticated users submit a report
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.report import ReportIn, ReportOut
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/{artifact_id}", response_model=ReportOut, status_code=status.HTTP_200_OK)
async def submit_report(
    artifact_id: UUID,
    body: ReportIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a content report. One report per user per artifact (idempotent)."""
    try:
        result = await ReportService.submit_report(
            db,
            artifact_id=artifact_id,
            reporter_id=current_user.id,
            reason=body.reason.value,
            detail=body.detail,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return result
