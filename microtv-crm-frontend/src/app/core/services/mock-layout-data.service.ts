import { inject, Injectable } from '@angular/core';
import { combineLatest, forkJoin, map, merge, of, shareReplay, startWith, switchMap, catchError } from 'rxjs';

import { DashboardData } from '../models/dashboard.model';
import { BrandInfo, CurrentUser, LayoutMockData, TopbarInfo } from '../models/layout.model';
import { NavigationSection } from '../models/navigation.model';
import { MockAccessControlService } from './mock-access-control.service';
import { MockUserContextService } from './mock-user-context.service';
import { TaskManagementService } from './task-management.service';
import { TicketManagementService } from './ticket-management.service';
import layoutData from '../../../mocks/layout-data.json';

@Injectable({ providedIn: 'root' })
export class MockLayoutDataService {
  private readonly mockAccessControlService = inject(MockAccessControlService);
  private readonly mockUserContextService = inject(MockUserContextService);
  private readonly ticketManagementService = inject(TicketManagementService);
  private readonly taskManagementService = inject(TaskManagementService);
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
  private readonly countsRefresh$ = merge(
    this.ticketManagementService.badgeRefresh$,
    this.taskManagementService.badgeRefresh$
  ).pipe(startWith(void 0));

  private readonly assignedCounts$ = this.countsRefresh$.pipe(
    switchMap(() =>
      forkJoin({
        tickets: this.ticketManagementService
          .listAssignedTickets()
          .pipe(
            map((tickets) => tickets.filter((ticket) => ticket.status !== 'CLOSED').length),
            catchError(() => of(0))
          ),
        tasks: this.taskManagementService
          .listAssignedTasks()
          .pipe(
            map((tasks) => tasks.filter((task) => task.status !== 'COMPLETED').length),
            catchError(() => of(0))
          )
      })
    ),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  readonly navigation$ = this.selectFromSource((data) => data.navigation).pipe(
    switchMap((navigation) => this.mockAccessControlService.filterNavigationForActiveUser(navigation)),
    switchMap((navigation) => this.assignedCounts$.pipe(map((counts) => this.applyDynamicBadges(navigation, counts)))),
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

  private applyDynamicBadges(
    sections: NavigationSection[],
    counts: { tickets: number; tasks: number }
  ): NavigationSection[] {
    return sections.map((section) => ({
      ...section,
      items: section.items.map((item) => {
        if (item.id === 'tickets') {
          return { ...item, badge: counts.tickets > 0 ? counts.tickets : undefined };
        }

        if (item.id === 'tasks') {
          return { ...item, badge: counts.tasks > 0 ? counts.tasks : undefined };
        }

        return item;
      })
    }));
  }

  private selectFromSource<T>(project: (data: LayoutMockData) => T) {
    return this.layoutDataSource$.pipe(map(project));
  }
}

export type { BrandInfo, CurrentUser, DashboardData, NavigationSection, TopbarInfo };