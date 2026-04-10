import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

import { TaskAttachment } from '../models/task-attachment.model';
import { TaskProgressState } from '../models/task-progress.model';

const TASK_PROGRESS_STORAGE_KEY = 'microtv-crm.task-progress';

@Injectable({ providedIn: 'root' })
export class MockTaskProgressStorageService {
  private readonly isBrowser: boolean;
  private readonly cache = new Map<string, TaskProgressState>();
  private initialized = false;

  constructor(@Inject(PLATFORM_ID) platformId: object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  initialize(initialProgress: readonly TaskProgressState[]): void {
    if (this.initialized) {
      return;
    }

    const persistedProgress = this.readPersistedProgress();
    const sourceProgress = persistedProgress ?? initialProgress.map((progress) => this.sanitizeProgress(progress));

    this.cache.clear();

    for (const progress of sourceProgress) {
      this.cache.set(progress.taskId, progress);
    }

    if (!persistedProgress) {
      this.writePersistedProgress();
    }

    this.initialized = true;
  }

  getAllProgress(): TaskProgressState[] {
    return Array.from(this.cache.values()).map((progress) => this.cloneProgress(progress));
  }

  getProgress(taskId: string): TaskProgressState | null {
    const progress = this.cache.get(taskId);
    return progress ? this.cloneProgress(progress) : null;
  }

  saveProgress(progress: TaskProgressState): void {
    this.cache.set(progress.taskId, this.sanitizeProgress(progress));
    this.writePersistedProgress();
  }

  clearProgress(taskId: string): void {
    this.cache.delete(taskId);
    this.writePersistedProgress();
  }

  private readPersistedProgress(): TaskProgressState[] | null {
    if (!this.isBrowser) {
      return null;
    }

    const rawValue = localStorage.getItem(TASK_PROGRESS_STORAGE_KEY);

    if (!rawValue) {
      return null;
    }

    try {
      const parsedValue = JSON.parse(rawValue);

      if (!Array.isArray(parsedValue)) {
        return null;
      }

      return parsedValue
        .filter((item): item is TaskProgressState => typeof item?.taskId === 'string')
        .map((progress) => this.sanitizeProgress(progress));
    } catch {
      return null;
    }
  }

  private writePersistedProgress(): void {
    if (!this.isBrowser) {
      return;
    }

    const payload = Array.from(this.cache.values()).map((progress) => this.sanitizeProgress(progress));
    localStorage.setItem(TASK_PROGRESS_STORAGE_KEY, JSON.stringify(payload));
  }

  private sanitizeProgress(progress: TaskProgressState): TaskProgressState {
    return {
      taskId: progress.taskId,
      completedSubtaskIds: [...progress.completedSubtaskIds],
      comment: progress.comment,
      attachments: progress.attachments.map((attachment) => this.sanitizeAttachment(attachment)),
      finalized: progress.finalized,
      updatedAt: progress.updatedAt
    };
  }

  private sanitizeAttachment(attachment: TaskAttachment): TaskAttachment {
    return {
      id: attachment.id,
      fileName: attachment.fileName,
      fileType: attachment.fileType,
      kind: attachment.kind,
      previewUrl: null,
      size: attachment.size ?? null
    };
  }

  private cloneProgress(progress: TaskProgressState): TaskProgressState {
    return {
      taskId: progress.taskId,
      completedSubtaskIds: [...progress.completedSubtaskIds],
      comment: progress.comment,
      attachments: progress.attachments.map((attachment) => ({ ...attachment })),
      finalized: progress.finalized,
      updatedAt: progress.updatedAt
    };
  }
}