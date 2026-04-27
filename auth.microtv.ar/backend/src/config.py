import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/auth_microtv",
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me")
    environment: str = os.getenv("ENVIRONMENT", "development")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "auth.crm.ycc.internal")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "microtv-platform")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    refresh_token_expire_minutes: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
    login_ticket_expire_minutes: int = int(os.getenv("LOGIN_TICKET_EXPIRE_MINUTES", "10"))
    allowed_origins: list[str] = None  # type: ignore[assignment]

    # ── SMTP (transactional email) ────────────────────────────────────────────
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.microtv.ar")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "noreply@microtv.ar")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "MicroTV")

    # ── Frontend URL (used for email verification links) ──────────────────────
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # ── SaaS base URL (used for invitation acceptance links) ──────────────────
    saas_base_url: str = os.getenv("SAAS_BASE_URL", "http://localhost:5173")

    # ── Service-to-service shared secret (pay → auth callbacks) ──────────────
    service_jwt_secret: str = os.getenv("SERVICE_JWT_SECRET", "change-me-service")

    # ── AFIP public padron API ────────────────────────────────────────────────
    afip_base_url: str = os.getenv("AFIP_BASE_URL", "https://soa.afip.gob.ar/sr-padron/v2")

    # ── Google reCAPTCHA v3 ───────────────────────────────────────────────────
    recaptcha_secret_key: str = os.getenv("RECAPTCHA_SECRET_KEY", "")
    recaptcha_min_score: float = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.5"))

    # ── CRM internal auth bootstrap ──────────────────────────────────────────
    crm_auth_tenant_type: str = os.getenv("CRM_AUTH_TENANT_TYPE", "company")
    crm_auth_tenant_id: str = os.getenv("CRM_AUTH_TENANT_ID", "YCC")
    crm_auth_admin_email: str = os.getenv("CRM_AUTH_ADMIN_EMAIL", "admin@ycc.local")
    crm_auth_admin_password: str = os.getenv("CRM_AUTH_ADMIN_PASSWORD", "changeme-secure-password")
    crm_auth_admin_name: str = os.getenv("CRM_AUTH_ADMIN_NAME", "Administrador CRM")

    def __post_init__(self) -> None:
        raw = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8002,http://localhost:5173,https://saas.microtv.ar",
        )
        object.__setattr__(self, "allowed_origins", [o.strip() for o in raw.split(",") if o.strip()])


settings = Settings()
