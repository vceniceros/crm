"""Media processing status endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from crm_backend.api.dependencies import get_authenticated_crm_session
from crm_backend.db import get_db_session
from crm_backend.infrastructure.video_job_repository import VideoJobRepository
from crm_backend.schemas.media import MediaStatusResponse
from crm_backend.services.auth_service import ResolvedCrmSession

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{media_id}/status", response_model=MediaStatusResponse)
def get_media_status(
    media_id: str,
    _: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    session: Session = Depends(get_db_session),
) -> MediaStatusResponse:
    job = VideoJobRepository(session).get_by_id(media_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Media no encontrado.")
    return MediaStatusResponse.model_validate(job)
