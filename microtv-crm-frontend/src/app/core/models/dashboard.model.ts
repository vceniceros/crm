export type DashboardStatVariant = 'danger' | 'info' | 'warning' | 'success';

export type TicketPriorityTone = 'critical' | 'high' | 'medium' | 'low';

export type TicketStatusTone = 'neutral' | 'progress' | 'warning' | 'success';

export type ActivityTone = 'danger' | 'info' | 'warning' | 'success';

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

export interface DashboardData {
  pageTitle: string;
  pageSubtitle: string;
  stats: DashboardStat[];
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

export interface DashboardSummaryApiResponse {
  page_title: string;
  page_subtitle: string;
  kpis: DashboardKpiApiResponse[];
  recent_tickets: DashboardRecentTicketApiResponse[];
  recent_activity: DashboardRecentActivityApiResponse[];
}