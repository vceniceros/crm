"""Ticket export service: ZIP + PDF report for the full ticket development."""

from __future__ import annotations

import io
import logging
import os
import re
import zipfile
from datetime import UTC, datetime
from html import escape as html_escape
from pathlib import Path
from typing import TYPE_CHECKING

from crm_backend.core.exceptions import TicketAccessDeniedError
from crm_backend.models.ticket import (
    Ticket,
    TicketAttachmentType,
    TicketCommentType,
    TicketStatus,
)

if TYPE_CHECKING:
    from crm_backend.services.auth_service import ResolvedCrmSession

_logger = logging.getLogger(__name__)


def _safe_str(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _format_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    try:
        local = dt.astimezone()
        return local.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


def _sanitize_zip_name(name: str) -> str:
    """Prevent path traversal in ZIP entries."""
    return re.sub(r"[^\w.\-]", "_", name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])[:200] or "file"


def _survey_status_for_pdf(ticket: Ticket) -> str:
    if getattr(ticket, "survey_completed_at", None):
        return "Respondida"
    if getattr(ticket, "survey_generated_at", None):
        return "Generada - pendiente de respuesta"

    raw_status = (_safe_str(getattr(ticket, "survey_status_label", None), "")).lower()
    if raw_status == "respondido":
        return "Respondida"
    if raw_status in {"pendiente", "expirado", "revocado"}:
        return "Generada - pendiente de respuesta"
    return "Sin encuesta"


class TicketExportService:
    """Build a ZIP archive containing a PDF report and all media for a ticket."""

    def __init__(
        self,
        *,
        media_root_dir: Path | str,
        media_public_url: str = "/media",
        legacy_public_dir: Path | str | None = None,
    ) -> None:
        self._media_root_dir = Path(media_root_dir).resolve()
        self._media_public_url = media_public_url.rstrip("/") or "/media"
        self._legacy_public_dir = Path(legacy_public_dir).resolve() if legacy_public_dir is not None else None

        self._allowed_roots: list[Path] = [self._media_root_dir]
        if self._legacy_public_dir is not None:
            self._allowed_roots.append(self._legacy_public_dir)

    def export_development_zip(
        self,
        actor: "ResolvedCrmSession",
        ticket: Ticket,
    ) -> bytes:
        """Return the raw ZIP bytes for streaming download.

        Access: admin or ejecutivo only.
        """
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TicketAccessDeniedError("Solo admin o ejecutivo pueden exportar el desarrollo de un ticket.")
        if ticket.status != TicketStatus.CLOSED.value:
            raise TicketAccessDeniedError(
                "Solo se puede exportar historial de tickets cerrados."
            )

        zip_buffer = io.BytesIO()
        ticket_number = _safe_str(ticket.ticket_number, "sin_numero")
        comments = sorted(ticket.comments or [], key=lambda c: c.created_at or datetime.min)
        comment_order = {
            comment.ticket_comment_id: index + 1
            for index, comment in enumerate(comments)
            if comment.ticket_comment_id
        }
        media_name_counter: dict[str, int] = {}

        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Build PDF report
            pdf_bytes = self._build_pdf(ticket)
            zf.writestr(f"ticket_{ticket_number}.pdf", pdf_bytes)

            # Embed media files that still exist on disk
            media_folder = "media"
            for attachment in ticket.attachments or []:
                file_path = self._resolve_attachment_path(attachment)
                if file_path is None:
                    continue
                if not self._is_safe_path(file_path) or not file_path.is_file():
                    continue
                base_name = _sanitize_zip_name(file_path.name)
                comment_index = comment_order.get(attachment.ticket_comment_id or "", 0)
                prefixed_name = f"comentario_{comment_index}_{base_name}" if comment_index > 0 else base_name

                normalized_key = prefixed_name.lower()
                media_name_counter[normalized_key] = media_name_counter.get(normalized_key, 0) + 1
                if media_name_counter[normalized_key] > 1:
                    stem, suffix = os.path.splitext(prefixed_name)
                    safe_name = f"{stem}_{media_name_counter[normalized_key]}{suffix}"
                else:
                    safe_name = prefixed_name
                try:
                    zf.write(str(file_path), arcname=f"{media_folder}/{safe_name}")
                except Exception as exc:
                    _logger.warning("Could not embed attachment %s: %s", file_path, exc)

        return zip_buffer.getvalue()

    def _is_safe_path(self, path: Path) -> bool:
        """Reject paths outside the media base dir (path traversal guard)."""
        resolved = path.resolve()
        for root in self._allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    # ------------------------------------------------------------------
    # PDF builder
    # ------------------------------------------------------------------

    def _build_pdf(self, ticket: Ticket) -> bytes:  # noqa: PLR0912, PLR0915
        """Build a PDF report with reportlab and return raw bytes."""
        try:
            from reportlab.lib import colors  # type: ignore[import-untyped]
            from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
            from reportlab.lib.units import cm  # type: ignore[import-untyped]
            from reportlab.platypus import (  # type: ignore[import-untyped]
                HRFlowable,
                Image,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
            from PIL import Image as PILImage  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "Para exportar el desarrollo del ticket es necesario instalar 'reportlab' y 'Pillow'."
            ) from exc

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        h1 = styles["h1"]
        h2 = ParagraphStyle("h2", parent=styles["h2"], spaceAfter=4)
        normal = styles["Normal"]
        small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=colors.grey)
        code_style = ParagraphStyle("code", parent=normal, fontName="Courier", fontSize=9, backColor=colors.whitesmoke)

        ticket_number = _safe_str(ticket.ticket_number)
        asset_links = sorted(getattr(ticket, "asset_links", []) or [], key=lambda item: item.linked_at or datetime.min)
        story = []

        def pdf_text(value: object, fallback: str = "-"):
            text = html_escape(_safe_str(value, fallback)).replace("\n", "<br/>")
            return Paragraph(text, normal)

        def user_display_name(user: object | None) -> str:
            if user is None:
                return "-"
            return _safe_str(
                getattr(user, "display_name", None)
                or getattr(user, "email", None)
                or f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
            )

        # Title
        story.append(Paragraph(f"Historial del Ticket #{ticket_number}", h1))
        story.append(Spacer(1, 0.3 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 0.4 * cm))

        # Header info table
        client_name = "—"
        location_name = "—"
        maps_link = None
        if ticket.client:
            client_name = _safe_str(
                getattr(ticket.client, "business_name", None) or getattr(ticket.client, "company_name", None)
            )
        if ticket.location:
            location_name = _safe_str(
                getattr(ticket.location, "address_label", None)
                or getattr(ticket.location, "formatted_address", None)
                or getattr(ticket.location, "name", None)
                or getattr(ticket.location, "address", None)
            )
            lat = getattr(ticket.location, "latitude", None)
            lng = getattr(ticket.location, "longitude", None)
            if lat is not None and lng is not None:
                maps_link = f"https://maps.google.com/?q={lat},{lng}"

        location_cell = location_name
        if maps_link:
            location_cell = Paragraph(f'<link href="{maps_link}">{maps_link}</link>', normal)

        header_data = [
            ["N° Ticket", ticket_number, "Estado", _safe_str(ticket.status)],
            ["Cliente", client_name, "Prioridad", _safe_str(ticket.priority)],
            ["Ubicación", location_cell, "Creado", _format_dt(ticket.created_at)],
            ["Título", _safe_str(ticket.title, "Sin título"), "Cerrado", _format_dt(ticket.closed_at)],
            ["Aprobación", "Cerrado y aprobado" if ticket.approved_by_executive else "Sin aprobación ejecutiva", "Encuesta", _survey_status_for_pdf(ticket)],
        ]
        header_data.append(
            [
                "Activos manipulados",
                f"{len(asset_links)} activo(s) vinculado(s)",
                "Detalle",
                "Ver seccion de activos" if asset_links else "Sin activos",
            ]
        )
        col_widths = [3.5 * cm, 7 * cm, 3.5 * cm, 5 * cm]
        tbl = Table(header_data, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8f8f8")]),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5 * cm))

        # Description
        if ticket.description:
            story.append(Paragraph("Descripción del problema", h2))
            story.append(Paragraph(ticket.description.replace("\n", "<br/>"), normal))
            story.append(Spacer(1, 0.4 * cm))

        if asset_links:
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Activos manipulados", h2))

            for link in asset_links:
                asset = getattr(link, "asset", None)
                if asset is None:
                    continue

                linked_by = user_display_name(getattr(link, "linked_by_user", None))
                asset_rows = [
                    ["Activo", pdf_text(getattr(asset, "asset_name", None))],
                    ["Categoria", pdf_text(getattr(asset, "category_name", None))],
                    ["Cliente", pdf_text(getattr(asset, "client_name", None))],
                    ["Vinculado a", pdf_text(getattr(asset, "parent_asset_name", None))],
                    ["Fecha de vinculacion", pdf_text(_format_dt(getattr(link, "linked_at", None)))],
                    ["Vinculado por", pdf_text(linked_by)],
                ]

                field_values = sorted(
                    getattr(asset, "field_values", []) or [],
                    key=lambda item: _safe_str(getattr(item, "field_name", None), ""),
                )
                for field_value in field_values:
                    asset_rows.append([
                        _safe_str(getattr(field_value, "field_name", None), "Campo"),
                        pdf_text(getattr(field_value, "raw_value", None)),
                    ])

                if getattr(asset, "notes", None):
                    asset_rows.append(["Notas", pdf_text(getattr(asset, "notes", None))])

                asset_tbl = Table(asset_rows, colWidths=[4.5 * cm, 14.5 * cm])
                asset_tbl.setStyle(TableStyle([
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8f8f8")]),
                ]))
                story.append(asset_tbl)
                story.append(Spacer(1, 0.35 * cm))

        # Timeline: comments
        comments = sorted(ticket.comments or [], key=lambda c: c.created_at or datetime.min)
        if comments:
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Historial de actividad (comentarios)", h2))

            type_labels = {
                TicketCommentType.GENERAL.value: "Comentario",
                TicketCommentType.SYSTEM.value: "Sistema",
                TicketCommentType.CLOSURE.value: "Cierre",
                TicketCommentType.ARRIVAL_REGISTRATION.value: "Llegada al sitio",
                TicketCommentType.CLOSURE_EVIDENCE.value: "Evidencia de cierre",
            }

            for comment in comments:
                label = type_labels.get(comment.comment_type or "", "Comentario")
                author = "—"
                if comment.author:
                    author = _safe_str(
                        getattr(comment.author, "display_name", None)
                        or getattr(comment.author, "email", None)
                        or f"{getattr(comment.author, 'first_name', '')} {getattr(comment.author, 'last_name', '')}".strip()
                    )
                ts = _format_dt(comment.created_at)

                meta = f"<b>[{label}]</b>  {author}  ·  {ts}"
                story.append(Paragraph(meta, small))

                if comment.body:
                    story.append(Paragraph(comment.body.replace("\n", "<br/>"), normal))

                # Attachments for this comment
                comment_attachments = [
                    a for a in (ticket.attachments or [])
                    if a.ticket_comment_id == comment.ticket_comment_id
                ]
                for attachment in comment_attachments:
                    attachment_path = self._resolve_attachment_path(attachment)
                    if attachment_path is None:
                        continue
                    if attachment.attachment_type == TicketAttachmentType.PHOTO.value:
                        self._embed_image(story, attachment_path, Image, PILImage, Paragraph, small)
                    else:
                        # Video/document: reference as text
                        fname = _sanitize_zip_name(attachment_path.name)
                        story.append(Paragraph(f"Ver archivo: media/{fname}", small))

                story.append(Spacer(1, 0.3 * cm))

        # Timeline: status transitions
        transitions = sorted(ticket.status_history or [], key=lambda item: item.created_at or datetime.min)
        if transitions:
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Historial de estados", h2))
            for transition in transitions:
                performer = _safe_str(transition.performed_by_display_name, "Sistema")
                title = f"{_format_dt(transition.created_at)} · {performer} · {transition.action}"
                change = f"{transition.from_status} -> {transition.to_status}"
                story.append(Paragraph(title, small))
                story.append(Paragraph(change, normal))
                story.append(Spacer(1, 0.18 * cm))

        # Timeline: inventory requests (solicitudes a deposito)
        requests = sorted(ticket.inventory_requests or [], key=lambda item: item.requested_at or datetime.min)
        if requests:
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Solicitudes a depósito", h2))
            for request in requests:
                requester = _safe_str(getattr(request, "requested_by_display_name", None), "Usuario")
                requested_at = _format_dt(getattr(request, "requested_at", None))
                status = _safe_str(getattr(request, "request_status", None))
                item_count = len(getattr(request, "items", []) or [])
                story.append(Paragraph(f"{requested_at} · {requester}", small))
                story.append(Paragraph(f"{item_count} item(s) · Estado: {status}", normal))
                story.append(Spacer(1, 0.18 * cm))

        # Closure and approval summary
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Cierre y aprobación", h2))
        story.append(Paragraph(f"Cerrado: {_format_dt(ticket.closed_at)}", normal))
        story.append(
            Paragraph(
                "Aprobado por ejecutivo: Sí" if ticket.approved_by_executive else "Aprobado por ejecutivo: No",
                normal,
            )
        )

        # Satisfaction response
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Encuesta de satisfacción", h2))

        sat_response = None
        for form in getattr(ticket, "satisfaction_forms", []) or []:
            if form.response is not None:
                sat_response = form.response
                break

        if sat_response is None:
            story.append(Paragraph("Sin respuesta registrada.", small))
        else:
            rating_stars = "★" * round(sat_response.rating) + "☆" * (5 - round(sat_response.rating))
            story.append(Paragraph(f"Puntuación: {sat_response.rating:.1f} / 5  {rating_stars}", normal))
            if sat_response.comment:
                story.append(Paragraph(f"Comentario: {sat_response.comment}", normal))
            story.append(Paragraph(f"Enviado: {_format_dt(sat_response.submitted_at)}", small))

        doc.build(story)
        return buffer.getvalue()

    def _embed_image(
        self,
        story: list,
        image_path: Path,
        Image,  # reportlab Image  # noqa: N803
        PILImage,  # Pillow Image  # noqa: N803
        Paragraph,
        caption_style,
    ) -> None:
        path = image_path
        if not path.is_file():
            return
        try:
            from reportlab.lib.units import cm  # noqa: PLC0415
            from io import BytesIO  # noqa: PLC0415

            MAX_WIDTH_CM = 14  # noqa: N806
            max_width_pt = MAX_WIDTH_CM * cm

            with PILImage.open(str(path)) as pil_img:
                # Convert to RGB if needed (e.g. PNG with alpha)
                if pil_img.mode not in ("RGB", "L"):
                    pil_img = pil_img.convert("RGB")

                orig_w, orig_h = pil_img.size
                if orig_w > 1200:
                    scale = 1200 / orig_w
                    new_w = int(orig_w * scale)
                    new_h = int(orig_h * scale)
                    pil_img = pil_img.resize((new_w, new_h), PILImage.LANCZOS)

                img_buffer = BytesIO()
                pil_img.save(img_buffer, format="JPEG", quality=80)
                img_buffer.seek(0)

                # Calculate display dimensions
                w, h = pil_img.size
                aspect = h / w
                display_w = min(max_width_pt, w)
                display_h = display_w * aspect

            img_obj = Image(img_buffer, width=display_w, height=display_h)
            story.append(img_obj)
            fname = _sanitize_zip_name(path.name)
            story.append(Paragraph(f"Imagen: {fname}", caption_style))

        except Exception as exc:
            _logger.warning("Could not embed image %s: %s", path, exc)
            fname = _sanitize_zip_name(path.name)
            story.append(Paragraph(f"[Imagen no disponible: {fname}]", caption_style))

    def _resolve_attachment_path(self, attachment) -> Path | None:
        """Resolve attachment to a local file path using persisted URL/storage metadata."""
        file_path = getattr(attachment, "file_path", None)
        if isinstance(file_path, str) and file_path.strip():
            return Path(file_path)

        storage_path = getattr(attachment, "storagePath", None)
        if isinstance(storage_path, str) and storage_path.strip():
            candidate = Path(storage_path)
            if candidate.is_absolute():
                return candidate
            resolved_from_storage = self._resolve_public_or_relative_path(storage_path)
            if resolved_from_storage is not None:
                return resolved_from_storage

        file_url = getattr(attachment, "file_url", None)
        if isinstance(file_url, str) and file_url.strip():
            resolved_from_url = self._resolve_public_or_relative_path(file_url)
            if resolved_from_url is not None:
                return resolved_from_url

        return None

    def _resolve_public_or_relative_path(self, raw_path: str) -> Path | None:
        normalized = (raw_path or "").strip().replace("\\", "/")
        if not normalized:
            return None

        lower = normalized.lower()
        if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("data:") or lower.startswith("blob:"):
            return None

        media_prefix = f"{self._media_public_url}/"
        if normalized.startswith(media_prefix):
            return self._safe_join(self._media_root_dir, normalized[len(media_prefix) :])

        compact_media_prefix = f"{self._media_public_url.lstrip('/')}/"
        if normalized.startswith(compact_media_prefix):
            return self._safe_join(self._media_root_dir, normalized[len(compact_media_prefix) :])

        if self._legacy_public_dir is not None:
            if normalized.startswith("/images/") or normalized.startswith("/videos/"):
                return self._safe_join(self._legacy_public_dir, normalized.lstrip("/"))
            if normalized.startswith("images/") or normalized.startswith("videos/"):
                return self._safe_join(self._legacy_public_dir, normalized)
            if normalized.startswith("/public/"):
                return self._safe_join(self._legacy_public_dir, normalized[len("/public/") :])
            if normalized.startswith("public/"):
                return self._safe_join(self._legacy_public_dir, normalized[len("public/") :])

        if normalized.startswith("/"):
            return None

        return self._safe_join(self._media_root_dir, normalized)

    def _safe_join(self, root: Path, relative_path: str) -> Path | None:
        candidate = (root / relative_path.lstrip("/")).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate
