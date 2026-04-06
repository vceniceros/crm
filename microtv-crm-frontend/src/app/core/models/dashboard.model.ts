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
  subject: string;
  client: string;
  priority: string;
  priorityTone: TicketPriorityTone;
  status: string;
  statusTone: TicketStatusTone;
  assignedTo: string;
  assignedInitials: string;
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