import { TicketPriorityTone, TicketStatusTone } from './dashboard.model';

export interface TicketPageAction {
  id: string;
  label: string;
  icon: string;
  variant: 'primary' | 'secondary';
}

export interface TicketPriorityOption {
  id: TicketPriorityTone;
  label: string;
}

export interface TicketListItem {
  id: string;
  title: string;
  category: string;
  affectedDevice: string;
  status: string;
  statusTone: TicketStatusTone;
  priority: string;
  priorityTone: TicketPriorityTone;
  createdAt: string;
  assigneeId: number | string | null;
  assigneeName?: string | null;
  assigneeInitials?: string | null;
}

export interface TicketsTableColumn {
  key: 'id' | 'title' | 'category' | 'affectedDevice' | 'status' | 'priority' | 'createdAt' | 'assignee';
  label: string;
}

export interface TicketsTableData {
  title: string;
  columns: TicketsTableColumn[];
  items: TicketListItem[];
}

export interface TicketsPageData {
  pageTitle: string;
  pageSubtitle: string;
  primaryAction: TicketPageAction;
  secondaryAction: TicketPageAction;
  ticketsTable: TicketsTableData;
}