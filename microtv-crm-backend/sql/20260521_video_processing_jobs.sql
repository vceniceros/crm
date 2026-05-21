CREATE TABLE IF NOT EXISTS video_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    original_url TEXT NOT NULL,
    original_path TEXT NOT NULL,
    optimized_url TEXT,
    optimized_path TEXT,
    thumbnail_url TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE task_attachments
    ADD COLUMN IF NOT EXISTS video_job_id UUID REFERENCES video_processing_jobs(id) ON DELETE SET NULL;

ALTER TABLE ticket_attachments
    ADD COLUMN IF NOT EXISTS video_job_id UUID REFERENCES video_processing_jobs(id) ON DELETE SET NULL;

ALTER TABLE ticket_satisfaction_media
    ADD COLUMN IF NOT EXISTS video_job_id UUID REFERENCES video_processing_jobs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_video_processing_jobs_status ON video_processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_task_attachments_video_job ON task_attachments(video_job_id);
CREATE INDEX IF NOT EXISTS idx_ticket_attachments_video_job ON ticket_attachments(video_job_id);
CREATE INDEX IF NOT EXISTS idx_ticket_satisfaction_media_video_job ON ticket_satisfaction_media(video_job_id);
