"""Tests for arrival registration (US-1) and satisfaction form (US-2)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
import zipfile

import pytest
from sqlalchemy import select

from crm_backend.adapters.auth_service_adapter import ActiveMembershipContext, AuthenticatedAuthResult
from crm_backend.api.dependencies import get_auth_service_adapter
from crm_backend.models import Client, CrmRole, CrmUser, CrmUserRole, Location, Ticket, TicketAttachment


# ---------------------------------------------------------------------------
# Fake adapter (same as test_tickets_api.py)
# ---------------------------------------------------------------------------


class FakeTicketAuthAdapter:
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
        "ejecutivo-token": {
            "auth_user_id": "auth-ejecutivo",
            "email": "ejecutivo@ycc.com",
            "display_name": "Ejecutivo",
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_user(db_session, *, role_key: str, auth_user_id: str, email: str, display_name: str) -> CrmUser:
    role = db_session.scalar(select(CrmRole).where(CrmRole.role_key == role_key))
    assert role is not None, f"Role {role_key} not found — bootstrap may not have run."
    user = CrmUser(auth_user_id=auth_user_id, email=email, display_name=display_name)
    user.assigned_roles.append(CrmUserRole(crm_role_id=role.crm_role_id, role=role))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _seed_client_and_location(db_session) -> tuple[Client, Location]:
    client = Client(business_name="Test Client SA", tax_id="30-99988877-6", email="test@client.example")
    location = Location(latitude=-34.6, longitude=-58.38, address_label="Oficina 1", formatted_address="Oficina 1")
    db_session.add(client)
    db_session.add(location)
    db_session.commit()
    db_session.refresh(client)
    db_session.refresh(location)
    return client, location


def _create_and_assign_ticket(client_fixture, db_session, *, tech_user: CrmUser, client_entity: Client, location: Location) -> dict:
    """Helper: create and auto-assign a ticket to tech_user, returns API body."""
    create_resp = client_fixture.post(
        "/tickets",
        headers=_auth("admin-token"),
        json={
            "title": "Test Ticket",
            "description": "Descripción de prueba.",
            "client_id": client_entity.client_id,
            "location_id": location.location_id,
            "priority": "HIGH",
            "requires_arrival_comment": False,
            "assigned_role_id": tech_user.assigned_roles[0].crm_role_id,
            "assigned_user_id": tech_user.crm_user_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    return create_resp.json()


def _upload_video_attachment(client_fixture, ticket_id: str, token: str, tmp_path: Path) -> dict:
    """Upload a dummy video attachment and return the first attachment dict."""
    video_content = b"\x00" * 100  # Fake bytes
    resp = client_fixture.post(
        f"/tickets/{ticket_id}/attachments",
        headers=_auth(token),
        files=[("files", ("evidence.mp4", BytesIO(video_content), "video/mp4"))],
    )
    assert resp.status_code == 200, resp.text
    attachments = resp.json()
    assert len(attachments) >= 1
    return attachments[0]


def _create_and_assign_ticket_requiring_arrival(client_fixture, *, tech_user: CrmUser, client_entity: Client, location: Location) -> dict:
    create_resp = client_fixture.post(
        "/tickets",
        headers=_auth("admin-token"),
        json={
            "title": "Ticket con llegada requerida",
            "description": "Descripción de prueba.",
            "client_id": client_entity.client_id,
            "location_id": location.location_id,
            "priority": "HIGH",
            "requires_arrival_comment": True,
            "assigned_role_id": tech_user.assigned_roles[0].crm_role_id,
            "assigned_user_id": tech_user.crm_user_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    return create_resp.json()


def _close_and_approve_ticket(client_fixture, ticket_id: str, tmp_path: Path) -> None:
    close_attachment = _upload_video_attachment(client_fixture, ticket_id, "tech-token", tmp_path)
    close_attachment_id = close_attachment.get("id") or close_attachment.get("attachment_id")
    assert close_attachment_id

    close_resp = client_fixture.patch(
        f"/tickets/{ticket_id}/close",
        headers=_auth("tech-token"),
        json={"comment": "Cierre técnico para aprobación.", "attachment_ids": [close_attachment_id]},
    )
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["status"] == "PENDING_APPROVAL"

    approve_resp = client_fixture.patch(
        f"/tickets/{ticket_id}/approve",
        headers=_auth("ejecutivo-token"),
        json={"comment": "Aprobado por ejecutivo"},
    )
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "CLOSED"


# ---------------------------------------------------------------------------
# US-1: Arrival registration
# ---------------------------------------------------------------------------


class TestArrivalRegistration:
    def test_comment_with_media_and_location_registers_arrival(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket_requiring_arrival(client, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        attachment = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        attachment_id = attachment.get("id") or attachment.get("attachment_id")
        assert attachment_id

        resp = client.post(
            f"/tickets/{ticket_id}/comments",
            headers=_auth("tech-token"),
            json={
                "body": "Llegué al domicilio del cliente.",
                "location_id": location.location_id,
                "attachment_ids": [attachment_id],
            },
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["requires_arrival_comment"] is True
        assert body["arrival_registered_at"] is not None
        assert body["arrival_comment_id"] is not None
        arrival_comment = next(c for c in body["comments"] if c["ticket_comment_id"] == body["arrival_comment_id"])
        assert arrival_comment["location"] is not None
        assert len(arrival_comment["attachments"]) >= 1

    def test_comment_without_attachment_does_not_register_arrival(self, client, db_session) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket_requiring_arrival(client, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        resp = client.post(
            f"/tickets/{ticket_id}/comments",
            headers=_auth("tech-token"),
            json={
                "body": "Llegué sin adjuntos.",
                "location_id": location.location_id,
                "attachment_ids": [],
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["arrival_registered_at"] is None

    def test_comment_without_location_does_not_register_arrival(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket_requiring_arrival(client, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        attachment = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        attachment_id = attachment.get("id") or attachment.get("attachment_id")
        assert attachment_id

        resp = client.post(
            f"/tickets/{ticket_id}/comments",
            headers=_auth("tech-token"),
            json={
                "body": "Comentario con multimedia pero sin ubicación.",
                "attachment_ids": [attachment_id],
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["arrival_registered_at"] is None

    def test_first_valid_comment_wins_and_close_is_blocked_until_arrival(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket_requiring_arrival(client, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        close_attachment = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        close_attachment_id = close_attachment.get("id") or close_attachment.get("attachment_id")
        assert close_attachment_id

        blocked_close = client.patch(
            f"/tickets/{ticket_id}/close",
            headers=_auth("tech-token"),
            json={"comment": "Intento de cierre sin llegada", "attachment_ids": [close_attachment_id]},
        )
        assert blocked_close.status_code == 409, blocked_close.text
        assert "requiere registrar llegada" in blocked_close.text

        arrival_attachment_first = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        first_attachment_id = arrival_attachment_first.get("id") or arrival_attachment_first.get("attachment_id")
        assert first_attachment_id

        first_valid = client.post(
            f"/tickets/{ticket_id}/comments",
            headers=_auth("tech-token"),
            json={
                "body": "Primera visita válida",
                "location_id": location.location_id,
                "attachment_ids": [first_attachment_id],
            },
        )
        assert first_valid.status_code == 200, first_valid.text
        first_body = first_valid.json()
        first_arrival_comment_id = first_body["arrival_comment_id"]
        assert first_arrival_comment_id is not None

        arrival_attachment_second = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        second_attachment_id = arrival_attachment_second.get("id") or arrival_attachment_second.get("attachment_id")
        assert second_attachment_id

        second_valid = client.post(
            f"/tickets/{ticket_id}/comments",
            headers=_auth("tech-token"),
            json={
                "body": "Segunda visita válida",
                "location_id": location.location_id,
                "attachment_ids": [second_attachment_id],
            },
        )
        assert second_valid.status_code == 200, second_valid.text
        assert second_valid.json()["arrival_comment_id"] == first_arrival_comment_id

        final_close_attachment = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        final_close_attachment_id = final_close_attachment.get("id") or final_close_attachment.get("attachment_id")
        assert final_close_attachment_id
        close_after_arrival = client.patch(
            f"/tickets/{ticket_id}/close",
            headers=_auth("tech-token"),
            json={"comment": "Cierre posterior a llegada", "attachment_ids": [final_close_attachment_id]},
        )
        assert close_after_arrival.status_code == 200, close_after_arrival.text


# ---------------------------------------------------------------------------
# US-2: Satisfaction form generation (basic lifecycle)
# ---------------------------------------------------------------------------


class TestSatisfactionFormLifecycle:
    def test_admin_can_generate_form_for_closed_ticket(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        _seed_user(
            db_session,
            role_key="admin_crm",
            auth_user_id="auth-admin",
            email="admin.crm@microtv.com",
            display_name="Admin CRM",
        )
        _seed_user(
            db_session,
            role_key="ejecutivo",
            auth_user_id="auth-ejecutivo",
            email="ejecutivo@ycc.com",
            display_name="Ejecutivo",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        _close_and_approve_ticket(client, ticket_id, tmp_path)

        # Generate satisfaction form
        form_resp = client.post(
            f"/tickets/{ticket_id}/generate-survey",
            headers=_auth("admin-token"),
        )
        assert form_resp.status_code == 200, form_resp.text
        body = form_resp.json()
        assert "public_link_token" in body
        assert body["survey_path"].startswith("/survey/")
        assert len(body["public_link_token"]) > 30
        assert body["status_label"] == "pendiente"

    def test_cannot_generate_form_for_open_ticket(self, client, db_session) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        _seed_user(
            db_session,
            role_key="admin_crm",
            auth_user_id="auth-admin",
            email="admin.crm@microtv.com",
            display_name="Admin CRM",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        # Ticket is still OPEN/IN_PROGRESS — must fail
        form_resp = client.post(
            f"/tickets/{ticket_id}/generate-survey",
            headers=_auth("admin-token"),
        )
        assert form_resp.status_code == 403, form_resp.text

    def test_cannot_generate_form_for_closed_ticket_without_executive_approval(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        _seed_user(
            db_session,
            role_key="admin_crm",
            auth_user_id="auth-admin",
            email="admin.crm@microtv.com",
            display_name="Admin CRM",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        close_attachment = _upload_video_attachment(client, ticket_id, "admin-token", tmp_path)
        close_attachment_id = close_attachment.get("id") or close_attachment.get("attachment_id")
        assert close_attachment_id
        close_resp = client.patch(
            f"/tickets/{ticket_id}/close",
            headers=_auth("admin-token"),
            json={"comment": "Cierre administrativo directo.", "attachment_ids": [close_attachment_id]},
        )
        assert close_resp.status_code == 200, close_resp.text
        assert close_resp.json()["status"] == "CLOSED"

        form_resp = client.post(
            f"/tickets/{ticket_id}/generate-survey",
            headers=_auth("admin-token"),
        )
        assert form_resp.status_code == 403, form_resp.text

    def test_public_form_returns_safe_info(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        _seed_user(
            db_session,
            role_key="admin_crm",
            auth_user_id="auth-admin",
            email="admin.crm@microtv.com",
            display_name="Admin CRM",
        )
        _seed_user(
            db_session,
            role_key="ejecutivo",
            auth_user_id="auth-ejecutivo",
            email="ejecutivo@ycc.com",
            display_name="Ejecutivo",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket_data = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket_data["ticket_id"]

        _close_and_approve_ticket(client, ticket_id, tmp_path)

        # Generate form
        form_resp = client.post(f"/tickets/{ticket_id}/generate-survey", headers=_auth("admin-token"))
        assert form_resp.status_code == 200, form_resp.text
        token = form_resp.json()["public_link_token"]

        # GET public info — no auth
        public_resp = client.get(f"/public/tickets/satisfaction/{token}")
        assert public_resp.status_code == 200, public_resp.text
        public_body = public_resp.json()
        assert "ticket_id" not in public_body
        assert "form_id" not in public_body
        assert "ticket_number" in public_body

    def test_invalid_token_returns_404(self, client, db_session) -> None:
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()
        resp = client.get("/public/tickets/satisfaction/invalid-fake-token-that-does-not-exist")
        assert resp.status_code == 404, resp.text

    def test_public_submit_stores_customer_identity_and_media_detail(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        _seed_user(
            db_session,
            role_key="admin_crm",
            auth_user_id="auth-admin",
            email="admin.crm@microtv.com",
            display_name="Admin CRM",
        )
        _seed_user(
            db_session,
            role_key="ejecutivo",
            auth_user_id="auth-ejecutivo",
            email="ejecutivo@ycc.com",
            display_name="Ejecutivo",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket_data = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket_data["ticket_id"]
        _close_and_approve_ticket(client, ticket_id, tmp_path)

        form_resp = client.post(f"/tickets/{ticket_id}/generate-survey", headers=_auth("admin-token"))
        assert form_resp.status_code == 200, form_resp.text
        token = form_resp.json()["public_link_token"]

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
        submit_resp = client.post(
            f"/public/tickets/satisfaction/{token}",
            data={
                "rating": "4.5",
                "customer_name": "Juan Perez",
                "customer_company": "Cliente SA",
                "comment": "Muy buena atención.",
            },
            files=[("files", ("foto.png", BytesIO(image_bytes), "image/png"))],
        )
        assert submit_resp.status_code == 200, submit_resp.text
        body = submit_resp.json()
        assert body["customer_name"] == "Juan Perez"
        assert body["customer_company"] == "Cliente SA"
        assert body["media_count"] == 1
        assert len(body["media_files"]) == 1
        assert body["media_files"][0]["file_type"] == "image/png"
        assert body["media_files"][0]["file_path"].startswith("/images/satisfaction/")

        private_resp = client.get(f"/tickets/{ticket_id}/satisfaction-form/response", headers=_auth("admin-token"))
        assert private_resp.status_code == 200, private_resp.text
        private_body = private_resp.json()
        assert private_body["customer_name"] == "Juan Perez"
        assert private_body["customer_company"] == "Cliente SA"
        assert private_body["media_count"] == 1
        assert private_body["media_files"][0]["survey_id"]


class TestTicketExportHistory:
    def test_export_requires_executive_approval(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        _seed_user(
            db_session,
            role_key="admin_crm",
            auth_user_id="auth-admin",
            email="admin.crm@microtv.com",
            display_name="Admin CRM",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        close_attachment = _upload_video_attachment(client, ticket_id, "admin-token", tmp_path)
        close_attachment_id = close_attachment.get("id") or close_attachment.get("attachment_id")
        assert close_attachment_id
        close_resp = client.patch(
            f"/tickets/{ticket_id}/close",
            headers=_auth("admin-token"),
            json={"comment": "Cierre administrativo directo.", "attachment_ids": [close_attachment_id]},
        )
        assert close_resp.status_code == 200, close_resp.text

        export_resp = client.get(f"/tickets/{ticket_id}/export", headers=_auth("admin-token"))
        assert export_resp.status_code == 403, export_resp.text

    def test_export_returns_zip_with_pdf_and_media(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        _seed_user(
            db_session,
            role_key="admin_crm",
            auth_user_id="auth-admin",
            email="admin.crm@microtv.com",
            display_name="Admin CRM",
        )
        _seed_user(
            db_session,
            role_key="ejecutivo",
            auth_user_id="auth-ejecutivo",
            email="ejecutivo@ycc.com",
            display_name="Ejecutivo",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        _close_and_approve_ticket(client, ticket_id, tmp_path)

        export_resp = client.get(f"/tickets/{ticket_id}/export", headers=_auth("admin-token"))
        assert export_resp.status_code == 200, export_resp.text
        assert export_resp.headers.get("content-type", "").startswith("application/zip")

        with zipfile.ZipFile(BytesIO(export_resp.content), "r") as zip_file:
            names = zip_file.namelist()
            ticket_number = ticket["ticket_number"]
            assert f"ticket_{ticket_number}.pdf" in names
            assert any(name.startswith("media/") for name in names)
