import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, Input, Output, ViewChild, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MarkdownModule } from 'ngx-markdown';

@Component({
  selector: 'app-knowledge-markdown-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, MarkdownModule, MatButtonModule, MatIconModule, MatTabsModule],
  templateUrl: './knowledge-markdown-editor.component.html',
  styleUrl: './knowledge-markdown-editor.component.scss'
})
export class KnowledgeMarkdownEditorComponent {
  @Input() value = '';
  @Input() uploadDisabled = false;
  @Output() valueChange = new EventEmitter<string>();
  @Output() imageSelected = new EventEmitter<File>();
  @Output() videoSelected = new EventEmitter<File>();
  @ViewChild('textarea') textarea?: ElementRef<HTMLTextAreaElement>;
  @ViewChild('imageInput') imageInput?: ElementRef<HTMLInputElement>;
  @ViewChild('videoInput') videoInput?: ElementRef<HTMLInputElement>;

  mode: 'paste' | 'write' = 'paste';

  setValue(value: string): void {
    this.value = value;
    this.valueChange.emit(value);
  }

  insert(prefix: string, suffix = '', placeholder = 'texto'): void {
    const target = this.textarea?.nativeElement;
    if (!target) {
      this.setValue(`${this.value}${prefix}${placeholder}${suffix}`);
      return;
    }
    const start = target.selectionStart;
    const end = target.selectionEnd;
    const selected = this.value.slice(start, end) || placeholder;
    const next = `${this.value.slice(0, start)}${prefix}${selected}${suffix}${this.value.slice(end)}`;
    this.setValue(next);
    queueMicrotask(() => {
      target.focus();
      target.setSelectionRange(start + prefix.length, start + prefix.length + selected.length);
    });
  }

  triggerImageInput(): void {
    this.imageInput?.nativeElement.click();
  }

  triggerVideoInput(): void {
    this.videoInput?.nativeElement.click();
  }

  selectImage(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) {
      this.imageSelected.emit(file);
    }
    (event.target as HTMLInputElement).value = '';
  }

  selectVideo(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) {
      this.videoSelected.emit(file);
    }
    (event.target as HTMLInputElement).value = '';
  }

  pasteImage(event: ClipboardEvent): void {
    if (this.uploadDisabled) {
      return;
    }
    const imageItem = Array.from(event.clipboardData?.items ?? []).find((item) => item.type.startsWith('image/'));
    const file = imageItem?.getAsFile();
    if (!file) {
      return;
    }
    event.preventDefault();
    const extension = file.type.split('/')[1] || 'png';
    const namedFile = new File([file], `imagen-pegada-${Date.now()}.${extension}`, { type: file.type });
    this.imageSelected.emit(namedFile);
  }

  appendImageMarkdown(alt: string, url: string): void {
    this.setValue(`${this.value}${this.value.endsWith('\n') || !this.value ? '' : '\n'}![${alt}](${url})\n`);
  }
}
