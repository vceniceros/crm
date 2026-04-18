import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
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
    path: '**',
    renderMode: RenderMode.Prerender
  }
];
