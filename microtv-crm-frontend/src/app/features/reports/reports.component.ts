import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { PageTitleComponent } from '../../shared/ui/page-title/page-title.component';
import { REPORT_TABS } from './report.types';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet, PageTitleComponent],
  templateUrl: './reports.component.html',
  styleUrl: './reports.component.scss'
})
export class ReportsComponent {
  readonly tabs = REPORT_TABS;
}
