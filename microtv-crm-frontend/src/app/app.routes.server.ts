import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  {
    path: 'assets/:assetId',
    renderMode: RenderMode.Server
  },
  {
    path: 'knowledge-base/:articleId/edit',
    renderMode: RenderMode.Server
  },
  {
    path: 'knowledge-base/:articleId',
    renderMode: RenderMode.Server
  },
  {
    path: 'tickets/:ticketId',
    renderMode: RenderMode.Server
  },
  {
    path: 'tasks/templates/:templateId/edit',
    renderMode: RenderMode.Server
  },
  {
    path: 'tasks/templates/:templateId',
    renderMode: RenderMode.Server
  },
  {
    path: 'tasks/:taskId',
    renderMode: RenderMode.Server
  },
  {
    path: 'reports/:category',
    renderMode: RenderMode.Server
  },
  {
    path: 'reports/:category/:reportId',
    renderMode: RenderMode.Server
  },
  {
    path: 'satisfaction/:token',
    renderMode: RenderMode.Server
  },
  {
    path: 'survey/:token',
    renderMode: RenderMode.Server
  },
  {
    path: 'pre-form/:token',
    renderMode: RenderMode.Server
  },
  {
    path: '**',
    renderMode: RenderMode.Prerender
  }
];
