export interface Notification {
  notification_id: string;
  recipient_crm_user_id: string;
  notification_type: string;
  title: string;
  body: string;
  entity_type: 'ticket' | 'task' | 'deposit_request' | null;
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
