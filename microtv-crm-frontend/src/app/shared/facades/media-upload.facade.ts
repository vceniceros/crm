import { isPlatformBrowser } from '@angular/common';
import { inject, Injectable, PLATFORM_ID } from '@angular/core';
import { from, Observable, switchMap } from 'rxjs';

import { TaskAttachment } from '../../core/models/task-attachment.model';
import { TaskManagementService } from '../../core/services/task-management.service';
import { optimizeImageForUpload } from '../../core/utils/media-upload-optimization';

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

    return from(this.prepareFilesForUpload(files, context)).pipe(
      switchMap((preparedFiles) => this.taskManagementService.uploadTaskAttachments(context.taskId, preparedFiles, context.subtaskId ?? null))
    );
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

  private async prepareFilesForUpload(files: readonly File[], context: MediaUploadContext): Promise<File[]> {
    const prepared: File[] = [];

    for (const file of files) {
      const strategy = this.resolveStrategy(context, file);
      if (strategy.kind === 'image') {
        const optimized = await optimizeImageForUpload(file);
        strategy.validate(optimized);
        prepared.push(optimized);
        continue;
      }

      strategy.validate(file);
      prepared.push(file);
    }

    return prepared;
  }
}