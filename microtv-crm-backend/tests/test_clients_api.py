"""Clients module API tests."""

from __future__ import annotations

from sqlalchemy import select

from crm_backend.adapters.auth_service_adapter import ActiveMembershipContext, AuthenticatedAuthResult
from crm_backend.api.dependencies import get_auth_service_adapter
from crm_backend.models import Client, ClientLocation, CrmRole, CrmUser, CrmUserRole, Location


class FakeClientsAuthAdapter:
    """Fake auth adapter returning deterministic CRM sessions."""

    USER_FIXTURES = {
        "admin-token": {
            "auth_user_id": "auth-admin",
            "email": "admin.crm@microtv.com",
            "display_name": "Admin CRM",
            "roles": ["platform_admin"],
            "tenant_id": "MICROTV",
        },
        "ejecutivo-token": {
            "auth_user_id": "auth-ejecutivo",
            "email": "ejecutivo.crm@yccbrothers.com",
            "display_name": "Ejecutivo CRM",
            "roles": ["ejecutivo"],
            "tenant_id": "YCC",
        },
        "tech-token": {
            "auth_user_id": "auth-tech",
            "email": "tecnico.campo@yccbrothers.com",
            "display_name": "Tecnico Campo",
            "roles": [],
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


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def _seed_client(db_session, *, business_name: str = "Cliente Acme SA", tax_id: str = "30-12345678-9") -> Client:
    client = Client(
        business_name=business_name,
        tax_id=tax_id,
        email="operaciones@acme.test",
        phone="11-5555-0000",
        is_active=True,
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


def test_tecnico_can_list_clients_with_real_persistence(client, db_session) -> None:
    """`GET /clients` debe permitir lectura al técnico cuando el cliente existe en la BD."""

    _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.campo@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    seeded_client = _seed_client(db_session)
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeClientsAuthAdapter()

    response = client.get("/clients", headers=_auth_header("tech-token"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["client_id"] == seeded_client.client_id
    assert body[0]["business_name"] == "Cliente Acme SA"
    assert body[0]["tax_id"] == "30-12345678-9"
    assert body[0]["is_active"] is True


def test_admin_can_create_and_delete_client(client, db_session) -> None:
    """`POST` y `DELETE /clients` deben persistir alta y baja lógica para admin."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeClientsAuthAdapter()

    create_response = client.post(
        "/clients",
        headers=_auth_header("admin-token"),
        json={
            "business_name": "Cliente Beta SRL",
            "tax_id": "30-98765432-1",
            "email": "beta@test.com",
            "phone": "11-4444-2222",
            "location": {
                "latitude": -34.6037,
                "longitude": -58.3816,
                "address_label": "Casa central CABA",
                "formatted_address": "Casa central CABA"
            },
        },
    )

    assert create_response.status_code == 201, create_response.text
    created_body = create_response.json()
    assert created_body["business_name"] == "Cliente Beta SRL"
    assert created_body["tax_id"] == "30-98765432-1"
    assert created_body["is_active"] is True
    assert created_body["location"]["latitude"] == -34.6037
    assert created_body["location"]["longitude"] == -58.3816
    assert created_body["location"]["address_label"] == "Casa central CABA"

    client_id = created_body["client_id"]
    persisted_client = db_session.scalar(select(Client).where(Client.client_id == client_id))
    if persisted_client is None:
        raise AssertionError("No se encontró el cliente recién creado en la base.")

    assert persisted_client.deleted_at is None
    assert persisted_client.is_active is True

    client_location = db_session.scalar(select(ClientLocation).where(ClientLocation.client_id == client_id))
    if client_location is None:
        raise AssertionError("No se encontró la relación cliente-ubicación recién creada.")

    persisted_location = db_session.scalar(select(Location).where(Location.location_id == client_location.location_id))
    if persisted_location is None:
        raise AssertionError("No se encontró la ubicación recién creada para el cliente.")

    assert float(persisted_location.latitude) == -34.6037
    assert float(persisted_location.longitude) == -58.3816
    assert persisted_location.address_label == "Casa central CABA"

    delete_response = client.delete(f"/clients/{client_id}", headers=_auth_header("admin-token"))

    assert delete_response.status_code == 204, delete_response.text

    db_session.expire_all()
    deleted_client = db_session.scalar(select(Client).where(Client.client_id == client_id))
    if deleted_client is None:
        raise AssertionError("No se encontró el cliente eliminado para validar la baja lógica.")

    assert deleted_client.is_active is False
    assert deleted_client.deleted_at is not None

    list_response = client.get("/clients", headers=_auth_header("admin-token"))
    assert list_response.status_code == 200
    assert all(item["client_id"] != client_id for item in list_response.json())


def test_ejecutivo_can_create_and_delete_client(client) -> None:
    """El rol ejecutivo debe poder operar altas y bajas reales de clientes."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeClientsAuthAdapter()

    create_response = client.post(
        "/clients",
        headers=_auth_header("ejecutivo-token"),
        json={
            "business_name": "Cliente Ejecutivo SAS",
            "tax_id": "30-22223333-4",
            "email": "ejecutivo@test.com",
            "phone": "11-7000-1000",
            "location": None,
        },
    )

    assert create_response.status_code == 201, create_response.text
    client_id = create_response.json()["client_id"]

    delete_response = client.delete(f"/clients/{client_id}", headers=_auth_header("ejecutivo-token"))
    assert delete_response.status_code == 204, delete_response.text


def test_tecnico_cannot_create_and_duplicate_tax_id_is_rejected(client, db_session) -> None:
    """El técnico no debe poder escribir y el CUIT duplicado debe devolver 409."""

    _seed_local_role_user(
        db_session,
        role_key="tecnico_campo",
        auth_user_id="auth-tech",
        email="tecnico.campo@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    _seed_client(db_session, business_name="Cliente Duplicado", tax_id="30-11112222-3")
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeClientsAuthAdapter()

    forbidden_response = client.post(
        "/clients",
        headers=_auth_header("tech-token"),
        json={
            "business_name": "Cliente No Permitido",
            "tax_id": "30-99999999-9",
            "email": "tech@test.com",
            "phone": "11-8888-9999",
        },
    )

    assert forbidden_response.status_code == 403, forbidden_response.text
    assert forbidden_response.json()["error"]["code"] == "client_access_denied"

    duplicate_response = client.post(
        "/clients",
        headers=_auth_header("admin-token"),
        json={
            "business_name": "Cliente Duplicado 2",
            "tax_id": "30-11112222-3",
            "email": "duplicado@test.com",
            "phone": "11-1010-2020",
        },
    )

    assert duplicate_response.status_code == 409, duplicate_response.text
    assert duplicate_response.json()["error"]["code"] == "client_tax_id_duplicated"


def test_admin_can_get_and_update_client_with_real_location(client, db_session) -> None:
    """`GET` y `PUT /clients/{id}` deben exponer y persistir edición real con ubicación."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeClientsAuthAdapter()

    create_response = client.post(
        "/clients",
        headers=_auth_header("admin-token"),
        json={
            "business_name": "Cliente Editar SA",
            "tax_id": "30-44445555-6",
            "email": "editar@test.com",
            "phone": "11-9999-0000",
            "location": {
                "latitude": -34.6001,
                "longitude": -58.3801,
                "address_label": "Oficina inicial",
                "formatted_address": "Oficina inicial"
            },
        },
    )

    assert create_response.status_code == 201, create_response.text
    client_id = create_response.json()["client_id"]

    detail_response = client.get(f"/clients/{client_id}", headers=_auth_header("admin-token"))

    assert detail_response.status_code == 200, detail_response.text
    detail_body = detail_response.json()
    assert detail_body["business_name"] == "Cliente Editar SA"
    assert detail_body["location"]["address_label"] == "Oficina inicial"

    update_response = client.put(
        f"/clients/{client_id}",
        headers=_auth_header("admin-token"),
        json={
            "business_name": "Cliente Editado SA",
            "tax_id": "30-44445555-6",
            "email": "editado@test.com",
            "phone": "11-9999-1111",
            "is_active": True,
            "location": {
                "latitude": -34.615,
                "longitude": -58.433,
                "address_label": "Sucursal Palermo",
                "formatted_address": "Sucursal Palermo"
            },
        },
    )

    assert update_response.status_code == 200, update_response.text
    updated_body = update_response.json()
    assert updated_body["business_name"] == "Cliente Editado SA"
    assert updated_body["email"] == "editado@test.com"
    assert updated_body["phone"] == "11-9999-1111"
    assert updated_body["location"]["latitude"] == -34.615
    assert updated_body["location"]["longitude"] == -58.433
    assert updated_body["location"]["address_label"] == "Sucursal Palermo"

    db_session.expire_all()
    persisted_client = db_session.scalar(select(Client).where(Client.client_id == client_id))
    if persisted_client is None:
        raise AssertionError("No se encontró el cliente actualizado.")

    assert persisted_client.business_name == "Cliente Editado SA"
    assert persisted_client.email == "editado@test.com"

    client_location = db_session.scalar(select(ClientLocation).where(ClientLocation.client_id == client_id))
    if client_location is None:
        raise AssertionError("No se encontró la relación primaria cliente-ubicación tras la edición.")

    persisted_location = db_session.scalar(select(Location).where(Location.location_id == client_location.location_id))
    if persisted_location is None:
        raise AssertionError("No se encontró la ubicación actualizada del cliente.")

    assert float(persisted_location.latitude) == -34.615
    assert float(persisted_location.longitude) == -58.433
    assert persisted_location.address_label == "Sucursal Palermo"


def test_admin_can_remove_client_location_on_update(client) -> None:
    """`PUT /clients/{id}` debe permitir limpiar la ubicación primaria del cliente."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeClientsAuthAdapter()

    create_response = client.post(
        "/clients",
        headers=_auth_header("admin-token"),
        json={
            "business_name": "Cliente Sin Ubicacion",
            "tax_id": "30-66667777-8",
            "email": "sinubicacion@test.com",
            "phone": "11-1234-5678",
            "location": {
                "latitude": -34.61,
                "longitude": -58.39,
                "address_label": "Punto inicial",
                "formatted_address": "Punto inicial"
            },
        },
    )

    client_id = create_response.json()["client_id"]

    update_response = client.put(
        f"/clients/{client_id}",
        headers=_auth_header("admin-token"),
        json={
            "business_name": "Cliente Sin Ubicacion",
            "tax_id": "30-66667777-8",
            "email": "sinubicacion@test.com",
            "phone": "11-1234-5678",
            "is_active": True,
            "location": None,
        },
    )

    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["location"] is None