import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { combineLatest, map } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';

import { MockUserContextService } from '../../../core/services/mock-user-context.service';
import { UserAvatarComponent } from '../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-sidebar-user-switcher',
  standalone: true,
  imports: [AsyncPipe, MatIconModule, MatMenuModule, UserAvatarComponent],
  templateUrl: './sidebar-user-switcher.component.html',
  styleUrl: './sidebar-user-switcher.component.scss'
})
export class SidebarUserSwitcherComponent {
  private readonly mockUserContextService = inject(MockUserContextService);

  readonly viewModel$ = combineLatest({
    activeUser: this.mockUserContextService.activeUser(),
    users: this.mockUserContextService.getUsers()
  }).pipe(
    map(({ activeUser, users }) => ({
      activeUser,
      users: users.map((user) => ({
        ...user,
        isActive: user.id === activeUser.id
      }))
    }))
  );

  setActiveUser(userId: number | string): void {
    this.mockUserContextService.setActiveUser(userId);
  }
}