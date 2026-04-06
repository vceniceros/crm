import { Routes } from '@angular/router';

import { DashboardPageComponent } from './features/dashboard/components/dashboard-page/dashboard-page.component';
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
				path: 'tasks',
				component: TasksPageComponent,
				data: { title: 'Tareas' }
			}
		]
	}
];
