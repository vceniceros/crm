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

-- Sistema
(gen_random_uuid(), 'user_assigned_role', 'Asignación de rol', false, '["admin"]')

ON CONFLICT (event_code) DO NOTHING;