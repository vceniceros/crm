import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { AsyncPipe } from '@angular/common';

import { REPORT_CARDS, ReportCardDefinition, ReportCategoryKey } from './report.types';

@Component({
  selector: 'app-report-list',
  standalone: true,
  imports: [AsyncPipe, RouterLink],
  templateUrl: './report-list.component.html',
  styleUrl: './report-list.component.scss'
})
export class ReportListComponent {
  private readonly route = inject(ActivatedRoute);

  readonly vm$ = this.route.paramMap.pipe(
    map((params) => {
      const category = (params.get('category') as ReportCategoryKey | null) ?? 'tickets';
      const cards = REPORT_CARDS.filter((card) => card.category === category);
      return {
        category,
        cards
      };
    })
  );

  trackById(_: number, card: ReportCardDefinition): string {
    return card.id;
  }
}
