import { TicketStatusTone } from './dashboard.model';

export interface TaskPageAction {
  id: string;
  label: string;
  icon: string;
  variant: 'primary' | 'secondary';
}

export interface TaskListItem {
  id: string;
  title: string;
  client: string;
  completedSubtasks: number;
  totalSubtasks: number;
  status: string;
  statusTone: TicketStatusTone;
  assignedTo: string;
  assignedInitials: string;
}

export interface TasksTableColumn {
  key: 'id' | 'title' | 'client' | 'subtasks' | 'status' | 'assignedTo';
  label: string;
}

export interface TasksTableData {
  title: string;
  columns: TasksTableColumn[];
  items: TaskListItem[];
}

export interface TasksPageData {
  pageTitle: string;
  pageSubtitle: string;
  primaryAction: TaskPageAction;
  secondaryAction: TaskPageAction;
  tasksTable: TasksTableData;
}