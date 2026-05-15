"""Database bootstrap helpers."""

import logging
import os

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from crm_backend.db import Base
from crm_backend.models import CrmRole, CrmUser, CrmUserRole, RolePermission, StockCategory, StockProduct, Warehouse


_logger = logging.getLogger(__name__)
BOOTSTRAP_ADVISORY_LOCK_KEY = 4200142401


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

ROLE_PERMISSION_SEEDS = (
    ("admin", "stock.manage", True),
    ("admin", "stock.delete_product", True),
    ("admin", "ticket.reassign", True),
    ("admin", "order.reassign", True),
    ("admin", "comment.delete", True),
    ("admin", "auth_user.create_non_admin", True),
    ("deposito", "stock.manage", True),
    ("deposito", "stock.delete_product", False),
    ("deposito", "ticket.reassign", True),
    ("tecnico", "ticket.reassign", True),
    ("ejecutivo", "ticket.reassign", True),
    ("ejecutivo", "order.reassign", True),
    ("ejecutivo", "auth_user.create_non_admin", True),
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

    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        _initialize_database_inner(session)
        return

    # Keep a dedicated DB connection for the whole bootstrap so the advisory lock
    # cannot be bypassed by connection pool swaps across intermediate commits.
    with bind.connect() as connection:
        locked_session = Session(bind=connection)
        try:
            locked_session.execute(
                text("SELECT pg_advisory_lock(:lock_key)"),
                {"lock_key": BOOTSTRAP_ADVISORY_LOCK_KEY},
            )
            _initialize_database_inner(locked_session)
        finally:
            _release_bootstrap_lock(locked_session)
            locked_session.close()


def _initialize_database_inner(session: Session) -> None:
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
    _ensure_seed_role_permissions(session)
    session.commit()


def _release_bootstrap_lock(session: Session) -> None:
    try:
        session.rollback()
    except Exception:
        pass

    try:
        session.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": BOOTSTRAP_ADVISORY_LOCK_KEY},
        )
        session.commit()
    except Exception:
        session.rollback()
        _logger.exception("Failed to release bootstrap advisory lock")


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
        "crm_role_permissions",
        "crm_user_permissions",
        "activity_log",
        "activity_log_archive",
        "template_materials",
        "task_required_materials",
        "task_extra_materials",
        "inventory_requests",
        "inventory_request_items",
        "inventory_dispatches",
        "inventory_dispatch_items",
        "stock_import_batches",
        "stock_import_rows",
        "stock_backups",
        "stock_backup_rows",
        "tickets",
        "ticket_required_materials",
        "ticket_comments",
        "ticket_attachments",
        "ticket_status_transitions",
        "ticket_assignment_history",
        "ticket_audit_events",
        "crm_notifications",
        "push_subscriptions",
        "ticket_satisfaction_forms",
        "ticket_satisfaction_responses",
        "ticket_satisfaction_media",
    ]
    bind = session.get_bind()
    inspector = inspect(bind)
    present_tables = set(inspector.get_table_names())
    missing_tables = [Base.metadata.tables[name] for name in table_names if name in Base.metadata.tables and name not in present_tables]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables)

    _ensure_inventory_product_columns(session, inspector)
    _ensure_inventory_dispatch_columns(session, inspector)
    _ensure_task_rule_columns(session, inspector)
    _ensure_task_attachment_columns(session, inspector)
    _ensure_ticket_attachment_columns(session, inspector)
    _ensure_ticket_columns(session, inspector)
    _ensure_crm_user_columns(session, inspector)
    _ensure_crm_role_columns(session, inspector)
    _ensure_satisfaction_columns(session, inspector)


def _ensure_seed_role_permissions(session: Session) -> None:
    existing = {(row.role_key, row.permission_code) for row in session.query(RolePermission).all()}
    for role_key, permission_code, is_granted in ROLE_PERMISSION_SEEDS:
        key = (role_key, permission_code)
        if key in existing:
            continue
        session.add(RolePermission(role_key=role_key, permission_code=permission_code, is_granted=is_granted))


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


def _ensure_task_rule_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())

    for table_name in ("template_subtasks", "subtasks"):
        if table_name not in table_names:
            continue

        columns = {column["name"] for column in active_inspector.get_columns(table_name)}
        schema_changed = False
        for column_name in ("requires_arrival_comment", "requires_video_evidence"):
            if column_name in columns:
                continue
            session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} BOOLEAN NOT NULL DEFAULT FALSE"))
            schema_changed = True

        if schema_changed:
            session.commit()

    active_inspector = inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if {"task_templates", "template_subtasks"}.issubset(table_names):
        template_columns = {column["name"] for column in active_inspector.get_columns("task_templates")}
        subtask_columns = {column["name"] for column in active_inspector.get_columns("template_subtasks")}
        if {
            "requires_arrival_comment",
            "requires_video_evidence",
        }.issubset(template_columns | subtask_columns) and {
            "requires_arrival_comment",
            "requires_video_evidence",
        }.issubset(subtask_columns):
            session.execute(
                text(
                    "UPDATE template_subtasks "
                    "SET requires_arrival_comment = TRUE "
                    "WHERE template_id IN (SELECT template_id FROM task_templates WHERE requires_arrival_comment = TRUE) "
                    "  AND order_index = ("
                    "    SELECT MAX(ts2.order_index) FROM template_subtasks ts2 WHERE ts2.template_id = template_subtasks.template_id"
                    "  )"
                )
            )
            session.execute(
                text(
                    "UPDATE template_subtasks "
                    "SET requires_video_evidence = TRUE "
                    "WHERE template_id IN (SELECT template_id FROM task_templates WHERE requires_video_evidence = TRUE) "
                    "  AND order_index = ("
                    "    SELECT MAX(ts2.order_index) FROM template_subtasks ts2 WHERE ts2.template_id = template_subtasks.template_id"
                    "  )"
                )
            )
            session.commit()

    if {"tasks", "subtasks"}.issubset(table_names):
        task_columns = {column["name"] for column in active_inspector.get_columns("tasks")}
        subtask_columns = {column["name"] for column in active_inspector.get_columns("subtasks")}
        if {
            "requires_arrival_comment",
            "requires_video_evidence",
        }.issubset(task_columns | subtask_columns) and {
            "requires_arrival_comment",
            "requires_video_evidence",
        }.issubset(subtask_columns):
            session.execute(
                text(
                    "UPDATE subtasks "
                    "SET requires_arrival_comment = TRUE "
                    "WHERE task_id IN (SELECT task_id FROM tasks WHERE requires_arrival_comment = TRUE) "
                    "  AND order_index = ("
                    "    SELECT MAX(s2.order_index) FROM subtasks s2 WHERE s2.task_id = subtasks.task_id"
                    "  )"
                )
            )
            session.execute(
                text(
                    "UPDATE subtasks "
                    "SET requires_video_evidence = TRUE "
                    "WHERE task_id IN (SELECT task_id FROM tasks WHERE requires_video_evidence = TRUE) "
                    "  AND order_index = ("
                    "    SELECT MAX(s2.order_index) FROM subtasks s2 WHERE s2.task_id = subtasks.task_id"
                    "  )"
                )
            )
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


def _ensure_inventory_dispatch_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "inventory_dispatches" not in table_names:
        return

    dispatch_columns = {column["name"] for column in active_inspector.get_columns("inventory_dispatches")}
    if "received_by_crm_user_id" not in dispatch_columns:
        if bind.dialect.name == "postgresql" and "crm_users" in table_names:
            session.execute(
                text(
                    "ALTER TABLE inventory_dispatches "
                    "ADD COLUMN received_by_crm_user_id UUID REFERENCES crm_users(crm_user_id)"
                )
            )
        else:
            session.execute(text("ALTER TABLE inventory_dispatches ADD COLUMN received_by_crm_user_id VARCHAR(36)"))
        session.commit()

    if "received_at" not in dispatch_columns:
        if bind.dialect.name == "postgresql":
            session.execute(text("ALTER TABLE inventory_dispatches ADD COLUMN received_at TIMESTAMPTZ"))
        else:
            session.execute(text("ALTER TABLE inventory_dispatches ADD COLUMN received_at DATETIME"))
        session.commit()

    if "reception_comment" not in dispatch_columns:
        session.execute(text("ALTER TABLE inventory_dispatches ADD COLUMN reception_comment TEXT"))
        session.commit()

    session.execute(text("CREATE INDEX IF NOT EXISTS idx_inventory_dispatches_received_by ON inventory_dispatches(received_by_crm_user_id)"))
    session.commit()


def _ensure_ticket_attachment_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "ticket_attachments" not in table_names:
        return

    attachment_columns = {column["name"] for column in active_inspector.get_columns("ticket_attachments")}
    if "ticket_comment_id" not in attachment_columns:
        if bind.dialect.name == "postgresql" and "ticket_comments" in table_names:
            session.execute(
                text(
                    "ALTER TABLE ticket_attachments "
                    "ADD COLUMN ticket_comment_id UUID REFERENCES ticket_comments(ticket_comment_id) ON DELETE SET NULL"
                )
            )
        else:
            session.execute(text("ALTER TABLE ticket_attachments ADD COLUMN ticket_comment_id VARCHAR(36)"))
        session.commit()

    session.execute(text("CREATE INDEX IF NOT EXISTS idx_ticket_attachments_comment ON ticket_attachments(ticket_comment_id)"))
    session.commit()


def _ensure_ticket_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "tickets" not in table_names:
        return

    ticket_columns = {column["name"] for column in active_inspector.get_columns("tickets")}
    original_ticket_columns = set(ticket_columns)
    column_statements = [
        ("title", "ALTER TABLE tickets ADD COLUMN title VARCHAR(255) NOT NULL DEFAULT ''"),
        ("description", "ALTER TABLE tickets ADD COLUMN description TEXT NOT NULL DEFAULT ''"),
        ("status", "ALTER TABLE tickets ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'OPEN'"),
        ("client_id", "ALTER TABLE tickets ADD COLUMN client_id UUID REFERENCES clients(client_id)"),
        ("location_id", "ALTER TABLE tickets ADD COLUMN location_id UUID REFERENCES locations(location_id)"),
        ("created_at", "ALTER TABLE tickets ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
        ("ticket_number", "ALTER TABLE tickets ADD COLUMN ticket_number VARCHAR(30)"),
        ("priority", "ALTER TABLE tickets ADD COLUMN priority VARCHAR(30) NOT NULL DEFAULT 'MEDIUM'"),
        ("assigned_role_id", "ALTER TABLE tickets ADD COLUMN assigned_role_id UUID REFERENCES crm_roles(crm_role_id)"),
        ("assigned_user_id", "ALTER TABLE tickets ADD COLUMN assigned_user_id UUID REFERENCES crm_users(crm_user_id)"),
        (
            "created_by_crm_user_id",
            "ALTER TABLE tickets ADD COLUMN created_by_crm_user_id UUID REFERENCES crm_users(crm_user_id)",
        ),
        (
            "resolved_by_crm_user_id",
            "ALTER TABLE tickets ADD COLUMN resolved_by_crm_user_id UUID REFERENCES crm_users(crm_user_id)",
        ),
        ("resolved_at", "ALTER TABLE tickets ADD COLUMN resolved_at TIMESTAMPTZ"),
        (
            "closed_by_crm_user_id",
            "ALTER TABLE tickets ADD COLUMN closed_by_crm_user_id UUID REFERENCES crm_users(crm_user_id)",
        ),
        ("closed_at", "ALTER TABLE tickets ADD COLUMN closed_at TIMESTAMPTZ"),
        ("requires_arrival_comment", "ALTER TABLE tickets ADD COLUMN requires_arrival_comment BOOLEAN NOT NULL DEFAULT FALSE"),
        ("requires_video_evidence", "ALTER TABLE tickets ADD COLUMN requires_video_evidence BOOLEAN NOT NULL DEFAULT TRUE"),
        ("arrival_registered_at", "ALTER TABLE tickets ADD COLUMN arrival_registered_at TIMESTAMPTZ"),
        ("updated_at", "ALTER TABLE tickets ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
        ("deleted_at", "ALTER TABLE tickets ADD COLUMN deleted_at TIMESTAMPTZ"),
    ]

    schema_changed = False
    for column_name, ddl in column_statements:
        if column_name in ticket_columns:
            continue
        session.execute(text(ddl))
        ticket_columns.add(column_name)
        schema_changed = True

    if schema_changed:
        session.commit()

    if "arrival_comment_id" not in ticket_columns:
        if bind.dialect.name == "postgresql":
            session.execute(text("ALTER TABLE tickets ADD COLUMN arrival_comment_id UUID"))
        else:
            session.execute(text("ALTER TABLE tickets ADD COLUMN arrival_comment_id VARCHAR(36)"))
        ticket_columns.add("arrival_comment_id")
        schema_changed = True

    if "solution_comment_id" not in ticket_columns:
        if bind.dialect.name == "postgresql":
            session.execute(text("ALTER TABLE tickets ADD COLUMN solution_comment_id UUID"))
        else:
            session.execute(text("ALTER TABLE tickets ADD COLUMN solution_comment_id VARCHAR(36)"))
        ticket_columns.add("solution_comment_id")
        schema_changed = True

    if schema_changed:
        session.commit()

    if bind.dialect.name == "postgresql" and "arrival_comment_id" in ticket_columns and "ticket_comments" in table_names:
        fk_names = {
            fk.get("name")
            for fk in inspect(bind).get_foreign_keys("tickets")
            if fk.get("name")
        }
        if "fk_tickets_arrival_comment" not in fk_names:
            session.execute(
                text(
                    "ALTER TABLE tickets "
                    "ADD CONSTRAINT fk_tickets_arrival_comment "
                    "FOREIGN KEY (arrival_comment_id) "
                    "REFERENCES ticket_comments(ticket_comment_id) "
                    "ON DELETE SET NULL"
                )
            )
            session.commit()

    if bind.dialect.name == "postgresql" and "solution_comment_id" in ticket_columns and "ticket_comments" in table_names:
        fk_names = {
            fk.get("name")
            for fk in inspect(bind).get_foreign_keys("tickets")
            if fk.get("name")
        }
        if "fk_tickets_solution_comment" not in fk_names:
            session.execute(
                text(
                    "ALTER TABLE tickets "
                    "ADD CONSTRAINT fk_tickets_solution_comment "
                    "FOREIGN KEY (solution_comment_id) "
                    "REFERENCES ticket_comments(ticket_comment_id) "
                    "ON DELETE SET NULL"
                )
            )
            session.commit()

    # Migrate legacy title/description columns if this DB comes from an older ticket schema.
    if "ticket_title" in original_ticket_columns and "title" in ticket_columns:
        session.execute(
            text(
                "UPDATE tickets "
                "SET title = COALESCE(NULLIF(ticket_title, ''), title) "
                "WHERE title IS NULL OR title = ''"
            )
        )

    if "ticket_description" in original_ticket_columns and "description" in ticket_columns:
        session.execute(
            text(
                "UPDATE tickets "
                "SET description = COALESCE(NULLIF(ticket_description, ''), description) "
                "WHERE description IS NULL OR description = ''"
            )
        )

    # Map legacy status catalog (status_id -> status_key) into the new enum-like status column.
    status_mapping = {
        "OPEN": "OPEN",
        "IN_PROGRESS": "IN_PROGRESS",
        "AWAITING_APPROVAL": "ON_HOLD",
        "RESOLVED": "RESOLVED",
        "CLOSED": "CLOSED",
        "CANCELLED": "CLOSED",
    }
    if "status_id" in original_ticket_columns and "ticket_statuses" in table_names and "status" in ticket_columns:
        legacy_status_rows = session.execute(
            text(
                "SELECT t.ticket_id, ts.status_key "
                "FROM tickets t "
                "LEFT JOIN ticket_statuses ts ON ts.status_id = t.status_id "
                "WHERE t.status IS NULL OR t.status = '' "
                "ORDER BY t.ticket_id"
            )
        ).fetchall()
        for ticket_id, legacy_status_key in legacy_status_rows:
            mapped_status = status_mapping.get((legacy_status_key or "").upper(), "OPEN")
            session.execute(
                text("UPDATE tickets SET status = :status WHERE ticket_id = :ticket_id"),
                {"status": mapped_status, "ticket_id": ticket_id},
            )

    # Map legacy priority catalog (priority_id -> priority_key) into the new enum-like priority column.
    priority_mapping = {
        "BAJA": "LOW",
        "MEDIA": "MEDIUM",
        "ALTA": "HIGH",
        "CRITICA": "CRITICAL",
    }
    if "priority_id" in original_ticket_columns and "ticket_priorities" in table_names and "priority" in ticket_columns:
        legacy_priority_rows = session.execute(
            text(
                "SELECT t.ticket_id, tp.priority_key "
                "FROM tickets t "
                "LEFT JOIN ticket_priorities tp ON tp.priority_id = t.priority_id "
                "WHERE t.priority IS NULL OR t.priority = '' OR t.priority = 'MEDIUM' "
                "ORDER BY t.ticket_id"
            )
        ).fetchall()
        for ticket_id, legacy_priority_key in legacy_priority_rows:
            mapped_priority = priority_mapping.get((legacy_priority_key or "").upper())
            if not mapped_priority:
                continue
            session.execute(
                text("UPDATE tickets SET priority = :priority WHERE ticket_id = :ticket_id"),
                {"priority": mapped_priority, "ticket_id": ticket_id},
            )

    if {"arrival_registered_at", "arrival_comment_id"}.issubset(ticket_columns) and "ticket_comments" in table_names:
        legacy_arrival_rows = session.execute(
            text(
                "SELECT tc.ticket_id, tc.ticket_comment_id, tc.created_at "
                "FROM ticket_comments tc "
                "WHERE LOWER(tc.comment_type) = 'arrival_registration' "
                "ORDER BY tc.created_at ASC"
            )
        ).fetchall()
        seen_ticket_ids: set[str] = set()
        for ticket_id, comment_id, created_at in legacy_arrival_rows:
            if ticket_id in seen_ticket_ids:
                continue
            seen_ticket_ids.add(ticket_id)
            session.execute(
                text(
                    "UPDATE tickets "
                    "SET arrival_registered_at = COALESCE(arrival_registered_at, :created_at), "
                    "    arrival_comment_id = COALESCE(arrival_comment_id, :comment_id) "
                    "WHERE ticket_id = :ticket_id"
                ),
                {
                    "ticket_id": ticket_id,
                    "comment_id": comment_id,
                    "created_at": created_at,
                },
            )

    # Backfill ticket_number in legacy rows when the column is newly introduced.
    # Use a portable query/update flow so this works on SQLite tests and PostgreSQL.
    missing_rows = session.execute(
        text(
            "SELECT ticket_id "
            "FROM tickets "
            "WHERE ticket_number IS NULL OR ticket_number = '' "
            "ORDER BY created_at, ticket_id"
        )
    ).fetchall()
    for sequence, row in enumerate(missing_rows, start=1):
        session.execute(
            text("UPDATE tickets SET ticket_number = :ticket_number WHERE ticket_id = :ticket_id"),
            {
                "ticket_number": f"TCK-{sequence:06d}",
                "ticket_id": row[0],
            },
        )

    session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_tickets_ticket_number ON tickets(ticket_number)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_assigned_role ON tickets(assigned_role_id)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_assigned_user ON tickets(assigned_user_id)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_updated_at ON tickets(updated_at)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_requires_arrival_comment ON tickets(requires_arrival_comment)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_requires_video_evidence ON tickets(requires_video_evidence)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_arrival_comment_id ON tickets(arrival_comment_id)"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_tickets_solution_comment_id ON tickets(solution_comment_id)"))

    if "ticket_comments" in table_names:
        comment_columns = {column["name"] for column in active_inspector.get_columns("ticket_comments")}
        if "location_id" not in comment_columns:
            session.execute(text("ALTER TABLE ticket_comments ADD COLUMN location_id UUID REFERENCES locations(location_id)"))
    session.commit()


def _ensure_crm_user_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "crm_users" not in table_names:
        return

    user_columns = {column["name"] for column in active_inspector.get_columns("crm_users")}
    if "avatar_url" not in user_columns:
        session.execute(text("ALTER TABLE crm_users ADD COLUMN avatar_url VARCHAR(500)"))
        session.commit()


def _ensure_crm_role_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "crm_roles" not in table_names:
        return

    role_columns = {column["name"] for column in active_inspector.get_columns("crm_roles")}
    schema_changed = False

    if "role_label" not in role_columns:
        session.execute(text("ALTER TABLE crm_roles ADD COLUMN role_label VARCHAR(100) NOT NULL DEFAULT ''"))
        schema_changed = True

    if "description" not in role_columns:
        session.execute(text("ALTER TABLE crm_roles ADD COLUMN description TEXT"))
        schema_changed = True

    if "is_active" not in role_columns:
        session.execute(text("ALTER TABLE crm_roles ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"))
        schema_changed = True

    if "created_at" not in role_columns:
        if bind.dialect.name == "postgresql":
            session.execute(text("ALTER TABLE crm_roles ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        else:
            session.execute(text("ALTER TABLE crm_roles ADD COLUMN created_at DATETIME"))
        schema_changed = True

    if "updated_at" not in role_columns:
        if bind.dialect.name == "postgresql":
            session.execute(text("ALTER TABLE crm_roles ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"))
        else:
            session.execute(text("ALTER TABLE crm_roles ADD COLUMN updated_at DATETIME"))
        schema_changed = True

    if schema_changed:
        session.execute(
            text(
                "UPDATE crm_roles "
                "SET role_label = COALESCE(NULLIF(role_label, ''), role_key), "
                "    is_active = COALESCE(is_active, TRUE)"
            )
        )
        session.commit()


def _ensure_satisfaction_columns(session: Session, inspector=None) -> None:
    bind = session.get_bind()
    active_inspector = inspector or inspect(bind)
    table_names = set(active_inspector.get_table_names())
    if "ticket_satisfaction_responses" not in table_names:
        return

    response_columns = {column["name"] for column in active_inspector.get_columns("ticket_satisfaction_responses")}
    schema_changed = False

    if "customer_name" not in response_columns:
        session.execute(text("ALTER TABLE ticket_satisfaction_responses ADD COLUMN customer_name VARCHAR(255)"))
        schema_changed = True

    if "customer_company" not in response_columns:
        session.execute(text("ALTER TABLE ticket_satisfaction_responses ADD COLUMN customer_company VARCHAR(255)"))
        schema_changed = True

    if schema_changed:
        session.execute(
            text(
                "UPDATE ticket_satisfaction_responses "
                "SET customer_name = COALESCE(NULLIF(customer_name, ''), 'Cliente'), "
                "    customer_company = COALESCE(NULLIF(customer_company, ''), 'Empresa no indicada')"
            )
        )
        session.commit()
