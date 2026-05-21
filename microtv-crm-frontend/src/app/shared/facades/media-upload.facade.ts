import { isPlatformBrowser } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { inject, Injectable, PLATFORM_ID, signal } from '@angular/core';
import { filter, from, map, Observable, switchMap, tap } from 'rxjs';

import { TaskAttachment } from '../../core/models/task-attachment.model';
import { TaskManagementService } from '../../core/services/task-management.service';
import { MediaStatusPollerService } from '../../core/services/media-status-poller.service';
import { optimizeImageForUpload } from '../../core/utils/media-upload-optimization';

import { ImageUploadStrategy } from './media-upload/image-upload.strategy';
import { MediaUploadContext, MediaUploadPort, MediaUploadStrategy } from './media-upload/media-upload.types';
import { VideoUploadStrategy } from './media-upload/video-upload.strategy';

@Injectable({ providedIn: 'root' })
export class MediaUploadFacade implements MediaUploadPort {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly taskManagementService = inject(TaskManagementService);
  private readonly mediaStatusPoller = inject(MediaStatusPollerService);
  readonly uploadProgress = signal<number | null>(null);
  readonly mediaStatus = signal<'uploading' | 'processing' | 'ready' | 'failed' | null>(null);
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
      switchMap((preparedFiles) => this.taskManagementService.uploadTaskAttachmentsWithProgress(context.taskId, preparedFiles, context.subtaskId ?? null)),
      tap((event) => {
        if (event.type === HttpEventType.UploadProgress) {
          this.mediaStatus.set('uploading');
          this.uploadProgress.set(event.total ? Math.round((event.loaded / event.total) * 100) : null);
          return;
        }

        if (event.type !== HttpEventType.Response) {
          return;
        }

        this.uploadProgress.set(100);
        const mediaId = event.body?.find((attachment) => Boolean(attachment.media_id))?.media_id;
        if (!mediaId) {
          this.mediaStatus.set(null);
          return;
        }

        this.mediaStatus.set('processing');
        this.mediaStatusPoller.pollUntilDone(mediaId).subscribe((status) => {
          this.mediaStatus.set(status.status === 'ready' ? 'ready' : status.status === 'failed' ? 'failed' : 'processing');
        });
      }),
      filter((event) => event.type === HttpEventType.Response),
      map((event) => event.body ?? [])
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
