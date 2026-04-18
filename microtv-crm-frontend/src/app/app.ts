import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthSessionService } from './core/services/auth-session.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  private readonly authSessionService = inject(AuthSessionService);

  constructor() {
    this.authSessionService.bootstrap();
  }
}
