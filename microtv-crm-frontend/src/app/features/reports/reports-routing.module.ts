import { Routes } from '@angular/router';

import { ReportDetailComponent } from './report-detail.component';
import { ReportListComponent } from './report-list.component';
import { ReportsComponent } from './reports.component';

export const REPORTS_ROUTES: Routes = [
  {
    path: '',
    component: ReportsComponent,
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'tickets'
      },
      {
        path: ':category',
        component: ReportListComponent
      },
      {
        path: ':category/:reportId',
        component: ReportDetailComponent
      }
    ]
  }
];
