import { CommonModule } from '@angular/common';
import { Component, DestroyRef, ViewChild, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { KnowledgeCategory } from '../../../../core/models/knowledge.model';
import { KnowledgeBaseService } from '../../../../core/services/knowledge-base.service';
import { KnowledgeMarkdownEditorComponent } from '../knowledge-markdown-editor/knowledge-markdown-editor.component';

@Component({
  selector: 'app-knowledge-article-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    KnowledgeMarkdownEditorComponent,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule
  ],
  templateUrl: './knowledge-article-editor.component.html',
  styleUrl: './knowledge-article-editor.component.scss'
})
export class KnowledgeArticleEditorComponent {
  @ViewChild(KnowledgeMarkdownEditorComponent) markdownEditor?: KnowledgeMarkdownEditorComponent;

  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly service = inject(KnowledgeBaseService);
  private readonly destroyRef = inject(DestroyRef);

  readonly categories = signal<KnowledgeCategory[]>([]);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly uploading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly articleId = signal<string | null>(null);

  title = '';
  categoryId: string | null = null;
  contentMd = '';

  constructor() {
    this.service.listCategories().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((categories) => this.categories.set(categories));
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const articleId = params.get('articleId');
      if (articleId) {
        this.load(articleId);
      } else {
        this.createAutoDraft();
      }
    });
  }

  save(): void {
    const articleId = this.articleId();
    if (!articleId) {
      return;
    }
    if (this.title.trim().length < 3) {
      this.errorMessage.set('El titulo debe tener al menos 3 caracteres.');
      return;
    }
    this.saving.set(true);
    this.errorMessage.set(null);
    this.service
      .updateArticle(articleId, {
        title: this.title.trim(),
        category_id: this.categoryId,
        content_md: this.contentMd,
        status: 'published'
      })
      .subscribe({
        next: (article) => this.router.navigate(['/knowledge-base', article.article_id]),
        error: (error: unknown) => {
          this.errorMessage.set(error instanceof Error ? error.message : 'No se pudo guardar el articulo.');
          this.saving.set(false);
        }
      });
  }

  uploadImage(file: File): void {
    this.upload(file, true);
  }

  uploadVideo(file: File): void {
    this.upload(file, false);
  }

  private upload(file: File, insertInline: boolean): void {
    const articleId = this.articleId();
    if (!articleId) {
      return;
    }
    this.uploading.set(true);
    this.service.uploadAttachment(articleId, file).subscribe({
      next: (attachment) => {
        if (insertInline) {
          this.markdownEditor?.appendImageMarkdown(attachment.original_filename, attachment.file_url);
          this.contentMd = this.markdownEditor?.value ?? this.contentMd;
        }
        this.uploading.set(false);
      },
      error: (error: unknown) => {
        this.errorMessage.set(error instanceof Error ? error.message : 'No se pudo subir el adjunto.');
        this.uploading.set(false);
      }
    });
  }

  private load(articleId: string): void {
    this.loading.set(true);
    this.articleId.set(articleId);
    this.service.getArticle(articleId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (article) => {
        this.title = article.title;
        this.categoryId = article.category?.category_id ?? null;
        this.contentMd = article.content_md;
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.errorMessage.set(error instanceof Error ? error.message : 'No se pudo cargar el articulo.');
        this.loading.set(false);
      }
    });
  }

  private createAutoDraft(): void {
    this.loading.set(true);
    this.service
      .createArticle({ title: '', content_md: '', status: 'draft', is_auto_draft: true })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (article) => {
          this.articleId.set(article.article_id);
          this.loading.set(false);
        },
        error: (error: unknown) => {
          this.errorMessage.set(error instanceof Error ? error.message : 'No se pudo preparar el editor.');
          this.loading.set(false);
        }
      });
  }
}
