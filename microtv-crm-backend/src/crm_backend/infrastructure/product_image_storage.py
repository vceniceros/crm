"""Filesystem storage for product images."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from crm_backend.core.config import Settings
from crm_backend.core.exceptions import InvalidStockProductImageError


class ProductImageStorage:
    """Persist product images on the local filesystem."""

    _SIGNATURES = {
        "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
        "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._target_dir = settings.product_images_dir
        self._target_dir.mkdir(parents=True, exist_ok=True)

    async def store(self, image: UploadFile) -> str:
        """Validate and persist an uploaded image.

        Returns the relative public URL stored in DB.
        """

        content = await image.read()
        if not content:
            raise InvalidStockProductImageError("La imagen enviada está vacía.")
        if len(content) > self._settings.product_images_max_bytes:
            raise InvalidStockProductImageError("La imagen supera el límite de 2 MB.")

        suffix = self._detect_suffix(content=content, content_type=image.content_type)
        filename = f"{uuid4()}{suffix}"
        destination = self._target_dir / filename
        destination.write_bytes(content)
        return f"{self._settings.product_images_public_prefix}/{filename}"

    def delete(self, relative_url: str | None) -> None:
        """Delete a previously stored image if it exists."""

        if not relative_url:
            return
        filename = Path(relative_url).name
        if not filename:
            return
        candidate = self._target_dir / filename
        if candidate.exists():
            candidate.unlink()
            return

        fallback = self._settings.resolve_media_filesystem_path(relative_url)
        if fallback is not None and fallback.exists():
            fallback.unlink()

    def _detect_suffix(self, *, content: bytes, content_type: str | None) -> str:
        if content.startswith(self._SIGNATURES["image/jpeg"][0]):
            detected_type = "image/jpeg"
        elif content.startswith(self._SIGNATURES["image/png"][0]):
            detected_type = "image/png"
        elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            detected_type = "image/webp"
        else:
            raise InvalidStockProductImageError("La imagen debe ser JPG, PNG o WEBP válida.")

        if content_type and content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise InvalidStockProductImageError("El tipo MIME de la imagen no es válido.")
        if content_type and content_type != detected_type:
            raise InvalidStockProductImageError("El archivo no coincide con el tipo MIME informado.")

        if detected_type == "image/webp":
            return ".webp"
        return self._SIGNATURES[detected_type][1]