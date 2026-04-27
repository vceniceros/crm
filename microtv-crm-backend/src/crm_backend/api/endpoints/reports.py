"""HTTP endpoints for CRM reports."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query

from crm_backend.api.dependencies import get_authenticated_crm_session, get_reports_service
from crm_backend.schemas import ErrorResponse
from crm_backend.schemas.reports import (
    DepositRequestReportResponse,
    ReportOptionItem,
    StockCriticalReportResponse,
    TaskReportResponse,
    TicketReportResponse,
    UserActivityReportResponse,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.reports_service import ReportsService


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get(
    "/options/users",
    response_model=list[ReportOptionItem],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_report_user_options(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> list[ReportOptionItem]:
    return reports_service.list_user_options(actor)


@router.get(
    "/options/clients",
    response_model=list[ReportOptionItem],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_report_client_options(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> list[ReportOptionItem]:
    return reports_service.list_client_options(actor)


@router.get(
    "/options/categories",
    response_model=list[ReportOptionItem],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_report_category_options(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> list[ReportOptionItem]:
    return reports_service.list_category_options(actor)


@router.get(
    "/options/warehouses",
    response_model=list[ReportOptionItem],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_report_warehouse_options(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> list[ReportOptionItem]:
    return reports_service.list_warehouse_options(actor)


@router.get(
    "/options/technicians",
    response_model=list[ReportOptionItem],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_report_technician_options(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> list[ReportOptionItem]:
    return reports_service.list_technician_options(actor)


@router.get(
    "/options/action-types",
    response_model=list[ReportOptionItem],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_report_action_type_options(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> list[ReportOptionItem]:
    return reports_service.list_action_type_options(actor)


@router.get(
    "/tickets",
    response_model=TicketReportResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_tickets_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    group_by: Literal["status", "priority", "client"] = Query(default="status"),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    client_id: str | None = Query(default=None),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> TicketReportResponse:
    return reports_service.tickets_report(
        actor,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        status=status,
        priority=priority,
        client_id=client_id,
    )


@router.get(
    "/tasks",
    response_model=TaskReportResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_tasks_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    group_by: Literal["status", "technician"] = Query(default="status"),
    technician_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> TaskReportResponse:
    return reports_service.tasks_report(
        actor,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        technician_id=technician_id,
        status=status,
    )


@router.get(
    "/stock-critical",
    response_model=StockCriticalReportResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_stock_critical_report(
    category: str | None = Query(default=None),
    warehouse_id: str | None = Query(default=None),
    only_critical: bool = Query(default=True),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> StockCriticalReportResponse:
    return reports_service.stock_critical_report(
        actor,
        category=category,
        warehouse_id=warehouse_id,
        only_critical=only_critical,
    )


@router.get(
    "/deposit-requests",
    response_model=DepositRequestReportResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_deposit_requests_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: str | None = Query(default=None),
    requester: str | None = Query(default=None),
    approver: str | None = Query(default=None),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> DepositRequestReportResponse:
    return reports_service.deposit_requests_report(
        actor,
        date_from=date_from,
        date_to=date_to,
        status=status,
        requester=requester,
        approver=approver,
    )


@router.get(
    "/user-activity",
    response_model=UserActivityReportResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_user_activity_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    reports_service: ReportsService = Depends(get_reports_service),
) -> UserActivityReportResponse:
    return reports_service.user_activity_report(
        actor,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action_type=action_type,
    )
