import { Routes } from '@angular/router';

import { DashboardPageComponent } from './features/dashboard/components/dashboard-page/dashboard-page.component';
import { ClientsPageComponent } from './features/clients/components/clients-page/clients-page.component';
import { InventoryPageComponent } from './features/inventory/components/inventory-page/inventory-page.component';
import { TaskExecutionPageComponent } from './features/tasks/components/task-execution-page/task-execution-page.component';
import { TicketExecutionPageComponent } from './features/tickets/components/ticket-execution-page/ticket-execution-page.component';
import { TicketsPageComponent } from './features/tickets/components/tickets-page/tickets-page.component';
import { TasksPageComponent } from './features/tasks/components/tasks-page/tasks-page.component';
import { AppShellComponent } from './layout/components/app-shell/app-shell.component';

export const routes: Routes = [
	{
		path: '',
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
				component: TasksPageComponent,
				data: { title: 'Tareas' }
			},
			{
				path: 'tasks/:taskId',
				component: TaskExecutionPageComponent,
				data: { title: 'Ejecución de tarea' }
			}
		]
	}
];
