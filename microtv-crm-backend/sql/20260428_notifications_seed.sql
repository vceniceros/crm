CREATE TABLE IF NOT EXISTS crm_notification_rules (
	notification_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	event_code           TEXT NOT NULL UNIQUE,
	label                TEXT NOT NULL,
	notify_assigned      BOOLEAN NOT NULL DEFAULT TRUE,
	notify_roles_json    JSONB NOT NULL DEFAULT '[]',
	created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO crm_notification_rules 
(notification_rule_id, event_code, label, notify_assigned, notify_roles_json)
VALUES

-- Tickets
(gen_random_uuid(), 'ticket_assigned', 'Ticket asignado', true, '["admin","tecnico"]'),
(gen_random_uuid(), 'ticket_unassigned', 'Ticket desasignado', true, '["admin"]'),
(gen_random_uuid(), 'ticket_status_changed', 'Cambio de estado de ticket', true, '["admin","tecnico"]'),
(gen_random_uuid(), 'ticket_closed', 'Ticket cerrado', true, '["admin"]'),
(gen_random_uuid(), 'ticket_reopened', 'Ticket reabierto', true, '["admin","tecnico"]'),

-- Comentarios
(gen_random_uuid(), 'ticket_comment_added', 'Nuevo comentario en ticket', true, '["admin","tecnico"]'),

-- Depósito
(gen_random_uuid(), 'inventory_request_created', 'Solicitud de depósito creada', true, '["deposito"]'),
(gen_random_uuid(), 'inventory_request_approved', 'Solicitud aprobada', true, '["tecnico","admin"]'),
(gen_random_uuid(), 'inventory_request_rejected', 'Solicitud rechazada', true, '["tecnico","admin"]'),
(gen_random_uuid(), 'inventory_dispatch_done', 'Despacho realizado', true, '["tecnico","admin"]'),

-- Tareas
(gen_random_uuid(), 'task_assigned', 'Tarea asignada', true, '["tecnico"]'),
(gen_random_uuid(), 'task_completed', 'Tarea completada', true, '["admin"]'),
(gen_random_uuid(), 'task_comment_added', 'Comentario en tarea', true, '["admin","tecnico"]'),

-- Nuevos eventos de notificaciones operativas
(gen_random_uuid(), 'task_pre_form_completed', 'Formulario previo completado del pedido', true, '["ejecutivo"]'),
(gen_random_uuid(), 'ticket_satisfaction_submitted', 'Encuesta de satisfacción de ticket respondida', true, '["ejecutivo","tecnico"]'),
(gen_random_uuid(), 'task_satisfaction_submitted', 'Encuesta de satisfacción de pedido respondida', true, '["ejecutivo","tecnico"]'),
(gen_random_uuid(), 'stock_low', 'Producto con stock bajo', true, '["ejecutivo","deposito"]'),
(gen_random_uuid(), 'stock_out', 'Producto sin stock', true, '["ejecutivo","deposito"]'),
(gen_random_uuid(), 'ticket_unassigned_in_role', 'Ticket sin asignar en el rol', true, '["tecnico"]'),
(gen_random_uuid(), 'task_unassigned_in_role', 'Pedido o subtarea sin asignar en el rol', true, '["tecnico","deposito","ejecutivo"]'),
(gen_random_uuid(), 'deposit_pending_dispatch', 'Solicitud aprobada pendiente de despacho', true, '["deposito"]'),
(gen_random_uuid(), 'deposit_products_installed', 'Materiales confirmados como recibidos/instalados', true, '["deposito"]'),

-- Sistema
(gen_random_uuid(), 'user_assigned_role', 'Asignación de rol', false, '["admin"]')

ON CONFLICT (event_code) DO NOTHING;