"""Schemas for CRM reporting endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ReportKind = Literal[
    "tickets",
    "tasks",
    "stock_critical",
    "deposit_requests",
    "user_activity",
]

ChartKind = Literal["area", "line", "bar", "horizontal_bar", "donut", "pie"]


class ReportSeriesPoint(BaseModel):
    label: str
    date: str
    value: float
    meta: dict[str, str | float | int | None] = Field(default_factory=dict)


class ReportOptionItem(BaseModel):
    id: str
    label: str


class ReportKpiItem(BaseModel):
    key: str
    label: str
    value: float | int | str


class ReportSummaryBase(BaseModel):
    total: int


class TicketReportSummary(ReportSummaryBase):
    open: int
    closed: int
    pending: int
    avg_resolution_hours: float | None = None


class TaskReportSummary(ReportSummaryBase):
    in_progress: int
    closed: int
    overdue: int
    blocked: int


class StockCriticalReportSummary(ReportSummaryBase):
    without_stock: int
    below_minimum: int
    valued_stock: float | None = None


class DepositRequestReportSummary(ReportSummaryBase):
    pending: int
    approved: int
    dispatched: int
    rejected: int
    avg_dispatch_hours: float | None = None


class UserActivityReportSummary(ReportSummaryBase):
    tickets_created: int
    tickets_assigned: int
    tickets_closed: int
    tasks_assigned: int
    tasks_closed: int
    requests_created: int
    requests_approved: int
    requests_dispatched: int


class TicketReportRow(BaseModel):
    ticket_number: str
    title: str
    client: str
    priority: str
    status: str
    assigned_to: str | None = None
    created_at: datetime
    closed_at: datetime | None = None


class TaskReportRow(BaseModel):
    task_code: str
    title: str
    status: str
    technician: str | None = None
    client: str
    created_at: datetime
    due_at: datetime | None = None
    closed_at: datetime | None = None


class StockCriticalReportRow(BaseModel):
    sku: str
    product: str
    category: str
    stock_current: float
    stock_minimum: float
    status: str
    updated_at: datetime | None = None


class DepositRequestReportRow(BaseModel):
    request_number: str
    source: str
    requester: str | None = None
    status: str
    approved_by: str | None = None
    dispatched_by: str | None = None
    created_at: datetime
    dispatched_at: datetime | None = None


class UserActivityReportRow(BaseModel):
    user: str
    action: str
    entity: str
    entity_code: str
    date: datetime
    description: str


class TicketReportResponse(BaseModel):
    report_kind: Literal["tickets"] = "tickets"
    chart_kind: ChartKind
    summary: TicketReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[TicketReportRow] = Field(default_factory=list)


class TaskReportResponse(BaseModel):
    report_kind: Literal["tasks"] = "tasks"
    chart_kind: ChartKind
    summary: TaskReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[TaskReportRow] = Field(default_factory=list)


class StockCriticalReportResponse(BaseModel):
    report_kind: Literal["stock_critical"] = "stock_critical"
    chart_kind: ChartKind
    summary: StockCriticalReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[StockCriticalReportRow] = Field(default_factory=list)


class DepositRequestReportResponse(BaseModel):
    report_kind: Literal["deposit_requests"] = "deposit_requests"
    chart_kind: ChartKind
    summary: DepositRequestReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[DepositRequestReportRow] = Field(default_factory=list)


class UserActivityReportResponse(BaseModel):
    report_kind: Literal["user_activity"] = "user_activity"
    chart_kind: ChartKind
    summary: UserActivityReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[UserActivityReportRow] = Field(default_factory=list)
