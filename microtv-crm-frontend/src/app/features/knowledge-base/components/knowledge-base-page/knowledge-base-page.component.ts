import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { KnowledgeArticleListItem, KnowledgeCategory } from '../../../../core/models/knowledge.model';
import { KnowledgeBaseService } from '../../../../core/services/knowledge-base.service';

@Component({
  selector: 'app-knowledge-base-page',
  standalone: true,
  imports: [CommonModule, RouterLink, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  templateUrl: './knowledge-base-page.component.html',
  styleUrl: './knowledge-base-page.component.scss'
})
export class KnowledgeBasePageComponent {
  private readonly service = inject(KnowledgeBaseService);
  private readonly destroyRef = inject(DestroyRef);

  readonly articles = signal<KnowledgeArticleListItem[]>([]);
  readonly categories = signal<KnowledgeCategory[]>([]);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly search = signal('');
  readonly categoryId = signal<string | null>(null);

  constructor() {
    this.service.listCategories().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((categories) => this.categories.set(categories));
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    this.service
      .listArticles({ search: this.search(), categoryId: this.categoryId(), status: 'published' })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (articles) => {
          this.articles.set(articles);
          this.loading.set(false);
        },
        error: (error: unknown) => {
          this.errorMessage.set(error instanceof Error ? error.message : 'No se pudo cargar la base de conocimientos.');
          this.loading.set(false);
        }
      });
  }

  setSearch(value: string): void {
    this.search.set(value);
    this.reload();
  }

  setCategory(value: string): void {
    this.categoryId.set(value || null);
    this.reload();
  }
}
