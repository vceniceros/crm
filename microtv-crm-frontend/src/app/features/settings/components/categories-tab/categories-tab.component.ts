import { ChangeDetectionStrategy, Component, DestroyRef, Input, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { forkJoin } from 'rxjs';

import { SettingsCategory, SettingsCategoryWriteRequest, SettingsRole } from '../../../../core/models/settings-management.model';
import { SettingsManagementService } from '../../../../core/services/settings-management.service';
import { CategoryEditDialogComponent } from './category-edit-dialog.component';

@Component({
  selector: 'app-categories-tab',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatIconModule],
  templateUrl: './categories-tab.component.html',
  styleUrl: './categories-tab.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CategoriesTabComponent implements OnInit {
  private readonly settingsService = inject(SettingsManagementService);
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly categories = signal<SettingsCategory[]>([]);
  readonly roles = signal<SettingsRole[]>([]);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({
      categories: this.settingsService.listCategories('operational'),
      roles: this.settingsService.listRoles()
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ categories, roles }) => {
          this.categories.set(categories);
          this.roles.set(roles);
          this.loading.set(false);
        },
        error: (err: Error) => {
          this.error.set(err.message);
          this.loading.set(false);
        }
      });
  }

  openDialog(item?: SettingsCategory): void {
    this.dialog
      .open(CategoryEditDialogComponent, {
        width: '46rem',
        data: { item, roles: this.roles() }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: SettingsCategoryWriteRequest | undefined) => {
        if (!value) return;
        const request$ = item
          ? this.settingsService.updateCategory(item.category_id, value)
          : this.settingsService.createCategory(value);
        request$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => this.load(),
          error: (err: Error) => this.error.set(err.message)
        });
      });
  }

  formatSchedulePeriod(cat: SettingsCategory): string {
    if (!cat.allows_scheduling || !cat.schedule_period_type) return '—';
    const labels: Record<string, string> = {
      daily: 'Diario',
      weekly: 'Semanal',
      biweekly: 'Quincenal',
      monthly: 'Mensual',
      custom: `Cada ${cat.schedule_interval_weeks ?? '?'} sem.`
    };
    const period = labels[cat.schedule_period_type] ?? cat.schedule_period_type;
    const days = this.formatWeekdays(cat.schedule_weekdays_json);
    return days ? `${period} · ${days}` : period;
  }

  private formatWeekdays(days: readonly number[] | null | undefined): string {
    if (!days?.length) return '';
    const labels: Record<number, string> = {
      1: 'Lun',
      2: 'Mar',
      3: 'Mie',
      4: 'Jue',
      5: 'Vie',
      6: 'Sab',
      7: 'Dom'
    };
    return [...days].sort((left, right) => left - right).map((day) => labels[day]).filter(Boolean).join(', ');
  }
}
