"""Database bootstrap helpers."""

import os

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from crm_backend.db import Base
from crm_backend.models import CrmRole, CrmUser, CrmUserRole, StockCategory, StockProduct, Warehouse


ROLE_SEEDS = (
    ("admin_crm", "Administrador del CRM", "Acceso total al sistema CRM (NO implica platform_admin de auth)"),
    ("ejecutivo", "Ejecutivo", "Visualiza todos los modulos del CRM para seguimiento operativo y de gestion"),
    ("tecnico_campo", "Tecnico de Campo", "Ejecuta tareas y tickets en ubicaciones del cliente"),
    ("encargado_deposito", "Encargado de Deposito", "Gestiona inventario, despachos y recepciones"),
)

STOCK_CATEGORY_SEEDS = (
    {"name": "Audio y video"},
    {"name": "Reparados"},
    {"name": "Cargadores"},
    {"name": "Visualizacion"},
    {"name": "Sistemas Android"},
    {"name": "Sistemas TAMO"},
    {"name": "Repuestos de monitores"},
    {"name": "Varios"},
)

STOCK_PRODUCT_SEEDS = (
    {
        "name": "Fuente switching 12V 5A",
        "category_name": "Cargadores",
        "image_url": "https://placehold.co/96x96/e9eef3/4f5a66?text=12V",
        "stock": 12,
    },
    {
        "name": "Monitor LED 19 pulgadas reparado",
        "category_name": "Reparados",
        "image_url": "https://placehold.co/96x96/f1f4f7/5b6470?text=LED",
        "stock": 3,
    },
    {
        "name": "Placa main Android carteleria",
        "category_name": "Sistemas Android",
        "image_url": "https://placehold.co/96x96/edf3ec/54634f?text=AND",
        "stock": 7,
    },
    {
        "name": "Driver de retroiluminacion monitor 24",
        "category_name": "Repuestos de monitores",
        "image_url": "https://placehold.co/96x96/f6f0e8/6d5b42?text=DRV",
        "stock": 0,
    },
    {
        "name": "Modulo TAMO telemetria",
        "category_name": "Sistemas TAMO",
        "image_url": "https://placehold.co/96x96/e9f0f7/45617e?text=TMO",
        "stock": 5,
    },
    {
        "name": "Splitter HDMI 1x4",
        "category_name": "Audio y video",
        "image_url": "https://placehold.co/96x96/f0edf8/65578b?text=HDMI",
        "stock": 2,
    },
    {
        "name": "Soporte VESA universal",
        "category_name": "Visualizacion",
        "image_url": "https://placehold.co/96x96/edf1ef/536157?text=VESA",
        "stock": 9,
    },
    {
        "name": "Kit conectores y tornilleria",
        "category_name": "Varios",
        "image_url": None,
        "stock": 0,
    },
)


def _ensure_schema_ready(session: Session) -> None:
    if session.bind.dialect.name == "sqlite":
        return

    required_tables = {
        "crm_users",
        "crm_roles",
        "crm_user_roles",
        "warehouses",
        "inventory_categories",
        "inventory_products",
        "inventory_stock",
        "inventory_movements",
    }
    present_tables = set(session.bind.dialect.get_table_names(session.connection()))
    missing_tables = sorted(required_tables - present_tables)
    if missing_tables:
        missing = ", ".join(missing_tables)
        raise RuntimeError(
            f"Faltan tablas del schema v4 del CRM: {missing}. Ejecuta lab_start.bat para bootstrappear PostgreSQL antes de iniciar el backend."
        )


def initialize_database(session: Session) -> None:
    """Validate schema v4 and seed minimal operational data.

    Args:
        session: Active SQLAlchemy session.
    """

    _ensure_schema_ready(session)
    _ensure_extension_tables(session)

    existing_keys = {role.role_key for role in session.query(CrmRole).all()}
    for role_key, role_label, description in ROLE_SEEDS:
        if role_key in existing_keys:
            continue
        session.add(CrmRole(role_key=role_key, role_label=role_label, description=description))

    warehouse = session.scalar(select(Warehouse).order_by(Warehouse.created_at.asc()))
    if warehouse is None:
        warehouse = Warehouse(warehouse_name="Deposito Principal", address="Buenos Aires, Argentina")
        session.add(warehouse)
        session.flush()

    category_by_name = {category.name: category for category in session.query(StockCategory).all()}
    for seed in STOCK_CATEGORY_SEEDS:
        category = category_by_name.get(seed["name"])
        if category is None:
            category = StockCategory(category_name=seed["name"], is_active=True)
            session.add(category)
            session.flush()
            category_by_name[seed["name"]] = category
            continue
        category.category_name = seed["name"]
        category.is_active = True

    persisted_products = session.query(StockProduct).all()
    existing_products = {product.name for product in persisted_products}
    existing_product_codes = {product.product_code for product in persisted_products if product.product_code}
    for product in persisted_products:
        if product.product_code:
            continue
        candidate_code = product.visible_product_code
        if candidate_code in existing_product_codes:
            candidate_code = f"PRD-{product.stock_product_id[:8].upper()}"
        product.product_code = candidate_code
        existing_product_codes.add(candidate_code)

    for seed in STOCK_PRODUCT_SEEDS:
        if seed["name"] in existing_products:
            continue
        category = category_by_name[seed["category_name"]]
        session.add(
            StockProduct.create(
                name=seed["name"],
                product_code=StockProduct._build_product_code(name=seed["name"]),
                stock_category_id=category.stock_category_id,
                initial_stock=seed["stock"],
                image_url=seed["image_url"],
                requires_tracking=False,
                actor_crm_user_id=None,
                warehouse_id=warehouse.warehouse_id,
            )
        )

    _ensure_seed_tech_user(session)
    session.commit()


def _ensure_seed_tech_user(session: Session) -> None:
    if os.getenv("ENVIRONMENT", "development").lower() == "test":
        return

    auth_user_id = os.getenv("CRM_LOCAL_YCC_TECH_USER_ID", "auth-user-ycc-tech-001")
    email = os.getenv("CRM_LOCAL_YCC_TECH_EMAIL", "tecnico.campo@yccbrothers.com")
    display_name = os.getenv("CRM_LOCAL_YCC_TECH_DISPLAY_NAME", "Tecnico Campo YCC")

    role = session.scalar(select(CrmRole).where(CrmRole.role_key == "tecnico_campo"))
    if role is None:
        return

    crm_user = session.scalar(select(CrmUser).where(CrmUser.auth_user_id == auth_user_id))
    if crm_user is None:
        crm_user = CrmUser(auth_user_id=auth_user_id, email=email, display_name=display_name)
        session.add(crm_user)
        session.flush()
    else:
        crm_user.email = email
        crm_user.display_name = display_name

    already_assigned = any(assignment.crm_role_id == role.crm_role_id for assignment in crm_user.assigned_roles)
    if not already_assigned:
        crm_user.assigned_roles.append(
            CrmUserRole(
                crm_user_id=crm_user.crm_user_id,
                crm_role_id=role.crm_role_id,
                role=role,
            )
        )


def _ensure_extension_tables(session: Session) -> None:
    table_names = [
        "template_materials",
        "task_required_materials",
        "inventory_requests",
        "inventory_request_items",
        "inventory_dispatches",
        "inventory_dispatch_items",
    ]
    bind = session.get_bind()
    inspector = inspect(bind)
    present_tables = set(inspector.get_table_names())
    missing_tables = [Base.metadata.tables[name] for name in table_names if name in Base.metadata.tables and name not in present_tables]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables)

    _ensure_inventory_product_columns(session, inspector)
    _ensure_task_attachment_columns(session, inspector)


def _ensure_inventory_product_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "inventory_products" not in table_names:
        return

    product_columns = {column["name"] for column in active_inspector.get_columns("inventory_products")}
    if "requires_tracking" in product_columns:
        return

    # Lab environments may already have the inventory table without this newer column.
    session.execute(text("ALTER TABLE inventory_products ADD COLUMN requires_tracking BOOLEAN NOT NULL DEFAULT FALSE"))
    session.commit()


def _ensure_task_attachment_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "task_attachments" not in table_names:
        return

    attachment_columns = {column["name"] for column in active_inspector.get_columns("task_attachments")}
    if "task_comment_id" not in attachment_columns:
        session.execute(
            text(
                "ALTER TABLE task_attachments "
                "ADD COLUMN task_comment_id UUID REFERENCES task_comments(task_comment_id) ON DELETE SET NULL"
            )
        )
        session.commit()

    session.execute(text("CREATE INDEX IF NOT EXISTS idx_task_attachments_comment ON task_attachments(task_comment_id)"))
    session.commit()
