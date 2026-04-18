"""Módulo de configuración de la aplicación."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from typing import Annotated

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
        auth_base_url: Base URL de auth.microtv.ar.
        auth_login_path: Path relativo de login en auth.microtv.ar.
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
    auth_jwt_issuer: str = Field(default="auth.microtv.ar")
    auth_jwt_audience: str = Field(default="microtv-platform")
    auto_provision_crm_role: bool = Field(default=True)
    product_images_max_bytes: int = Field(default=2 * 1024 * 1024)
    task_images_max_bytes: int = Field(default=8 * 1024 * 1024)
    task_videos_max_bytes: int = Field(default=128 * 1024 * 1024)
    default_admin_auth_roles: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["platform_admin", "company_admin"]
    )
    default_deposito_auth_roles: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["company_operator"])
    default_tech_auth_roles: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["company_operator"])
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

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def public_dir(self) -> Path:
        return self.project_root / "public"

    @property
    def public_images_dir(self) -> Path:
        return self.public_dir / "images"

    @property
    def public_videos_dir(self) -> Path:
        return self.public_dir / "videos"

    @property
    def product_images_dir(self) -> Path:
        return self.public_images_dir / "products"

    @property
    def task_images_dir(self) -> Path:
        return self.public_images_dir / "task"

    @property
    def task_videos_dir(self) -> Path:
        return self.public_videos_dir / "task"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve un objeto de settings cacheado.

    Returns:
        Settings: Configuración parseada de la aplicación.
    """

    return Settings()
