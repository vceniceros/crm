"""Tests for arrival registration (US-1) and satisfaction form (US-2)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ---------------------------------------------------------------------------
# US-1: Arrival registration
# ---------------------------------------------------------------------------


class TestArrivalRegistration:
    def test_technician_can_register_arrival_with_video(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        attachment = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)

        resp = client.post(
            f"/tickets/{ticket_id}/arrival",
            headers=_auth("tech-token"),
            json={"body": "Llegué al domicilio del cliente.", "attachment_ids": [attachment["attachment_id"]]},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        arrival_comments = [c for c in body["comments"] if c.get("comment_type") == "arrival_registration"]
        assert len(arrival_comments) == 1
        assert arrival_comments[0]["body"] == "Llegué al domicilio del cliente."

    def test_cannot_register_arrival_without_attachment(self, client, db_session) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        resp = client.post(
            f"/tickets/{ticket_id}/arrival",
            headers=_auth("tech-token"),
            json={"body": "Llegué.", "attachment_ids": []},
        )
        assert resp.status_code == 422, resp.text

    def test_cannot_register_arrival_twice(self, client, db_session, tmp_path) -> None:
        tech = _seed_user(
            db_session,
            role_key="tecnico_campo",
            auth_user_id="auth-tech",
            email="tecnico.crm@yccbrothers.com",
            display_name="Tecnico",
        )
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        attachment = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        attach_ids = [attachment["attachment_id"]]

        # First registration must succeed
        resp = client.post(
            f"/tickets/{ticket_id}/arrival",
            headers=_auth("tech-token"),
            json={"body": "Primera llegada.", "attachment_ids": attach_ids},
        )
        assert resp.status_code == 200, resp.text

        # Second registration must fail
        resp2 = client.post(
            f"/tickets/{ticket_id}/arrival",
            headers=_auth("tech-token"),
            json={"body": "Intento repetido.", "attachment_ids": attach_ids},
        )
        assert resp2.status_code == 409, resp2.text


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
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket["ticket_id"]

        # Register arrival
        arrival_attachment = _upload_video_attachment(client, ticket_id, "tech-token", tmp_path)
        client.post(
            f"/tickets/{ticket_id}/arrival",
            headers=_auth("tech-token"),
            json={"body": "Llegué.", "attachment_ids": [arrival_attachment["attachment_id"]]},
        )

        # Close ticket with video (admin bypasses arrival check)
        close_attachment = _upload_video_attachment(client, ticket_id, "admin-token", tmp_path)
        close_resp = client.patch(
            f"/tickets/{ticket_id}/close",
            headers=_auth("admin-token"),
            json={"comment": "Cierre administrativo.", "attachment_ids": [close_attachment["attachment_id"]]},
        )
        assert close_resp.status_code == 200, close_resp.text

        # Generate satisfaction form
        form_resp = client.post(
            f"/tickets/{ticket_id}/satisfaction-form",
            headers=_auth("admin-token"),
        )
        assert form_resp.status_code == 200, form_resp.text
        body = form_resp.json()
        assert "public_link_token" in body
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
            f"/tickets/{ticket_id}/satisfaction-form",
            headers=_auth("admin-token"),
        )
        assert form_resp.status_code == 409, form_resp.text

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
        client_entity, location = _seed_client_and_location(db_session)
        client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeTicketAuthAdapter()

        ticket_data = _create_and_assign_ticket(client, db_session, tech_user=tech, client_entity=client_entity, location=location)
        ticket_id = ticket_data["ticket_id"]

        # Close ticket
        close_attachment = _upload_video_attachment(client, ticket_id, "admin-token", tmp_path)
        client.patch(
            f"/tickets/{ticket_id}/close",
            headers=_auth("admin-token"),
            json={"comment": "Cierre.", "attachment_ids": [close_attachment["attachment_id"]]},
        )

        # Generate form
        form_resp = client.post(f"/tickets/{ticket_id}/satisfaction-form", headers=_auth("admin-token"))
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
