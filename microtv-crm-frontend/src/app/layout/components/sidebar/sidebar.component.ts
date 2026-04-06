import { Component, input, output } from '@angular/core';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';

import { CurrentUser, BrandInfo } from '../../../core/models/layout.model';
import { NavigationSection } from '../../../core/models/navigation.model';
import { UserAvatarComponent } from '../../../shared/ui/user-avatar/user-avatar.component';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [MatDividerModule, MatIconModule, RouterModule, UserAvatarComponent],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {
  readonly brand = input.required<BrandInfo>();
  readonly navigation = input.required<NavigationSection[]>();
  readonly currentUser = input.required<CurrentUser>();
  readonly itemSelected = output<string>();

  isExactRoute(route?: string): boolean {
    return route === '/';
  }
}