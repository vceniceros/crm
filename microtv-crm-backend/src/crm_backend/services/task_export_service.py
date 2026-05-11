"""Task export service: ZIP + PDF report for task development."""

from __future__ import annotations

import io
import logging
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from crm_backend.core.exceptions import TaskAccessDeniedError
from crm_backend.models import Task, TaskAttachmentType, TaskCommentType, TaskStatus

if TYPE_CHECKING:
    from crm_backend.services.auth_service import ResolvedCrmSession

_logger = logging.getLogger(__name__)


def _safe_str(value: object, fallback: str = "-") -> str:
    if value is None:
        return fallback
    normalized = str(value).strip()
    return normalized or fallback


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "-"
    try:
        return value.astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


def _sanitize_zip_name(name: str) -> str:
    return re.sub(r"[^\w.\-]", "_", name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])[:200] or "file"


class TaskExportService:
    """Build a ZIP archive containing a PDF report and task media files."""

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

    def export_development_zip(self, actor: "ResolvedCrmSession", task: Task) -> bytes:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("Solo admin o ejecutivo pueden exportar el desarrollo de un pedido.")
        if task.status != TaskStatus.COMPLETED.value:
            raise TaskAccessDeniedError("Solo se puede exportar historial de pedidos completados.")

        zip_buffer = io.BytesIO()
        task_label = _safe_str(task.task_id, "sin_id")
        comments = sorted(task.comments or [], key=lambda c: c.created_at or datetime.min)
        comment_order = {
            comment.task_comment_id: index + 1
            for index, comment in enumerate(comments)
            if comment.task_comment_id
        }
        media_name_counter: dict[str, int] = {}

        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            pdf_bytes = self._build_pdf(task)
            zf.writestr(f"pedido_{task_label}.pdf", pdf_bytes)

            for attachment in self._iter_task_attachments(task):
                file_path = self._resolve_attachment_path(attachment)
                if file_path is None:
                    continue
                if not self._is_safe_path(file_path) or not file_path.is_file():
                    continue

                base_name = _sanitize_zip_name(file_path.name)
                comment_index = comment_order.get(attachment.task_comment_id or "", 0)
                prefixed_name = f"comentario_{comment_index}_{base_name}" if comment_index > 0 else base_name

                normalized_key = prefixed_name.lower()
                media_name_counter[normalized_key] = media_name_counter.get(normalized_key, 0) + 1
                if media_name_counter[normalized_key] > 1:
                    stem, suffix = os.path.splitext(prefixed_name)
                    safe_name = f"{stem}_{media_name_counter[normalized_key]}{suffix}"
                else:
                    safe_name = prefixed_name

                try:
                    zf.write(str(file_path), arcname=f"media/{safe_name}")
                except Exception as exc:
                    _logger.warning("Could not embed attachment %s: %s", file_path, exc)

        return zip_buffer.getvalue()

    def _iter_task_attachments(self, task: Task):
        for comment in task.comments or []:
            for attachment in comment.attachments or []:
                yield attachment

    def _build_pdf(self, task: Task) -> bytes:  # noqa: PLR0912
        try:
            from reportlab.lib import colors  # type: ignore[import-untyped]
            from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
            from reportlab.lib.units import cm  # type: ignore[import-untyped]
            from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("Para exportar pedidos es necesario instalar 'reportlab'.") from exc

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

        location_label = "-"
        if task.location is not None:
            location_label = _safe_str(
                getattr(task.location, "address_label", None)
                or getattr(task.location, "formatted_address", None)
                or f"{getattr(task.location, 'latitude', '-')}, {getattr(task.location, 'longitude', '-')}"
            )

        story = [
            Paragraph(f"Historial del Pedido {_safe_str(task.task_title)}", h1),
            Spacer(1, 0.3 * cm),
            HRFlowable(width="100%", thickness=1, color=colors.grey),
            Spacer(1, 0.4 * cm),
        ]

        header_data = [
            ["ID", _safe_str(task.task_id), "Estado", _safe_str(task.status)],
            ["Cliente", _safe_str(task.client_name), "Template", _safe_str(task.template_name)],
            ["Ubicación", location_label, "Creado", _format_dt(task.created_at)],
            ["Finalizado", _format_dt(task.finalized_at), "Finalizó", _safe_str(task.finalized_by_display_name)],
        ]
        table = Table(header_data, colWidths=[3.5 * cm, 7 * cm, 3.5 * cm, 5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                    ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))

        if task.task_description:
            story.append(Paragraph("Descripción", h2))
            story.append(Paragraph(task.task_description.replace("\n", "<br/>"), normal))
            story.append(Spacer(1, 0.3 * cm))

        subtasks = sorted(task.subtasks or [], key=lambda item: item.order_index)
        if subtasks:
            story.append(Paragraph("Timeline de subtareas", h2))
            for subtask in subtasks:
                story.append(
                    Paragraph(
                        f"#{subtask.order_index + 1} - {_safe_str(subtask.subtask_title)} - {_safe_str(subtask.status)}",
                        normal,
                    )
                )
                story.append(
                    Paragraph(
                        f"Responsable: {_safe_str(subtask.assigned_user_display_name)} - Tipo: {_safe_str(subtask.subtask_type)}",
                        small,
                    )
                )
                story.append(Spacer(1, 0.15 * cm))
            story.append(Spacer(1, 0.3 * cm))

        comments = sorted(task.comments or [], key=lambda c: c.created_at or datetime.min)
        if comments:
            type_labels = {
                TaskCommentType.GENERAL.value: "Comentario",
                TaskCommentType.TRANSITION.value: "Transición",
                TaskCommentType.PROGRESS.value: "Progreso",
                TaskCommentType.CLOSURE.value: "Cierre",
                TaskCommentType.ARRIVAL_REGISTRATION.value: "Registro de llegada",
                TaskCommentType.CLOSURE_EVIDENCE.value: "Evidencia de cierre",
            }
            story.append(Paragraph("Comentarios", h2))
            for comment in comments:
                label = type_labels.get(comment.comment_type or "", "Comentario")
                location = _safe_str(getattr(comment.location, "formatted_address", None) or getattr(comment.location, "address_label", None), "Sin ubicación")
                story.append(
                    Paragraph(
                        f"[{label}] {_safe_str(comment.author_display_name)} - {_format_dt(comment.created_at)} - {location}",
                        small,
                    )
                )
                story.append(Paragraph(_safe_str(comment.body), normal))
                for attachment in comment.attachments or []:
                    attachment_name = _safe_str(getattr(attachment, "file_name", None))
                    story.append(Paragraph(f"Adjunto: {attachment_name}", small))
                story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("Encuesta de satisfacción", h2))
        latest_form = (task.satisfaction_forms or [None])[0]
        if latest_form is None or latest_form.response is None:
            story.append(Paragraph("Sin respuesta registrada.", small))
        else:
            response = latest_form.response
            story.append(Paragraph(f"Puntuación: {response.rating:.1f} / 5", normal))
            story.append(Paragraph(f"Cliente: {_safe_str(response.customer_name)} - {_safe_str(response.customer_company)}", normal))
            if response.comment:
                story.append(Paragraph(f"Comentario: {response.comment}", normal))
            story.append(Paragraph(f"Enviado: {_format_dt(response.submitted_at)}", small))

        doc.build(story)
        return buffer.getvalue()

    def _is_safe_path(self, path: Path) -> bool:
        resolved = path.resolve()
        for root in self._allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _resolve_attachment_path(self, attachment) -> Path | None:
        file_url = getattr(attachment, "file_url", None)
        if isinstance(file_url, str) and file_url.strip():
            return self._resolve_public_or_relative_path(file_url)
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
