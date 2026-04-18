"""Script de seed para el entorno local de auth del CRM."""

from __future__ import annotations

import importlib
import os
from uuid import uuid4

import psycopg


password_hasher = importlib.import_module("argon2").PasswordHasher()


def normalize_database_url(database_url: str) -> str:
    """Convierte una URL PostgreSQL de SQLAlchemy a un DSN para psycopg.

    Args:
        database_url: URL de base tomada del entorno.

    Returns:
        str: DSN normalizado para psycopg.
    """

    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def ensure_role(cursor: psycopg.Cursor, role_name: str) -> str:
    """Garantiza que exista un rol de auth.

    Args:
        cursor: Cursor PostgreSQL activo.
        role_name: Nombre del rol a garantizar.

    Returns:
        str: Identificador del rol.
    """

    role_id = str(uuid4())
    cursor.execute(
        """
        INSERT INTO roles (role_id, role_name)
        VALUES (%s, %s)
        ON CONFLICT (role_name) DO NOTHING
        """,
        (role_id, role_name),
    )
    cursor.execute("SELECT role_id FROM roles WHERE role_name = %s", (role_name,))
    result = cursor.fetchone()
    if result is None:
        raise RuntimeError(f"Role '{role_name}' could not be created.")
    return str(result[0])


def ensure_company(cursor: psycopg.Cursor, *, company_id: str, company_name: str) -> str:
    """Garantiza que exista un tenant de compañía.

    Args:
        cursor: Cursor PostgreSQL activo.
        company_id: Identificador externo de la compañía.
        company_name: Nombre de la compañía.

    Returns:
        str: Identificador de la compañía.
    """

    cursor.execute(
        """
        INSERT INTO companies (company_id, company_name, logo_url, status)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (company_id) DO UPDATE
        SET company_name = EXCLUDED.company_name,
            status = EXCLUDED.status
        """,
        (company_id, company_name, None, "active"),
    )
    return company_id


def ensure_user(cursor: psycopg.Cursor, *, email: str, password: str, display_name: str, user_id: str | None = None) -> str:
    """Garantiza que exista un usuario local en auth.

    Args:
        cursor: Cursor PostgreSQL activo.
        email: Email del usuario.
        password: Contraseña seed en texto plano.
        display_name: Nombre visible del usuario.

    Returns:
        str: Identificador del usuario.
    """

    user_id = user_id or str(uuid4())
    password_hash = password_hasher.hash(password)
    cursor.execute(
        """
        INSERT INTO users (user_id, email, display_name, password_hash, status, email_verified, user_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (email) DO UPDATE
        SET display_name = EXCLUDED.display_name,
            password_hash = EXCLUDED.password_hash,
            status = EXCLUDED.status,
            email_verified = EXCLUDED.email_verified,
            user_type = EXCLUDED.user_type
        RETURNING user_id
        """,
        (user_id, email, display_name, password_hash, "active", True, "company_employee"),
    )
    result = cursor.fetchone()
    if result is None:
        raise RuntimeError(f"User '{email}' could not be created.")
    return str(result[0])


def ensure_membership(cursor: psycopg.Cursor, *, user_id: str, company_id: str, role_id: str) -> None:
    """Garantiza que el usuario pertenezca a la compañía con el rol indicado.

    Args:
        cursor: Cursor PostgreSQL activo.
        user_id: Identificador del usuario.
        company_id: Identificador de la compañía.
        role_id: Identificador del rol.
    """

    cursor.execute(
        """
        SELECT membership_id
        FROM memberships
        WHERE user_id = %s AND tenant_type = %s AND tenant_id = %s
        """,
        (user_id, "company", company_id),
    )
    result = cursor.fetchone()
    membership_id = str(result[0]) if result else str(uuid4())
    if result is None:
        cursor.execute(
            """
            INSERT INTO memberships (membership_id, user_id, tenant_type, tenant_id)
            VALUES (%s, %s, %s, %s)
            """,
            (membership_id, user_id, "company", company_id),
        )

    cursor.execute(
        """
        SELECT assignment_id
        FROM role_assignments
        WHERE membership_id = %s AND role_id = %s
        """,
        (membership_id, role_id),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            """
            INSERT INTO role_assignments (assignment_id, membership_id, role_id)
            VALUES (%s, %s, %s)
            """,
            (str(uuid4()), membership_id, role_id),
        )


def main() -> None:
    """Genera usuarios locales determinísticos para probar la integración del CRM."""

    database_url = normalize_database_url(
        os.getenv("DATABASE_URL", "postgresql+psycopg://authmicrotv:authmicrotv@localhost:5432/auth_microtv")
    )
    admin_email = os.getenv("CRM_LOCAL_ADMIN_EMAIL", "admin.crm@microtv.com")
    admin_password = os.getenv("CRM_LOCAL_ADMIN_PASSWORD", "Passw0rd!")
    ycc_email = os.getenv("CRM_LOCAL_YCC_EMAIL", "operador.crm@yccbrothers.com")
    ycc_password = os.getenv("CRM_LOCAL_YCC_PASSWORD", "Passw0rd!")
    ycc_aux_email = os.getenv("CRM_LOCAL_YCC_AUX_EMAIL", "deposito.aux@yccbrothers.com")
    ycc_aux_password = os.getenv("CRM_LOCAL_YCC_AUX_PASSWORD", "Passw0rd!")
    ycc_executive_email = os.getenv("CRM_LOCAL_YCC_EXECUTIVE_EMAIL", "ejecutivo.crm@yccbrothers.com")
    ycc_executive_password = os.getenv("CRM_LOCAL_YCC_EXECUTIVE_PASSWORD", "Passw0rd!")
    ycc_tech_email = os.getenv("CRM_LOCAL_YCC_TECH_EMAIL", "tecnico.campo@yccbrothers.com")
    ycc_tech_password = os.getenv("CRM_LOCAL_YCC_TECH_PASSWORD", "Passw0rd!")
    ycc_tech_user_id = os.getenv("CRM_LOCAL_YCC_TECH_USER_ID", "auth-user-ycc-tech-001")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            platform_admin_role_id = ensure_role(cursor, "platform_admin")
            company_operator_role_id = ensure_role(cursor, "company_operator")
            ejecutivo_role_id = ensure_role(cursor, "ejecutivo")

            microtv_company_id = ensure_company(cursor, company_id="MICROTV", company_name="MicroTV")
            ycc_company_id = ensure_company(cursor, company_id="YCC", company_name="YCC Brothers")

            admin_user_id = ensure_user(
                cursor,
                email=admin_email,
                password=admin_password,
                display_name="Admin MicroTV",
            )
            ycc_user_id = ensure_user(
                cursor,
                email=ycc_email,
                password=ycc_password,
                display_name="Operador YCC Brothers",
            )
            ycc_aux_user_id = ensure_user(
                cursor,
                email=ycc_aux_email,
                password=ycc_aux_password,
                display_name="Auxiliar Deposito YCC",
            )
            ycc_executive_user_id = ensure_user(
                cursor,
                email=ycc_executive_email,
                password=ycc_executive_password,
                display_name="Ejecutivo YCC Brothers",
            )
            ycc_tech_user_id = ensure_user(
                cursor,
                email=ycc_tech_email,
                password=ycc_tech_password,
                display_name="Tecnico Campo YCC",
                user_id=ycc_tech_user_id,
            )

            ensure_membership(
                cursor,
                user_id=admin_user_id,
                company_id=microtv_company_id,
                role_id=platform_admin_role_id,
            )
            ensure_membership(
                cursor,
                user_id=ycc_user_id,
                company_id=ycc_company_id,
                role_id=company_operator_role_id,
            )
            ensure_membership(
                cursor,
                user_id=ycc_aux_user_id,
                company_id=ycc_company_id,
                role_id=company_operator_role_id,
            )
            ensure_membership(
                cursor,
                user_id=ycc_executive_user_id,
                company_id=ycc_company_id,
                role_id=ejecutivo_role_id,
            )
            ensure_membership(
                cursor,
                user_id=ycc_tech_user_id,
                company_id=ycc_company_id,
                role_id=company_operator_role_id,
            )
        connection.commit()


if __name__ == "__main__":
    main()
