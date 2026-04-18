import { Routes } from '@angular/router';

import { guestOnlyGuard, authGuard } from './core/guards/auth.guard';
import { DashboardPageComponent } from './features/dashboard/components/dashboard-page/dashboard-page.component';
import { LoginPageComponent } from './features/auth/components/login-page/login-page.component';
import { ClientsPageComponent } from './features/clients/components/clients-page/clients-page.component';
import { InventoryPageComponent } from './features/inventory/components/inventory-page/inventory-page.component';
import { InventoryRequestsPageComponent } from './features/inventory/components/inventory-requests-page/inventory-requests-page.component';
import { TicketExecutionPageComponent } from './features/tickets/components/ticket-execution-page/ticket-execution-page.component';
import { TicketsPageComponent } from './features/tickets/components/tickets-page/tickets-page.component';
import { AppShellComponent } from './layout/components/app-shell/app-shell.component';

export const routes: Routes = [
	{
		path: 'login',
		canActivate: [guestOnlyGuard],
		component: LoginPageComponent,
		data: { title: 'Ingresar' }
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
				component: TicketsPageComponent,
				data: { title: 'Tickets' }
			},
			{
				path: 'tickets/:ticketId',
				component: TicketExecutionPageComponent,
				data: { title: 'Ejecución de ticket' }
			},
			{
				path: 'tasks',
				loadComponent: () => import('./features/tasks/components/tasks-page/tasks-page.component').then((module) => module.TasksPageComponent),
				data: { title: 'Tareas' }
			},
			{
				path: 'tasks/templates',
				loadComponent: () => import('./features/task-templates/components/task-templates-page/task-templates-page.component').then((module) => module.TaskTemplatesPageComponent),
				data: { title: 'Templates de tareas' }
			},
			{
				path: 'tasks/templates/new',
				loadComponent: () => import('./features/task-templates/components/task-template-form-page/task-template-form-page.component').then((module) => module.TaskTemplateFormPageComponent),
				data: { title: 'Nuevo template de tarea' }
			},
			{
				path: 'tasks/templates/:templateId',
				loadComponent: () => import('./features/task-templates/components/task-template-detail-page/task-template-detail-page.component').then((module) => module.TaskTemplateDetailPageComponent),
				data: { title: 'Detalle de template' }
			},
			{
				path: 'tasks/templates/:templateId/edit',
				loadComponent: () => import('./features/task-templates/components/task-template-form-page/task-template-form-page.component').then((module) => module.TaskTemplateFormPageComponent),
				data: { title: 'Editar template de tarea' }
			},
			{
				path: 'tasks/:taskId',
				loadComponent: () => import('./features/tasks/components/task-execution-page/task-execution-page.component').then((module) => module.TaskExecutionPageComponent),
				data: { title: 'Ejecución de tarea' }
			}
		]
	},
	{
		path: '**',
		redirectTo: ''
	}
];
