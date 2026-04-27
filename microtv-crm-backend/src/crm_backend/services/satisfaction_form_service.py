"""Satisfaction form service: secure one-use survey links for closed tickets."""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from crm_backend.core.exceptions import (
    SatisfactionFormConflictError,
    SatisfactionFormNotFoundError,
    TicketAccessDeniedError,
    TicketConflictError,
    TicketNotFoundError,
    TicketValidationError,
)
from crm_backend.models.ticket import (
    Ticket,
    TicketSatisfactionForm,
    TicketSatisfactionMedia,
    TicketSatisfactionResponse,
    TicketStatus,
)

if TYPE_CHECKING:
    from crm_backend.services.auth_service import ResolvedCrmSession

_logger = logging.getLogger(__name__)

# Size limits (configurable via Settings but using sensible defaults here)
_MAX_IMAGE_BYTES = 8 * 1024 * 1024   # 8 MB
_MAX_VIDEO_BYTES = 64 * 1024 * 1024  # 64 MB
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
_ALLOWED_MIME_TYPES = _ALLOWED_IMAGE_TYPES | _ALLOWED_VIDEO_TYPES
_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "webm", "mov"}

# Default token expiry in hours
_DEFAULT_EXPIRY_HOURS = 72


def _hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string (never store raw)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _hash_ip(ip: str) -> str:
    """Return a one-way SHA-256 digest of an IP address for basic audit."""
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def _sanitize_filename(name: str) -> str:
    """Strip path components and non-safe chars from a filename."""
    basename = re.sub(r"[^\w.\-]", "_", name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
    return basename[:200] or "file"


class PublicSatisfactionFormService:
    """Handle generation, validation and submission of satisfaction forms.

    Token lifecycle:
        1. admin/ejecutivo calls generate_form → raw token returned (shown once), hash stored.
        2. External client GETs /public/ticket-satisfaction/{raw_token} → form info.
        3. External client POSTs the form → response saved, form marked used.
        4. Any subsequent POST with same token → HTTP 409.
        5. admin/ejecutivo can revoke before submission.
    """

    def __init__(
        self,
        session: Session,
        satisfaction_images_dir: object,  # pathlib.Path
        satisfaction_videos_dir: object,  # pathlib.Path
        expiry_hours: int = _DEFAULT_EXPIRY_HOURS,
    ) -> None:
        self._session = session
        self._images_dir = Path(satisfaction_images_dir)  # type: ignore[arg-type]
        self._videos_dir = Path(satisfaction_videos_dir)  # type: ignore[arg-type]
        self._expiry_hours = expiry_hours

    # ------------------------------------------------------------------
    # Internal (authenticated) operations
    # ------------------------------------------------------------------

    def generate_form(self, actor: "ResolvedCrmSession", ticket: Ticket) -> tuple[TicketSatisfactionForm, str]:
        """Create a new satisfaction form for a closed ticket.

        Returns:
            (form, raw_token) — the raw token must be shown to the actor exactly once.
        """
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TicketAccessDeniedError("Solo admin o ejecutivo pueden generar formularios de satisfacción.")

        if ticket.status != TicketStatus.CLOSED.value or not ticket.approved_by_executive:
            raise TicketAccessDeniedError(
                "Solo se puede generar encuesta en tickets cerrados y aprobados por ejecutivo."
            )

        # Allow only one active (non-expired, non-revoked) form per ticket at a time.
        existing = (
            self._session.query(TicketSatisfactionForm)
            .filter_by(ticket_id=ticket.ticket_id)
            .filter(TicketSatisfactionForm.revoked_at.is_(None))
            .filter(TicketSatisfactionForm.expires_at > datetime.now(UTC))
            .first()
        )
        if existing is not None:
            raise SatisfactionFormConflictError(
                "Ya existe un formulario activo para este ticket. Revocalo antes de generar uno nuevo."
            )

        raw_token = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw_token)

        form = TicketSatisfactionForm(
            form_id=str(uuid4()),
            ticket_id=ticket.ticket_id,
            token_hash=token_hash,
            created_by_user_id=actor.crm_user.crm_user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=self._expiry_hours),
        )
        self._session.add(form)
        self._session.commit()
        self._session.refresh(form)
        return form, raw_token

    def get_form_status(self, actor: "ResolvedCrmSession", ticket: Ticket) -> TicketSatisfactionForm | None:
        """Return the most recent satisfaction form for a ticket (any state)."""
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TicketAccessDeniedError("Solo admin o ejecutivo pueden consultar el estado del formulario.")

        return (
            self._session.query(TicketSatisfactionForm)
            .filter_by(ticket_id=ticket.ticket_id)
            .order_by(TicketSatisfactionForm.created_at.desc())
            .first()
        )

    def revoke_form(self, actor: "ResolvedCrmSession", ticket: Ticket) -> TicketSatisfactionForm:
        """Revoke the active form for a ticket. Only works before a response is submitted."""
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TicketAccessDeniedError("Solo admin o ejecutivo pueden revocar formularios.")

        form = (
            self._session.query(TicketSatisfactionForm)
            .filter_by(ticket_id=ticket.ticket_id)
            .filter(TicketSatisfactionForm.revoked_at.is_(None))
            .order_by(TicketSatisfactionForm.created_at.desc())
            .first()
        )
        if form is None:
            raise SatisfactionFormNotFoundError()

        if form.used_at is not None:
            raise SatisfactionFormConflictError(
                "El formulario ya fue respondido y no puede revocarse."
            )

        form.revoked_at = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(form)
        return form

    def get_response_for_ticket(self, actor: "ResolvedCrmSession", ticket: Ticket) -> TicketSatisfactionResponse | None:
        """Return the satisfaction response for the ticket, if any."""
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TicketAccessDeniedError("Solo admin o ejecutivo pueden consultar respuestas de satisfacción.")

        form = (
            self._session.query(TicketSatisfactionForm)
            .filter_by(ticket_id=ticket.ticket_id)
            .filter(TicketSatisfactionForm.used_at.isnot(None))
            .order_by(TicketSatisfactionForm.created_at.desc())
            .first()
        )
        if form is None or form.response is None:
            return None
        return form.response

    # ------------------------------------------------------------------
    # Public (unauthenticated) operations
    # ------------------------------------------------------------------

    def get_public_form_info(self, raw_token: str) -> TicketSatisfactionForm:
        """Look up a form by raw token for public display.

        Returns only the form model — caller decides what to expose.
        Raises SatisfactionFormNotFoundError for any invalid/expired/used/revoked state.
        """
        form = self._resolve_token(raw_token)
        return form

    async def submit_response(
        self,
        raw_token: str,
        rating: float,
        customer_name: str,
        customer_company: str,
        comment: str | None,
        media_files: list[UploadFile],
        submitter_ip: str | None,
        submitter_user_agent: str | None,
    ) -> TicketSatisfactionResponse:
        """Submit a client response. Token is consumed atomically."""
        form = self._resolve_token(raw_token)

        self._validate_rating(rating)

        # Mark form as used immediately to prevent race conditions.
        now = datetime.now(UTC)
        form.used_at = now
        self._session.flush()

        normalized_customer_name = self._normalize_customer_field(customer_name, "nombre")
        normalized_customer_company = self._normalize_customer_field(customer_company, "empresa")

        response = TicketSatisfactionResponse(
            response_id=str(uuid4()),
            form_id=form.form_id,
            ticket_id=form.ticket_id,
            customer_name=normalized_customer_name,
            customer_company=normalized_customer_company,
            rating=round(rating * 2) / 2,  # Quantize to nearest 0.5
            comment=(comment or "").strip() or None,
            submitter_ip_hash=_hash_ip(submitter_ip) if submitter_ip else None,
            submitter_user_agent=(submitter_user_agent or "")[:500] or None,
        )
        self._session.add(response)
        self._session.flush()

        # Persist media files
        stored_files: list[str] = []
        try:
            for upload in media_files:
                content = await upload.read()
                self._validate_satisfaction_media(upload, content)
                mime = (upload.content_type or "").lower()
                is_video = mime in _ALLOWED_VIDEO_TYPES
                target_dir = self._videos_dir if is_video else self._images_dir
                target_dir.mkdir(parents=True, exist_ok=True)

                suffix = self._resolve_file_suffix(upload)
                file_name = f"{uuid4().hex}{suffix}"
                dest = target_dir / file_name
                dest.write_bytes(content)
                stored_files.append(str(dest))

                media = TicketSatisfactionMedia(
                    media_id=str(uuid4()),
                    response_id=response.response_id,
                    file_path=self._build_public_media_path(file_name, is_video=is_video),
                    file_name=_sanitize_filename(upload.filename or file_name),
                    mime_type=upload.content_type or "application/octet-stream",
                    size_bytes=len(content),
                )
                self._session.add(media)

        except Exception:
            self._session.rollback()
            # Clean up any already-stored files.
            for path in stored_files:
                try:
                    import os as _os  # noqa: PLC0415
                    _os.unlink(path)
                except OSError:
                    pass
            raise

        self._session.commit()
        self._session.refresh(response)
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_token(self, raw_token: str) -> TicketSatisfactionForm:
        """Look up form by hashed token.  Raises SatisfactionFormNotFoundError for any failure."""
        if not raw_token or len(raw_token) > 200:
            raise SatisfactionFormNotFoundError()

        token_hash = _hash_token(raw_token)
        form = (
            self._session.query(TicketSatisfactionForm)
            .filter_by(token_hash=token_hash)
            .first()
        )
        # Always return a generic error — no data leakage.
        if form is None or not form.is_usable:
            raise SatisfactionFormNotFoundError()
        return form

    def _validate_rating(self, rating: float) -> None:
        quantized = round(rating * 2) / 2
        if quantized < 0.5 or quantized > 5.0:
            raise TicketValidationError("La puntuación debe estar entre 0.5 y 5.0 estrellas.")

    def _validate_satisfaction_media(self, upload: UploadFile, content: bytes) -> None:
        if not content:
            raise TicketValidationError("El archivo adjunto está vacío.")

        mime = (upload.content_type or "").lower()
        if mime not in _ALLOWED_MIME_TYPES:
            raise TicketValidationError(
                "Solo se admiten imágenes (JPEG, PNG, WEBP) y videos (MP4, WEBM, MOV) en la encuesta."
            )

        # Real MIME validation via magic bytes
        self._check_magic_bytes(content, mime)

        is_video = mime in _ALLOWED_VIDEO_TYPES
        max_bytes = _MAX_VIDEO_BYTES if is_video else _MAX_IMAGE_BYTES
        if len(content) > max_bytes:
            limit_mb = max_bytes // (1024 * 1024)
            raise TicketValidationError(f"El archivo supera el límite permitido de {limit_mb} MB.")

    def _check_magic_bytes(self, content: bytes, declared_mime: str) -> None:
        """Validate file magic bytes against the declared MIME type."""
        if declared_mime in {"image/jpeg"}:
            if not content[:3] == b"\xff\xd8\xff":
                raise TicketValidationError("El archivo no es una imagen JPEG válida.")
        elif declared_mime == "image/png":
            if not content[:8] == b"\x89PNG\r\n\x1a\n":
                raise TicketValidationError("El archivo no es una imagen PNG válida.")
        elif declared_mime == "video/mp4":
            # ftyp box at offset 4 — lenient check
            if len(content) > 8 and content[4:8] not in (b"ftyp", b"moov", b"mdat"):
                # Many valid MP4s have mdat first; just check length is sane
                if len(content) < 100:
                    raise TicketValidationError("El archivo MP4 parece inválido o truncado.")
        # For other MIME types, rely on extension/content-type validation above.

    def _resolve_file_suffix(self, upload: UploadFile) -> str:
        if upload.filename and "." in upload.filename:
            ext = upload.filename.lower().rsplit(".", 1)[1]
            if ext in _ALLOWED_EXTENSIONS:
                return f".{ext}"
        mime = (upload.content_type or "").lower()
        defaults = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/quicktime": ".mov",
        }
        return defaults.get(mime, ".bin")

    def _normalize_customer_field(self, value: str, field_label: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise TicketValidationError(f"Debes indicar {field_label} del cliente para responder la encuesta.")
        if len(normalized) > 255:
            raise TicketValidationError(f"El campo {field_label} supera el máximo permitido de 255 caracteres.")
        return normalized

    def _build_public_media_path(self, file_name: str, *, is_video: bool) -> str:
        base = "/videos/satisfaction" if is_video else "/images/satisfaction"
        return f"{base}/{file_name}"
