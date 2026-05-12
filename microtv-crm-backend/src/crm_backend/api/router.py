"""Application router configuration."""

from fastapi import APIRouter

from crm_backend.api.endpoints.auth import router as auth_router
from crm_backend.api.endpoints.clients import router as clients_router
from crm_backend.api.endpoints.crm_users import router as crm_users_router
from crm_backend.api.endpoints.dashboard import router as dashboard_router
from crm_backend.api.endpoints.health import router as health_router
from crm_backend.api.endpoints.inventory_flow import router as inventory_flow_router
from crm_backend.api.endpoints.locations import router as locations_router
from crm_backend.api.endpoints.me import router as me_router
from crm_backend.api.endpoints.notifications import router as notifications_router
from crm_backend.api.endpoints.push_subscriptions import router as push_subscriptions_router
from crm_backend.api.endpoints.reports import router as reports_router
from crm_backend.api.endpoints.settings import router as settings_router
from crm_backend.api.endpoints.activity_log import router as activity_log_router
from crm_backend.api.endpoints.stock import router as stock_router
from crm_backend.api.endpoints.tasks import router as tasks_router
from crm_backend.api.endpoints.tickets import router as tickets_router
from crm_backend.api.endpoints.public_tickets import router as public_tickets_router
from crm_backend.api.endpoints.public_tasks import router as public_tasks_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(clients_router)
api_router.include_router(crm_users_router)
api_router.include_router(locations_router)
api_router.include_router(me_router)
api_router.include_router(stock_router)
api_router.include_router(inventory_flow_router)
api_router.include_router(tasks_router)
api_router.include_router(tickets_router)
api_router.include_router(public_tickets_router)
api_router.include_router(public_tasks_router)
api_router.include_router(notifications_router)
api_router.include_router(push_subscriptions_router)
api_router.include_router(reports_router)
api_router.include_router(activity_log_router)
api_router.include_router(settings_router)
