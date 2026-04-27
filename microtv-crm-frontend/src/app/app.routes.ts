import { Routes } from '@angular/router';

import { guestOnlyGuard, authGuard, adminOnlyGuard, adminOrExecutiveGuard } from './core/guards/auth.guard';
import { DashboardPageComponent } from './features/dashboard/components/dashboard-page/dashboard-page.component';
import { LoginPageComponent } from './features/auth/components/login-page/login-page.component';
import { ClientsPageComponent } from './features/clients/components/clients-page/clients-page.component';
import { InventoryPageComponent } from './features/inventory/components/inventory-page/inventory-page.component';
import { InventoryRequestsPageComponent } from './features/inventory/components/inventory-requests-page/inventory-requests-page.component';
import { AppShellComponent } from './layout/components/app-shell/app-shell.component';

export const routes: Routes = [
	{
		path: 'login',
		canActivate: [guestOnlyGuard],
		component: LoginPageComponent,
		data: { title: 'Ingresar' }
	},
	{
		// Public survey form alias — NO auth guard
		path: 'survey/:token',
		loadComponent: () =>
			import('./features/satisfaction/components/satisfaction-page/satisfaction-page.component').then(
				(m) => m.SatisfactionPageComponent
			),
		data: { title: 'Encuesta de satisfacción' }
	},
	{
		// Public satisfaction form — NO auth guard
		path: 'satisfaction/:token',
		loadComponent: () =>
			import('./features/satisfaction/components/satisfaction-page/satisfaction-page.component').then(
				(m) => m.SatisfactionPageComponent
			),
		data: { title: 'Encuesta de satisfacción' }
	},
	{
		path: '',
		canActivate: [authGuard],
		component: AppShellComponent,
		children: [
			{
				path: '',
				pathMatch: 'full',
				component: DashboardPageComponent,
				data: { title: 'Dashboard' }
			},
			{
				path: 'inventory',
				component: InventoryPageComponent,
				data: { title: 'Deposito' }
			},
			{
				path: 'inventory/requests',
				component: InventoryRequestsPageComponent,
				data: { title: 'Solicitudes de depósito' }
			},
			{
				path: 'clients',
				component: ClientsPageComponent,
				data: { title: 'Clientes' }
			},
			{
				path: 'tickets',
				loadComponent: () => import('./features/tickets/components/tickets-page/tickets-page.component').then((module) => module.TicketsPageComponent),
				data: { title: 'Tickets' }
			},
			{
				path: 'tickets/:ticketId',
				loadComponent: () =>
					import('./features/tickets/components/ticket-execution-page/ticket-execution-page.component').then(
						(module) => module.TicketExecutionPageComponent
					),
				data: { title: 'Ejecución de ticket' }
			},
			{
				path: 'tasks',
				loadComponent: () => import('./features/tasks/components/tasks-page/tasks-page.component').then((module) => module.TasksPageComponent),
				data: { title: 'Tareas' }
			},
			{
				path: 'tasks/history',
				canActivate: [adminOrExecutiveGuard],
				loadComponent: () => import('./features/tasks/components/tasks-page/tasks-page.component').then((module) => module.TasksPageComponent),
				data: { title: 'Historial de tareas' }
			},
			{
				path: 'tasks/templates',
				canActivate: [adminOnlyGuard],
				loadComponent: () => import('./features/task-templates/components/task-templates-page/task-templates-page.component').then((module) => module.TaskTemplatesPageComponent),
				data: { title: 'Templates de tareas' }
			},
			{
				path: 'tasks/templates/new',
				canActivate: [adminOnlyGuard],
				loadComponent: () => import('./features/task-templates/components/task-template-form-page/task-template-form-page.component').then((module) => module.TaskTemplateFormPageComponent),
				data: { title: 'Nuevo template de tarea' }
			},
			{
				path: 'tasks/templates/:templateId',
				canActivate: [adminOnlyGuard],
				loadComponent: () => import('./features/task-templates/components/task-template-detail-page/task-template-detail-page.component').then((module) => module.TaskTemplateDetailPageComponent),
				data: { title: 'Detalle de template' }
			},
			{
				path: 'tasks/templates/:templateId/edit',
				canActivate: [adminOnlyGuard],
				loadComponent: () => import('./features/task-templates/components/task-template-form-page/task-template-form-page.component').then((module) => module.TaskTemplateFormPageComponent),
				data: { title: 'Editar template de tarea' }
			},
			{
				path: 'tasks/subtask-success',
				loadComponent: () => import('./features/tasks/components/subtask-success-page/subtask-success-page.component').then((module) => module.SubtaskSuccessPageComponent),
				data: { title: 'Subtarea completada' }
			},
			{
				path: 'tasks/:taskId',
				loadComponent: () => import('./features/tasks/components/task-execution-page/task-execution-page.component').then((module) => module.TaskExecutionPageComponent),
				data: { title: 'Ejecución de tarea' }
			},
			{
				path: 'reports',
				canActivate: [adminOrExecutiveGuard],
				loadChildren: () => import('./features/reports/reports-routing.module').then((module) => module.REPORTS_ROUTES),
				data: { title: 'Reportes' }
			},
			{
				path: 'settings',
				canActivate: [adminOrExecutiveGuard],
				loadComponent: () => import('./features/settings/components/settings-page/settings-page.component').then((module) => module.SettingsPageComponent),
				data: { title: 'Configuración' }
			}
		]
	},
	{
		path: '**',
		redirectTo: ''
	}
];
