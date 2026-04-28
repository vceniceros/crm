"""Punto de entrada de la aplicación FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from crm_backend.api.error_handlers import register_error_handlers
from crm_backend.api.router import api_router
from crm_backend.core.config import get_settings
from crm_backend.db.bootstrap import initialize_database
from crm_backend.db.session import SessionLocal


_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Inicializa la infraestructura necesaria para la aplicación.

    Args:
        _: Instancia de la aplicación FastAPI.

    Yields:
        AsyncIterator[None]: Flujo de control del lifespan.
    """

    session = SessionLocal()
    try:
        initialize_database(session)
    finally:
        session.close()
    yield


def create_app() -> FastAPI:
    """Crea la aplicación FastAPI.

    Returns:
        FastAPI: Instancia configurada de la aplicación.
    """

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    register_error_handlers(app)

    media_dirs = [
        settings.crm_media_root_path,
        settings.task_images_dir,
        settings.task_videos_dir,
        settings.product_images_dir,
        settings.satisfaction_images_dir,
        settings.satisfaction_videos_dir,
        settings.public_images_dir,
        settings.public_videos_dir,
    ]
    for media_dir in media_dirs:
        try:
            media_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            _logger.exception("No se pudo crear el directorio de multimedia: %s", media_dir)

    app.mount(
        settings.crm_media_public_url,
        StaticFiles(directory=settings.crm_media_root_path, check_dir=False),
        name="media",
    )
    if settings.crm_media_public_url != "/images":
        app.mount("/images", StaticFiles(directory=settings.public_images_dir, check_dir=False), name="images")
    if settings.crm_media_public_url != "/videos":
        app.mount("/videos", StaticFiles(directory=settings.public_videos_dir, check_dir=False), name="videos")
    app.include_router(api_router)

    return app


app = create_app()
