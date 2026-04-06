import { Injectable } from '@angular/core';
import { map, of, shareReplay } from 'rxjs';

import { DashboardData } from '../models/dashboard.model';
import { BrandInfo, CurrentUser, LayoutMockData, TopbarInfo } from '../models/layout.model';
import { NavigationSection } from '../models/navigation.model';
import layoutData from '../../../mocks/layout-data.json';

@Injectable({ providedIn: 'root' })
export class MockLayoutDataService {
  readonly layoutData$ = of(layoutData as LayoutMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );

  readonly brand$ = this.select((data) => data.brand);
  readonly currentUser$ = this.select((data) => data.currentUser);
  readonly topbar$ = this.select((data) => data.topbar);
  readonly navigation$ = this.select((data) => data.navigation);
  readonly dashboard$ = this.select((data) => data.dashboard);
  readonly stats$ = this.select((data) => data.dashboard.stats);
  readonly recentTickets$ = this.select((data) => data.dashboard.recentTickets);
  readonly recentActivity$ = this.select((data) => data.dashboard.recentActivity);

  private select<T>(project: (data: LayoutMockData) => T) {
    return this.layoutData$.pipe(map(project));
  }
}

export type { BrandInfo, CurrentUser, DashboardData, NavigationSection, TopbarInfo };