export type UiHelpModuleId = 'dashboard' | 'tickets' | 'tasks' | 'inventory' | 'clients' | 'settings';

export interface UiHelpEmptyStateText {
  title: string;
  description: string;
}

export interface UiHelpModuleTexts {
  moduleTitle: string;
  summary: string;
  bullets: readonly string[];
  actions: readonly string[];
  tooltip: string;
  emptyStates: Readonly<Record<string, UiHelpEmptyStateText>>;
}

export const UI_HELP_TEXTS: Readonly<Record<UiHelpModuleId, UiHelpModuleTexts>> = {
  dashboard: {
    moduleTitle: 'Dashboard',
    summary: 'Resumen operativo del dia para detectar atrasos, volumen y foco inmediato.',
    bullets: [
      'Los KPIs muestran carga actual y cumplimiento del equipo.',
      'Tickets recientes permite entrar rapido a casos activos.',
      'Actividad reciente muestra cambios y responsables en tiempo real.'
    ],
    actions: [
      'Priorizar lo urgente antes de asignar nuevas tareas.',
      'Entrar a Tickets o Tareas desde los bloques con desvio.'
    ],
    tooltip: 'Leelo como tablero de control: si un indicador sube o baja fuerte, entra al modulo relacionado.',
    emptyStates: {
      noData: {
        title: 'Todavia no hay actividad para mostrar.',
        description: 'Cuando ingresen tickets o avances, este resumen se completa automaticamente.'
      }
    }
  },
  tickets: {
    moduleTitle: 'Tickets',
    summary: 'Registro y seguimiento de incidentes o pedidos desde el alta hasta el cierre.',
    bullets: [
      'Un ticket representa un caso de cliente con trazabilidad.',
      'Crealo desde Crear ticket y completalo con datos claros.',
      'Estados: Abierto, En gestion, En espera, Resuelto y Cerrado.'
    ],
    actions: [
      'Tomar tickets sin asignar cuando tu rol lo permita.',
      'Entrar en Ver ejecucion para cargar avances y evidencia.'
    ],
    tooltip: 'Cada pestaña separa tu trabajo: asignados, disponibles, seguimiento general e historial.',
    emptyStates: {
      assigned: {
        title: 'No tenes tickets asignados en esta vista.',
        description: 'Revisa Sin asignar o ajusta filtros para ver mas casos.'
      },
      unassigned: {
        title: 'No hay tickets disponibles para tomar.',
        description: 'Cuando ingrese un caso nuevo en tu rol, aparecera aqui.'
      },
      tracking: {
        title: 'No hay tickets para seguimiento general.',
        description: 'Proba otro estado o amplia la busqueda para ver historial operativo.'
      },
      history: {
        title: 'No hay tickets cerrados con esos filtros.',
        description: 'Quita filtros para revisar cierres y encuestas anteriores.'
      }
    }
  },
  tasks: {
    moduleTitle: 'Tareas',
    summary: 'Ejecucion operativa de trabajo planificado en subtareas por rol.',
    bullets: [
      'Una tarea nace desde un template y puede estar ligada a un ticket.',
      'A diferencia del ticket, la tarea ordena ejecucion paso a paso.',
      'El progreso avanza al completar subtareas en orden.'
    ],
    actions: [
      'Tomar subtareas pendientes de tu rol.',
      'Completar la subtarea activa para desbloquear la siguiente.'
    ],
    tooltip: 'Si una subtarea no se completa, la tarea no avanza aunque tenga otros datos cargados.',
    emptyStates: {
      assigned: {
        title: 'No tenes tareas asignadas en este momento.',
        description: 'Cuando se te asigne una tarea, la veras en esta bandeja.'
      },
      unassigned: {
        title: 'No hay subtareas pendientes para tus roles.',
        description: 'Apareceran aqui cuando haya trabajo disponible para tomar.'
      },
      tracking: {
        title: 'No hay tareas para seguimiento general.',
        description: 'Ajusta filtros o cambia de pestaña para revisar otras tareas.'
      },
      history: {
        title: 'No hay tareas aprobadas en el historial.',
        description: 'Cuando una tarea se cierre correctamente, se listara aqui.'
      }
    }
  },
  inventory: {
    moduleTitle: 'Deposito y stock',
    summary: 'Control de productos y flujo de entrega para mantener la operacion abastecida.',
    bullets: [
      'Una solicitud inicia el flujo de salida de materiales.',
      'Flujo recomendado: solicitud, autorizacion y despacho.',
      'Cada rol ve acciones segun permisos de deposito.'
    ],
    actions: [
      'Filtrar por codigo o categoria para ubicar productos rapido.',
      'Crear producto nuevo cuando este habilitado tu rol.'
    ],
    tooltip: 'Este modulo combina stock disponible y gestion de solicitudes para despacho operativo.',
    emptyStates: {
      filters: {
        title: 'No hay resultados para los filtros actuales.',
        description: 'Cambia categoria, limpia filtros o busca por otro codigo.'
      }
    }
  },
  clients: {
    moduleTitle: 'Clientes y ubicaciones',
    summary: 'Base comercial con datos de contacto y ubicacion para operar tickets y tareas.',
    bullets: [
      'Cada cliente puede tener ubicaciones para trabajo en campo.',
      'La ubicacion se reutiliza en tareas y rutas de atencion.',
      'Mantener datos al dia evita errores en asignaciones.'
    ],
    actions: [
      'Crear o editar clientes con informacion completa.',
      'Abrir ubicacion para validar direccion antes de operar.'
    ],
    tooltip: 'Si un cliente no existe o esta incompleto, despues faltaran datos en Tickets y Tareas.',
    emptyStates: {
      default: {
        title: 'Todavia no hay clientes activos.',
        description: 'Crea el primer cliente para habilitar tareas y seguimiento asociado.'
      }
    }
  },
  settings: {
    moduleTitle: 'Configuracion',
    summary: 'Administracion central de usuarios, permisos, reglas y catalogos del CRM.',
    bullets: [
      'Aqui se definen roles, estados, prioridades y SLA.',
      'Usuarios y permisos impactan lo que cada perfil puede hacer.',
      'Templates y notificaciones ordenan el flujo operativo.'
    ],
    actions: [
      'Actualizar catalogos antes de cambios de proceso.',
      'Revisar permisos cuando un usuario no ve una accion.'
    ],
    tooltip: 'Cambios en Configuracion afectan a todo el CRM; conviene aplicarlos con criterio y validacion.',
    emptyStates: {}
  }
} as const;