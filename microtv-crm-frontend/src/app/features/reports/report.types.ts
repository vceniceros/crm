export type ReportCategoryKey = 'saved' | 'tickets' | 'tasks' | 'stock' | 'deposit-requests' | 'activity';

export type ReportId =
  | 'saved-reports'
  | 'tickets-by-status'
  | 'tickets-by-priority'
  | 'tickets-by-client'
  | 'tasks-by-status'
  | 'tasks-by-technician'
  | 'tasks-overdue-blocked'
  | 'stock-critical'
  | 'stock-movements'
  | 'stock-consumption'
  | 'deposit-requests-status'
  | 'deposit-requests-approved'
  | 'deposit-requests-dispatched'
  | 'activity-by-user'
  | 'activity-by-action-type'
  | 'activity-closures-by-user';

export interface ReportTabDefinition {
  key: ReportCategoryKey;
  label: string;
}

export interface ReportCardDefinition {
  id: ReportId;
  category: ReportCategoryKey;
  title: string;
  description: string;
  enabled: boolean;
}

export interface ReportColumn {
  key: string;
  label: string;
}

export interface ReportSeriesPoint {
  label: string;
  date: string;
  value: number;
  meta?: Record<string, string | number | null>;
}

export interface ReportKpi {
  key: string;
  label: string;
  value: number | string;
}

export interface ReportPayload {
  report_kind: 'tickets' | 'tasks' | 'stock_critical' | 'deposit_requests' | 'user_activity';
  chart_kind: 'area' | 'line' | 'bar' | 'horizontal_bar' | 'donut' | 'pie';
  kpis: ReportKpi[];
  series: ReportSeriesPoint[];
  rows: Record<string, unknown>[];
}

export interface ReportOption {
  id: string;
  label: string;
}

export interface ReportFilterCatalogs {
  users: ReportOption[];
  clients: ReportOption[];
  categories: ReportOption[];
  warehouses: ReportOption[];
  technicians: ReportOption[];
  actionTypes: ReportOption[];
}

export interface ReportRequestFilters {
  date_from?: string;
  date_to?: string;
  group_by?: string;
  status?: string;
  priority?: string;
  client_id?: string;
  technician_id?: string;
  category?: string;
  warehouse_id?: string;
  only_critical?: boolean;
  requester?: string;
  approver?: string;
  user_id?: string;
  action_type?: string;
}

export const REPORT_TABS: ReportTabDefinition[] = [
  { key: 'saved', label: 'Mis Reportes' },
  { key: 'tickets', label: 'Tickets' },
  { key: 'tasks', label: 'Tareas' },
  { key: 'stock', label: 'Depósito / Stock' },
  { key: 'deposit-requests', label: 'Solicitudes a depósito' },
  { key: 'activity', label: 'Actividad' }
];

export const REPORT_CARDS: ReportCardDefinition[] = [
  { id: 'saved-reports', category: 'saved', title: 'Reportes guardados', description: 'Accesos rápidos personales.', enabled: true },
  { id: 'tickets-by-status', category: 'tickets', title: 'Tickets por estado', description: 'Evolución y distribución por estado.', enabled: true },
  { id: 'tickets-by-priority', category: 'tickets', title: 'Tickets por prioridad', description: 'Carga por urgencia operativa.', enabled: true },
  { id: 'tickets-by-client', category: 'tickets', title: 'Tickets por cliente', description: 'Volumen por cartera de clientes.', enabled: true },
  { id: 'tasks-by-status', category: 'tasks', title: 'Tareas por estado', description: 'Seguimiento operativo por etapa.', enabled: true },
  { id: 'tasks-by-technician', category: 'tasks', title: 'Tareas por técnico', description: 'Distribución por responsable.', enabled: true },
  { id: 'tasks-overdue-blocked', category: 'tasks', title: 'Tareas vencidas / bloqueadas', description: 'Control de cuellos de botella.', enabled: false },
  { id: 'stock-critical', category: 'stock', title: 'Stock crítico', description: 'Productos sin stock o bajo mínimo.', enabled: true },
  { id: 'stock-movements', category: 'stock', title: 'Movimientos de stock', description: 'Entradas y salidas en el período.', enabled: false },
  { id: 'stock-consumption', category: 'stock', title: 'Consumo por ticket/tarea', description: 'Consumo asociado a operación.', enabled: false },
  { id: 'deposit-requests-status', category: 'deposit-requests', title: 'Solicitudes por estado', description: 'Pipeline completo de solicitudes.', enabled: true },
  { id: 'deposit-requests-approved', category: 'deposit-requests', title: 'Solicitudes autorizadas', description: 'Seguimiento de aprobaciones.', enabled: false },
  { id: 'deposit-requests-dispatched', category: 'deposit-requests', title: 'Solicitudes despachadas', description: 'Tiempos y cumplimiento de despacho.', enabled: false },
  { id: 'activity-by-user', category: 'activity', title: 'Actividad por usuario', description: 'Auditoría de acciones por operador.', enabled: true },
  { id: 'activity-by-action-type', category: 'activity', title: 'Acciones por tipo', description: 'Distribución por tipo de evento.', enabled: false },
  { id: 'activity-closures-by-user', category: 'activity', title: 'Cierres por usuario', description: 'Cierres de tickets/tareas por usuario.', enabled: false }
];

export const REPORT_COLUMNS: Record<ReportId, ReportColumn[]> = {
  'saved-reports': [],
  'tickets-by-status': [
    { key: 'ticket_number', label: 'Ticket' },
    { key: 'title', label: 'Título' },
    { key: 'client', label: 'Cliente' },
    { key: 'priority', label: 'Prioridad' },
    { key: 'status', label: 'Estado' },
    { key: 'assigned_to', label: 'Asignado' },
    { key: 'created_at', label: 'Creación' },
    { key: 'closed_at', label: 'Cierre' }
  ],
  'tickets-by-priority': [
    { key: 'ticket_number', label: 'Ticket' },
    { key: 'title', label: 'Título' },
    { key: 'client', label: 'Cliente' },
    { key: 'priority', label: 'Prioridad' },
    { key: 'status', label: 'Estado' },
    { key: 'assigned_to', label: 'Asignado' },
    { key: 'created_at', label: 'Creación' },
    { key: 'closed_at', label: 'Cierre' }
  ],
  'tickets-by-client': [
    { key: 'ticket_number', label: 'Ticket' },
    { key: 'title', label: 'Título' },
    { key: 'client', label: 'Cliente' },
    { key: 'priority', label: 'Prioridad' },
    { key: 'status', label: 'Estado' },
    { key: 'assigned_to', label: 'Asignado' },
    { key: 'created_at', label: 'Creación' },
    { key: 'closed_at', label: 'Cierre' }
  ],
  'tasks-by-status': [
    { key: 'task_code', label: 'Código' },
    { key: 'title', label: 'Título' },
    { key: 'status', label: 'Estado' },
    { key: 'technician', label: 'Técnico' },
    { key: 'client', label: 'Cliente' },
    { key: 'created_at', label: 'Creación' },
    { key: 'due_at', label: 'Vencimiento' },
    { key: 'closed_at', label: 'Cierre' }
  ],
  'tasks-by-technician': [
    { key: 'task_code', label: 'Código' },
    { key: 'title', label: 'Título' },
    { key: 'status', label: 'Estado' },
    { key: 'technician', label: 'Técnico' },
    { key: 'client', label: 'Cliente' },
    { key: 'created_at', label: 'Creación' },
    { key: 'due_at', label: 'Vencimiento' },
    { key: 'closed_at', label: 'Cierre' }
  ],
  'tasks-overdue-blocked': [],
  'stock-critical': [
    { key: 'sku', label: 'SKU' },
    { key: 'product', label: 'Producto' },
    { key: 'category', label: 'Categoría' },
    { key: 'stock_current', label: 'Stock actual' },
    { key: 'stock_minimum', label: 'Stock mínimo' },
    { key: 'status', label: 'Estado' },
    { key: 'updated_at', label: 'Última actualización' }
  ],
  'stock-movements': [],
  'stock-consumption': [],
  'deposit-requests-status': [
    { key: 'request_number', label: 'Solicitud' },
    { key: 'source', label: 'Origen' },
    { key: 'requester', label: 'Solicitante' },
    { key: 'status', label: 'Estado' },
    { key: 'approved_by', label: 'Autorizado por' },
    { key: 'dispatched_by', label: 'Despachado por' },
    { key: 'created_at', label: 'Creación' },
    { key: 'dispatched_at', label: 'Despacho' }
  ],
  'deposit-requests-approved': [],
  'deposit-requests-dispatched': [],
  'activity-by-user': [
    { key: 'user', label: 'Usuario' },
    { key: 'action', label: 'Acción' },
    { key: 'entity', label: 'Entidad' },
    { key: 'entity_code', label: 'Código' },
    { key: 'date', label: 'Fecha' },
    { key: 'description', label: 'Descripción' }
  ],
  'activity-by-action-type': [],
  'activity-closures-by-user': []
};

export const ACTION_TYPE_LABELS: Record<string, string> = {
  'ticket.created': 'Ticket creado',
  'ticket.assignment_changed': 'Asignación de ticket modificada',
  'ticket.pending_executive_approval': 'Ticket pendiente de aprobación ejecutiva',
  'ticket.closed': 'Ticket cerrado',
  'ticket.approved_by_executive': 'Ticket aprobado por ejecutivo',
  'subtask.assigned_manually': 'Tarea asignada',
  'subtask.claimed': 'Tarea tomada por técnico',
  'subtask.closed': 'Tarea cerrada',
  'task.approved_by_executive': 'Tarea aprobada por ejecutivo',
  'request.created': 'Solicitud a depósito creada',
  'request.reviewed': 'Solicitud a depósito autorizada',
  'request.dispatched': 'Solicitud a depósito despachada',
  'stock.critical_marked': 'Stock marcado como crítico'
};

export const STATUS_LABELS: Record<string, string> = {
  OPEN: 'Abierto',
  IN_PROGRESS: 'En progreso',
  ON_HOLD: 'Bloqueado',
  RESOLVED: 'Resuelto',
  PENDING_APPROVAL: 'Pendiente',
  CLOSED: 'Cerrado',
  PENDING: 'Pendiente',
  PENDING_DISPATCH: 'Pendiente de despacho',
  PENDING_RECEIPT: 'Pendiente de recepción',
  APPROVED: 'Autorizado',
  COMPLETED: 'Completado',
  REJECTED: 'Rechazado',
  CANCELLED: 'Cancelado',
  BLOCKED: 'Bloqueado',
  SIN_STOCK: 'Sin stock',
  BAJO_MINIMO: 'Bajo mínimo',
  OK: 'OK'
};

export const PRIORITY_LABELS: Record<string, string> = {
  LOW: 'Baja',
  MEDIUM: 'Media',
  HIGH: 'Alta',
  CRITICAL: 'Crítica'
};

export const STATUS_OPTIONS = ['OPEN', 'IN_PROGRESS', 'ON_HOLD', 'RESOLVED', 'PENDING_APPROVAL', 'CLOSED', 'PENDING', 'PENDING_DISPATCH', 'PENDING_RECEIPT', 'APPROVED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'BLOCKED'];
export const PRIORITY_OPTIONS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

export function formatReportStatus(value: string | null | undefined): string {
  if (!value) {
    return '';
  }

  return STATUS_LABELS[value] ?? fallbackReadableLabel(value);
}

export function formatReportPriority(value: string | null | undefined): string {
  if (!value) {
    return '';
  }

  return PRIORITY_LABELS[value] ?? fallbackReadableLabel(value);
}

export function formatReportActionType(value: string | null | undefined): string {
  if (!value) {
    return '';
  }

  return ACTION_TYPE_LABELS[value] ?? fallbackReadableLabel(value);
}

export function formatReportDateTime(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) {
    return value === null || value === undefined ? '' : String(value);
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function fallbackReadableLabel(value: string): string {
  return value
    .replaceAll('.', ' ')
    .replaceAll('_', ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}
