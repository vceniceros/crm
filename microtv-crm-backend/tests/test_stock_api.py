"""Pruebas del módulo real inicial de depósito."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from crm_backend.adapters.auth_service_adapter import ActiveMembershipContext, AuthenticatedAuthResult
from crm_backend.api.dependencies import get_auth_service_adapter
from crm_backend.core.config import get_settings
from crm_backend.models import CrmRole, CrmUser, CrmUserRole, StockProduct


PNG_1X1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082"
)


class FakeStockAuthAdapter:
    """Adapter fake para probar endpoints protegidos de depósito."""

    def __init__(self, *, tenant_id: str = "YCC", roles: list[str] | None = None) -> None:
        """Crea el adapter fake.

        Args:
            tenant_id: Tenant devuelto por auth.
            roles: Roles externos activos.
        """

        self._tenant_id = tenant_id
        self._roles = ["company_operator"] if roles is None else roles

    def validate_access_token(self, access_token: str) -> AuthenticatedAuthResult:
        """Resuelve un token fake hacia una sesión autenticada.

        Args:
            access_token: Token ignorado.

        Returns:
            AuthenticatedAuthResult: Resultado autenticado determinístico.
        """

        return AuthenticatedAuthResult(
            access_token=access_token,
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=3600,
            refresh_expires_in=86400,
            auth_user_id=f"auth-user-{self._tenant_id.lower()}",
            email="operador.crm@yccbrothers.com",
            display_name="Operador Deposito YCC",
            active_membership=ActiveMembershipContext(
                membership_id="membership-ycc",
                tenant_type="company",
                tenant_id=self._tenant_id,
                roles=self._roles,
            ),
            claims={
                "sub": f"auth-user-{self._tenant_id.lower()}",
                "email": "operador.crm@yccbrothers.com",
            },
        )

    def login(self, *, email: str, password: str):
        """No se usa en estas pruebas."""

        raise NotImplementedError


def _seed_local_role_user(db_session, *, role_key: str, auth_user_id: str = "auth-user-ycc", email: str = "operador.crm@yccbrothers.com", display_name: str) -> None:
    role = db_session.scalar(select(CrmRole).where(CrmRole.role_key == role_key))
    if role is None:
        raise AssertionError(f"No se encontró el rol {role_key} seed.")

    crm_user = CrmUser(
        auth_user_id=auth_user_id,
        email=email,
        display_name=display_name,
    )
    crm_user.assigned_roles.append(
        CrmUserRole(
            crm_role_id=role.crm_role_id,
            role=role,
        )
    )
    db_session.add(crm_user)
    db_session.commit()


def test_list_categories_requires_authenticated_deposito_ycc(client) -> None:
    """`GET /stock/categories` debe devolver categorías reales para depósito YCC."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    response = client.get("/stock/categories", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 8
    assert any(category["name"] == "Cargadores" for category in body)


def test_list_products_returns_seeded_products(client) -> None:
    """`GET /stock/products` debe listar productos persistidos."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body[0]["id"], str)
    assert UUID(body[0]["id"])
    assert any(product["name"] == "Fuente switching 12V 5A" for product in body)


def test_admin_can_access_stock_even_outside_ycc_tenant(client) -> None:
    """Admin debe poder operar depósito aunque su contexto no sea YCC."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(
        tenant_id="MICROTV",
        roles=["platform_admin"],
    )

    response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_ejecutivo_can_view_stock_products_and_categories(client, db_session) -> None:
    """El rol ejecutivo debe poder consultar categorías y productos de depósito."""

    _seed_local_role_user(db_session, role_key="ejecutivo", display_name="Ejecutivo YCC")
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(roles=[])

    categories_response = client.get("/stock/categories", headers={"Authorization": "Bearer access-token"})
    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})

    assert categories_response.status_code == 200
    assert products_response.status_code == 200
    assert any(category["name"] == "Cargadores" for category in categories_response.json())
    assert any(product["name"] == "Fuente switching 12V 5A" for product in products_response.json())


def test_create_product_persists_new_product(client) -> None:
    """`POST /stock/products` debe crear un producto real con stock inicial."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    categories_response = client.get("/stock/categories", headers={"Authorization": "Bearer access-token"})
    category_id = next(category["id"] for category in categories_response.json() if category["name"] == "Varios")

    response = client.post(
        "/stock/products",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": "Cable HDMI 2m",
            "product_code": "PRD-CABLE-HDMI-2M-001",
            "category_id": category_id,
            "initial_stock": 4,
            "image_url": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Cable HDMI 2m"
    assert body["product_code"] == "PRD-CABLE-HDMI-2M-001"
    assert body["current_stock"] == 4
    assert body["category_name"] == "Varios"


def test_create_product_rejects_duplicated_product_code(client) -> None:
    """`POST /stock/products` debe rechazar códigos duplicados con 409."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    categories_response = client.get("/stock/categories", headers={"Authorization": "Bearer access-token"})
    category_id = next(category["id"] for category in categories_response.json() if category["name"] == "Varios")

    payload = {
        "name": "Cable HDMI 5m",
        "product_code": "PRD-CABLE-HDMI-5M-001",
        "category_id": category_id,
        "initial_stock": 2,
        "image_url": None,
    }

    first_response = client.post("/stock/products", headers={"Authorization": "Bearer access-token"}, json=payload)
    second_response = client.post(
        "/stock/products",
        headers={"Authorization": "Bearer access-token"},
        json={**payload, "name": "Cable HDMI 5m duplicado"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "stock_product_code_duplicated"


def test_create_product_accepts_multipart_image_upload(client) -> None:
    """`POST /stock/products` debe persistir una imagen multipart y devolver su URL pública."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    categories_response = client.get("/stock/categories", headers={"Authorization": "Bearer access-token"})
    category_id = next(category["id"] for category in categories_response.json() if category["name"] == "Varios")
    response = client.post(
        "/stock/products",
        headers={"Authorization": "Bearer access-token"},
        data={
            "product_name": "Cable UTP interior",
            "product_code": "PRD-UTP-INT-001",
            "category_id": category_id,
            "stock_initial": "6",
        },
        files={"image": ("utp.png", PNG_1X1, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_code"] == "PRD-UTP-INT-001"
    assert body["image_url"].endswith(".png")

    image_path = get_settings().resolve_media_filesystem_path(body["image_url"]) or (get_settings().public_dir / Path(body["image_url"].lstrip("/")))
    try:
        assert image_path.exists()
    finally:
        if image_path.exists():
            image_path.unlink()


def test_deposito_can_edit_product_details_and_stock(client, db_session) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")
    categories_response = client.get("/stock/categories", headers={"Authorization": "Bearer access-token"})
    category_id = next(category["id"] for category in categories_response.json() if category["name"] == "Varios")

    response = client.patch(
        f"/stock/products/{product['product_id']}",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": "Splitter HDMI 1x4 editado",
            "product_code": "PRD-SPLITTER-EDIT-001",
            "category_id": category_id,
            "current_stock": 9,
            "minimum_stock": 5,
            "shelf_id": "B",
            "shelf_height": 2,
            "requires_tracking": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Splitter HDMI 1x4 editado"
    assert body["product_code"] == "PRD-SPLITTER-EDIT-001"
    assert body["category_name"] == "Varios"
    assert body["current_stock"] == 9
    assert body["minimum_stock"] == 5
    assert body["shelf_id"] == "B"
    assert body["shelf_height"] == 2
    assert body["requires_tracking"] is True

    db_session.expire_all()
    persisted = db_session.scalar(select(StockProduct).where(StockProduct.product_id == product["product_id"]))
    assert persisted is not None
    assert persisted.current_stock == 9
    assert persisted.product_code == "PRD-SPLITTER-EDIT-001"


def test_admin_can_edit_product_outside_ycc_tenant(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(
        tenant_id="MICROTV",
        roles=["platform_admin"],
    )

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    response = client.patch(
        f"/stock/products/{product['product_id']}",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": "Splitter admin edit",
            "product_code": "PRD-SPLITTER-ADMIN-EDIT-001",
            "category_id": product["category_id"],
            "current_stock": product["current_stock"],
            "minimum_stock": product["minimum_stock"],
            "requires_tracking": product["requires_tracking"],
        },
    )

    assert response.status_code == 200
    assert response.json()["product_code"] == "PRD-SPLITTER-ADMIN-EDIT-001"


def test_ejecutivo_cannot_edit_product(client, db_session) -> None:
    _seed_local_role_user(db_session, role_key="ejecutivo", display_name="Ejecutivo YCC")
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(roles=[])

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    response = client.patch(
        f"/stock/products/{product['product_id']}",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": "Splitter ejecutivo edit",
            "product_code": "PRD-SPLITTER-EJEC-EDIT-001",
            "category_id": product["category_id"],
            "current_stock": product["current_stock"],
            "minimum_stock": product["minimum_stock"],
            "requires_tracking": product["requires_tracking"],
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inventory_access_denied"


def test_edit_product_rejects_duplicate_product_code(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    products = products_response.json()
    target = next(product for product in products if product["name"] == "Splitter HDMI 1x4")
    existing = next(product for product in products if product["product_id"] != target["product_id"])

    response = client.patch(
        f"/stock/products/{target['product_id']}",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": target["name"],
            "product_code": existing["product_code"],
            "category_id": target["category_id"],
            "current_stock": target["current_stock"],
            "minimum_stock": target["minimum_stock"],
            "requires_tracking": target["requires_tracking"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stock_product_code_duplicated"


def test_edit_product_replaces_image_when_uploaded(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    response = client.patch(
        f"/stock/products/{product['product_id']}",
        headers={"Authorization": "Bearer access-token"},
        data={
            "product_name": product["name"],
            "product_code": "PRD-SPLITTER-IMAGE-EDIT-001",
            "category_id": product["category_id"],
            "current_stock": str(product["current_stock"]),
            "minimum_stock": str(product["minimum_stock"]),
            "requires_tracking": str(product["requires_tracking"]).lower(),
        },
        files={"image": ("splitter-edit.png", PNG_1X1, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["image_url"].endswith(".png")

    image_path = get_settings().resolve_media_filesystem_path(body["image_url"]) or (get_settings().public_dir / Path(body["image_url"].lstrip("/")))
    try:
        assert image_path.exists()
    finally:
        if image_path.exists():
            image_path.unlink()


def test_edit_product_without_image_keeps_existing_image(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product = next(product for product in products_response.json() if product["image_url"])
    original_image_url = product["image_url"]

    response = client.patch(
        f"/stock/products/{product['product_id']}",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": f"{product['name']} editado",
            "product_code": "PRD-KEEP-IMAGE-EDIT-001",
            "category_id": product["category_id"],
            "current_stock": product["current_stock"],
            "minimum_stock": product["minimum_stock"],
            "requires_tracking": product["requires_tracking"],
        },
    )

    assert response.status_code == 200
    assert response.json()["image_url"] == original_image_url


def test_edit_product_rejects_negative_stock(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    response = client.patch(
        f"/stock/products/{product['product_id']}",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": product["name"],
            "product_code": "PRD-SPLITTER-NEGATIVE-EDIT-001",
            "category_id": product["category_id"],
            "current_stock": -1,
            "minimum_stock": product["minimum_stock"],
            "requires_tracking": product["requires_tracking"],
        },
    )

    assert response.status_code == 422


def test_admin_can_delete_product_with_soft_delete(client, db_session) -> None:
    """`DELETE /stock/products/{id}` debe dar de baja lógica el producto cuando actúa admin."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(
        tenant_id="MICROTV",
        roles=["platform_admin"],
    )

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product_id = next(product["id"] for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    delete_response = client.delete(f"/stock/products/{product_id}", headers={"Authorization": "Bearer access-token"})

    assert delete_response.status_code == 204

    db_session.expire_all()
    persisted_product = db_session.scalar(select(StockProduct).where(StockProduct.product_id == product_id))
    if persisted_product is None:
        raise AssertionError("No se encontró el producto eliminado para validar la baja lógica.")

    assert persisted_product.is_active is False
    assert persisted_product.deleted_at is not None

    refreshed_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    assert all(product["id"] != product_id for product in refreshed_response.json())


def test_non_admin_cannot_delete_product(client) -> None:
    """`DELETE /stock/products/{id}` debe rechazar a usuarios no administradores."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product_id = next(product["id"] for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    response = client.delete(f"/stock/products/{product_id}", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inventory_admin_required"


def test_ejecutivo_cannot_create_product(client, db_session) -> None:
    """El rol ejecutivo no debe poder cargar productos nuevos."""

    _seed_local_role_user(db_session, role_key="ejecutivo", display_name="Ejecutivo YCC")
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(roles=[])

    categories_response = client.get("/stock/categories", headers={"Authorization": "Bearer access-token"})
    category_id = next(category["id"] for category in categories_response.json() if category["name"] == "Varios")

    response = client.post(
        "/stock/products",
        headers={"Authorization": "Bearer access-token"},
        json={
            "name": "Cable de prueba ejecutivo",
            "product_code": "PRD-EJECUTIVO-READONLY-001",
            "category_id": category_id,
            "initial_stock": 1,
            "image_url": None,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inventory_access_denied"


def test_ejecutivo_cannot_adjust_stock(client, db_session) -> None:
    """El rol ejecutivo no debe poder sumar ni restar stock."""

    _seed_local_role_user(db_session, role_key="ejecutivo", display_name="Ejecutivo YCC")
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(roles=[])

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product_id = next(product["id"] for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    increase_response = client.post(
        f"/stock/products/{product_id}/increase-stock",
        headers={"Authorization": "Bearer access-token"},
        json={"quantity": 1},
    )
    decrease_response = client.post(
        f"/stock/products/{product_id}/decrease-stock",
        headers={"Authorization": "Bearer access-token"},
        json={"quantity": 1},
    )

    assert increase_response.status_code == 403
    assert decrease_response.status_code == 403
    assert increase_response.json()["error"]["code"] == "inventory_access_denied"
    assert decrease_response.json()["error"]["code"] == "inventory_access_denied"


def test_ejecutivo_cannot_delete_product(client, db_session) -> None:
    """`DELETE /stock/products/{id}` debe rechazar al rol ejecutivo."""

    _seed_local_role_user(db_session, role_key="ejecutivo", display_name="Ejecutivo YCC")

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(roles=[])

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product_id = next(product["id"] for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    response = client.delete(f"/stock/products/{product_id}", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inventory_admin_required"


def test_increase_and_decrease_stock_updates_product(client) -> None:
    """Los ajustes de stock deben persistir y reflejarse en la API."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product_id = next(product["id"] for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")

    increase_response = client.post(
        f"/stock/products/{product_id}/increase-stock",
        headers={"Authorization": "Bearer access-token"},
        json={"quantity": 3},
    )
    decrease_response = client.post(
        f"/stock/products/{product_id}/decrease-stock",
        headers={"Authorization": "Bearer access-token"},
        json={"quantity": 2},
    )

    assert increase_response.status_code == 200
    assert increase_response.json()["current_stock"] == 5
    assert decrease_response.status_code == 200
    assert decrease_response.json()["current_stock"] == 3


def test_decrease_stock_rejects_negative_result(client) -> None:
    """No debe permitir bajar stock por debajo de cero."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    product_id = next(product["id"] for product in products_response.json() if product["name"] == "Driver de retroiluminacion monitor 24")

    response = client.post(
        f"/stock/products/{product_id}/decrease-stock",
        headers={"Authorization": "Bearer access-token"},
        json={"quantity": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"


def test_stock_endpoints_reject_non_ycc_membership(client) -> None:
    """El módulo debe quedar limitado al tenant YCC para esta etapa."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(tenant_id="MICROTV")

    response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inventory_access_denied"


def test_ycc_operator_with_existing_tech_role_gains_deposito_access(client, db_session) -> None:
    """Un operador YCC ya provisionado como técnico debe sumar depósito automáticamente."""

    tech_role = db_session.scalar(select(CrmRole).where(CrmRole.role_key == "tecnico_campo"))
    if tech_role is None:
        raise AssertionError("No se encontró el rol tecnico_campo seed.")

    stale_user = CrmUser(
        auth_user_id="auth-user-ycc",
        email="operador.crm@yccbrothers.com",
        display_name="Operador Deposito YCC",
    )
    stale_user.assigned_roles.append(
        CrmUserRole(
            crm_role_id=tech_role.crm_role_id,
            role=tech_role,
        )
    )
    db_session.add(stale_user)
    db_session.commit()

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})

    db_session.refresh(stale_user)
    persisted_roles = sorted(assignment.role.role_key for assignment in stale_user.assigned_roles)

    assert response.status_code == 200
    assert "encargado_deposito" in persisted_roles


def test_stock_import_csv_preview_updates_existing_and_creates_new(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    existing = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")
    csv_content = (
        "imagen,codigo,producto,categoria,stock,ubication\n"
        f"https://example.test/splitter.png,{existing['product_code']},Splitter HDMI 1x4,Audio y video,4,A-3\n"
        "https://example.test/new.png,PRD-IMPORT-NEW-001,Producto importado,Varios,7,\n"
    )

    response = client.post(
        "/stock/imports/preview",
        headers={"Authorization": "Bearer access-token"},
        files={"file": ("stock.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["can_confirm"] is True
    assert body["updated_count"] == 1
    assert body["created_count"] == 1
    assert body["total_import_stock"] == 11
    existing_row = next(row for row in body["rows"] if row["product_code"] == existing["product_code"])
    assert existing_row["old_stock"] == existing["current_stock"]
    assert existing_row["new_stock"] == existing["current_stock"] + 4


def test_stock_import_xlsx_preview_accepts_valid_file(client) -> None:
    from openpyxl import Workbook

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["imagen", "codigo", "producto", "categoria", "stock", "ubication"])
    sheet.append(["https://example.test/xlsx.png", "PRD-XLSX-001", "Importado XLSX", "Varios", 3, "B/2"])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    response = client.post(
        "/stock/imports/preview",
        headers={"Authorization": "Bearer access-token"},
        files={"file": ("stock.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["can_confirm"] is True
    assert body["rows"][0]["ubication"] == "B-2"


def test_stock_import_preview_reports_validation_errors(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    csv_content = (
        "imagen,codigo,producto,categoria,stock,ubication\n"
        "https://example.test/a.png,PRD-DUP-001,Dup,Varios,2,A-1\n"
        "https://example.test/b.png,PRD-DUP-001,Dup again,Varios,2,A-2\n"
        "https://example.test/c.png,PRD-BAD-CAT,Bad,No existe,2,A-3\n"
        "https://example.test/d.png,PRD-BAD-LOC,Bad loc,Varios,2,pasillo\n"
    )

    response = client.post(
        "/stock/imports/preview",
        headers={"Authorization": "Bearer access-token"},
        files={"file": ("stock.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["can_confirm"] is False
    assert body["invalid_rows"] == 3
    errors = " ".join(error for row in body["rows"] for error in row["errors"])
    assert "duplicado" in errors
    assert "categoria" in errors
    assert "ubication" in errors


def test_stock_import_confirm_creates_backup_and_applies_transaction(client, db_session) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    existing = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")
    csv_content = (
        "imagen,codigo,producto,categoria,stock,ubication\n"
        f"https://example.test/splitter.png,{existing['product_code']},Splitter HDMI 1x4,Audio y video,5,A-4\n"
    )
    preview_response = client.post(
        "/stock/imports/preview",
        headers={"Authorization": "Bearer access-token"},
        files={"file": ("stock.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    confirm_response = client.post(
        f"/stock/imports/{preview_response.json()['import_id']}/confirm",
        headers={"Authorization": "Bearer access-token"},
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["backup_id"]
    assert body["products"][0]["current_stock"] == existing["current_stock"] + 5

    db_session.expire_all()
    product = db_session.scalar(select(StockProduct).where(StockProduct.product_code == existing["product_code"]))
    assert product is not None
    assert product.current_stock == existing["current_stock"] + 5


def test_stock_import_confirm_rejects_stale_preview(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    existing = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")
    csv_content = (
        "imagen,codigo,producto,categoria,stock,ubication\n"
        f"https://example.test/splitter.png,{existing['product_code']},Splitter HDMI 1x4,Audio y video,5,A-4\n"
    )
    preview_response = client.post(
        "/stock/imports/preview",
        headers={"Authorization": "Bearer access-token"},
        files={"file": ("stock.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    client.post(
        f"/stock/products/{existing['product_id']}/increase-stock",
        headers={"Authorization": "Bearer access-token"},
        json={"quantity": 1},
    )

    confirm_response = client.post(
        f"/stock/imports/{preview_response.json()['import_id']}/confirm",
        headers={"Authorization": "Bearer access-token"},
    )

    assert confirm_response.status_code == 409
    assert confirm_response.json()["error"]["code"] == "stock_import_conflict"


def test_admin_can_rollback_latest_stock_import(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    products_response = client.get("/stock/products", headers={"Authorization": "Bearer access-token"})
    existing = next(product for product in products_response.json() if product["name"] == "Splitter HDMI 1x4")
    csv_content = (
        "imagen,codigo,producto,categoria,stock,ubication\n"
        f"https://example.test/splitter.png,{existing['product_code']},Splitter HDMI 1x4,Audio y video,5,A-4\n"
        "https://example.test/new.png,PRD-ROLLBACK-NEW-001,Producto rollback,Varios,2,\n"
    )
    preview_response = client.post(
        "/stock/imports/preview",
        headers={"Authorization": "Bearer access-token"},
        files={"file": ("stock.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    confirm_response = client.post(
        f"/stock/imports/{preview_response.json()['import_id']}/confirm",
        headers={"Authorization": "Bearer access-token"},
    )

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter(
        tenant_id="MICROTV",
        roles=["platform_admin"],
    )
    rollback_response = client.post(
        f"/stock/imports/{confirm_response.json()['import_id']}/rollback",
        headers={"Authorization": "Bearer access-token"},
    )

    assert rollback_response.status_code == 200
    products_after = client.get("/stock/products", headers={"Authorization": "Bearer access-token"}).json()
    restored = next(product for product in products_after if product["product_code"] == existing["product_code"])
    assert restored["current_stock"] == existing["current_stock"]
    assert all(product["product_code"] != "PRD-ROLLBACK-NEW-001" for product in products_after)


def test_non_admin_cannot_rollback_stock_import(client) -> None:
    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeStockAuthAdapter()

    response = client.post("/stock/imports/00000000-0000-0000-0000-000000000000/rollback", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inventory_admin_required"
