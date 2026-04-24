"""Application service for CRM settings module."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from crm_backend.core.exceptions import ApplicationError
from crm_backend.models import (
    CrmCategory,
    CrmPriority,
    CrmRole,
    CrmStatus,
    CrmUser,
    CrmUserRole,
    NotificationRule,
    SlaRule,
    TaskTemplate,
)
from crm_backend.schemas.settings import (
    SettingsCategoryWriteRequest,
    SettingsNotificationRuleWriteRequest,
    SettingsPriorityWriteRequest,
    SettingsRoleUpdateRequest,
    SettingsSlaRuleWriteRequest,
    SettingsStatusWriteRequest,
    SettingsTaskTemplateUpdateRequest,
)
from crm_backend.services.auth_service import ResolvedCrmSession


class SettingsService:
    """Coordinates CRUD operations for configurable CRM settings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_roles(self, actor: ResolvedCrmSession) -> list[CrmRole]:
        self._ensure_admin_or_executive(actor)
        return list(self._session.scalars(select(CrmRole).order_by(CrmRole.role_label.asc(), CrmRole.role_key.asc())).all())

    def update_role(self, actor: ResolvedCrmSession, role_id: str, payload: SettingsRoleUpdateRequest) -> CrmRole:
        self._ensure_admin(actor)
        role = self._session.get(CrmRole, role_id)
        if role is None:
            raise ApplicationError("settings_role_not_found", "El rol indicado no existe.", 404)

        role.role_label = payload.role_label.strip()
        role.description = payload.description.strip() if isinstance(payload.description, str) else None
        role.is_active = payload.is_active
        self._log_activity("settings.role.updated", actor.crm_user.crm_user_id, {"role_id": role_id, "role_key": role.role_key})
        self._session.commit()
        self._session.refresh(role)
        return role

    def list_user_role_assignments(self, actor: ResolvedCrmSession) -> list[CrmUser]:
        self._ensure_admin_or_executive(actor)
        return list(
            self._session.scalars(
                select(CrmUser)
                .where(CrmUser.deleted_at.is_(None))
                .where(CrmUser.is_active_in_crm.is_(True))
                .order_by(CrmUser.display_name.asc(), CrmUser.email.asc(), CrmUser.crm_user_id.asc())
            ).all()
        )

    def set_user_roles(self, actor: ResolvedCrmSession, user_id: str, role_keys: list[str]) -> CrmUser:
        self._ensure_admin(actor)
        user = self._session.get(CrmUser, user_id)
        if user is None or user.deleted_at is not None:
            raise ApplicationError("settings_user_not_found", "El usuario indicado no existe.", 404)

        normalized_keys = sorted({key.strip() for key in role_keys if isinstance(key, str) and key.strip()})
        available_roles = list(self._session.scalars(select(CrmRole).where(CrmRole.role_key.in_(normalized_keys))).all()) if normalized_keys else []
        available_role_map = {role.role_key: role for role in available_roles}

        missing = [role_key for role_key in normalized_keys if role_key not in available_role_map]
        if missing:
            raise ApplicationError("settings_role_invalid", f"Roles inválidos: {', '.join(missing)}.", 422)

        user.assigned_roles.clear()
        for role_key in normalized_keys:
            role = available_role_map[role_key]
            user.assigned_roles.append(
                CrmUserRole(
                    crm_user_id=user.crm_user_id,
                    crm_role_id=role.crm_role_id,
                    assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                )
            )

        self._log_activity(
            "settings.updated",
            actor.crm_user.crm_user_id,
            {"target": "user_roles", "user_id": user.crm_user_id, "role_keys": normalized_keys},
        )
        self._session.commit()
        self._session.refresh(user)
        return user

    def list_categories(self, actor: ResolvedCrmSession, category_type: str | None = None) -> list[CrmCategory]:
        self._ensure_admin_or_executive(actor)
        query = select(CrmCategory)
        if category_type:
            query = query.where(CrmCategory.category_type == category_type)
        return list(
            self._session.scalars(
                query.order_by(CrmCategory.category_type.asc(), CrmCategory.name.asc())
            ).all()
        )

    def create_category(self, actor: ResolvedCrmSession, payload: SettingsCategoryWriteRequest) -> CrmCategory:
        self._ensure_admin(actor)
        category = CrmCategory(
            name=payload.name.strip(),
            category_type=payload.category_type.strip().lower(),
            description=payload.description.strip() if isinstance(payload.description, str) else None,
            is_active=payload.is_active,
        )
        self._session.add(category)
        self._log_activity("settings.category.updated", actor.crm_user.crm_user_id, {"action": "create", "name": category.name})
        self._session.commit()
        self._session.refresh(category)
        return category

    def update_category(self, actor: ResolvedCrmSession, category_id: str, payload: SettingsCategoryWriteRequest) -> CrmCategory:
        self._ensure_admin(actor)
        category = self._session.get(CrmCategory, category_id)
        if category is None:
            raise ApplicationError("settings_category_not_found", "La categoría indicada no existe.", 404)

        category.name = payload.name.strip()
        category.category_type = payload.category_type.strip().lower()
        category.description = payload.description.strip() if isinstance(payload.description, str) else None
        category.is_active = payload.is_active
        self._log_activity("settings.category.updated", actor.crm_user.crm_user_id, {"action": "update", "category_id": category_id})
        self._session.commit()
        self._session.refresh(category)
        return category

    def list_priorities(self, actor: ResolvedCrmSession) -> list[CrmPriority]:
        self._ensure_admin_or_executive(actor)
        return list(self._session.scalars(select(CrmPriority).order_by(CrmPriority.order_index.asc(), CrmPriority.code.asc())).all())

    def create_priority(self, actor: ResolvedCrmSession, payload: SettingsPriorityWriteRequest) -> CrmPriority:
        self._ensure_admin(actor)
        priority = CrmPriority(
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            order_index=payload.order_index,
            color=payload.color.strip() if isinstance(payload.color, str) and payload.color.strip() else None,
            is_active=payload.is_active,
        )
        self._session.add(priority)
        self._log_activity("settings.updated", actor.crm_user.crm_user_id, {"target": "priorities", "action": "create", "code": priority.code})
        self._session.commit()
        self._session.refresh(priority)
        return priority

    def update_priority(self, actor: ResolvedCrmSession, priority_id: str, payload: SettingsPriorityWriteRequest) -> CrmPriority:
        self._ensure_admin(actor)
        priority = self._session.get(CrmPriority, priority_id)
        if priority is None:
            raise ApplicationError("settings_priority_not_found", "La prioridad indicada no existe.", 404)

        priority.code = payload.code.strip().upper()
        priority.name = payload.name.strip()
        priority.order_index = payload.order_index
        priority.color = payload.color.strip() if isinstance(payload.color, str) and payload.color.strip() else None
        priority.is_active = payload.is_active
        self._log_activity("settings.updated", actor.crm_user.crm_user_id, {"target": "priorities", "action": "update", "priority_id": priority_id})
        self._session.commit()
        self._session.refresh(priority)
        return priority

    def list_statuses(self, actor: ResolvedCrmSession, entity_type: str | None = None) -> list[CrmStatus]:
        self._ensure_admin_or_executive(actor)
        query = select(CrmStatus)
        if entity_type:
            query = query.where(CrmStatus.entity_type == entity_type)
        return list(self._session.scalars(query.order_by(CrmStatus.entity_type.asc(), CrmStatus.order_index.asc(), CrmStatus.code.asc())).all())

    def create_status(self, actor: ResolvedCrmSession, payload: SettingsStatusWriteRequest) -> CrmStatus:
        self._ensure_admin(actor)
        status_item = CrmStatus(
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            entity_type=payload.entity_type.strip().lower(),
            is_final=payload.is_final,
            order_index=payload.order_index,
            is_active=payload.is_active,
        )
        self._session.add(status_item)
        self._log_activity("settings.updated", actor.crm_user.crm_user_id, {"target": "statuses", "action": "create", "code": status_item.code})
        self._session.commit()
        self._session.refresh(status_item)
        return status_item

    def update_status(self, actor: ResolvedCrmSession, status_id: str, payload: SettingsStatusWriteRequest) -> CrmStatus:
        self._ensure_admin(actor)
        status_item = self._session.get(CrmStatus, status_id)
        if status_item is None:
            raise ApplicationError("settings_status_not_found", "El estado indicado no existe.", 404)

        status_item.code = payload.code.strip().upper()
        status_item.name = payload.name.strip()
        status_item.entity_type = payload.entity_type.strip().lower()
        status_item.is_final = payload.is_final
        status_item.order_index = payload.order_index
        status_item.is_active = payload.is_active
        self._log_activity("settings.updated", actor.crm_user.crm_user_id, {"target": "statuses", "action": "update", "status_id": status_id})
        self._session.commit()
        self._session.refresh(status_item)
        return status_item

    def list_task_templates(self, actor: ResolvedCrmSession) -> list[TaskTemplate]:
        self._ensure_admin_or_executive(actor)
        return list(self._session.scalars(select(TaskTemplate).order_by(TaskTemplate.template_name.asc())).all())

    def update_task_template(self, actor: ResolvedCrmSession, template_id: str, payload: SettingsTaskTemplateUpdateRequest) -> TaskTemplate:
        self._ensure_admin(actor)
        template = self._session.get(TaskTemplate, template_id)
        if template is None:
            raise ApplicationError("settings_template_not_found", "El template indicado no existe.", 404)

        template.template_name = payload.template_name.strip()
        template.description = payload.description.strip() if isinstance(payload.description, str) else None
        template.is_active = payload.is_active
        self._log_activity("settings.template.updated", actor.crm_user.crm_user_id, {"template_id": template_id})
        self._session.commit()
        self._session.refresh(template)
        return template

    def list_sla_rules(self, actor: ResolvedCrmSession) -> list[SlaRule]:
        self._ensure_admin_or_executive(actor)
        return list(self._session.scalars(select(SlaRule).order_by(SlaRule.entity_type.asc(), SlaRule.priority_code.asc())).all())

    def create_sla_rule(self, actor: ResolvedCrmSession, payload: SettingsSlaRuleWriteRequest) -> SlaRule:
        self._ensure_admin(actor)
        rule = SlaRule(
            entity_type=payload.entity_type.strip().lower(),
            priority_code=payload.priority_code.strip().upper(),
            response_time_minutes=payload.response_time_minutes,
            resolution_time_minutes=payload.resolution_time_minutes,
            is_active=payload.is_active,
        )
        self._session.add(rule)
        self._log_activity("settings.sla.updated", actor.crm_user.crm_user_id, {"action": "create", "entity_type": rule.entity_type})
        self._session.commit()
        self._session.refresh(rule)
        return rule

    def update_sla_rule(self, actor: ResolvedCrmSession, rule_id: str, payload: SettingsSlaRuleWriteRequest) -> SlaRule:
        self._ensure_admin(actor)
        rule = self._session.get(SlaRule, rule_id)
        if rule is None:
            raise ApplicationError("settings_sla_not_found", "La regla SLA indicada no existe.", 404)

        rule.entity_type = payload.entity_type.strip().lower()
        rule.priority_code = payload.priority_code.strip().upper()
        rule.response_time_minutes = payload.response_time_minutes
        rule.resolution_time_minutes = payload.resolution_time_minutes
        rule.is_active = payload.is_active
        self._log_activity("settings.sla.updated", actor.crm_user.crm_user_id, {"action": "update", "sla_rule_id": rule_id})
        self._session.commit()
        self._session.refresh(rule)
        return rule

    def list_notification_rules(self, actor: ResolvedCrmSession) -> list[NotificationRule]:
        self._ensure_admin_or_executive(actor)
        return list(self._session.scalars(select(NotificationRule).order_by(NotificationRule.event_code.asc())).all())

    def create_notification_rule(self, actor: ResolvedCrmSession, payload: SettingsNotificationRuleWriteRequest) -> NotificationRule:
        self._ensure_admin(actor)
        rule = NotificationRule(
            event_code=payload.event_code.strip().lower(),
            label=payload.label.strip(),
            notify_assigned=payload.notify_assigned,
            notify_roles_json=sorted({role_key.strip() for role_key in payload.notify_roles_json if role_key.strip()}),
            is_active=payload.is_active,
        )
        self._session.add(rule)
        self._log_activity("settings.updated", actor.crm_user.crm_user_id, {"target": "notifications", "action": "create", "event_code": rule.event_code})
        self._session.commit()
        self._session.refresh(rule)
        return rule

    def update_notification_rule(self, actor: ResolvedCrmSession, rule_id: str, payload: SettingsNotificationRuleWriteRequest) -> NotificationRule:
        self._ensure_admin(actor)
        rule = self._session.get(NotificationRule, rule_id)
        if rule is None:
            raise ApplicationError("settings_notification_rule_not_found", "La regla de notificación indicada no existe.", 404)

        rule.event_code = payload.event_code.strip().lower()
        rule.label = payload.label.strip()
        rule.notify_assigned = payload.notify_assigned
        rule.notify_roles_json = sorted({role_key.strip() for role_key in payload.notify_roles_json if role_key.strip()})
        rule.is_active = payload.is_active
        self._log_activity("settings.updated", actor.crm_user.crm_user_id, {"target": "notifications", "action": "update", "rule_id": rule_id})
        self._session.commit()
        self._session.refresh(rule)
        return rule

    def _ensure_admin_or_executive(self, actor: ResolvedCrmSession) -> None:
        if "admin" in actor.role_keys or "ejecutivo" in actor.role_keys:
            return
        raise ApplicationError("settings_access_denied", "La operación requiere rol administrador o ejecutivo.", 403)

    def _ensure_admin(self, actor: ResolvedCrmSession) -> None:
        if "admin" in actor.role_keys:
            return
        raise ApplicationError("settings_admin_required", "La operación requiere rol administrador.", 403)

    def _log_activity(self, event_code: str, actor_crm_user_id: str, payload: dict[str, object]) -> None:
        bind = self._session.get_bind()
        inspector = inspect(bind)
        if "activity_log" not in set(inspector.get_table_names()):
            return

        columns = {column["name"] for column in inspector.get_columns("activity_log")}
        insert_payload: dict[str, object] = {}

        if "activity_log_id" in columns:
            # Let DB default/trigger generate IDs when available.
            pass
        if "event_code" in columns:
            insert_payload["event_code"] = event_code
        elif "event_type" in columns:
            insert_payload["event_type"] = event_code

        if "actor_crm_user_id" in columns:
            insert_payload["actor_crm_user_id"] = actor_crm_user_id
        if "payload_json" in columns:
            insert_payload["payload_json"] = payload
        elif "payload" in columns:
            insert_payload["payload"] = payload

        if "created_at" in columns:
            insert_payload["created_at"] = datetime.now(UTC)

        if not insert_payload:
            return

        keys = ", ".join(insert_payload.keys())
        params = ", ".join(f":{key}" for key in insert_payload)
        self._session.execute(text(f"INSERT INTO activity_log ({keys}) VALUES ({params})"), insert_payload)
