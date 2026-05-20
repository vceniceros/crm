export type ReportCategoryKey = 'mis-reportes' | 'tickets' | 'tasks' | 'stock' | 'deposit-requests' | 'activity' | 'ejecutivos';

export type ReportRoleKey = 'admin' | 'ejecutivo' | 'deposito' | 'tecnico';

export type ReportId =
  | 'my-tickets'
  | 'my-tasks'
  | 'tickets-by-status'
  | 'tickets-by-priority'
  | 'tickets-by-client'
  | 'tickets-by-category'
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
  | 'activity-closures-by-user'
  | 'executive-performance'
  | 'executive-by-category'
  | 'executive-by-priority'
  | 'executive-by-client';

export interface ReportTabDefinition {
  key: ReportCategoryKey;
  label: string;
  roles?: ReportRoleKey[];
}

export interface ReportCardDefinition {
  id: ReportId;
  category: ReportCategoryKey;
  title: string;
  description: string;
  enabled: boolean;
  roles?: ReportRoleKey[];
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
  report_kind: 'tickets' | 'tasks' | 'my_tickets' | 'my_tasks' | 'stock_critical' | 'deposit_requests' | 'user_activity' | 'executive_performance';
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
  locations: ReportOption[];
  roles: ReportOption[];
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
  category_id?: string;
  location_id?: string;
  technician_id?: string;
  category?: string;
  warehouse_id?: string;
  only_critical?: boolean;
  requester?: string;
  approver?: string;
  user_id?: string;
  role_key?: string;
  action_type?: string;
}

export const REPORT_TABS: ReportTabDefinition[] = [
  { key: 'mis-reportes', label: 'Mis Reportes' },
  { key: 'tickets', label: 'Tickets', roles: ['admin', 'ejecutivo'] },
  { key: 'tasks', label: 'Tareas', roles: ['admin', 'ejecutivo'] },
  { key: 'stock', label: 'Depósito / Stock', roles: ['admin', 'ejecutivo'] },
  { key: 'deposit-requests', label: 'Solicitudes a depósito', roles: ['admin', 'ejecutivo'] },
  { key: 'activity', label: 'Actividad', roles: ['admin', 'ejecutivo'] },
  { key: 'ejecutivos', label: 'Reportes Ejecutivos', roles: ['admin', 'ejecutivo'] }
];

export const REPORT_CARDS: ReportCardDefinition[] = [
  { id: 'my-tickets', category: 'mis-reportes', title: 'Mis Tickets', description: 'Tus tickets creados o asignados con métricas de resolución.', enabled: true },
  { id: 'my-tasks', category: 'mis-reportes', title: 'Mis Tareas', description: 'Tus tareas activas y cerradas con métricas de cumplimiento.', enabled: true },
  { id: 'tickets-by-status', category: 'tickets', title: 'Tickets por estado', description: 'Evolución y distribución por estado.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'tickets-by-priority', category: 'tickets', title: 'Tickets por prioridad', description: 'Carga por urgencia operativa.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'tickets-by-client', category: 'tickets', title: 'Tickets por cliente', description: 'Volumen por cartera de clientes.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'tickets-by-category', category: 'tickets', title: 'Tickets por categoría', description: 'Tiempo de resolución promedio por categoría operacional.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'tasks-by-status', category: 'tasks', title: 'Tareas por estado', description: 'Seguimiento operativo por etapa.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'tasks-by-technician', category: 'tasks', title: 'Tareas por técnico', description: 'Distribución por responsable.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'tasks-overdue-blocked', category: 'tasks', title: 'Tareas vencidas / bloqueadas', description: 'Control de cuellos de botella.', enabled: false, roles: ['admin', 'ejecutivo'] },
  { id: 'stock-critical', category: 'stock', title: 'Stock crítico', description: 'Productos sin stock o bajo mínimo.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'stock-movements', category: 'stock', title: 'Movimientos de stock', description: 'Entradas y salidas en el período.', enabled: false, roles: ['admin', 'ejecutivo'] },
  { id: 'stock-consumption', category: 'stock', title: 'Consumo por ticket/tarea', description: 'Consumo asociado a operación.', enabled: false, roles: ['admin', 'ejecutivo'] },
  { id: 'deposit-requests-status', category: 'deposit-requests', title: 'Solicitudes por estado', description: 'Pipeline completo de solicitudes.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'deposit-requests-approved', category: 'deposit-requests', title: 'Solicitudes autorizadas', description: 'Seguimiento de aprobaciones.', enabled: false, roles: ['admin', 'ejecutivo'] },
  { id: 'deposit-requests-dispatched', category: 'deposit-requests', title: 'Solicitudes despachadas', description: 'Tiempos y cumplimiento de despacho.', enabled: false, roles: ['admin', 'ejecutivo'] },
  { id: 'activity-by-user', category: 'activity', title: 'Actividad por usuario', description: 'Auditoría de acciones por operador.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'activity-by-action-type', category: 'activity', title: 'Acciones por tipo', description: 'Distribución por tipo de evento.', enabled: false, roles: ['admin', 'ejecutivo'] },
  { id: 'activity-closures-by-user', category: 'activity', title: 'Cierres por usuario', description: 'Cierres de tickets/tareas por usuario.', enabled: false, roles: ['admin', 'ejecutivo'] },
  { id: 'executive-performance', category: 'ejecutivos', title: 'Desempeño por empleado', description: 'Performance comparativa por usuario o rol.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'executive-by-category', category: 'ejecutivos', title: 'Resolución por categoría', description: 'Comparativa ejecutiva por categoría operativa.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'executive-by-priority', category: 'ejecutivos', title: 'Resolución por criticidad', description: 'Comparativa ejecutiva por prioridad.', enabled: true, roles: ['admin', 'ejecutivo'] },
  { id: 'executive-by-client', category: 'ejecutivos', title: 'Análisis por cliente', description: 'Comparativa ejecutiva por cliente.', enabled: true, roles: ['admin', 'ejecutivo'] }
];

export const REPORT_COLUMNS: Record<ReportId, ReportColumn[]> = {
  'my-tickets': [
    { key: 'ticket_number', label: 'Ticket' },
    { key: 'title', label: 'Título' },
    { key: 'status', label: 'Estado' },
    { key: 'priority', label: 'Prioridad' },
    { key: 'category', label: 'Categoría' },
    { key: 'client', label: 'Cliente' },
    { key: 'location', label: 'Ubicación' },
    { key: 'created_at', label: 'Creación' },
    { key: 'resolution_hours', label: 'Hs resolución' }
  ],
  'my-tasks': [
    { key: 'task_code', label: 'Código' },
    { key: 'title', label: 'Tarea' },
    { key: 'status', label: 'Estado' },
    { key: 'priority', label: 'Prioridad' },
    { key: 'category', label: 'Categoría' },
    { key: 'client', label: 'Cliente' },
    { key: 'created_at', label: 'Inicio' },
    { key: 'completion_hours', label: 'Hs hasta cierre' }
  ],
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
  'tickets-by-category': [
    { key: 'category_name', label: 'Categoría' },
    { key: 'total_tickets', label: 'Total tickets' },
    { key: 'closed_tickets', label: 'Cerrados' },
    { key: 'avg_resolution_hours', label: 'Prom. hs resolución' },
    { key: 'min_resolution_hours', label: 'Mín. hs resolución' },
    { key: 'max_resolution_hours', label: 'Máx. hs resolución' }
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
  'activity-closures-by-user': [],
  'executive-performance': [
    { key: 'group_label', label: 'Empleado' },
    { key: 'primary_role', label: 'Rol principal' },
    { key: 'total_assigned', label: 'Asignados' },
    { key: 'closed_count', label: 'Cerrados' },
    { key: 'rejected_count', label: 'Rechazos' },
    { key: 'avg_close_hours', label: 'Prom. cierre (h)' },
    { key: 'min_close_hours', label: 'Mín. cierre (h)' },
    { key: 'max_close_hours', label: 'Máx. cierre (h)' },
    { key: 'total_comments', label: 'Comentarios' },
    { key: 'avg_comments_per_ticket', label: 'Prom. comentarios/ticket' }
  ],
  'executive-by-category': [
    { key: 'group_label', label: 'Categoría' },
    { key: 'total_assigned', label: 'Tickets' },
    { key: 'closed_count', label: 'Cerrados' },
    { key: 'rejected_count', label: 'Rechazos' },
    { key: 'avg_close_hours', label: 'Prom. cierre (h)' },
    { key: 'min_close_hours', label: 'Mín. cierre (h)' },
    { key: 'max_close_hours', label: 'Máx. cierre (h)' },
    { key: 'total_comments', label: 'Comentarios' },
    { key: 'avg_comments_per_ticket', label: 'Prom. comentarios/ticket' }
  ],
  'executive-by-priority': [
    { key: 'group_label', label: 'Prioridad' },
    { key: 'total_assigned', label: 'Tickets' },
    { key: 'closed_count', label: 'Cerrados' },
    { key: 'rejected_count', label: 'Rechazos' },
    { key: 'avg_close_hours', label: 'Prom. cierre (h)' },
    { key: 'min_close_hours', label: 'Mín. cierre (h)' },
    { key: 'max_close_hours', label: 'Máx. cierre (h)' },
    { key: 'total_comments', label: 'Comentarios' },
    { key: 'avg_comments_per_ticket', label: 'Prom. comentarios/ticket' }
  ],
  'executive-by-client': [
    { key: 'group_label', label: 'Cliente' },
    { key: 'total_assigned', label: 'Tickets' },
    { key: 'closed_count', label: 'Cerrados' },
    { key: 'rejected_count', label: 'Rechazos' },
    { key: 'avg_close_hours', label: 'Prom. cierre (h)' },
    { key: 'min_close_hours', label: 'Mín. cierre (h)' },
    { key: 'max_close_hours', label: 'Máx. cierre (h)' },
    { key: 'total_comments', label: 'Comentarios' },
    { key: 'avg_comments_per_ticket', label: 'Prom. comentarios/ticket' }
  ]
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
