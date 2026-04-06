import { Component, input } from '@angular/core';

@Component({
  selector: 'app-user-avatar',
  standalone: true,
  templateUrl: './user-avatar.component.html',
  styleUrl: './user-avatar.component.scss'
})
export class UserAvatarComponent {
  readonly initials = input.required<string>();
  readonly size = input(40);
}