"""Async video processing service abstraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from fastapi import BackgroundTasks

from crm_backend.core.config import Settings
from crm_backend.db.session import SessionLocal
from crm_backend.infrastructure.video_job_repository import VideoJobRepository
from crm_backend.infrastructure.video_processor import VideoProcessingError, VideoProcessor
from crm_backend.models.task_execution import TaskAttachment
from crm_backend.models.ticket import TicketAttachment, TicketSatisfactionMedia
from crm_backend.models.video_processing import VideoProcessingStatus

_logger = logging.getLogger(__name__)


class VideoProcessingPort(Protocol):
    def enqueue(self, job_id: str, input_path: Path, output_path: Path, optimized_url: str) -> None:
        ...


class BackgroundTaskVideoProcessingService(VideoProcessingPort):
    def __init__(self, background_tasks: BackgroundTasks, processor: VideoProcessor, settings: Settings) -> None:
        self._background_tasks = background_tasks
        self._processor = processor
        self._settings = settings

    def enqueue(self, job_id: str, input_path: Path, output_path: Path, optimized_url: str) -> None:
        self._background_tasks.add_task(self._run, job_id, input_path, output_path, optimized_url)

    def _run(self, job_id: str, input_path: Path, output_path: Path, optimized_url: str) -> None:
        session = SessionLocal()
        repo = VideoJobRepository(session)
        try:
            repo.update_status(job_id, VideoProcessingStatus.PROCESSING.value)
            duration = self._processor.get_duration_seconds(input_path)
            if duration is not None and duration > self._settings.video_max_duration_seconds:
                repo.update_status(
                    job_id,
                    VideoProcessingStatus.FAILED.value,
                    error=f"El video supera el limite de {self._settings.video_max_duration_seconds} segundos.",
                )
                self._delete_raw(input_path)
                return

            self._processor.compress(input_path, output_path, self._settings)
            self._mark_referencing_media_ready(session, job_id, optimized_url, output_path)
            repo.update_status(
                job_id,
                VideoProcessingStatus.READY.value,
                optimized_url=optimized_url,
                optimized_path=self._settings.to_public_storage_path(optimized_url),
            )
            self._delete_raw(input_path)
        except VideoProcessingError as exc:
            repo.update_status(job_id, VideoProcessingStatus.FAILED.value, error=str(exc))
            self._delete_raw(input_path)
        except Exception as exc:
            _logger.exception("Unexpected video processing failure for job %s", job_id)
            repo.update_status(job_id, VideoProcessingStatus.FAILED.value, error="No se pudo procesar el video.")
            self._delete_raw(input_path)
        finally:
            session.close()

    def _delete_raw(self, input_path: Path) -> None:
        try:
            input_path.unlink(missing_ok=True)
        except OSError:
            _logger.warning("Could not delete raw video file %s", input_path, exc_info=True)

    def _mark_referencing_media_ready(
        self,
        session,
        job_id: str,
        optimized_url: str,
        output_path: Path,
    ) -> None:
        file_name = output_path.name

        for attachment_model in (TaskAttachment, TicketAttachment):
            attachments = session.query(attachment_model).filter(attachment_model.video_job_id == job_id).all()
            for attachment in attachments:
                attachment.file_name = file_name
                attachment.file_url = optimized_url
                attachment.mime_type = "video/mp4"

        satisfaction_media = session.query(TicketSatisfactionMedia).filter(TicketSatisfactionMedia.video_job_id == job_id).all()
        for media in satisfaction_media:
            media.file_name = file_name
            media.file_path = optimized_url
            media.mime_type = "video/mp4"

        session.commit()
