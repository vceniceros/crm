import { Component, inject, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { Router } from '@angular/router';

import { DashboardStat } from '../../../../core/models/dashboard.model';

@Component({
  selector: 'app-stats-cards',
  standalone: true,
  imports: [MatCardModule],
  templateUrl: './stats-cards.component.html',
  styleUrl: './stats-cards.component.scss'
})
export class StatsCardsComponent {
  private readonly router = inject(Router);
  readonly stats = input.required<DashboardStat[]>();

  onCardClick(stat: DashboardStat): void {
    if (stat.route) {
      this.router.navigateByUrl(stat.route);
    }
  }
}