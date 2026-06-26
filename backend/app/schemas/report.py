from typing import Optional
from pydantic import BaseModel, field_validator
from app.services.report_service import ReportReason


class ReportIn(BaseModel):
    reason: ReportReason
    detail: Optional[str] = None

    @field_validator("detail")
    @classmethod
    def truncate_detail(cls, v):
        return v[:500] if v else v


class ReportOut(BaseModel):
    message: str
    already_reported: bool
    artifact_hidden: bool
    report_count: Optional[int] = None
