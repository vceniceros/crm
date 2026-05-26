"""FFmpeg-backed video processing helpers."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from crm_backend.core.config import Settings

_logger = logging.getLogger(__name__)


class VideoProcessingError(RuntimeError):
    """Raised when FFmpeg cannot optimize a video."""


class VideoProcessor:
    """Run ffprobe and ffmpeg through subprocess without shell execution."""

    def get_duration_seconds(self, input_path: Path) -> float | None:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(input_path)],
                shell=False,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                return None
            data = json.loads(result.stdout.decode("utf-8"))
            return float(data["format"]["duration"])
        except Exception:
            return None

    def compress(self, input_path: Path, output_path: Path, settings: Settings) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-fflags",
                "+genpts",
                "-i",
                str(input_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                f"scale=-2:{settings.video_target_height},fps={settings.video_target_fps}",
                "-af",
                "aresample=async=1000:first_pts=0",
                "-c:v",
                "libx264",
                "-crf",
                str(settings.video_ffmpeg_crf),
                "-preset",
                settings.video_ffmpeg_preset,
                "-pix_fmt",
                "yuv420p",
                "-fps_mode",
                "cfr",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-shortest",
                "-avoid_negative_ts",
                "make_zero",
                "-movflags",
                "+faststart",
                "-map_metadata",
                "-1",
                str(output_path),
            ],
            shell=False,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            _logger.error("FFmpeg video compression failed for %s: %s", input_path, stderr)
            raise VideoProcessingError("No se pudo procesar el video con FFmpeg.")
