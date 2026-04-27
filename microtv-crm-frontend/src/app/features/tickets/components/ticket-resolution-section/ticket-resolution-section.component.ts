import { effect, Component, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { debounceTime, distinctUntilChanged } from 'rxjs';

@Component({
  selector: 'app-ticket-resolution-section',
  standalone: true,
  imports: [MatCardModule, MatFormFieldModule, MatInputModule, ReactiveFormsModule],
  templateUrl: './ticket-resolution-section.component.html',
  styleUrl: './ticket-resolution-section.component.scss'
})
export class TicketResolutionSectionComponent {
  readonly comment = input('');
  readonly updatedAt = input('');
  readonly canEdit = input(false);
  readonly commentChange = output<string>();
  readonly commentControl = new FormControl('', { nonNullable: true });

  constructor() {
    effect(() => {
      const nextComment = this.comment();

      if (this.commentControl.value !== nextComment) {
        this.commentControl.setValue(nextComment, { emitEvent: false });
      }

      if (this.canEdit()) {
        this.commentControl.enable({ emitEvent: false });
        return;
      }

      this.commentControl.disable({ emitEvent: false });
    });

    this.commentControl.valueChanges
      .pipe(debounceTime(250), distinctUntilChanged(), takeUntilDestroyed())
      .subscribe((value) => this.commentChange.emit(value));
  }
}