11. poder acotar quien puede manejar el stock dentro de configuraciones, configurar quien puede manejar stock independiente al rol

12. poder agregar un importasdor a prodcutos para cargar productos masivamente desde un excel o csv

13. agregar productos minimos a tickets y tareas, para que al crear un ticket o tarea puedas agregar productos relacionados al mismo

14. darle permisos al ejecutivo de crear usuario no admin

15. crear todos los correos para todos los usuarios

2. agregar carga de documentos a los tickets y permitir descargar los documentos cargados en los tickets
3. mismo para tareas

10. ver si leafleat permite marcar ubicaciones por dirección y no solo por coordenadas

12. que refrescar no tire al dashboard, que te mantenga en el menu donde estabas

1. Add a dedicated section inside the Settings menu to manage role permissions and special user-level permissions. This section must be highly UX-friendly, so that any administrator can clearly understand what is being configured without ambiguity. Do not make it a raw technical permissions matrix only; present permissions grouped by functional domain and with clear labels, descriptions, and examples of impact. This section should also unify the stock-related and override permissions into the same permission system. In addition to role-based permissions, allow defining specific user-level overrides for sensitive actions. At minimum, support configuring:
   - which users can manage stock,
   - which users can delete products,
   - which users can reassign tickets or warehouse requests/orders to any role,
   - which users can delete comments.
   All users should still be allowed to edit their own comments, so comment editing must remain broadly available while comment deletion stays permission-based. The goal is to make permissions understandable, auditable, and easy to manage from a single coherent settings area.

2. Enable executive users to access and use the Settings menu as well. However, executive users must not be allowed to modify permissions that affect administrator capabilities or administrator-level access control. In practice, executives should be able to use operational and configuration areas that are relevant to business management, but the highest-sensitivity permission management must remain restricted to administrators only. Reflect this clearly both in backend authorization rules and in frontend visibility and UX, so the interface explains why some options are visible but read-only or hidden.

3. Add a Settings section to configure email delivery through SMTP. This configuration should be optional and safe by design. The CRM must continue working correctly even if SMTP is not configured. The system should validate configuration values, provide a clear status indicator, and explain whether email notifications are currently enabled or disabled. Include a test action if possible, but do not make email configuration mandatory for the rest of the platform to function.

4. Add email delivery as an optional channel for CRM notifications. Notification delivery must not break if SMTP has not been configured yet. If email settings are missing, invalid, or disabled, the system must continue sending in-app notifications normally and simply skip the email channel gracefully. Apply the same optional and fault-tolerant design to SMS and WhatsApp notifications as well: if Twilio or any related provider settings are not configured, the notification pipeline must still work without crashing, blocking, or producing broken UX. In short, external delivery channels must be additive and optional, never required for core notification functionality.

5. Add a Settings section to configure SMS delivery through Twilio. This configuration must be optional, validated, and integrated into the same notification channel strategy described above. If it is not configured, the CRM must keep functioning normally and notifications must continue through the channels that are available.

6. Add a Settings section to configure WhatsApp delivery through Twilio. This must follow the same design rules as SMTP and SMS: optional setup, clear status visibility, graceful fallback behavior, and no disruption to core CRM notifications if it is missing or disabled.

7. Add an imperative and comprehensive user activity log section. This is a required feature. Use the full database context to determine which relevant actions should be recorded. The activity log should allow administrators to inspect each user’s relevant actions across the system, including at minimum login, logout, and meaningful business actions performed inside the CRM. The log should not be limited to authentication events only; it should cover the operational actions already represented in the database and workflows. Design it so it is actually useful for audit, support, and internal control, not just as a passive technical log. Prefer structured records with actor, action, target entity, timestamp, and contextual summary.

8. Do not implement stock-related permission control as a separate disconnected feature. Merge it into the unified permissions system described in point 1. Stock handling permissions, product deletion permissions, reassignment permissions, and comment deletion permissions should all belong to the same centralized permission management model, with role-based defaults and optional user-specific overrides where necessary.

apartado config:

- agregar reglas de visibilidad para los tickets segun quien deberia poder ver cada cosa
- autoomatizar las asignaciones de tickets segun criterios definidos 
- templates de pedidos que vaya para config
- sla: - agregar un apartado para configurar los sla de cada tipo de ticket, con tiempos de respuesta y cierre, y que el sistema pueda mostrar alertas o marcar tickets que estén por vencer o vencidos
- agregar la base de conocimientos a config para que se pueda administrar desde ahí, con categorias, subcategorias, articulos, etc
- asociar activos: buses por ejemplo, dvr's, etc
- configurar aprovaciones: poder definir categorias de tickets o solicitudes que requieran de una cierta aprobacion de alguna persona o rol, y configurar quien es esa persona o rol que debe aprobar, y que el sistema pueda manejar ese flujo de aprobaciones

- reportes: poder compartir reportes con otros usuarios ahi entrar el armar reportes personalizados, y poder compartirlos con otros usuarios o roles, o dejarlos privados para el usuario que los creó



o
- meter busqueda de producto por nombre  despacho real
- agregar categorias a despachos reales/ productos requeridos (ejemplo si son 5 camaras marcar ccamaras 5 entoncers cualquier producto de tipo camara ya cumpliria esa categoria)
- agregar el boton de camara al adjuntaar multimedia

- poder pegar capturas en multimedia

- unificar las funciones en un panel
- poder buscar tickets por comentarios
- poder asignar a mas de un tecncio a un ticket
- agregar un campo de "tipo de solicitud" a los tickets, para poder categorizar mejor los tickets y luego poder hacer reportes o reglas de asignacion basados en ese campo

- base de conocimientos: 

- agregar una apartado de assets (activos) para poder asociar activos a los tickets

- agregar herramientas de trabajo (autos, herramientas, etc) para poder asociar a los tickets y llevar un control de su uso   

