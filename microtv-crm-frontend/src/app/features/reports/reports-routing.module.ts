import { inject } from '@angular/core';
import { CanActivateFn, Router, Routes } from '@angular/router';

import { AuthSessionService } from '../../core/services/auth-session.service';
import { ReportDetailComponent } from './report-detail.component';
import { ReportListComponent } from './report-list.component';
import { ReportsComponent } from './reports.component';
import { REPORT_CARDS, REPORT_TABS, ReportCardDefinition, ReportCategoryKey } from './report.types';

function hasRequiredRole(requiredRoles: string[] | undefined, currentRoles: string[]): boolean {
  return !requiredRoles || requiredRoles.some((role) => currentRoles.includes(role));
}

function resolveFallbackCategory(currentRoles: string[]): ReportCategoryKey {
  return REPORT_TABS.find((tab) => hasRequiredRole(tab.roles, currentRoles))?.key ?? 'mis-reportes';
}

function categoryAllowed(category: string | null, currentRoles: string[]): boolean {
  if (!category) {
    return true;
  }

  const tab = REPORT_TABS.find((candidate) => candidate.key === category);
  return Boolean(tab && hasRequiredRole(tab.roles, currentRoles));
}

function reportAllowed(reportId: string | null, currentRoles: string[]): boolean {
  if (!reportId) {
    return true;
  }

  const report = REPORT_CARDS.find((candidate) => candidate.id === reportId) as ReportCardDefinition | undefined;
  return Boolean(report && hasRequiredRole(report.roles, currentRoles));
}

const reportsCategoryGuard: CanActivateFn = (route) => {
  const authSessionService = inject(AuthSessionService);
  const router = inject(Router);
  const currentRoles = authSessionService.sessionSnapshot()?.user.role_keys ?? [];
  const category = route.paramMap.get('category');

  if (categoryAllowed(category, currentRoles)) {
    return true;
  }

  return router.createUrlTree(['/reports', resolveFallbackCategory(currentRoles)]);
};

const reportsDetailGuard: CanActivateFn = (route) => {
  const authSessionService = inject(AuthSessionService);
  const router = inject(Router);
  const currentRoles = authSessionService.sessionSnapshot()?.user.role_keys ?? [];
  const category = route.paramMap.get('category');
  const reportId = route.paramMap.get('reportId');

  if (categoryAllowed(category, currentRoles) && reportAllowed(reportId, currentRoles)) {
    return true;
  }

  return router.createUrlTree(['/reports', resolveFallbackCategory(currentRoles)]);
};

export const REPORTS_ROUTES: Routes = [
  {
    path: '',
    component: ReportsComponent,
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'mis-reportes'
      },
      {
        path: ':category',
        canActivate: [reportsCategoryGuard],
        component: ReportListComponent
      },
      {
        path: ':category/:reportId',
        canActivate: [reportsDetailGuard],
        component: ReportDetailComponent
      }
    ]
  }
];
