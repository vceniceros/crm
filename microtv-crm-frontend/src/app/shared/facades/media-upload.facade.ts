import { isPlatformBrowser } from '@angular/common';
import { inject, Injectable, PLATFORM_ID } from '@angular/core';
import { Observable } from 'rxjs';

import { TaskAttachment } from '../../core/models/task-attachment.model';
import { TaskManagementService } from '../../core/services/task-management.service';

import { ImageUploadStrategy } from './media-upload/image-upload.strategy';
import { MediaUploadContext, MediaUploadPort, MediaUploadStrategy } from './media-upload/media-upload.types';
import { VideoUploadStrategy } from './media-upload/video-upload.strategy';

@Injectable({ providedIn: 'root' })
export class MediaUploadFacade implements MediaUploadPort {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly strategies: MediaUploadStrategy[] = [
    new ImageUploadStrategy(),
    new VideoUploadStrategy()
  ];

  acceptAttribute(_context: MediaUploadContext['kind']): string {
    return this.strategies.map((strategy) => strategy.acceptPattern).join(',');
  }

  upload(files: readonly File[], context: MediaUploadContext): Observable<TaskAttachment[]> {
    if (!isPlatformBrowser(this.platformId)) {
      throw new Error('La subida de multimedia solo está disponible en el navegador.');
    }

    files.forEach((file) => this.resolveStrategy(context, file).validate(file));
    return this.taskManagementService.uploadTaskAttachments(context.taskId, files, context.subtaskId ?? null);
  }

  delete(attachmentId: string): Observable<void> {
    return this.taskManagementService.deleteTaskAttachment(attachmentId);
  }

  revokePreview(attachment: Pick<TaskAttachment, 'previewUrl'>): void {
    if (!isPlatformBrowser(this.platformId) || !attachment.previewUrl?.startsWith('blob:')) {
      return;
    }

    URL.revokeObjectURL(attachment.previewUrl);
  }

  private resolveStrategy(context: MediaUploadContext, file: File): MediaUploadStrategy {
    const strategy = this.getStrategiesFor(context).find((candidate) => candidate.supports(file));
    if (!strategy) {
      throw new Error(`No existe una estrategia de carga para ${file.name}.`);
    }

    return strategy;
  }

  private getStrategiesFor(_context: MediaUploadContext): MediaUploadStrategy[] {
    return this.strategies;
  }
}