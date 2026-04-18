"""Repository for task execution aggregates."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from crm_backend.models import (
    InventoryDispatch,
    InventoryDispatchItem,
    InventoryRequest,
    InventoryRequestItem,
    Subtask,
    SubtaskAssignment,
    SubtaskChecklistProgress,
    SubtaskItemValue,
    SubtaskTransition,
    Task,
    TaskAttachment,
    TaskAuditEvent,
    TaskComment,
    TaskRequiredMaterial,
)


class TaskRepository:
    """Persist and query tasks and subtasks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def save(self, task: Task) -> Task:
        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        return self.get_task_detail(task.task_id) or task

    def _summary_options(self):
        return (selectinload(Task.subtasks),)

    def _detail_options(self):
        return (
            selectinload(Task.subtasks).selectinload(Subtask.items).selectinload(SubtaskItemValue.progress),
            selectinload(Task.subtasks).selectinload(Subtask.assignments),
            selectinload(Task.subtasks).selectinload(Subtask.transitions),
            selectinload(Task.comments).selectinload(TaskComment.attachments),
            selectinload(Task.audit_events),
            selectinload(Task.required_materials).selectinload(TaskRequiredMaterial.product),
            selectinload(Task.inventory_requests).selectinload(InventoryRequest.items).selectinload(InventoryRequestItem.product),
            selectinload(Task.inventory_requests).selectinload(InventoryRequest.dispatches).selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product),
            selectinload(Task.dispatches).selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product),
        )

    def get_task_detail(self, task_id: str) -> Task | None:
        statement = (
            select(Task)
            .options(*self._detail_options())
            .where(Task.task_id == task_id)
        )
        return self._session.scalar(statement)

    def get_subtask_detail(self, subtask_id: str) -> Subtask | None:
        statement = (
            select(Subtask)
            .options(selectinload(Subtask.task).options(*self._detail_options()))
            .where(Subtask.subtask_id == subtask_id)
        )
        return self._session.scalar(statement)

    def get_attachment(self, attachment_id: str) -> TaskAttachment | None:
        return self._session.get(TaskAttachment, attachment_id)

    def list_tasks_assigned_to_user(self, crm_user_id: str) -> list[Task]:
        statement = (
            select(Task)
            .options(*self._summary_options())
            .where(
                or_(
                    Task.current_assigned_crm_user_id == crm_user_id,
                    Task.task_id.in_(
                        select(Subtask.task_id).where(Subtask.current_assigned_crm_user_id == crm_user_id)
                    ),
                )
            )
            .order_by(Task.updated_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def list_tracking_tasks_for_roles(self, role_keys: list[str]) -> list[Task]:
        statement = (
            select(Task)
            .options(*self._summary_options())
            .join(Subtask, Subtask.task_id == Task.task_id)
            .where(Subtask.responsible_role_key.in_(role_keys))
            .order_by(Task.updated_at.desc())
        )
        return list(self._session.scalars(statement).unique().all())

    def list_all_tasks(self) -> list[Task]:
        statement = select(Task).options(*self._summary_options()).order_by(Task.updated_at.desc())
        return list(self._session.scalars(statement).all())

    def list_unassigned_subtasks_for_roles(self, role_keys: list[str]) -> list[Subtask]:
        statement = (
            select(Subtask)
            .options(selectinload(Subtask.task))
            .where(
                Subtask.status == "pending_assignment",
                Subtask.current_assigned_crm_user_id.is_(None),
                Subtask.responsible_role_key.in_(role_keys),
            )
            .order_by(Subtask.created_at.asc(), Subtask.order_index.asc())
        )
        return list(self._session.scalars(statement).all())