"""Dashboard service tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from crm_backend.models import (
    Client,
    CrmRole,
    CrmUser,
    CrmUserRole,
    Location,
    Subtask,
    Task,
    TaskComment,
    TaskCommentMention,
    TaskStatus,
    TaskTemplate,
    TaskTemplateSubtask,
    Ticket,
    TicketCollaborator,
    TicketComment,
    TicketCommentMention,
    TicketPriority,
    TicketStatus,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.dashboard_service import DashboardService


def _seed_user(db_session, *, role_key: str, auth_user_id: str, display_name: str) -> CrmUser:
    role = db_session.scalar(select(CrmRole).where(CrmRole.role_key == role_key))
    assert role is not None
    user = CrmUser(auth_user_id=auth_user_id, email=f"{auth_user_id}@example.test", display_name=display_name)
    user.assigned_roles.append(CrmUserRole(crm_role_id=role.crm_role_id, role=role))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _actor(user: CrmUser, role_keys: list[str]) -> ResolvedCrmSession:
    return ResolvedCrmSession(crm_user=user, primary_role=role_keys[0], role_keys=role_keys, auth_result=None)  # type: ignore[arg-type]


def _seed_base_entities(db_session, admin_user: CrmUser) -> tuple[Client, Location, TaskTemplate, TaskTemplateSubtask]:
    client = Client(business_name="Cliente Dashboard SA", tax_id="30-00000000-1", email="ops@example.test")
    location = Location(latitude=-34.6, longitude=-58.4, address_label="Base", formatted_address="Base")
    template = TaskTemplate(template_name="Pedido operativo", description="Template", created_by_crm_user_id=admin_user.crm_user_id)
    template_subtask = TaskTemplateSubtask(
        subtask_title="Ejecución",
        order_index=0,
        responsible_role_key="tecnico",
        template=template,
    )
    db_session.add_all([client, location, template, template_subtask])
    db_session.commit()
    return client, location, template, template_subtask


def _ticket(
    db_session,
    *,
    client: Client,
    location: Location,
    creator: CrmUser,
    title: str,
    number: str,
    status: str,
    assigned_user: CrmUser | None = None,
    assigned_role_id: str | None = None,
    priority: str = TicketPriority.MEDIUM.value,
    updated_at: datetime | None = None,
) -> Ticket:
    ticket = Ticket(
        ticket_number=number,
        title=title,
        description=title,
        client_id=client.client_id,
        location_id=location.location_id,
        status=status,
        priority=priority,
        assigned_user_id=assigned_user.crm_user_id if assigned_user else None,
        assigned_role_id=assigned_role_id,
        created_by_crm_user_id=creator.crm_user_id,
        updated_at=updated_at or datetime.now(UTC),
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


def _task(
    db_session,
    *,
    client: Client,
    location: Location,
    template: TaskTemplate,
    template_subtask: TaskTemplateSubtask,
    creator: CrmUser,
    title: str,
    status: str,
    assigned_user: CrmUser | None = None,
    subtask_user: CrmUser | None = None,
    priority: str = "MEDIA",
    updated_at: datetime | None = None,
) -> Task:
    task = Task(
        client_id=client.client_id,
        location_id=location.location_id,
        template_id=template.template_id,
        task_title=title,
        task_description=title,
        status=status,
        priority=priority,
        current_assigned_crm_user_id=assigned_user.crm_user_id if assigned_user else None,
        created_by_crm_user_id=creator.crm_user_id,
        updated_at=updated_at or datetime.now(UTC),
    )
    task.subtasks.append(
        Subtask(
            template_subtask_id=template_subtask.template_subtask_id,
            subtask_title="Ejecución",
            order_index=0,
            responsible_role_key="tecnico",
            status="assigned",
            current_assigned_crm_user_id=subtask_user.crm_user_id if subtask_user else None,
        )
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_pending_menu_for_technician_uses_direct_collaborator_and_mentions_only(db_session) -> None:
    admin = _seed_user(db_session, role_key="admin_crm", auth_user_id="auth-admin", display_name="Admin")
    tech = _seed_user(db_session, role_key="tecnico_campo", auth_user_id="auth-tech", display_name="Técnico")
    other = _seed_user(db_session, role_key="tecnico_campo", auth_user_id="auth-other", display_name="Otro técnico")
    client, location, template, template_subtask = _seed_base_entities(db_session, admin)
    tech_role_id = tech.assigned_roles[0].crm_role_id
    now = datetime.now(UTC)

    assigned_ticket = _ticket(
        db_session,
        client=client,
        location=location,
        creator=admin,
        title="Ticket asignado",
        number="TCK-1",
        status=TicketStatus.IN_PROGRESS.value,
        assigned_user=tech,
        priority=TicketPriority.HIGH.value,
        updated_at=now,
    )
    collaborator_ticket = _ticket(
        db_session,
        client=client,
        location=location,
        creator=admin,
        title="Ticket colaborado",
        number="TCK-2",
        status=TicketStatus.OPEN.value,
        assigned_user=other,
        updated_at=now - timedelta(minutes=1),
    )
    collaborator_ticket.collaborators.append(TicketCollaborator(crm_user_id=tech.crm_user_id, source="manual"))
    mentioned_ticket = _ticket(
        db_session,
        client=client,
        location=location,
        creator=admin,
        title="Ticket mencionado",
        number="TCK-3",
        status=TicketStatus.ON_HOLD.value,
        assigned_user=other,
        updated_at=now - timedelta(minutes=2),
    )
    comment = TicketComment(ticket_id=mentioned_ticket.ticket_id, author_crm_user_id=other.crm_user_id, body="@tech")
    comment.mentions.append(TicketCommentMention(mentioned_crm_user_id=tech.crm_user_id, created_by_crm_user_id=other.crm_user_id))
    role_queue_ticket = _ticket(
        db_session,
        client=client,
        location=location,
        creator=admin,
        title="Ticket de cola",
        number="TCK-4",
        status=TicketStatus.OPEN.value,
        assigned_role_id=tech_role_id,
        updated_at=now - timedelta(minutes=3),
    )

    assigned_task = _task(
        db_session,
        client=client,
        location=location,
        template=template,
        template_subtask=template_subtask,
        creator=admin,
        title="Tarea asignada",
        status=TaskStatus.IN_PROGRESS.value,
        assigned_user=tech,
        updated_at=now - timedelta(minutes=4),
    )
    mentioned_task = _task(
        db_session,
        client=client,
        location=location,
        template=template,
        template_subtask=template_subtask,
        creator=admin,
        title="Tarea mencionada",
        status=TaskStatus.BLOCKED.value,
        assigned_user=other,
        updated_at=now - timedelta(minutes=5),
    )
    task_comment = TaskComment(task_id=mentioned_task.task_id, author_crm_user_id=other.crm_user_id, body="@tech")
    task_comment.mentions.append(TaskCommentMention(mentioned_crm_user_id=tech.crm_user_id, created_by_crm_user_id=other.crm_user_id))
    role_queue_task = _task(
        db_session,
        client=client,
        location=location,
        template=template,
        template_subtask=template_subtask,
        creator=admin,
        title="Tarea de cola",
        status=TaskStatus.PENDING.value,
        assigned_user=None,
        updated_at=now - timedelta(minutes=6),
    )
    db_session.add_all([comment, task_comment])
    db_session.commit()

    menu = DashboardService(db_session).get_pending_menu(_actor(tech, ["tecnico"]))
    codes_and_titles = {(item.public_code, item.title) for item in menu.items}

    assert ("TCK-1", assigned_ticket.title) in codes_and_titles
    assert ("TCK-2", collaborator_ticket.title) in codes_and_titles
    assert ("TCK-3", mentioned_ticket.title) in codes_and_titles
    assert (f"TAR-{assigned_task.task_id[:8].upper()}", assigned_task.task_title) in codes_and_titles
    assert (f"TAR-{mentioned_task.task_id[:8].upper()}", mentioned_task.task_title) in codes_and_titles
    assert ("TCK-4", role_queue_ticket.title) not in codes_and_titles
    assert (f"TAR-{role_queue_task.task_id[:8].upper()}", role_queue_task.task_title) not in codes_and_titles
    assert all(tab.key != "approvals" for tab in menu.tabs)


def test_pending_menu_admin_gets_global_operational_and_approvals_without_duplication(db_session) -> None:
    admin = _seed_user(db_session, role_key="admin_crm", auth_user_id="auth-admin", display_name="Admin")
    tech = _seed_user(db_session, role_key="tecnico_campo", auth_user_id="auth-tech", display_name="Técnico")
    client, location, template, template_subtask = _seed_base_entities(db_session, admin)

    approval_ticket = _ticket(
        db_session,
        client=client,
        location=location,
        creator=admin,
        title="Ticket aprobación",
        number="TCK-APR",
        status=TicketStatus.PENDING_APPROVAL.value,
        assigned_user=tech,
        priority=TicketPriority.LOW.value,
    )
    approval_task = _task(
        db_session,
        client=client,
        location=location,
        template=template,
        template_subtask=template_subtask,
        creator=admin,
        title="Tarea aprobación",
        status=TaskStatus.PENDING_APPROVAL.value,
        assigned_user=tech,
        priority="BAJA",
    )
    operational_ticket = _ticket(
        db_session,
        client=client,
        location=location,
        creator=admin,
        title="Ticket operativo",
        number="TCK-OP",
        status=TicketStatus.OPEN.value,
        assigned_user=None,
    )

    menu = DashboardService(db_session).get_pending_menu(_actor(admin, ["admin"]))
    approval_items = [item for item in menu.items if "approvals" in item.tab_keys]

    assert any(tab.key == "approvals" for tab in menu.tabs)
    assert {item.public_code for item in approval_items} == {"TCK-APR", f"TAR-{approval_task.task_id[:8].upper()}"}
    assert all("tickets" not in item.tab_keys and "tasks" not in item.tab_keys for item in approval_items)
    assert any(item.public_code == operational_ticket.ticket_number and "tickets" in item.tab_keys for item in menu.items)
    assert menu.items[0].public_code in {approval_ticket.ticket_number, f"TAR-{approval_task.task_id[:8].upper()}"}
