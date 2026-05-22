import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MarkdownModule } from 'ngx-markdown';

import { KnowledgeArticleDetail, KnowledgeAttachment } from '../../../../core/models/knowledge.model';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { KnowledgeBaseService } from '../../../../core/services/knowledge-base.service';

@Component({
  selector: 'app-knowledge-article-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, MarkdownModule, MatButtonModule, MatIconModule],
  templateUrl: './knowledge-article-detail.component.html',
  styleUrl: './knowledge-article-detail.component.scss'
})
export class KnowledgeArticleDetailComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly service = inject(KnowledgeBaseService);
  private readonly authSession = inject(AuthSessionService);
  private readonly destroyRef = inject(DestroyRef);

  readonly article = signal<KnowledgeArticleDetail | null>(null);
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly exportingPdf = signal(false);

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const articleId = params.get('articleId');
      if (articleId) {
        this.load(articleId);
      }
    });
  }

  get isAdmin(): boolean {
    return this.authSession.sessionSnapshot()?.user.role_keys?.includes('admin') ?? false;
  }

  get videos(): KnowledgeAttachment[] {
    return (this.article()?.attachments ?? []).filter((attachment) => attachment.file_type === 'video');
  }

  deleteArticle(): void {
    const article = this.article();
    if (!article || !window.confirm('Seguro que queres eliminar este articulo?')) {
      return;
    }
    this.service.deleteArticle(article.article_id).subscribe(() => this.router.navigateByUrl('/knowledge-base'));
  }

  async exportPdf(): Promise<void> {
    const article = this.article();
    if (!article || this.exportingPdf() || typeof window === 'undefined') {
      return;
    }
    this.exportingPdf.set(true);
    try {
      const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import('html2canvas'), import('jspdf')]);
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      const target = document.getElementById('knowledge-article-export');
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const canvas = await html2canvas(target, { backgroundColor: '#ffffff', scale: 2, useCORS: true });
      const pdf = new jsPDF({ unit: 'pt', format: 'a4' });
      this.appendCanvasToPdf(pdf, canvas);
      pdf.save(`base-conocimientos-${article.slug}.pdf`);
    } catch (error) {
      this.errorMessage.set(error instanceof Error ? error.message : 'No se pudo exportar el PDF.');
    } finally {
      this.exportingPdf.set(false);
    }
  }

  private load(articleId: string): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    this.service.getArticle(articleId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (article) => {
        this.article.set(article);
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.errorMessage.set(error instanceof Error ? error.message : 'No se pudo cargar el articulo.');
        this.loading.set(false);
      }
    });
  }

  private appendCanvasToPdf(pdf: import('jspdf').jsPDF, canvas: HTMLCanvasElement): void {
    const margin = 24;
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const usableWidth = pageWidth - margin * 2;
    const usableHeight = pageHeight - margin * 2;
    const scale = usableWidth / canvas.width;
    const sliceHeight = Math.max(1, Math.floor(usableHeight / scale));

    let offsetY = 0;
    let firstPage = true;
    while (offsetY < canvas.height) {
      if (!firstPage) {
        pdf.addPage();
      }

      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = Math.min(sliceHeight, canvas.height - offsetY);
      const context = pageCanvas.getContext('2d');
      if (context) {
        context.drawImage(canvas, 0, offsetY, canvas.width, pageCanvas.height, 0, 0, canvas.width, pageCanvas.height);
      }

      pdf.addImage(
        pageCanvas.toDataURL('image/png'),
        'PNG',
        margin,
        margin,
        usableWidth,
        pageCanvas.height * scale,
        undefined,
        'FAST'
      );

      offsetY += pageCanvas.height;
      firstPage = false;
    }
  }
}
