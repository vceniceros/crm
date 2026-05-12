import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

import { ActivityLogEntry, ActivityLogFilters } from '../../../../core/models/settings-management.model';
import { SettingsManagementService } from '../../../../core/services/settings-management.service';

@Component({
  selector: 'app-activity-log-tab',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule],
  templateUrl: './activity-log-tab.component.html',
  styleUrl: './activity-log-tab.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ActivityLogTabComponent {
  private readonly settingsManagementService = inject(SettingsManagementService);
  private readonly destroyRef = inject(DestroyRef);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly rows = signal<ActivityLogEntry[]>([]);
  readonly page = signal(1);
  readonly perPage = signal(50);
  readonly total = signal(0);

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    const filters: ActivityLogFilters = { page: this.page(), perPage: this.perPage() };
    this.settingsManagementService
      .listActivityLog(filters)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.rows.set(response.items);
          this.total.set(response.total);
          this.loading.set(false);
        },
        error: (error: Error) => {
          this.error.set(error.message);
          this.loading.set(false);
        }
      });
  }

  nextPage(): void {
    this.page.update((value) => value + 1);
    this.load();
  }

  previousPage(): void {
    this.page.update((value) => Math.max(1, value - 1));
    this.load();
  }
}
