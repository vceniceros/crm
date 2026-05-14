import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  forwardRef,
  inject,
  input,
  output,
  signal,
  viewChild
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR } from '@angular/forms';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { catchError, debounceTime, distinctUntilChanged, of, Subject, switchMap, tap } from 'rxjs';

import { CrmUserOption } from '../../../core/models/task-management.model';
import { CrmUsersService } from '../../../core/services/crm-users.service';

type SelectedMention = {
  userId: string;
  text: string;
};

@Component({
  selector: 'app-comment-mention-textarea',
  standalone: true,
  imports: [CommonModule, FormsModule, MatAutocompleteModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule],
  templateUrl: './comment-mention-textarea.component.html',
  styleUrl: './comment-mention-textarea.component.scss',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CommentMentionTextareaComponent),
      multi: true
    }
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CommentMentionTextareaComponent implements ControlValueAccessor {
  private readonly crmUsersService = inject(CrmUsersService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly searchTerms = new Subject<string>();
  private selectedMentions: SelectedMention[] = [];
  private mentionStart = -1;
  private mentionEnd = -1;

  readonly textarea = viewChild<ElementRef<HTMLTextAreaElement>>('textarea');
  readonly label = input('Comentario');
  readonly placeholder = input('');
  readonly rows = input(4);
  readonly disabled = input(false);
  readonly subscriptSizing = input<'fixed' | 'dynamic'>('dynamic');
  readonly mentionedUserIdsChange = output<string[]>();

  readonly value = signal('');
  readonly suggestions = signal<CrmUserOption[]>([]);
  readonly isSearching = signal(false);
  readonly isControlDisabled = signal(false);

  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  constructor() {
    this.searchTerms
      .pipe(
        debounceTime(200),
        distinctUntilChanged(),
        tap(() => this.isSearching.set(true)),
        switchMap((term) =>
          this.crmUsersService.searchMentionableUsers(term).pipe(
            catchError(() => of([]))
          )
        ),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((users) => {
        this.suggestions.set(users);
        this.isSearching.set(false);
      });
  }

  writeValue(value: string | null): void {
    this.value.set(value ?? '');
    this.syncSelectedMentions();
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.isControlDisabled.set(isDisabled);
  }

  handleInput(nextValue: string): void {
    this.value.set(nextValue);
    this.onChange(nextValue);
    this.syncSelectedMentions();
    this.updateMentionSearch();
  }

  handleBlur(): void {
    this.onTouched();
  }

  selectMention(event: MatAutocompleteSelectedEvent): void {
    const user = event.option.value as CrmUserOption;
    const textarea = this.textarea()?.nativeElement;
    if (!textarea || this.mentionStart < 0 || this.mentionEnd < this.mentionStart) {
      return;
    }

    const currentValue = this.value();
    const mentionText = `@${this.userLabel(user)}`;
    const replacement = `${mentionText} `;
    const nextValue = `${currentValue.slice(0, this.mentionStart)}${replacement}${currentValue.slice(this.mentionEnd)}`;
    const nextCursor = this.mentionStart + replacement.length;

    this.selectedMentions = [
      ...this.selectedMentions.filter((mention) => mention.userId !== user.crm_user_id),
      { userId: user.crm_user_id, text: mentionText }
    ];
    this.value.set(nextValue);
    this.onChange(nextValue);
    this.syncSelectedMentions();
    this.suggestions.set([]);
    this.mentionStart = -1;
    this.mentionEnd = -1;

    queueMicrotask(() => {
      textarea.focus();
      textarea.setSelectionRange(nextCursor, nextCursor);
    });
  }

  userLabel(user: CrmUserOption): string {
    return user.display_name?.trim() || user.email?.trim() || user.crm_user_id;
  }

  isDisabled(): boolean {
    return this.disabled() || this.isControlDisabled();
  }

  updateMentionSearch(): void {
    const textarea = this.textarea()?.nativeElement;
    if (!textarea) {
      this.suggestions.set([]);
      return;
    }

    const cursor = textarea.selectionStart ?? this.value().length;
    const beforeCursor = this.value().slice(0, cursor);
    const match = /(^|\s)@([^\s@]{1,64})$/.exec(beforeCursor);
    if (!match) {
      this.suggestions.set([]);
      this.mentionStart = -1;
      this.mentionEnd = -1;
      return;
    }

    this.mentionStart = cursor - match[2].length - 1;
    this.mentionEnd = cursor;
    this.searchTerms.next(match[2]);
  }

  private syncSelectedMentions(): void {
    const currentValue = this.value();
    this.selectedMentions = this.selectedMentions.filter((mention) => currentValue.includes(mention.text));
    this.mentionedUserIdsChange.emit([...new Set(this.selectedMentions.map((mention) => mention.userId))]);
  }
}
