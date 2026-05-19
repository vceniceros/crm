import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { catchError, map, of, startWith } from 'rxjs';

import { DashboardData } from '../../../../core/models/dashboard.model';
import { DashboardService } from '../../../../core/services/dashboard.service';
import { UI_HELP_TEXTS } from '../../../../core/config/ui-help-texts.config';
import { RecentActivityTimelineComponent } from '../recent-activity-timeline/recent-activity-timeline.component';
import { RecentTicketsTableComponent } from '../recent-tickets-table/recent-tickets-table.component';
import { StatsCardsComponent } from '../stats-cards/stats-cards.component';
import { PendingMenuComponent } from '../pending-menu/pending-menu.component';
import { ContextHelpCardComponent } from '../../../../shared/ui/context-help-card/context-help-card.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';

interface DashboardPageVm {
  dashboard: DashboardData | null;
  loading: boolean;
  error: string | null;
}

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [
    AsyncPipe,
    ContextHelpCardComponent,
    PageTitleComponent,
    PendingMenuComponent,
    RecentActivityTimelineComponent,
    RecentTicketsTableComponent,
    StatsCardsComponent
  ],
  templateUrl: './dashboard-page.component.html',
  styleUrl: './dashboard-page.component.scss'
})
export class DashboardPageComponent {
  private readonly dashboardService = inject(DashboardService);
  readonly helpText = UI_HELP_TEXTS.dashboard;

  readonly vm$ = this.dashboardService.getSummary().pipe(
    map(
      (dashboard): DashboardPageVm => ({
        dashboard,
        loading: false,
        error: null
      })
    ),
    startWith({
      dashboard: null,
      loading: true,
      error: null
    } satisfies DashboardPageVm),
    catchError((error: unknown) =>
      of({
        dashboard: null,
        loading: false,
        error: error instanceof Error ? error.message : 'No se pudo cargar el dashboard.'
      } satisfies DashboardPageVm)
    )
  );
}
