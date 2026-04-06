import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { filter, map, startWith } from 'rxjs';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';

import { MockLayoutDataService } from '../../../core/services/mock-layout-data.service';
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
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly mockLayoutDataService = inject(MockLayoutDataService);
  private readonly router = inject(Router);

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