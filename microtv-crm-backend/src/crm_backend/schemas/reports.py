"""Schemas for CRM reporting endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ReportKind = Literal[
    "tickets",
    "tasks",
    "my_tickets",
    "my_tasks",
    "stock_critical",
    "deposit_requests",
    "user_activity",
    "executive_performance",
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


class MyTicketReportParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    category_id: str | None = None
    priority: str | None = None
    client_id: str | None = None
    location_id: str | None = None
    group_by: str = "status"


class MyTaskReportParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    category_id: str | None = None
    priority: str | None = None
    client_id: str | None = None
    group_by: str = "status"


class ExecutivePerformanceParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    group_by: str = "user"
    category_id: str | None = None
    priority: str | None = None
    client_id: str | None = None
    role_key: str | None = None
    user_id: str | None = None


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


class MyTicketReportSummary(ReportSummaryBase):
    resolved: int
    closed: int
    open: int
    avg_resolution_hours: float | None = None
    min_resolution_hours: float | None = None
    max_resolution_hours: float | None = None
    resolution_rate: float = 0


class MyTaskReportSummary(ReportSummaryBase):
    completed: int
    pending: int
    blocked: int
    avg_completion_hours: float | None = None
    min_completion_hours: float | None = None
    max_completion_hours: float | None = None
    completion_rate: float = 0


class ExecutivePerformanceSummary(ReportSummaryBase):
    total_groups: int
    overall_avg_close_hours: float | None = None
    best_performer: str | None = None
    worst_performer: str | None = None


class MyTicketReportRow(BaseModel):
    ticket_number: str
    title: str
    status: str
    priority: str
    category: str | None = None
    client: str
    location: str | None = None
    created_at: datetime
    resolution_hours: float | None = None


class MyTaskReportRow(BaseModel):
    task_code: str
    title: str
    status: str
    priority: str
    category: str | None = None
    client: str
    created_at: datetime
    completion_hours: float | None = None


class ExecutivePerformanceRow(BaseModel):
    group_key: str
    group_label: str
    primary_role: str | None = None
    total_assigned: int
    closed_count: int
    rejected_count: int
    avg_close_hours: float | None = None
    min_close_hours: float | None = None
    max_close_hours: float | None = None
    total_comments: int
    avg_comments_per_ticket: float | None = None


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


class MyTicketReportResponse(BaseModel):
    report_kind: Literal["my_tickets"] = "my_tickets"
    chart_kind: ChartKind
    summary: MyTicketReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[MyTicketReportRow] = Field(default_factory=list)


class MyTaskReportResponse(BaseModel):
    report_kind: Literal["my_tasks"] = "my_tasks"
    chart_kind: ChartKind
    summary: MyTaskReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[MyTaskReportRow] = Field(default_factory=list)


class ExecutivePerformanceResponse(BaseModel):
    report_kind: Literal["executive_performance"] = "executive_performance"
    chart_kind: ChartKind = "horizontal_bar"
    summary: ExecutivePerformanceSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[ExecutivePerformanceRow] = Field(default_factory=list)


class CategoryResolutionRow(BaseModel):
    category_id: str
    category_name: str
    total_tickets: int
    closed_tickets: int
    avg_resolution_hours: float | None = None
    min_resolution_hours: float | None = None
    max_resolution_hours: float | None = None


class CategoryResolutionReportSummary(BaseModel):
    total_categories: int
    total_tickets: int
    overall_avg_resolution_hours: float | None = None


class CategoryResolutionReportResponse(BaseModel):
    report_kind: Literal["category_resolution"] = "category_resolution"
    chart_kind: ChartKind = "horizontal_bar"
    summary: CategoryResolutionReportSummary
    kpis: list[ReportKpiItem] = Field(default_factory=list)
    series: list[ReportSeriesPoint] = Field(default_factory=list)
    rows: list[CategoryResolutionRow] = Field(default_factory=list)
