import { Routes } from '@angular/router';
import { provideMarkdown } from 'ngx-markdown';

export const KNOWLEDGE_BASE_ROUTES: Routes = [
  {
    path: '',
    providers: [provideMarkdown()],
    children: [
      {
        path: '',
        loadComponent: () => import('./components/knowledge-base-page/knowledge-base-page.component').then((module) => module.KnowledgeBasePageComponent),
        data: { title: 'Base de conocimientos' }
      },
      {
        path: 'new',
        loadComponent: () => import('./components/knowledge-article-editor/knowledge-article-editor.component').then((module) => module.KnowledgeArticleEditorComponent),
        data: { title: 'Nuevo articulo' }
      },
      {
        path: ':articleId/edit',
        loadComponent: () => import('./components/knowledge-article-editor/knowledge-article-editor.component').then((module) => module.KnowledgeArticleEditorComponent),
        data: { title: 'Editar articulo' }
      },
      {
        path: ':articleId',
        loadComponent: () => import('./components/knowledge-article-detail/knowledge-article-detail.component').then((module) => module.KnowledgeArticleDetailComponent),
        data: { title: 'Articulo' }
      }
    ]
  }
];
