import { TicketStatusTone } from './dashboard.model';
import { InventoryDispatch, InventoryRequest, RequiredMaterial, RequiredMaterialWriteRequest } from './inventory-flow.model';
import { AppLocation } from './location.model';
import { TaskAttachment } from './task-attachment.model';

export type TaskAssignmentPolicy = 'role_queue_auto' | 'default_user_auto' | 'manual_required';
export type TaskItemType = 'checkbox' | 'text';
export type TaskAction = 'close_subtask' | 'reject_subtask' | 'put_on_hold';
export type TaskStatus = 'PENDING' | 'IN_PROGRESS' | 'BLOCKED' | 'PENDING_APPROVAL' | 'COMPLETED';
export type SubtaskStatus = 'locked' | 'pending_assignment' | 'assigned' | 'in_progress' | 'completed' | 'rejected' | 'on_hold';
export type TaskCommentType = 'general' | 'transition' | 'progress' | 'closure' | 'arrival_registration' | 'closure_evidence';
export type TaskSubtaskType = 'standard' | 'pre_form';
export type TaskPreFormFieldType = 'TEXT' | 'NUMBER' | 'TEXTAREA' | 'DATE' | 'TEL' | 'FILE' | 'CHECKBOX';

export interface ClientSummary {
  client_id: string;
  business_name: string;
  tax_id: string;
  email: string | null;
  phone: string | null;
  created_at: string;
}

export interface CrmUserOption {
  crm_user_id: string;
  display_name: string | null;
  email: string | null;
}

export interface TaskTemplateItemWriteRequest {
  item_label: string;
  item_order: number;
  item_type: TaskItemType;
  is_required: boolean;
}

export interface TaskTemplateSubtaskWriteRequest {
  subtask_title: string;
  subtask_description: string | null;
  order_index: number;
  responsible_role_key: string;
  default_responsible_crm_user_id: string | null;
  close_comment_required: boolean;
  next_assignment_policy: TaskAssignmentPolicy;
  subtask_type: TaskSubtaskType;
  items: TaskTemplateItemWriteRequest[];
}

export interface TaskPreFormFieldWriteRequest {
  label: string;
  field_type: TaskPreFormFieldType;
  is_required: boolean;
  order_index: number;
  placeholder: string | null;
}

export interface TaskPreFormDefinitionWriteRequest {
  title: string | null;
  instructions: string | null;
  fields: TaskPreFormFieldWriteRequest[];
}

export interface CreateTaskTemplateRequest {
  template_name: string;
  description: string | null;
  requires_arrival_comment: boolean;
  requires_video_evidence: boolean;
  requires_pre_form: boolean;
  pre_form: TaskPreFormDefinitionWriteRequest | null;
  subtasks: TaskTemplateSubtaskWriteRequest[];
  required_materials: RequiredMaterialWriteRequest[];
}

export interface UpdateTaskTemplateRequest extends CreateTaskTemplateRequest {}

export interface SetTaskTemplateActivationRequest {
  is_active: boolean;
}

export interface CreateTaskFromTemplateRequest {
  template_id: string;
  client_id: string;
  location_id: string | null;
  task_title: string | null;
  task_description: string | null;
  requires_arrival_comment?: boolean | null;
  requires_video_evidence?: boolean | null;
  extra_materials?: TaskExtraMaterialWrite[];
}

export interface TaskExtraMaterialWrite {
  product_id: string;
  quantity: number;
}

export interface TaskLocation {
  location_id: string;
  latitude: number;
  longitude: number;
  address_label: string | null;
  formatted_address: string | null;
}

export interface CreateLocationRequest {
  latitude: number;
  longitude: number;
  address_label: string | null;
  formatted_address: string | null;
}

export interface PersistedLocation extends AppLocation {
  locationId: string;
}

export interface UpdateSubtaskItemValueRequest {
  item_id: string;
  checkbox_value?: boolean | null;
  text_value?: string | null;
}

export interface UpdateSubtaskProgressRequest {
  items: UpdateSubtaskItemValueRequest[];
}

export interface ExecuteSubtaskActionRequest {
  action: TaskAction;
  comment: string;
  next_assigned_crm_user_id?: string | null;
  attachment_ids?: string[];
}

export interface AssignSubtaskRequest {
  assigned_crm_user_id: string;
  notes?: string | null;
}

export interface ApproveTaskRequest {
  comment?: string | null;
}

export interface RejectTaskApprovalRequest {
  comment: string;
}

export interface CreateTaskCommentRequest {
  body: string;
  location_id: string | null;
  attachment_ids: string[];
  mentioned_user_ids?: string[];
}

export interface TaskTemplateItem {
  task_template_item_id: string;
  item_label: string;
  item_order: number;
  item_type: TaskItemType;
  is_required: boolean;
}

export interface TaskTemplateSubtask {
  task_template_subtask_id: string;
  subtask_title: string;
  subtask_description: string | null;
  order_index: number;
  responsible_role_key: string;
  default_responsible_crm_user_id: string | null;
  close_comment_required: boolean;
  next_assignment_policy: TaskAssignmentPolicy;
  subtask_type: TaskSubtaskType;
  items: TaskTemplateItem[];
}

export interface TaskPreFormField {
  field_id: string;
  label: string;
  field_type: TaskPreFormFieldType;
  is_required: boolean;
  order_index: number;
  placeholder: string | null;
}

export interface TaskPreFormDefinition {
  form_id: string;
  title: string | null;
  instructions: string | null;
  fields: TaskPreFormField[];
}

export interface TaskTemplate {
  template_id: string;
  template_name: string;
  description: string | null;
  is_active: boolean;
  requires_arrival_comment: boolean;
  requires_video_evidence: boolean;
  requires_pre_form: boolean;
  created_by_crm_user_id: string;
  created_at: string;
  updated_at: string | null;
  required_materials: RequiredMaterial[];
  pre_form: TaskPreFormDefinition | null;
  subtasks: TaskTemplateSubtask[];
}

export interface TaskSummary {
  task_id: string;
  client_id: string;
  client_name: string;
  location_id: string | null;
  location: TaskLocation | null;
  template_id: string;
  template_name: string;
  task_title: string;
  task_description: string | null;
  status: TaskStatus;
  requires_arrival_comment: boolean;
  requires_video_evidence: boolean;
  arrival_registered_at: string | null;
  arrival_comment_id: string | null;
  current_subtask_id: string | null;
  current_assigned_crm_user_id: string | null;
  current_assigned_user_display_name: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface UnassignedSubtaskQueueItem {
  task_id: string;
  client_id: string;
  client_name: string;
  template_id: string;
  template_name: string;
  task_title: string;
  subtask_id: string;
  subtask_title: string;
  responsible_role_key: string;
  status: SubtaskStatus;
  order_index: number;
}

export interface SubtaskItemValue {
  subtask_item_value_id: string;
  item_label: string;
  item_order: number;
  item_type: TaskItemType;
  is_required: boolean;
  checkbox_value: boolean;
  text_value: string | null;
  last_updated_by_crm_user_id: string | null;
  completed_at: string | null;
}

export interface SubtaskAssignment {
  subtask_assignment_id: string;
  assigned_crm_user_id: string;
  assigned_user_display_name: string | null;
  assigned_by_crm_user_id: string | null;
  notes: string | null;
  assigned_at: string;
}

export interface SubtaskTransition {
  subtask_transition_id: string;
  from_status: SubtaskStatus;
  to_status: SubtaskStatus;
  action: string;
  performed_by_crm_user_id: string;
  performed_by_display_name: string | null;
  task_comment_id: string | null;
  created_at: string;
}

export interface TaskComment {
  task_comment_id: string;
  subtask_id: string | null;
  author_crm_user_id: string;
  author_display_name: string | null;
  comment_type: TaskCommentType;
  body: string;
  location: TaskLocation | null;
  created_at: string;
  attachments: TaskAttachment[];
  mentions?: TaskCommentMention[];
}

export interface TaskCommentMention {
  task_comment_mention_id: string;
  mentioned_crm_user_id: string;
  mentioned_display_name: string | null;
  mentioned_email: string | null;
  created_by_crm_user_id: string;
  created_at: string;
}

export interface TaskAuditEvent {
  task_audit_event_id: string;
  subtask_id: string | null;
  event_type: string;
  actor_crm_user_id: string;
  payload_json: Record<string, unknown>;
  created_at: string;
}

export interface Subtask {
  subtask_id: string;
  template_subtask_id: string;
  subtask_title: string;
  subtask_description: string | null;
  order_index: number;
  responsible_role_key: string;
  assigned_crm_user_id: string | null;
  assigned_user_display_name: string | null;
  default_responsible_crm_user_id: string | null;
  default_assigned_user_display_name: string | null;
  close_comment_required: boolean;
  next_assignment_policy: TaskAssignmentPolicy;
  subtask_type: TaskSubtaskType;
  status: SubtaskStatus;
  completed_at: string | null;
  closed_by_crm_user_id: string | null;
  closed_by_display_name: string | null;
  items: SubtaskItemValue[];
  assignments: SubtaskAssignment[];
  transitions: SubtaskTransition[];
}

export interface TaskDetail {
  task_id: string;
  client_id: string;
  client_name: string;
  location_id: string | null;
  location: TaskLocation | null;
  template_id: string;
  template_name: string;
  task_title: string;
  task_description: string | null;
  status: TaskStatus;
  requires_arrival_comment: boolean;
  requires_video_evidence: boolean;
  arrival_registered_at: string | null;
  arrival_comment_id: string | null;
  current_subtask_id: string | null;
  current_assigned_crm_user_id: string | null;
  current_assigned_user_display_name: string | null;
  created_by_crm_user_id: string;
  finalized_by_crm_user_id: string | null;
  finalized_by_display_name: string | null;
  finalized_at: string | null;
  created_at: string;
  updated_at: string | null;
  required_materials: RequiredMaterial[];
  extra_materials: TaskExtraMaterial[];
  inventory_requests: InventoryRequest[];
  dispatches: InventoryDispatch[];
  subtasks: Subtask[];
  comments: TaskComment[];
  audit_events: TaskAuditEvent[];
}

export interface TaskExtraMaterial {
  required_material_id: string;
  product_id: string;
  product_code: string;
  product_name: string;
  quantity: number;
  requires_tracking: boolean;
}

export interface GenerateTaskSatisfactionFormResponse {
  form_id: string;
  task_id: string;
  public_link_token: string;
  survey_path: string;
  expires_at: string;
  status_label: string;
}

export interface TaskSatisfactionFormStatusResponse {
  form_id: string;
  task_id: string;
  status_label: string;
  expires_at: string;
  used_at: string | null;
  revoked_at: string | null;
  created_at: string;
  has_response: boolean;
}

export interface TaskSatisfactionResponseDetailResponse {
  response_id: string;
  task_id: string;
  customer_name: string;
  customer_company: string;
  rating: number;
  comment: string | null;
  submitted_at: string;
}

export interface TaskPreFormStatusValue {
  field_id: string;
  label: string;
  field_type: TaskPreFormFieldType;
  text_value: string | null;
  file_attachment_id: string | null;
}

export interface TaskPreFormStatusResponse {
  instance_id: string;
  task_id: string;
  status_label: string;
  expires_at: string;
  submitted_at: string | null;
  revoked_at: string | null;
  form_link_path: string | null;
  response_values: TaskPreFormStatusValue[];
}

export interface PublicTaskSatisfactionFormInfoResponse {
  task_title: string;
  client_name: string | null;
  location_name: string | null;
  status_label: string;
}

export interface SubmitTaskSatisfactionFormRequest {
  rating: number;
  customer_name: string;
  customer_company: string;
  comment: string | null;
}

export interface PublicTaskPreFormInfoResponse {
  task_title: string;
  client_name: string | null;
  location_name: string | null;
  title: string | null;
  instructions: string | null;
  fields: TaskPreFormField[];
}

export interface SubmitTaskPreFormValueRequest {
  field_id: string;
  text_value: string | null;
}

export interface SubmitTaskPreFormRequest {
  values: SubmitTaskPreFormValueRequest[];
}

export const TASK_ROLE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'admin', label: 'Administrador CRM' },
  { value: 'ejecutivo', label: 'Ejecutivo' },
  { value: 'deposito', label: 'Encargado de depósito' },
  { value: 'tecnico', label: 'Técnico de campo' }
];

export const TASK_ASSIGNMENT_POLICY_OPTIONS: Array<{ value: TaskAssignmentPolicy; label: string }> = [
  { value: 'role_queue_auto', label: 'Cola del rol (sin asignar)' },
  { value: 'default_user_auto', label: 'Usuario por defecto' },
  { value: 'manual_required', label: 'Asignación manual obligatoria' }
];

export const TASK_ACTION_OPTIONS: Array<{ value: TaskAction; label: string; icon: string }> = [
  { value: 'close_subtask', label: 'Cerrar subtarea', icon: 'task_alt' },
  { value: 'reject_subtask', label: 'Rechazar', icon: 'cancel' },
  { value: 'put_on_hold', label: 'Poner en espera', icon: 'pause_circle' }
];

export function formatTaskStatus(status: string): string {
  switch (status) {
    case 'PENDING':
      return 'Pendiente';
    case 'IN_PROGRESS':
      return 'En progreso';
    case 'BLOCKED':
      return 'Bloqueada';
    case 'PENDING_APPROVAL':
      return 'Pendiente aprobación ejecutiva';
    case 'COMPLETED':
      return 'Completada';
    case 'locked':
      return 'Bloqueada';
    case 'pending_assignment':
      return 'Pendiente de asignación';
    case 'assigned':
      return 'Asignada';
    case 'in_progress':
      return 'En progreso';
    case 'completed':
      return 'Completada';
    case 'rejected':
      return 'Rechazada';
    case 'on_hold':
      return 'En espera';
    default:
      return status;
  }
}

export function formatRoleKey(roleKey: string | null | undefined): string {
  switch (roleKey) {
    case 'admin':
      return 'Administrador CRM';
    case 'ejecutivo':
      return 'Ejecutivo';
    case 'deposito':
      return 'Depósito';
    case 'tecnico':
      return 'Técnico';
    default:
      return roleKey ?? 'Sin rol';
  }
}

export function formatAssignmentPolicy(policy: TaskAssignmentPolicy): string {
  return TASK_ASSIGNMENT_POLICY_OPTIONS.find((option) => option.value === policy)?.label ?? policy;
}

export function toTaskTone(status: string): TicketStatusTone {
  switch (status) {
    case 'PENDING_APPROVAL':
      return 'warning';
    case 'COMPLETED':
    case 'completed':
      return 'success';
    case 'BLOCKED':
    case 'rejected':
    case 'on_hold':
      return 'warning';
    case 'IN_PROGRESS':
    case 'assigned':
    case 'in_progress':
      return 'progress';
    default:
      return 'neutral';
  }
}

export function buildInitials(value: string | null | undefined, fallback = 'CRM'): string {
  const source = (value ?? '').trim();
  if (!source) {
    return fallback;
  }

  const initials = source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment[0]?.toUpperCase() ?? '')
    .join('');

  return initials || fallback;
}

export function countCompletedSubtasks(subtasks: Subtask[]): number {
  return subtasks.filter((subtask) => subtask.status === 'completed').length;
}
