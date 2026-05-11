export const NOTIFICATION_TYPES = {
  TASK_ASSIGNED: 'task_assigned',
  TASK_PRE_FORM_COMPLETED: 'task_pre_form_completed',
  TASK_SATISFACTION_SUBMITTED: 'task_satisfaction_submitted',
  TASK_UNASSIGNED_IN_ROLE: 'task_unassigned_in_role',
  TICKET_SATISFACTION_SUBMITTED: 'ticket_satisfaction_submitted',
  TICKET_UNASSIGNED_IN_ROLE: 'ticket_unassigned_in_role',
  STOCK_LOW: 'stock_low',
  STOCK_OUT: 'stock_out',
  DEPOSIT_PENDING_DISPATCH: 'deposit_pending_dispatch',
  DEPOSIT_PRODUCTS_INSTALLED: 'deposit_products_installed',
} as const;

export type NotificationEntityType = 'ticket' | 'task' | 'deposit_request' | 'stock_product';

export interface Notification {
  notification_id: string;
  recipient_crm_user_id: string;
  notification_type: string;
  title: string;
  body: string;
  entity_type: NotificationEntityType | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
  metadata_json: Record<string, unknown> | null;
}

export interface NotificationListResponse {
  notifications: Notification[];
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}
