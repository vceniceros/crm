"""Repository for task templates."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from crm_backend.models import TaskTemplate, TaskTemplateItem, TaskTemplatePreForm, TaskTemplateSubtask, TemplateMaterial


class TaskTemplateRepository:
    """Persist and query task templates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *, include_inactive: bool = False) -> list[TaskTemplate]:
        statement = select(TaskTemplate).options(
            selectinload(TaskTemplate.subtasks).selectinload(TaskTemplateSubtask.items),
            selectinload(TaskTemplate.required_materials).selectinload(TemplateMaterial.product),
            selectinload(TaskTemplate.pre_form).selectinload(TaskTemplatePreForm.fields),
        )
        if not include_inactive:
            statement = statement.where(TaskTemplate.is_active.is_(True))
        statement = statement.order_by(TaskTemplate.created_at.desc())
        return list(self._session.scalars(statement).all())

    def get_by_id(self, template_id: str) -> TaskTemplate | None:
        statement = (
            select(TaskTemplate)
            .options(
                selectinload(TaskTemplate.subtasks).selectinload(TaskTemplateSubtask.items),
                selectinload(TaskTemplate.required_materials).selectinload(TemplateMaterial.product),
                selectinload(TaskTemplate.pre_form).selectinload(TaskTemplatePreForm.fields),
            )
            .where(TaskTemplate.template_id == template_id)
        )
        return self._session.scalar(statement)

    def save(self, template: TaskTemplate) -> TaskTemplate:
        self._session.add(template)
        self._session.commit()
        self._session.refresh(template)
        return self.get_by_id(template.template_id) or template