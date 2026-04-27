from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.admin import router as admin_router
from src.api.applications import router as applications_router
from src.api.auth import router as auth_router
from src.api.companies import router as companies_router
from src.api.crm_admin import router as crm_admin_router
from src.api.invitations import router as invitations_router
from src.config import settings


app = FastAPI(
    title="auth.microtv.ar",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-ID", "X-Membership-ID"],
)

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(admin_router)
app.include_router(crm_admin_router)
app.include_router(applications_router)
app.include_router(invitations_router)


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
