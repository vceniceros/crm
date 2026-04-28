import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AppUpdateService } from './core/services/app-update.service';
import { AuthSessionService } from './core/services/auth-session.service';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  private readonly authSessionService = inject(AuthSessionService);
  private readonly appUpdateService = inject(AppUpdateService);
  private readonly themeService = inject(ThemeService);

  constructor() {
    this.themeService.initialize();
    this.authSessionService.bootstrap();
    this.appUpdateService.start();
  }
}
