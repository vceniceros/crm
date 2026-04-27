import { effect, Component, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { debounceTime, distinctUntilChanged } from 'rxjs';

@Component({
  selector: 'app-task-comment-section',
  standalone: true,
  imports: [MatCardModule, MatFormFieldModule, MatInputModule, ReactiveFormsModule],
  templateUrl: './task-comment-section.component.html',
  styleUrl: './task-comment-section.component.scss'
})
export class TaskCommentSectionComponent {
  readonly comment = input('');
  readonly disabled = input(false);
  readonly commentChange = output<string>();
  readonly commentControl = new FormControl('', { nonNullable: true });

  constructor() {
    effect(() => {
      const nextComment = this.comment();

      if (this.commentControl.value !== nextComment) {
        this.commentControl.setValue(nextComment, { emitEvent: false });
      }

      if (this.disabled()) {
        this.commentControl.disable({ emitEvent: false });
        return;
      }

      this.commentControl.enable({ emitEvent: false });
    });

    this.commentControl.valueChanges
      .pipe(debounceTime(250), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe((value) => this.commentChange.emit(value));
  }
}