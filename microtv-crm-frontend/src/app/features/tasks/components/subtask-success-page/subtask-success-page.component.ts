import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { interval, timer } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-subtask-success-page',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatCardModule, MatIconModule],
  templateUrl: './subtask-success-page.component.html',
  styleUrl: './subtask-success-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SubtaskSuccessPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly redirectInSeconds = signal(4);
  readonly subtaskTitle = signal<string | null>(this.activatedRoute.snapshot.queryParamMap.get('subtask'));
  readonly title = computed(() => {
    const subtask = this.subtaskTitle()?.trim();
    if (!subtask) {
      return 'Subtarea completada con exito';
    }
    return `Subtarea completada: ${subtask}`;
  });

  constructor() {
    const totalSeconds = this.redirectInSeconds();

    interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((tick) => {
        const remaining = totalSeconds - (tick + 1);
        this.redirectInSeconds.set(Math.max(0, remaining));
      });

    timer(totalSeconds * 1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.goToTasks());
  }

  goToTasks(): void {
    this.router.navigate(['/tasks']);
  }
}
