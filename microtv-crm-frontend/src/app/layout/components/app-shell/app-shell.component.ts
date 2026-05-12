import { AsyncPipe } from '@angular/common';
import { Component, DestroyRef, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { distinctUntilChanged, filter, map, pairwise, startWith } from 'rxjs';
import { MatSidenav, MatSidenavContent, MatSidenavModule } from '@angular/material/sidenav';

import { AuthSessionService } from '../../../core/services/auth-session.service';
import { MockLayoutDataService } from '../../../core/services/mock-layout-data.service';
import { PushNotificationService } from '../../../core/services/push-notification.service';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { TopbarComponent } from '../topbar/topbar.component';

@Component({
  selector: 'app-app-shell',
  standalone: true,
  imports: [AsyncPipe, MatSidenavModule, RouterOutlet, SidebarComponent, TopbarComponent],
  templateUrl: './app-shell.component.html',
  styleUrl: './app-shell.component.scss'
})
export class AppShellComponent {
  private readonly authSessionService = inject(AuthSessionService);
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly destroyRef = inject(DestroyRef);
  private readonly mockLayoutDataService = inject(MockLayoutDataService);
  private readonly pushNotificationService = inject(PushNotificationService);
  private readonly router = inject(Router);

  @ViewChild(MatSidenavContent) private sidenavContent?: MatSidenavContent;

  readonly layoutData$ = this.mockLayoutDataService.layoutData$;
  readonly isCompact = toSignal(
    this.breakpointObserver.observe([Breakpoints.Handset, Breakpoints.TabletPortrait]).pipe(
      map((state) => state.matches)
    ),
    { initialValue: false }
  );
  readonly routeTitle = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      startWith(null),
      map(() => this.getCurrentRouteTitle())
    ),
    { initialValue: this.getCurrentRouteTitle() }
  );

  constructor() {
    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(() => {
        this.sidenavContent?.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      });

    this.authSessionService.isAuthenticated$
      .pipe(
        startWith(false),
        distinctUntilChanged(),
        pairwise(),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(([previous, current]) => {
        if (!previous && current) {
          void this.pushNotificationService.requestAndSubscribe();
          return;
        }

        if (previous && !current) {
          void this.pushNotificationService.unsubscribe();
        }
      });
  }

  closeIfCompact(drawer: MatSidenav): void {
    if (this.isCompact()) {
      drawer.close();
    }
  }

  private getCurrentRouteTitle(): string {
    let snapshot = this.router.routerState.snapshot.root;

    while (snapshot.firstChild) {
      snapshot = snapshot.firstChild;
    }

    return snapshot.data?.['title'] ?? 'Dashboard';
  }
}