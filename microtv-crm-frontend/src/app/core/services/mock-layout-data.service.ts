import { inject, Injectable } from '@angular/core';
import { combineLatest, map, of, shareReplay, switchMap } from 'rxjs';

import { DashboardData } from '../models/dashboard.model';
import { BrandInfo, CurrentUser, LayoutMockData, TopbarInfo } from '../models/layout.model';
import { NavigationSection } from '../models/navigation.model';
import { MockAccessControlService } from './mock-access-control.service';
import { MockUserContextService } from './mock-user-context.service';
import layoutData from '../../../mocks/layout-data.json';

@Injectable({ providedIn: 'root' })
export class MockLayoutDataService {
  private readonly mockAccessControlService = inject(MockAccessControlService);
  private readonly mockUserContextService = inject(MockUserContextService);
  private readonly layoutDataSource$ = of(layoutData as LayoutMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly currentUser$ = this.mockUserContextService.activeUser().pipe(
    map((user): CurrentUser => ({
      initials: user.initials,
      name: user.name,
      role: user.roleLabel
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly navigation$ = this.selectFromSource((data) => data.navigation).pipe(
    switchMap((navigation) => this.mockAccessControlService.filterNavigationForActiveUser(navigation)),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly layoutData$ = combineLatest({
    data: this.layoutDataSource$,
    currentUser: this.currentUser$,
    navigation: this.navigation$
  }).pipe(
    map(({ data, currentUser, navigation }) => ({
      ...data,
      currentUser,
      navigation
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  readonly brand$ = this.selectFromSource((data) => data.brand);
  readonly topbar$ = this.selectFromSource((data) => data.topbar);
  readonly dashboard$ = this.selectFromSource((data) => data.dashboard);
  readonly stats$ = this.selectFromSource((data) => data.dashboard.stats);
  readonly recentTickets$ = this.selectFromSource((data) => data.dashboard.recentTickets);
  readonly recentActivity$ = this.selectFromSource((data) => data.dashboard.recentActivity);

  private selectFromSource<T>(project: (data: LayoutMockData) => T) {
    return this.layoutDataSource$.pipe(map(project));
  }
}

export type { BrandInfo, CurrentUser, DashboardData, NavigationSection, TopbarInfo };