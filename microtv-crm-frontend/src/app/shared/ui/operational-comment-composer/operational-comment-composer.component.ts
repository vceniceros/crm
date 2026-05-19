import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, forwardRef, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ControlValueAccessor, FormControl, NG_VALUE_ACCESSOR, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule, MatMenuPanel } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import { CommentMentionTextareaComponent } from '../comment-mention-textarea/comment-mention-textarea.component';

@Component({
  selector: 'app-operational-comment-composer',
  standalone: true,
  imports: [CommonModule, CommentMentionTextareaComponent, MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule, ReactiveFormsModule],
  templateUrl: './operational-comment-composer.component.html',
  styleUrl: './operational-comment-composer.component.scss',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => OperationalCommentComposerComponent),
      multi: true
    }
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OperationalCommentComposerComponent implements ControlValueAccessor {
  readonly control = new FormControl('', { nonNullable: true });

  readonly label = input('Comentario');
  readonly placeholder = input('');
  readonly rows = input(4);
  readonly disabled = input(false);
  readonly loading = input(false);
  readonly attachmentCount = input(0);
  readonly hasLocation = input(false);
  readonly locationLabel = input('Sin ubicacion');
  readonly canAttach = input(true);
  readonly canPickLocation = input(true);
  readonly canRequestInventory = input(true);
  readonly showInventoryButton = input(true);
  readonly primaryActionLabel = input('Publicar');
  readonly primaryActionIcon = input('send');
  readonly primaryActionDisabled = input(false);
  readonly primaryActionMenu = input<MatMenuPanel | null>(null);

  readonly attachmentsClick = output<void>();
  readonly locationClick = output<void>();
  readonly inventoryClick = output<void>();
  readonly primaryActionClick = output<void>();
  readonly mentionedUserIdsChange = output<string[]>();

  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  constructor() {
    this.control.valueChanges.pipe(takeUntilDestroyed()).subscribe((value) => {
      this.onChange(value);
    });
  }

  writeValue(value: string | null): void {
    this.control.setValue(value ?? '', { emitEvent: false });
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    if (isDisabled) {
      this.control.disable({ emitEvent: false });
      return;
    }

    this.control.enable({ emitEvent: false });
  }

  isDisabled(): boolean {
    return this.disabled() || this.loading() || this.control.disabled;
  }

  markTouched(): void {
    this.onTouched();
  }
}
