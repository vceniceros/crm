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
  categoryId?: string | null;
  categoryName?: string | null;
  assignedToUserId: number | string | null;
  assignedTo: string;
  assignedInitials: string;
  routeTaskId?: string;
  rowActionLabel?: string;
  rowActionId?: string;
  rowActionDisabled?: boolean;
}

export interface TasksTableColumn {
  key: 'id' | 'title' | 'client' | 'category' | 'subtasks' | 'status' | 'assignedTo';
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
  templateAction?: TaskPageAction;
  primaryAction: TaskPageAction;
  secondaryAction: TaskPageAction;
  tasksTable: TasksTableData;
}
