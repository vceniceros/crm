"""Repository for video processing jobs."""

from __future__ import annotations

from sqlalchemy.orm import Session

from crm_backend.models.video_processing import VideoProcessingJob, VideoProcessingStatus


class VideoJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, original_url: str, original_path: str) -> VideoProcessingJob:
        job = VideoProcessingJob(
            status=VideoProcessingStatus.UPLOADED.value,
            original_url=original_url,
            original_path=original_path,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def update_status(
        self,
        job_id: str,
        status: str,
        optimized_url: str | None = None,
        optimized_path: str | None = None,
        error: str | None = None,
    ) -> None:
        job = self.get_by_id(job_id)
        if job is None:
            return
        job.status = status
        if optimized_url is not None:
            job.optimized_url = optimized_url
        if optimized_path is not None:
            job.optimized_path = optimized_path
        job.error = error
        self._session.commit()

    def get_by_id(self, job_id: str) -> VideoProcessingJob | None:
        return self._session.get(VideoProcessingJob, str(job_id))
