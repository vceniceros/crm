import { Component, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';

import { RecentActivityBlock } from '../../../../core/models/dashboard.model';

@Component({
  selector: 'app-recent-activity-timeline',
  standalone: true,
  imports: [MatCardModule],
  templateUrl: './recent-activity-timeline.component.html',
  styleUrl: './recent-activity-timeline.component.scss'
})
export class RecentActivityTimelineComponent {
  readonly block = input.required<RecentActivityBlock>();
}