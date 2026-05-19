"""Schemas for dashboard summary endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


KpiVariantLiteral = Literal["danger", "info", "warning", "success"]
TicketPriorityToneLiteral = Literal["critical", "high", "medium", "low"]
TicketStatusToneLiteral = Literal["neutral", "progress", "warning", "success"]
ActivityToneLiteral = Literal["danger", "info", "warning", "success"]
PendingMenuTabKeyLiteral = Literal["all", "tickets", "tasks", "approvals"]
PendingMenuItemTypeLiteral = Literal["ticket", "task"]


class DashboardKpiResponse(BaseModel):
    key: str
    label: str
    value: int
    secondary: str
    variant: KpiVariantLiteral


class DashboardRecentTicketResponse(BaseModel):
    ticket_id: str
    ticket_public_id: str
    subject: str
    client: str
    priority: str
    priority_tone: TicketPriorityToneLiteral
    status: str
    status_tone: TicketStatusToneLiteral
    assigned_to: str
    assigned_initials: str
    target_route: str


class DashboardRecentActivityResponse(BaseModel):
    type: str
    tone: ActivityToneLiteral
    text: str
    timestamp: datetime
    actor: str
    target_entity_type: str | None
    target_entity_id: str | None
    target_public_code: str | None
    target_route: str | None


class DashboardPendingMenuTabResponse(BaseModel):
    key: PendingMenuTabKeyLiteral
    label: str
    count: int


class DashboardPendingMenuItemResponse(BaseModel):
    item_type: PendingMenuItemTypeLiteral
    public_code: str
    title: str
    client: str
    status: str
    status_tone: TicketStatusToneLiteral
    priority: str | None = None
    priority_tone: TicketPriorityToneLiteral | None = None
    assigned_to: str
    assigned_initials: str
    reason: str
    updated_at: datetime
    target_route: str
    tab_keys: list[PendingMenuTabKeyLiteral]


class DashboardPendingMenuResponse(BaseModel):
    title: str
    tabs: list[DashboardPendingMenuTabResponse]
    items: list[DashboardPendingMenuItemResponse]


class DashboardSummaryResponse(BaseModel):
    page_title: str
    page_subtitle: str
    kpis: list[DashboardKpiResponse]
    pending_menu: DashboardPendingMenuResponse
    recent_tickets: list[DashboardRecentTicketResponse]
    recent_activity: list[DashboardRecentActivityResponse]
