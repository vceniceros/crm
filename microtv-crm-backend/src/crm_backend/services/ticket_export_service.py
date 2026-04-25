"""Ticket export service: ZIP + PDF report for the full ticket development."""

from __future__ import annotations

import io
import logging
import os
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from crm_backend.core.exceptions import TicketAccessDeniedError, TicketNotFoundError
from crm_backend.models.ticket import (
    Ticket,
    TicketAttachmentType,
    TicketCommentType,
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


class TicketExportService:
    """Build a ZIP archive containing a PDF report and all media for a ticket."""

    def __init__(self, media_base_dir: Path | str) -> None:
        self._media_base_dir = Path(media_base_dir)

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

        zip_buffer = io.BytesIO()
        ticket_number = _safe_str(ticket.ticket_number, "sin_numero")
        folder = f"ticket_{ticket_number}"

        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Build PDF report
            pdf_bytes = self._build_pdf(ticket)
            zf.writestr(f"{folder}/desarrollo_ticket_{ticket_number}.pdf", pdf_bytes)

            # Embed media files that still exist on disk
            media_folder = f"{folder}/multimedia"
            for attachment in ticket.attachments or []:
                if not attachment.file_path:
                    continue
                file_path = Path(attachment.file_path)
                if not self._is_safe_path(file_path) or not file_path.is_file():
                    continue
                safe_name = _sanitize_zip_name(file_path.name)
                try:
                    zf.write(str(file_path), arcname=f"{media_folder}/{safe_name}")
                except Exception as exc:
                    _logger.warning("Could not embed attachment %s: %s", file_path, exc)

        return zip_buffer.getvalue()

    def _is_safe_path(self, path: Path) -> bool:
        """Reject paths outside the media base dir (path traversal guard)."""
        try:
            path.resolve().relative_to(self._media_base_dir.resolve())
            return True
        except ValueError:
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
        story = []

        # Title
        story.append(Paragraph(f"Desarrollo del Ticket #{ticket_number}", h1))
        story.append(Spacer(1, 0.3 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 0.4 * cm))

        # Header info table
        client_name = "—"
        location_name = "—"
        maps_link = None
        if ticket.client:
            client_name = _safe_str(ticket.client.business_name or ticket.client.company_name)
        if ticket.location:
            location_name = _safe_str(ticket.location.address or ticket.location.name)
            lat = getattr(ticket.location, "latitude", None)
            lng = getattr(ticket.location, "longitude", None)
            if lat and lng:
                maps_link = f"https://maps.google.com/?q={lat},{lng}"

        header_data = [
            ["N° Ticket", ticket_number, "Estado", _safe_str(ticket.status)],
            ["Cliente", client_name, "Prioridad", _safe_str(ticket.priority)],
            ["Ubicación", location_name if not maps_link else f"{location_name} ({maps_link})", "Creado", _format_dt(ticket.created_at)],
            ["Título", _safe_str(ticket.title, "Sin título"), "Cerrado", _format_dt(ticket.closed_at)],
        ]
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

        # Timeline: comments
        comments = sorted(ticket.comments or [], key=lambda c: c.created_at or datetime.min)
        if comments:
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Historial de actividad", h2))

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
                        comment.author.full_name
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
                    if attachment.attachment_type == TicketAttachmentType.PHOTO.value:
                        self._embed_image(story, attachment, Image, PILImage, small)
                    else:
                        # Video: reference as text
                        fname = _sanitize_zip_name(Path(attachment.file_path or "").name)
                        story.append(Paragraph(f"📹  Ver archivo: multimedia/{fname}", small))

                story.append(Spacer(1, 0.3 * cm))

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
        attachment,
        Image,  # reportlab Image  # noqa: N803
        PILImage,  # Pillow Image  # noqa: N803
        caption_style,
    ) -> None:
        if not attachment.file_path:
            return
        path = Path(attachment.file_path)
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
            story.append(Paragraph(f"📷 {fname}", caption_style))

        except Exception as exc:
            _logger.warning("Could not embed image %s: %s", path, exc)
            fname = _sanitize_zip_name(path.name)
            story.append(Paragraph(f"[Imagen no disponible: {fname}]", caption_style))
