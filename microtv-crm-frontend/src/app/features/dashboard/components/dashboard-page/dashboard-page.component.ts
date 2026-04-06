import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';

import { MockLayoutDataService } from '../../../../core/services/mock-layout-data.service';
import { RecentActivityTimelineComponent } from '../recent-activity-timeline/recent-activity-timeline.component';
import { RecentTicketsTableComponent } from '../recent-tickets-table/recent-tickets-table.component';
import { StatsCardsComponent } from '../stats-cards/stats-cards.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [
    AsyncPipe,
    PageTitleComponent,
    RecentActivityTimelineComponent,
    RecentTicketsTableComponent,
    StatsCardsComponent
  ],
  templateUrl: './dashboard-page.component.html',
  styleUrl: './dashboard-page.component.scss'
})
export class DashboardPageComponent {
  private readonly mockLayoutDataService = inject(MockLayoutDataService);

  readonly dashboard$ = this.mockLayoutDataService.dashboard$;
}