"""Task module API tests."""

from __future__ import annotations

from io import BytesIO

from sqlalchemy import select

from crm_backend.adapters.auth_service_adapter import ActiveMembershipContext, AuthenticatedAuthResult
from crm_backend.api.dependencies import get_auth_service_adapter
from crm_backend.models import Client, CrmRole, CrmUser, CrmUserRole, Location, StockProduct, Task, TaskAttachment, TaskTemplatePreForm


class FakeTaskAuthAdapter:
    """Fake auth adapter returning deterministic CRM sessions per bearer token."""

    USER_FIXTURES = {
        "admin-token": {
            "auth_user_id": "auth-admin",
            "email": "admin.crm@microtv.com",
            "display_name": "Admin CRM",
            "roles": ["platform_admin"],
            "tenant_id": "MICROTV",
        },
        "tech-token": {
            "auth_user_id": "auth-tech",
            "email": "tecnico.crm@yccbrothers.com",
            "display_name": "Tecnico Campo",
            "roles": [],
            "tenant_id": "YCC",
        },
        "deposito-token": {
            "auth_user_id": "auth-deposito",
            "email": "deposito.crm@yccbrothers.com",
            "display_name": "Encargado Deposito",
            "roles": [],
            "tenant_id": "YCC",
        },
        "ejecutivo-token": {
            "auth_user_id": "auth-ejecutivo",
            "email": "ejecutivo.crm@yccbrothers.com",
            "display_name": "Ejecutivo CRM",
            "roles": ["ejecutivo"],
            "tenant_id": "YCC",
        },
    }

    def validate_access_token(self, access_token: str) -> AuthenticatedAuthResult:
        fixture = self.USER_FIXTURES[access_token]
        return AuthenticatedAuthResult(
            access_token=access_token,
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=3600,
            refresh_expires_in=86400,
            auth_user_id=fixture["auth_user_id"],
            email=fixture["email"],
            display_name=fixture["display_name"],
            active_membership=ActiveMembershipContext(
                membership_id=f"membership-{fixture['auth_user_id']}",
                tenant_type="company",
                tenant_id=fixture["tenant_id"],
                roles=fixture["roles"],
            ),
            claims={"sub": fixture["auth_user_id"], "email": fixture["email"]},
        )

    def login(self, *, email: str, password: str):
        raise NotImplementedError


def _seed_local_role_user(db_session, *, role_key: str, auth_user_id: str, email: str, display_name: str) -> CrmUser:
    role = db_session.scalar(select(CrmRole).where(CrmRole.role_key == role_key))
    if role is None:
        raise AssertionError(f"No se encontró el rol {role_key} seed.")

    crm_user = CrmUser(auth_user_id=auth_user_id, email=email, display_name=display_name)
    crm_user.assigned_roles.append(CrmUserRole(crm_role_id=role.crm_role_id, role=role))
    db_session.add(crm_user)
    db_session.commit()
    db_session.refresh(crm_user)
    return crm_user


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_client(db_session) -> Client:
    client = Client(business_name="Cliente Acme SA", tax_id="30-12345678-9", email="operaciones@acme.test")
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


def _create_template(client, *, headers: dict[str, str], default_tech_user_id: str | None = None, next_policy: str = "role_queue_auto"):
    response = client.post(
        "/tasks/templates",
        headers=headers,
        json={
            "template_name": "Instalacion DVR estandar",
            "description": "Plantilla operativa completa",
            "subtasks": [
                {
                    "subtask_title": "Visita tecnica",
                    "subtask_description": "Diagnostico y checklist tecnico",
                    "order_index": 0,
                    "responsible_role_key": "tecnico",
                    "default_responsible_crm_user_id": default_tech_user_id,
                    "close_comment_required": True,
                    "next_assignment_policy": "role_queue_auto",
                    "items": [
                        {
                            "item_label": "Equipo revisado",
                            "item_order": 0,
                            "item_type": "checkbox",
                            "is_required": True,
                        },
                        {
                            "item_label": "Observaciones tecnicas",
                            "item_order": 1,
                            "item_type": "text",
                            "is_required": True,
                        },
                    ],
                },
                {
                    "subtask_title": "Preparacion de deposito",
                    "subtask_description": "Despacho y entrega",
                    "order_index": 1,
                    "responsible_role_key": "deposito",
                    "default_responsible_crm_user_id": None,
                    "close_comment_required": True,
                    "next_assignment_policy": next_policy,
                    "items": [
                        {
                            "item_label": "Material preparado",
                            "item_order": 0,
                            "item_type": "checkbox",
                            "is_required": True,
                        }
                    ],
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_task(client, template_id: str, client_id: str, headers: dict[str, str]):
    response = client.post(
        "/tasks",
        headers=headers,
        json={
            "template_id": template_id,
            "client_id": client_id,
            "task_title": "Instalacion cliente Acme",
            "task_description": "Flujo operativo real",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_create_template_and_task_from_it(client, db_session) -> None:
    """Admin must be able to define templates and create operational tasks."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))

    assigned_response = client.get("/tasks/assigned/me", headers=_auth_header("tech-token"))

    assert template["template_name"] == "Instalacion DVR estandar"
    assert len(template["subtasks"]) == 2
    assert task["task_title"] == "Instalacion cliente Acme"
    assert task["status"] == "IN_PROGRESS"
    assert task["location"] is None
    assert task["client_name"] == "Cliente Acme SA"
    assert task["template_name"] == "Instalacion DVR estandar"
    assert task["current_assigned_user_display_name"] == "Tecnico Campo"
    assert task["subtasks"][0]["assigned_crm_user_id"] == tech_user.crm_user_id
    assert task["subtasks"][0]["assigned_user_display_name"] == "Tecnico Campo"
    assert task["subtasks"][0]["status"] == "assigned"
    assert task["subtasks"][1]["status"] == "locked"
    assert assigned_response.status_code == 200
    assert any(item["task_id"] == task["task_id"] for item in assigned_response.json())


def test_update_template_with_pre_form_keeps_single_pre_form_record(client, db_session) -> None:
    """Updating a template with pre-form enabled must not fail nor duplicate pre-form rows."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    create_response = client.post(
        "/tasks/templates",
        headers=_auth_header("admin-token"),
        json={
            "template_name": "Template con pre-form",
            "description": "Primera versión",
            "requires_arrival_comment": False,
            "requires_video_evidence": False,
            "requires_pre_form": True,
            "pre_form": {
                "title": "Formulario inicial",
                "instructions": "Completar antes de iniciar",
                "fields": [
                    {
                        "label": "Nombre cliente",
                        "field_type": "TEXT",
                        "is_required": True,
                        "order_index": 0,
                        "placeholder": "Nombre"
                    }
                ]
            },
            "required_materials": [],
            "subtasks": [
                {
                    "subtask_title": "Visita técnica",
                    "subtask_description": "Diagnóstico",
                    "order_index": 0,
                    "responsible_role_key": "tecnico",
                    "default_responsible_crm_user_id": None,
                    "close_comment_required": True,
                    "next_assignment_policy": "role_queue_auto",
                    "subtask_type": "standard",
                    "items": [
                        {
                            "item_label": "Checklist inicial",
                            "item_order": 0,
                            "item_type": "checkbox",
                            "is_required": True
                        }
                    ]
                }
            ]
        },
    )

    assert create_response.status_code == 200, create_response.text
    template_id = create_response.json()["template_id"]

    update_response = client.put(
        f"/tasks/templates/{template_id}",
        headers=_auth_header("admin-token"),
        json={
            "template_name": "Template con pre-form actualizado",
            "description": "Segunda versión",
            "requires_arrival_comment": False,
            "requires_video_evidence": False,
            "requires_pre_form": True,
            "pre_form": {
                "title": "Formulario actualizado",
                "instructions": "Completar y validar datos",
                "fields": [
                    {
                        "label": "Nombre cliente",
                        "field_type": "TEXT",
                        "is_required": True,
                        "order_index": 0,
                        "placeholder": "Nombre"
                    },
                    {
                        "label": "Teléfono",
                        "field_type": "TEL",
                        "is_required": False,
                        "order_index": 1,
                        "placeholder": "11 1234 5678"
                    }
                ]
            },
            "required_materials": [],
            "subtasks": [
                {
                    "subtask_title": "Visita técnica",
                    "subtask_description": "Diagnóstico",
                    "order_index": 0,
                    "responsible_role_key": "tecnico",
                    "default_responsible_crm_user_id": None,
                    "close_comment_required": True,
                    "next_assignment_policy": "role_queue_auto",
                    "subtask_type": "standard",
                    "items": [
                        {
                            "item_label": "Checklist inicial",
                            "item_order": 0,
                            "item_type": "checkbox",
                            "is_required": True
                        }
                    ]
                }
            ]
        },
    )

    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["template_name"] == "Template con pre-form actualizado"
    assert updated["pre_form"]["title"] == "Formulario actualizado"
    assert len(updated["pre_form"]["fields"]) == 2

    pre_forms = list(db_session.scalars(select(TaskTemplatePreForm).where(TaskTemplatePreForm.template_id == template_id)).all())
    assert len(pre_forms) == 1


def test_update_template_materials_updates_existing_rows_without_duplicate_insert(client, db_session) -> None:
    """Updating required materials must reuse existing template-material rows."""

    products = list(
        db_session.scalars(
            select(StockProduct).where(StockProduct.is_active.is_(True), StockProduct.requires_tracking.is_(False))
        ).all()
    )
    assert len(products) >= 2
    first_product, second_product = products[:2]
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    create_response = client.post(
        "/tasks/templates",
        headers=_auth_header("admin-token"),
        json={
            "template_name": "Template con materiales",
            "description": "Primera version",
            "requires_arrival_comment": False,
            "requires_video_evidence": False,
            "requires_pre_form": False,
            "required_materials": [
                {"product_id": first_product.product_id, "quantity_required": 1, "notes": "Inicial"},
            ],
            "subtasks": [
                {
                    "subtask_title": "Visita tecnica",
                    "subtask_description": "Diagnostico",
                    "order_index": 0,
                    "responsible_role_key": "tecnico",
                    "default_responsible_crm_user_id": None,
                    "close_comment_required": True,
                    "next_assignment_policy": "role_queue_auto",
                    "subtask_type": "standard",
                    "items": [],
                }
            ],
        },
    )
    assert create_response.status_code == 200, create_response.text
    template_id = create_response.json()["template_id"]

    update_response = client.put(
        f"/tasks/templates/{template_id}",
        headers=_auth_header("admin-token"),
        json={
            "template_name": "Template con materiales actualizado",
            "description": "Segunda version",
            "requires_arrival_comment": False,
            "requires_video_evidence": False,
            "requires_pre_form": False,
            "required_materials": [
                {"product_id": first_product.product_id, "quantity_required": 2, "notes": "Actualizado"},
                {"product_id": second_product.product_id, "quantity_required": 1, "notes": None},
            ],
            "subtasks": [
                {
                    "subtask_title": "Visita tecnica",
                    "subtask_description": "Diagnostico",
                    "order_index": 0,
                    "responsible_role_key": "tecnico",
                    "default_responsible_crm_user_id": None,
                    "close_comment_required": True,
                    "next_assignment_policy": "role_queue_auto",
                    "subtask_type": "standard",
                    "items": [],
                }
            ],
        },
    )

    assert update_response.status_code == 200, update_response.text
    updated_materials = update_response.json()["required_materials"]
    assert len(updated_materials) == 2
    assert any(material["product_id"] == first_product.product_id and material["quantity_required"] == 2 for material in updated_materials)
    assert any(material["product_id"] == second_product.product_id for material in updated_materials)


def test_can_regenerate_pre_form_link_after_customer_submission(client, db_session) -> None:
    """After a customer submits pre-form once, executive/admin should be able to resend a new link."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template_response = client.post(
        "/tasks/templates",
        headers=_auth_header("admin-token"),
        json={
            "template_name": "Template con formulario reenviable",
            "description": "Formulario previo editable",
            "requires_arrival_comment": False,
            "requires_video_evidence": False,
            "requires_pre_form": True,
            "pre_form": {
                "title": "Formulario previo",
                "instructions": "Completar antes de la visita",
                "assignment_role_key": "tecnico",
                "assignment_crm_user_id": tech_user.crm_user_id,
                "fields": [
                    {
                        "label": "Nombre del titular",
                        "field_type": "TEXT",
                        "is_required": True,
                        "order_index": 0,
                        "placeholder": "Nombre"
                    }
                ]
            },
            "required_materials": [],
            "subtasks": [
                {
                    "subtask_title": "Visita técnica",
                    "subtask_description": "Diagnóstico",
                    "order_index": 0,
                    "responsible_role_key": "tecnico",
                    "default_responsible_crm_user_id": tech_user.crm_user_id,
                    "close_comment_required": True,
                    "next_assignment_policy": "role_queue_auto",
                    "subtask_type": "standard",
                    "items": [
                        {
                            "item_label": "Checklist inicial",
                            "item_order": 0,
                            "item_type": "checkbox",
                            "is_required": True
                        }
                    ]
                }
            ]
        },
    )
    assert template_response.status_code == 200, template_response.text
    template_body = template_response.json()
    assert len(template_body["subtasks"]) == 1
    assert template_body["subtasks"][0]["subtask_type"] == "standard"
    template_id = template_response.json()["template_id"]

    task = _create_task(client, template_id, seeded_client.client_id, _auth_header("admin-token"))
    assert task["status"] == "PENDING"
    assert task["current_assigned_crm_user_id"] is None
    assert len(task["subtasks"]) == 1
    assert task["subtasks"][0]["status"] == "locked"

    generate_response = client.post(
        f"/tasks/{task['task_id']}/pre-form/generate",
        headers=_auth_header("admin-token"),
    )
    assert generate_response.status_code == 200, generate_response.text
    first_path = generate_response.json()["form_link_path"]
    assert isinstance(first_path, str) and first_path.startswith("/pre-form/")
    first_token = first_path.rsplit("/", maxsplit=1)[-1]

    public_form = client.get(f"/pre-form/{first_token}")
    assert public_form.status_code == 200, public_form.text
    field_id = public_form.json()["fields"][0]["field_id"]

    submit_response = client.post(
        f"/pre-form/{first_token}",
        json={
            "values": [
                {
                    "field_id": field_id,
                    "text_value": "Cliente corregido"
                }
            ]
        },
    )
    assert submit_response.status_code == 200, submit_response.text

    task_after_submit = client.get(f"/tasks/{task['task_id']}", headers=_auth_header("admin-token"))
    assert task_after_submit.status_code == 200, task_after_submit.text
    task_after_submit_body = task_after_submit.json()
    assert task_after_submit_body["status"] == "IN_PROGRESS"
    assert task_after_submit_body["current_assigned_crm_user_id"] == tech_user.crm_user_id
    assert task_after_submit_body["subtasks"][0]["status"] == "assigned"

    regenerate_response = client.post(
        f"/tasks/{task['task_id']}/pre-form/generate",
        headers=_auth_header("admin-token"),
    )
    assert regenerate_response.status_code == 200, regenerate_response.text
    second_path = regenerate_response.json()["form_link_path"]
    assert isinstance(second_path, str) and second_path.startswith("/pre-form/")
    second_token = second_path.rsplit("/", maxsplit=1)[-1]
    assert second_token != first_token

    status_response = client.get(
        f"/tasks/{task['task_id']}/pre-form/status",
        headers=_auth_header("admin-token"),
    )
    assert status_response.status_code == 200, status_response.text
    status_payload = status_response.json()
    assert status_payload["status_label"] == "pendiente"
    assert status_payload["submitted_at"] is None


def test_list_crm_users_filters_candidates_by_role(client, db_session) -> None:
    """The template form should receive only active CRM users for the selected role."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    response = client.get("/crm-users?role_key=tecnico", headers=_auth_header("admin-token"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["crm_user_id"] == tech_user.crm_user_id
    assert body[0]["display_name"] == "Tecnico Campo"


def test_cannot_close_subtask_when_required_items_are_missing(client, db_session) -> None:
    """Close must fail until every required item is complete."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]

    response = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Checklist incompleto"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "task_validation_error"


def test_close_advances_flow_and_exposes_unassigned_next_subtask(client, db_session) -> None:
    """Closing a valid subtask must unlock the next one and preserve audit/comment trace."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    items = first_subtask["items"]

    progress_response = client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": items[1]["subtask_item_value_id"], "text_value": "Equipo listo para despacho"},
            ]
        },
    )
    close_response = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Trabajo tecnico finalizado"},
    )
    unassigned_response = client.get("/tasks/unassigned/me", headers=_auth_header("deposito-token"))

    assert progress_response.status_code == 200, progress_response.text
    assert close_response.status_code == 200, close_response.text
    body = close_response.json()
    next_subtask = body["subtasks"][1]
    assert body["current_subtask_id"] == next_subtask["subtask_id"]
    assert body["subtasks"][0]["status"] == "completed"
    assert next_subtask["status"] == "pending_assignment"
    assert next_subtask["assigned_crm_user_id"] is None
    assert any(comment["body"] == "Trabajo tecnico finalizado" for comment in body["comments"])
    assert any(event["event_type"] == "subtask.progress_saved" for event in body["audit_events"])
    assert any(event["event_type"] == "subtask.closed" for event in body["audit_events"])
    assert unassigned_response.status_code == 200
    assert any(item["subtask_id"] == next_subtask["subtask_id"] for item in unassigned_response.json())


def test_cannot_close_subtask_until_request_is_approved_dispatched_and_received(client, db_session) -> None:
    """Requester cannot close the active subtask while material flow is pending approval, dispatch, or receipt."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    checklist_items = first_subtask["items"]

    progress_response = client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": checklist_items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": checklist_items[1]["subtask_item_value_id"], "text_value": "Checklist completo"},
            ]
        },
    )
    assert progress_response.status_code == 200, progress_response.text

    dispatchable_product = db_session.scalar(
        select(StockProduct).where(StockProduct.is_active.is_(True), StockProduct.requires_tracking.is_(False))
    )
    assert dispatchable_product is not None

    request_response = client.post(
        "/inventory-flow/requests",
        headers=_auth_header("tech-token"),
        json={
            "source_type": "TASK",
            "task_id": task["task_id"],
            "request_reason": "Falta material critico",
            "items": [{"product_id": dispatchable_product.product_id, "quantity_requested": 3, "notes": "Urgente"}],
        },
    )
    assert request_response.status_code == 200, request_response.text
    request_body = request_response.json()
    request_id = request_body["inventory_request_id"]

    blocked_by_pending = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Intento de cierre"},
    )
    assert blocked_by_pending.status_code == 422

    review_response = client.post(
        f"/inventory-flow/requests/{request_id}/review",
        headers=_auth_header("deposito-token"),
        json={"status": "APPROVED", "review_notes": "Aprobado para despacho"},
    )
    assert review_response.status_code == 200, review_response.text
    assert review_response.json()["request_status"] == "PENDING_DISPATCH"

    blocked_by_pending_dispatch = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Intento de cierre"},
    )
    assert blocked_by_pending_dispatch.status_code == 422

    dispatch_response = client.post(
        f"/inventory-flow/tasks/{task['task_id']}/dispatches",
        headers=_auth_header("deposito-token"),
        json={
            "request_id": request_id,
            "dispatch_notes": "Despacho parcial",
            "items": [{"product_id": dispatchable_product.product_id, "quantity_dispatched": 3}],
        },
    )
    assert dispatch_response.status_code == 200, dispatch_response.text
    dispatch_body = dispatch_response.json()
    assert dispatch_body["dispatches"][0]["items"][0]["quantity_dispatched"] == 3
    linked_request = next(item for item in dispatch_body["inventory_requests"] if item["inventory_request_id"] == request_id)
    assert linked_request["request_status"] == "PENDING_RECEIPT"

    blocked_by_pending_receipt = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Intento de cierre"},
    )
    assert blocked_by_pending_receipt.status_code == 422

    dispatch_item_id = dispatch_body["dispatches"][0]["items"][0]["inventory_dispatch_item_id"]
    confirm_received_response = client.post(
        f"/inventory-flow/dispatch-items/{dispatch_item_id}/confirmations",
        headers=_auth_header("tech-token"),
        json={"confirmation_type": "received"},
    )
    assert confirm_received_response.status_code == 200, confirm_received_response.text
    confirm_received_body = confirm_received_response.json()
    linked_request_after_receipt = next(
        item for item in confirm_received_body["inventory_requests"] if item["inventory_request_id"] == request_id
    )
    assert linked_request_after_receipt["request_status"] == "COMPLETED"

    close_response = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Material recibido y checklist completo"},
    )
    assert close_response.status_code == 200, close_response.text


def test_upload_task_media_and_associate_it_with_close_comment(client, db_session) -> None:
    """Uploaded task media must persist on disk metadata and become attached to the closing comment."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    items = first_subtask["items"]

    progress_response = client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": items[1]["subtask_item_value_id"], "text_value": "Checklist completo con foto"},
            ]
        },
    )
    assert progress_response.status_code == 200, progress_response.text

    upload_response = client.post(
        f"/tasks/{task['task_id']}/attachments",
        headers=_auth_header("tech-token"),
        data={"subtask_id": first_subtask["subtask_id"]},
        files={"files": ("evidencia.jpg", BytesIO(b"fake-image-content"), "image/jpeg")},
    )

    assert upload_response.status_code == 200, upload_response.text
    uploaded = upload_response.json()
    assert len(uploaded) == 1
    assert uploaded[0]["publicUrl"].startswith("/media/tasks/images/")
    assert uploaded[0]["storagePath"].startswith("media/tasks/images/")

    close_response = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={
            "action": "close_subtask",
            "comment": "Cierre con evidencia multimedia",
            "attachment_ids": [uploaded[0]["id"]],
        },
    )

    assert close_response.status_code == 200, close_response.text
    body = close_response.json()
    persisted_comment = next(comment for comment in body["comments"] if comment["body"] == "Cierre con evidencia multimedia")
    assert len(persisted_comment["attachments"]) == 1
    assert persisted_comment["attachments"][0]["id"] == uploaded[0]["id"]

    persisted_attachment = db_session.scalar(select(TaskAttachment).where(TaskAttachment.attachment_id == uploaded[0]["id"]))
    assert persisted_attachment is not None
    assert persisted_attachment.task_comment_id == persisted_comment["task_comment_id"]


def test_final_close_with_multimedia_requirement_accepts_photo_evidence(client, db_session) -> None:
    """When multimedia evidence is required, a photo attachment must unblock final close."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="ejecutivo",
        auth_user_id="auth-ejecutivo",
        email="ejecutivo.crm@yccbrothers.com",
        display_name="Ejecutivo CRM",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template_response = client.post(
        "/tasks/templates",
        headers=_auth_header("admin-token"),
        json={
            "template_name": "Template cierre con multimedia",
            "description": "Cierre final requiere evidencia",
            "requires_arrival_comment": False,
            "requires_video_evidence": True,
            "requires_pre_form": False,
            "pre_form": None,
            "required_materials": [],
            "subtasks": [
                {
                    "subtask_title": "Visita técnica",
                    "subtask_description": "Subtarea única",
                    "order_index": 0,
                    "responsible_role_key": "tecnico",
                    "default_responsible_crm_user_id": tech_user.crm_user_id,
                    "close_comment_required": True,
                    "next_assignment_policy": "role_queue_auto",
                    "subtask_type": "standard",
                    "items": [
                        {
                            "item_label": "Checklist",
                            "item_order": 0,
                            "item_type": "checkbox",
                            "is_required": True,
                        },
                        {
                            "item_label": "Observaciones",
                            "item_order": 1,
                            "item_type": "text",
                            "is_required": True,
                        },
                    ],
                }
            ],
        },
    )
    assert template_response.status_code == 200, template_response.text
    template_id = template_response.json()["template_id"]

    task = _create_task(client, template_id, seeded_client.client_id, _auth_header("admin-token"))
    subtask = task["subtasks"][0]
    items = subtask["items"]

    progress_response = client.put(
        f"/tasks/subtasks/{subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": items[1]["subtask_item_value_id"], "text_value": "Checklist completo"},
            ]
        },
    )
    assert progress_response.status_code == 200, progress_response.text

    close_without_media = client.post(
        f"/tasks/subtasks/{subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Intento sin adjuntos"},
    )
    assert close_without_media.status_code == 422
    assert close_without_media.json()["error"]["code"] == "task_validation_error"

    upload_response = client.post(
        f"/tasks/{task['task_id']}/attachments",
        headers=_auth_header("tech-token"),
        data={"subtask_id": subtask["subtask_id"]},
        files={"files": ("evidencia.jpg", BytesIO(b"fake-image-content"), "image/jpeg")},
    )
    assert upload_response.status_code == 200, upload_response.text
    uploaded = upload_response.json()
    assert len(uploaded) == 1

    close_with_photo = client.post(
        f"/tasks/subtasks/{subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={
            "action": "close_subtask",
            "comment": "Cierre final con foto de evidencia",
            "attachment_ids": [uploaded[0]["id"]],
        },
    )

    assert close_with_photo.status_code == 200, close_with_photo.text


def test_manual_next_assignment_policy_requires_explicit_user(client, db_session) -> None:
    """Manual next-assignment policy must reject close without a concrete assignee."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    deposito_user = _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(
        client,
        headers=_auth_header("admin-token"),
        default_tech_user_id=tech_user.crm_user_id,
        next_policy="manual_required",
    )
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    items = first_subtask["items"]

    client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": items[1]["subtask_item_value_id"], "text_value": "Checklist completo"},
            ]
        },
    )

    invalid_close_response = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Listo para pasar a deposito"},
    )
    valid_close_response = client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={
            "action": "close_subtask",
            "comment": "Asignando explicitamente a deposito",
            "next_assigned_crm_user_id": deposito_user.crm_user_id,
        },
    )

    assert invalid_close_response.status_code == 422
    assert invalid_close_response.json()["error"]["code"] == "task_validation_error"
    assert valid_close_response.status_code == 200, valid_close_response.text
    body = valid_close_response.json()
    assert body["subtasks"][1]["assigned_crm_user_id"] == deposito_user.crm_user_id
    assert body["subtasks"][1]["status"] == "assigned"
    assert body["current_assigned_crm_user_id"] == deposito_user.crm_user_id


def test_only_matching_role_can_claim_unassigned_subtask(client, db_session) -> None:
    """Users outside the responsible role must not be able to claim a queued subtask."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    items = first_subtask["items"]

    client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": items[1]["subtask_item_value_id"], "text_value": "Checklist completo"},
            ]
        },
    )
    client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Pasa a deposito"},
    )

    unassigned_response = client.get("/tasks/unassigned/me", headers=_auth_header("deposito-token"))
    queued_subtask_id = unassigned_response.json()[0]["subtask_id"]
    invalid_claim = client.post(f"/tasks/subtasks/{queued_subtask_id}/claim", headers=_auth_header("tech-token"))
    valid_claim = client.post(f"/tasks/subtasks/{queued_subtask_id}/claim", headers=_auth_header("deposito-token"))

    assert invalid_claim.status_code == 403
    assert invalid_claim.json()["error"]["code"] == "task_access_denied"
    assert valid_claim.status_code == 200, valid_claim.text
    assert valid_claim.json()["subtasks"][1]["assigned_crm_user_id"] is not None


def test_deposito_can_reassign_subtask_to_another_deposito_user(client, db_session) -> None:
    """A deposito user must be able to reassign active deposito subtask to another deposito peer."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    peer_deposito = _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito-peer",
        email="deposito.peer@yccbrothers.com",
        display_name="Depósito Peer",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    items = first_subtask["items"]

    client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": items[1]["subtask_item_value_id"], "text_value": "Checklist completo"},
            ]
        },
    )
    client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Pasa a deposito"},
    )

    unassigned_response = client.get("/tasks/unassigned/me", headers=_auth_header("deposito-token"))
    deposito_subtask_id = unassigned_response.json()[0]["subtask_id"]
    claim_response = client.post(f"/tasks/subtasks/{deposito_subtask_id}/claim", headers=_auth_header("deposito-token"))
    assert claim_response.status_code == 200, claim_response.text

    reassign_response = client.patch(
        f"/tasks/subtasks/{deposito_subtask_id}/assignment",
        headers=_auth_header("deposito-token"),
        json={"assigned_crm_user_id": peer_deposito.crm_user_id, "notes": "Cobertura de turno"},
    )

    assert reassign_response.status_code == 200, reassign_response.text
    body = reassign_response.json()
    assert body["subtasks"][1]["assigned_crm_user_id"] == peer_deposito.crm_user_id


def test_ejecutivo_can_reassign_active_subtask(client, db_session) -> None:
    """Executive users must be able to reassign active subtasks."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    peer_tech = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech-peer",
        email="tecnico.peer@yccbrothers.com",
        display_name="Tecnico Peer",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]

    reassign_response = client.patch(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/assignment",
        headers=_auth_header("ejecutivo-token"),
        json={"assigned_crm_user_id": peer_tech.crm_user_id, "notes": "Redistribución de carga"},
    )

    assert reassign_response.status_code == 200, reassign_response.text
    body = reassign_response.json()
    assert body["subtasks"][0]["assigned_crm_user_id"] == peer_tech.crm_user_id


def test_assignment_rejects_non_uuid_user_id_with_422(client, db_session) -> None:
    """Assignment should return a domain validation error when user id format is invalid."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]

    response = client.patch(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/assignment",
        headers=_auth_header("ejecutivo-token"),
        json={"assigned_crm_user_id": "wen", "notes": "Prueba ID inválido"},
    )

    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["error"]["code"] == "task_validation_error"
    assert "formato inválido" in payload["error"]["message"]


def test_completed_task_requires_executive_approval_and_moves_to_history(client, db_session) -> None:
    """Finalized flow must remain pending approval until executive approval, then move from tracking to history."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    executive_user = _seed_local_role_user(
        db_session,
        role_key="ejecutivo",
        auth_user_id="auth-ejecutivo",
        email="ejecutivo.crm@yccbrothers.com",
        display_name="Ejecutivo CRM",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    first_items = first_subtask["items"]

    client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": first_items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": first_items[1]["subtask_item_value_id"], "text_value": "Checklist completo"},
            ]
        },
    )
    client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Pasa a deposito"},
    )

    unassigned_response = client.get("/tasks/unassigned/me", headers=_auth_header("deposito-token"))
    deposito_subtask_id = unassigned_response.json()[0]["subtask_id"]
    claimed_task = client.post(f"/tasks/subtasks/{deposito_subtask_id}/claim", headers=_auth_header("deposito-token")).json()
    second_items = claimed_task["subtasks"][1]["items"]

    client.put(
        f"/tasks/subtasks/{deposito_subtask_id}/items",
        headers=_auth_header("deposito-token"),
        json={"items": [{"item_id": second_items[0]["subtask_item_value_id"], "checkbox_value": True}]},
    )
    close_final_response = client.post(
        f"/tasks/subtasks/{deposito_subtask_id}/actions",
        headers=_auth_header("deposito-token"),
        json={"action": "close_subtask", "comment": "Despacho completado"},
    )
    assert close_final_response.status_code == 200, close_final_response.text
    pending_approval_body = close_final_response.json()
    assert pending_approval_body["status"] == "BLOCKED"
    assert pending_approval_body["current_assigned_crm_user_id"] == executive_user.crm_user_id

    admin_tracking_before = client.get("/tasks/tracking/me", headers=_auth_header("admin-token"))
    assert any(item["task_id"] == task["task_id"] for item in admin_tracking_before.json())

    approval_response = client.patch(
        f"/tasks/{task['task_id']}/approve",
        headers=_auth_header("ejecutivo-token"),
        json={"comment": "Aprobación ejecutiva final"},
    )
    assert approval_response.status_code == 200, approval_response.text
    approved_body = approval_response.json()
    assert approved_body["status"] == "COMPLETED"
    assert approved_body["finalized_by_display_name"] == "Ejecutivo CRM"
    assert approved_body["current_assigned_crm_user_id"] is None
    assert approved_body["current_subtask_id"] is None

    admin_tracking_after = client.get("/tasks/tracking/me", headers=_auth_header("admin-token"))
    assert not any(item["task_id"] == task["task_id"] for item in admin_tracking_after.json())

    executive_history = client.get("/tasks/history/me", headers=_auth_header("ejecutivo-token"))
    assert executive_history.status_code == 200, executive_history.text
    assert any(item["task_id"] == task["task_id"] for item in executive_history.json())


def test_completed_task_can_be_rejected_by_executive_with_comment(client, db_session) -> None:
    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    executive_user = _seed_local_role_user(
        db_session,
        role_key="ejecutivo",
        auth_user_id="auth-ejecutivo",
        email="ejecutivo.crm@yccbrothers.com",
        display_name="Ejecutivo CRM",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    first_items = first_subtask["items"]

    client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("tech-token"),
        json={
            "items": [
                {"item_id": first_items[0]["subtask_item_value_id"], "checkbox_value": True},
                {"item_id": first_items[1]["subtask_item_value_id"], "text_value": "Checklist completo"},
            ]
        },
    )
    client.post(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/actions",
        headers=_auth_header("tech-token"),
        json={"action": "close_subtask", "comment": "Pasa a deposito"},
    )

    unassigned_response = client.get("/tasks/unassigned/me", headers=_auth_header("deposito-token"))
    deposito_subtask_id = unassigned_response.json()[0]["subtask_id"]
    claimed_task = client.post(f"/tasks/subtasks/{deposito_subtask_id}/claim", headers=_auth_header("deposito-token")).json()
    second_items = claimed_task["subtasks"][1]["items"]

    client.put(
        f"/tasks/subtasks/{deposito_subtask_id}/items",
        headers=_auth_header("deposito-token"),
        json={"items": [{"item_id": second_items[0]["subtask_item_value_id"], "checkbox_value": True}]},
    )
    close_final_response = client.post(
        f"/tasks/subtasks/{deposito_subtask_id}/actions",
        headers=_auth_header("deposito-token"),
        json={"action": "close_subtask", "comment": "Despacho completado"},
    )
    assert close_final_response.status_code == 200, close_final_response.text
    pending_approval_body = close_final_response.json()
    assert pending_approval_body["status"] == "BLOCKED"
    assert pending_approval_body["current_assigned_crm_user_id"] == executive_user.crm_user_id

    reject_without_comment = client.patch(
        f"/tasks/{task['task_id']}/reject",
        headers=_auth_header("ejecutivo-token"),
        json={"comment": ""},
    )
    assert reject_without_comment.status_code == 422, reject_without_comment.text

    reject_response = client.patch(
        f"/tasks/{task['task_id']}/reject",
        headers=_auth_header("ejecutivo-token"),
        json={"comment": "Falta validación final del despacho y evidencia de cierre."},
    )
    assert reject_response.status_code == 200, reject_response.text
    rejected_body = reject_response.json()
    assert rejected_body["status"] == "IN_PROGRESS"
    assert rejected_body["current_assigned_crm_user_id"] != executive_user.crm_user_id
    assert rejected_body["subtasks"][-1]["status"] == "in_progress"
    assert any(comment["body"] == "Falta validación final del despacho y evidencia de cierre." for comment in rejected_body["comments"])


def test_admin_can_create_task_with_persisted_real_location(client, db_session) -> None:
    """Task creation must accept a real persisted location without exposing raw manual entry in the UI."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    location_response = client.post(
        "/locations",
        headers=_auth_header("admin-token"),
        json={
            "latitude": -34.6037,
            "longitude": -58.3816,
            "address_label": "Obelisco",
            "formatted_address": "Av. 9 de Julio, CABA",
        },
    )

    assert location_response.status_code == 201, location_response.text
    persisted_location = location_response.json()

    task_response = client.post(
        "/tasks",
        headers=_auth_header("admin-token"),
        json={
            "template_id": template["template_id"],
            "client_id": seeded_client.client_id,
            "location_id": persisted_location["location_id"],
            "task_title": "Instalacion cliente Acme",
            "task_description": "Flujo operativo real",
        },
    )

    assert task_response.status_code == 200, task_response.text
    body = task_response.json()
    assert body["location_id"] == persisted_location["location_id"]
    assert body["location"]["location_id"] == persisted_location["location_id"]
    assert body["location"]["address_label"] == "Obelisco"
    assert body["location"]["formatted_address"] == "Av. 9 de Julio, CABA"

    stored_task = db_session.scalar(select(Task).where(Task.task_id == body["task_id"]))
    stored_location = db_session.scalar(select(Location).where(Location.location_id == persisted_location["location_id"]))
    assert stored_task is not None
    assert stored_task.location_id == persisted_location["location_id"]
    assert stored_location is not None


def test_tracking_visibility_is_role_based(client, db_session) -> None:
    """Tracking must expose all tasks to admin/executive and role-relevant tasks to technicians and deposito."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_local_role_user(
        db_session,
        role_key="encargado_deposito",
        auth_user_id="auth-deposito",
        email="deposito.crm@yccbrothers.com",
        display_name="Encargado Deposito",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    created_task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))

    admin_tracking = client.get("/tasks/tracking/me", headers=_auth_header("admin-token"))
    ejecutivo_tracking = client.get("/tasks/tracking/me", headers=_auth_header("ejecutivo-token"))
    tech_tracking = client.get("/tasks/tracking/me", headers=_auth_header("tech-token"))
    deposito_tracking = client.get("/tasks/tracking/me", headers=_auth_header("deposito-token"))

    assert admin_tracking.status_code == 200, admin_tracking.text
    assert ejecutivo_tracking.status_code == 200, ejecutivo_tracking.text
    assert tech_tracking.status_code == 200, tech_tracking.text
    assert deposito_tracking.status_code == 200, deposito_tracking.text
    assert any(item["task_id"] == created_task["task_id"] for item in admin_tracking.json())
    assert any(item["task_id"] == created_task["task_id"] for item in ejecutivo_tracking.json())
    assert any(item["task_id"] == created_task["task_id"] for item in tech_tracking.json())
    assert any(item["task_id"] == created_task["task_id"] for item in deposito_tracking.json())


def test_admin_cannot_operate_subtask_assigned_to_other_user(client, db_session) -> None:
    """Users may see by role, but only the assigned user can operate the subtask."""

    tech_user = _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.crm@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTaskAuthAdapter()

    template = _create_template(client, headers=_auth_header("admin-token"), default_tech_user_id=tech_user.crm_user_id)
    task = _create_task(client, template["template_id"], seeded_client.client_id, _auth_header("admin-token"))
    first_subtask = task["subtasks"][0]
    items = first_subtask["items"]

    save_response = client.put(
        f"/tasks/subtasks/{first_subtask['subtask_id']}/items",
        headers=_auth_header("admin-token"),
        json={"items": [{"item_id": items[0]["subtask_item_value_id"], "checkbox_value": True}]},
    )

    assert save_response.status_code == 403
    assert save_response.json()["error"]["code"] == "task_access_denied"
