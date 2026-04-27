import { Component, input, output } from '@angular/core';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';

import { BrandInfo } from '../../../core/models/layout.model';
import { NavigationSection } from '../../../core/models/navigation.model';
import { SidebarUserSwitcherComponent } from '../sidebar-user-switcher/sidebar-user-switcher.component';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [MatDividerModule, MatIconModule, RouterModule, SidebarUserSwitcherComponent],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {
  readonly brand = input.required<BrandInfo>();
  readonly navigation = input.required<NavigationSection[]>();
  readonly itemSelected = output<string>();

  isExactRoute(route?: string): boolean {
    return route === '/';
  }
}