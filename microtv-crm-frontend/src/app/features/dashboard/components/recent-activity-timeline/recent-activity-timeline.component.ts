import { Component, inject, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { Router } from '@angular/router';

import { RecentActivityBlock } from '../../../../core/models/dashboard.model';

@Component({
  selector: 'app-recent-activity-timeline',
  standalone: true,
  imports: [MatCardModule],
  templateUrl: './recent-activity-timeline.component.html',
  styleUrl: './recent-activity-timeline.component.scss'
})
export class RecentActivityTimelineComponent {
  private readonly router = inject(Router);

  readonly block = input.required<RecentActivityBlock>();

  navigateTo(targetRoute?: string): void {
    if (!targetRoute) {
      return;
    }
    void this.router.navigateByUrl(targetRoute);
  }
}