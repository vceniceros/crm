"""Módulo de configuración de la aplicación."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated
from typing import Literal

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Expone los valores de configuración de la aplicación.

    Attributes:
        app_name: Nombre público de la aplicación.
        environment: Etiqueta del entorno de ejecución.
        host: Host del servidor ASGI local.
        port: Puerto del servidor ASGI local.
        database_url: URL SQLAlchemy de la base del CRM.
        cors_origins: Orígenes permitidos para clientes browser.
        cors_origin_regex: Regex opcional para permitir orígenes dinámicos, por ejemplo LAN privada.
        auth_base_url: Base URL de auth interno del CRM.
        auth_login_path: Path relativo de login en auth interno.
        auth_timeout_seconds: Timeout de llamadas a auth externo.
        auth_jwt_secret: Secret compartido para validar JWTs de auth.
        auth_jwt_algorithm: Algoritmo de firma del JWT.
        auth_jwt_issuer: Issuer esperado en el JWT de auth.
        auth_jwt_audience: Audience esperado en el JWT de auth.
        auto_provision_crm_role: Indica si el CRM debe bootstrappear un rol local.
        default_admin_auth_roles: Roles externos de auth que mapean a admin en CRM.
        default_deposito_auth_roles: Roles externos de auth que mapean a deposito en CRM.
        default_tech_auth_roles: Roles externos de auth que mapean a tecnico en CRM.
        deposito_demo_tenant_id: Tenant habilitado para el flujo inicial real de deposito.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="MicroTV CRM Backend")
    environment: Literal["development", "test", "production"] = Field(default="development")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8010)
    database_url: str = Field()
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:4200", "http://localhost:5173"]
    )
    cors_origin_regex: str | None = Field(default=None)
    auth_base_url: str = Field(default="http://localhost:8001")
    auth_login_path: str = Field(default="/v1/auth/login")
    auth_timeout_seconds: float = Field(default=10.0)
    auth_jwt_secret: str = Field(default="change-me")
    auth_jwt_algorithm: str = Field(default="HS256")
    auth_jwt_issuer: str = Field(default="auth.crm.ycc.internal")
    auth_jwt_audience: str = Field(default="microtv-platform")
    auth_service_recaptcha_token: str = Field(default="crm-backend")
    auto_provision_crm_role: bool = Field(default=True)
    crm_media_root: str = Field(default="public")
    crm_media_public_url: str = Field(default="/media")
    product_images_max_bytes: int = Field(default=2 * 1024 * 1024)
    task_images_max_bytes: int = Field(default=8 * 1024 * 1024)
    task_videos_max_bytes: int = Field(default=128 * 1024 * 1024)
    default_admin_auth_roles: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["admin", "platform_admin", "company_admin"]
    )
    default_deposito_auth_roles: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["operador_deposito", "company_operator"]
    )
    default_tech_auth_roles: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["tecnico_campo"])
    deposito_demo_tenant_id: str = Field(default="YCC")

    @field_validator(
        "cors_origins",
        "default_admin_auth_roles",
        "default_deposito_auth_roles",
        "default_tech_auth_roles",
        mode="before",
    )
    @classmethod
    def split_comma_separated_values(cls, value: str | list[str]) -> list[str]:
        """Normaliza variables de entorno separadas por coma.

        Args:
            value: Valor crudo de entorno.

        Returns:
            list[str]: Lista normalizada de strings.
        """

        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator("cors_origin_regex", mode="before")
    @classmethod
    def normalize_optional_regex(cls, value: str | None) -> str | None:
        """Normaliza regex opcional vacío a None."""

        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("crm_media_root", mode="before")
    @classmethod
    def normalize_media_root(cls, value: str | Path | None) -> str:
        """Normaliza la raíz física de multimedia."""

        if value is None:
            return "public"
        normalized = str(value).strip()
        return normalized or "public"

    @field_validator("crm_media_public_url", mode="before")
    @classmethod
    def normalize_media_public_url(cls, value: str | None) -> str:
        """Normaliza el prefijo público de multimedia."""

        normalized = (value or "/media").strip() or "/media"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        normalized = normalized.rstrip("/")
        return normalized or "/media"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def crm_media_root_path(self) -> Path:
        root = Path(self.crm_media_root)
        if root.is_absolute():
            return root
        return (self.project_root / root).resolve()

    @property
    def public_dir(self) -> Path:
        """Legacy media directory used by older /images and /videos URLs."""

        return self.project_root / "public"

    @property
    def public_images_dir(self) -> Path:
        return self.public_dir / "images"

    @property
    def public_videos_dir(self) -> Path:
        return self.public_dir / "videos"

    @property
    def public_avatars_dir(self) -> Path:
        return self.public_dir / "avatars"

    @property
    def product_images_dir(self) -> Path:
        return self.crm_media_root_path / "products" / "images"

    @property
    def task_images_dir(self) -> Path:
        return self.crm_media_root_path / "tasks" / "images"

    @property
    def task_videos_dir(self) -> Path:
        return self.crm_media_root_path / "tasks" / "videos"

    @property
    def task_images_public_prefix(self) -> str:
        return self._build_media_public_prefix("tasks", "images")

    @property
    def task_videos_public_prefix(self) -> str:
        return self._build_media_public_prefix("tasks", "videos")

    @property
    def product_images_public_prefix(self) -> str:
        return self._build_media_public_prefix("products", "images")

    satisfaction_images_max_bytes: int = Field(default=8 * 1024 * 1024)
    satisfaction_videos_max_bytes: int = Field(default=64 * 1024 * 1024)
    satisfaction_form_expiry_hours: int = Field(default=72)

    @property
    def satisfaction_images_dir(self) -> Path:
        return self.crm_media_root_path / "satisfaction" / "images"

    @property
    def satisfaction_videos_dir(self) -> Path:
        return self.crm_media_root_path / "satisfaction" / "videos"

    @property
    def satisfaction_images_public_prefix(self) -> str:
        return self._build_media_public_prefix("satisfaction", "images")

    @property
    def satisfaction_videos_public_prefix(self) -> str:
        return self._build_media_public_prefix("satisfaction", "videos")

    @property
    def satisfaction_media_dir(self) -> Path:
        return self.crm_media_root_path / "satisfaction"

    def to_public_storage_path(self, raw_path: str) -> str:
        """Normaliza una URL/path público para persistirlo como path relativo público."""

        normalized = (raw_path or "").strip().replace("\\", "/")
        if not normalized:
            return ""
        if normalized.startswith("/public/"):
            normalized = normalized[len("/public/") :]
        elif normalized.startswith("public/"):
            normalized = normalized[len("public/") :]
        return normalized.lstrip("/")

    def resolve_media_filesystem_path(self, raw_path: str | None) -> Path | None:
        """Resuelve una URL/path público al archivo físico con fallback legacy."""

        normalized = (raw_path or "").strip().replace("\\", "/")
        if not normalized:
            return None
        lower = normalized.lower()
        if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("data:") or lower.startswith("blob:"):
            return None

        media_prefix = f"{self.crm_media_public_url}/"
        legacy_public_prefix = "/public/"
        if normalized.startswith(media_prefix):
            relative = normalized[len(media_prefix) :].lstrip("/")
            return self._safe_join(self.crm_media_root_path, relative)

        if normalized.startswith(self.crm_media_public_url.lstrip("/") + "/"):
            relative = normalized[len(self.crm_media_public_url.lstrip("/") + "/") :].lstrip("/")
            return self._safe_join(self.crm_media_root_path, relative)

        if normalized.startswith("/images/") or normalized.startswith("/videos/"):
            return self._safe_join(self.public_dir, normalized.lstrip("/"))

        if normalized.startswith(legacy_public_prefix):
            return self._safe_join(self.public_dir, normalized[len(legacy_public_prefix) :])

        if normalized.startswith("public/"):
            return self._safe_join(self.public_dir, normalized[len("public/") :])

        if normalized.startswith("images/") or normalized.startswith("videos/"):
            return self._safe_join(self.public_dir, normalized)

        if normalized.startswith("/"):
            return None

        return self._safe_join(self.crm_media_root_path, normalized)

    def _build_media_public_prefix(self, *segments: str) -> str:
        clean_segments = [segment.strip("/") for segment in segments if segment.strip("/")]
        if not clean_segments:
            return self.crm_media_public_url
        return f"{self.crm_media_public_url}/{'/'.join(clean_segments)}"

    def _safe_join(self, root: Path, relative_path: str) -> Path | None:
        base = root.resolve()
        candidate = (base / relative_path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            return None
        return candidate


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve un objeto de settings cacheado.

    Returns:
        Settings: Configuración parseada de la aplicación.
    """

    return Settings()
