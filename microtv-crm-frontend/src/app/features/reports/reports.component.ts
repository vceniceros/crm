import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthSessionService } from '../../core/services/auth-session.service';
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
  private readonly authSessionService = inject(AuthSessionService);

  get tabs() {
    const roles = this.authSessionService.sessionSnapshot()?.user.role_keys ?? [];
    return REPORT_TABS.filter((tab) => !tab.roles || tab.roles.some((role) => roles.includes(role)));
  }
}
