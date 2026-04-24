export interface SettingsRole {
  crm_role_id: string;
  role_key: string;
  role_label: string;
  description: string | null;
  is_active: boolean;
}

export interface SettingsRoleUpdateRequest {
  role_label: string;
  description?: string | null;
  is_active: boolean;
}

export interface SettingsUserRoleAssignment {
  crm_user_id: string;
  display_name: string | null;
  email: string | null;
  role_keys: string[];
}

export interface SettingsUserRoleAssignmentRequest {
  role_keys: string[];
}

export interface SettingsCategory {
  category_id: string;
  name: string;
  category_type: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SettingsCategoryWriteRequest {
  name: string;
  category_type: string;
  description?: string | null;
  is_active: boolean;
}

export interface SettingsPriority {
  priority_id: string;
  code: string;
  name: string;
  order_index: number;
  color: string | null;
  is_active: boolean;
}

export interface SettingsPriorityWriteRequest {
  code: string;
  name: string;
  order_index: number;
  color?: string | null;
  is_active: boolean;
}

export interface SettingsStatus {
  status_id: string;
  code: string;
  name: string;
  entity_type: string;
  is_final: boolean;
  order_index: number;
  is_active: boolean;
}

export interface SettingsStatusWriteRequest {
  code: string;
  name: string;
  entity_type: string;
  is_final: boolean;
  order_index: number;
  is_active: boolean;
}

export interface SettingsTaskTemplate {
  template_id: string;
  template_name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface SettingsTaskTemplateUpdateRequest {
  template_name: string;
  description?: string | null;
  is_active: boolean;
}

export interface SettingsSlaRule {
  sla_rule_id: string;
  entity_type: string;
  priority_code: string;
  response_time_minutes: number;
  resolution_time_minutes: number;
  is_active: boolean;
}

export interface SettingsSlaRuleWriteRequest {
  entity_type: string;
  priority_code: string;
  response_time_minutes: number;
  resolution_time_minutes: number;
  is_active: boolean;
}

export interface SettingsNotificationRule {
  notification_rule_id: string;
  event_code: string;
  label: string;
  notify_assigned: boolean;
  notify_roles_json: string[];
  is_active: boolean;
}

export interface SettingsNotificationRuleWriteRequest {
  event_code: string;
  label: string;
  notify_assigned: boolean;
  notify_roles_json: string[];
  is_active: boolean;
}
