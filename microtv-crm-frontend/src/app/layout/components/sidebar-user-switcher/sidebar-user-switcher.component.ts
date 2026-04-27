import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { combineLatest, map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';

import { AuthSessionService } from '../../../core/services/auth-session.service';
import { MockUserContextService } from '../../../core/services/mock-user-context.service';
import { UserAvatarComponent } from '../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-sidebar-user-switcher',
  standalone: true,
  imports: [AsyncPipe, MatButtonModule, MatIconModule, MatMenuModule, UserAvatarComponent],
  templateUrl: './sidebar-user-switcher.component.html',
  styleUrl: './sidebar-user-switcher.component.scss'
})
export class SidebarUserSwitcherComponent {
  private readonly authSessionService = inject(AuthSessionService);
  private readonly mockUserContextService = inject(MockUserContextService);

  readonly viewModel$ = combineLatest({
    activeUser: this.mockUserContextService.activeUser(),
    session: this.authSessionService.session$
  }).pipe(
    map(({ activeUser, session }) => ({
      activeUser,
      email: session?.user.email ?? 'Sin email',
      roleKeys: session?.user.role_keys ?? []
    }))
  );

  logout(): void {
    this.authSessionService.logout();
  }
}