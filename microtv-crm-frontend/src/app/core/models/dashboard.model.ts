export type DashboardStatVariant = 'danger' | 'info' | 'warning' | 'success';

export type TicketPriorityTone = 'critical' | 'high' | 'medium' | 'low';

export type TicketStatusTone = 'neutral' | 'progress' | 'warning' | 'success';

export type ActivityTone = 'danger' | 'info' | 'warning' | 'success';

export type PendingMenuTabKey = 'all' | 'tickets' | 'tasks' | 'approvals';

export type PendingMenuItemType = 'ticket' | 'task';

export interface DashboardStat {
  label: string;
  value: string;
  sublabel: string;
  variant: DashboardStatVariant;
}

export interface RecentTicket {
  id: string;
  ticketId?: string;
  subject: string;
  client: string;
  priority: string;
  priorityTone: TicketPriorityTone;
  status: string;
  statusTone: TicketStatusTone;
  assignedTo: string;
  assignedInitials: string;
  targetRoute?: string;
}

export interface RecentTicketsColumn {
  key: 'id' | 'subject' | 'client' | 'priority' | 'status' | 'assignedTo';
  label: string;
}

export interface RecentTicketsBlock {
  title: string;
  columns: RecentTicketsColumn[];
  items: RecentTicket[];
}

export interface RecentActivityItem {
  type: string;
  tone: ActivityTone;
  text: string;
  timestamp: string;
  actor: string;
  targetRoute?: string;
}

export interface RecentActivityBlock {
  title: string;
  items: RecentActivityItem[];
}

export interface PendingMenuTab {
  key: PendingMenuTabKey;
  label: string;
  count: number;
}

export interface PendingMenuItem {
  itemType: PendingMenuItemType;
  publicCode: string;
  title: string;
  client: string;
  status: string;
  statusTone: TicketStatusTone;
  priority?: string;
  priorityTone?: TicketPriorityTone;
  assignedTo: string;
  assignedInitials: string;
  reason: string;
  updatedAt: string;
  targetRoute: string;
  tabKeys: PendingMenuTabKey[];
}

export interface PendingMenuBlock {
  title: string;
  tabs: PendingMenuTab[];
  items: PendingMenuItem[];
}

export interface DashboardData {
  pageTitle: string;
  pageSubtitle: string;
  stats: DashboardStat[];
  pendingMenu: PendingMenuBlock;
  recentTickets: RecentTicketsBlock;
  recentActivity: RecentActivityBlock;
}

export interface DashboardKpiApiResponse {
  key: string;
  label: string;
  value: number;
  secondary: string;
  variant: DashboardStatVariant;
}

export interface DashboardRecentTicketApiResponse {
  ticket_id: string;
  ticket_public_id: string;
  subject: string;
  client: string;
  priority: string;
  priority_tone: TicketPriorityTone;
  status: string;
  status_tone: TicketStatusTone;
  assigned_to: string;
  assigned_initials: string;
  target_route: string;
}

export interface DashboardRecentActivityApiResponse {
  type: string;
  tone: ActivityTone;
  text: string;
  timestamp: string;
  actor: string;
  target_route: string | null;
}

export interface DashboardPendingMenuTabApiResponse {
  key: PendingMenuTabKey;
  label: string;
  count: number;
}

export interface DashboardPendingMenuItemApiResponse {
  item_type: PendingMenuItemType;
  public_code: string;
  title: string;
  client: string;
  status: string;
  status_tone: TicketStatusTone;
  priority: string | null;
  priority_tone: TicketPriorityTone | null;
  assigned_to: string;
  assigned_initials: string;
  reason: string;
  updated_at: string;
  target_route: string;
  tab_keys: PendingMenuTabKey[];
}

export interface DashboardPendingMenuApiResponse {
  title: string;
  tabs: DashboardPendingMenuTabApiResponse[];
  items: DashboardPendingMenuItemApiResponse[];
}

export interface DashboardSummaryApiResponse {
  page_title: string;
  page_subtitle: string;
  kpis: DashboardKpiApiResponse[];
  pending_menu: DashboardPendingMenuApiResponse;
  recent_tickets: DashboardRecentTicketApiResponse[];
  recent_activity: DashboardRecentActivityApiResponse[];
}
