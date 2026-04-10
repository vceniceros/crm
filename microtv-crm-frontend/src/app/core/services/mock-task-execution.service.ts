import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, combineLatest, map, of, shareReplay } from 'rxjs';

import { TaskExecutionData, TaskExecutionDefinition, TaskExecutionItem, TaskExecutionSubtaskDefinition, TaskExecutionSubtaskView } from '../models/task-execution.model';
import { TaskAttachment, TaskAttachmentKind } from '../models/task-attachment.model';
import { TaskProgressData, TaskProgressState } from '../models/task-progress.model';
import { TaskListItem } from '../models/task.model';
import { MockUserProfile, MockUserContextService } from './mock-user-context.service';
import { MockTaskProgressStorageService } from './mock-task-progress-storage.service';
import taskExecutionData from '../../../mocks/task-execution-data.json';
import taskProgressData from '../../../mocks/task-progress-data.json';

@Injectable({ providedIn: 'root' })
export class MockTaskExecutionService {
  private readonly mockUserContextService = inject(MockUserContextService);
  private readonly taskProgressStorageService = inject(MockTaskProgressStorageService);
  private readonly taskDefinitions = (taskExecutionData as TaskExecutionData).tasks;
  private readonly progressSeed = (taskProgressData as TaskProgressData).progress;
  private readonly progressStateSubject = new BehaviorSubject<Record<string, TaskProgressState>>({});

  readonly taskSummaries$ = combineLatest([
    of(this.taskDefinitions),
    this.progressStateSubject.asObservable(),
    this.mockUserContextService.activeUser()
  ]).pipe(
    map(([tasks, progressByTaskId, user]) =>
      tasks
        .filter((task) => this.canUserAccessTask(task, user))
        .map((task) => this.buildTaskListItem(task, this.getProgressForTask(task.id, progressByTaskId)))
    ),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  constructor() {
    this.taskProgressStorageService.initialize(this.progressSeed);
    this.progressStateSubject.next(this.buildProgressRecord(this.taskProgressStorageService.getAllProgress()));
  }

  getTaskExecution(taskId: string) {
    return combineLatest([
      of(this.taskDefinitions),
      this.progressStateSubject.asObservable(),
      this.mockUserContextService.activeUser()
    ]).pipe(
      map(([tasks, progressByTaskId, user]) => {
        const task = tasks.find((item) => item.id === taskId);

        if (!task || !this.canUserAccessTask(task, user)) {
          return null;
        }

        return this.buildTaskExecutionItem(task, this.getProgressForTask(task.id, progressByTaskId));
      })
    );
  }

  updateSubtask(taskId: string, subtaskId: string, completed: boolean): boolean {
    const task = this.findTask(taskId);

    if (!task) {
      return false;
    }

    const progress = this.cloneProgress(this.getCurrentProgress(taskId));

    if (progress.finalized) {
      return false;
    }

    const completedSubtaskIds = new Set(progress.completedSubtaskIds);

    if (completed) {
      if (!this.canCompleteSubtask(task, progress.completedSubtaskIds, subtaskId)) {
        return false;
      }

      completedSubtaskIds.add(subtaskId);
    } else {
      completedSubtaskIds.delete(subtaskId);
    }

    progress.completedSubtaskIds = this.normalizeCompletedSubtaskIds(task, completedSubtaskIds);
    progress.updatedAt = new Date().toISOString();
    this.persistProgress(progress);
    return true;
  }

  updateComment(taskId: string, comment: string): boolean {
    const task = this.findTask(taskId);

    if (!task) {
      return false;
    }

    const progress = this.cloneProgress(this.getCurrentProgress(taskId));

    if (progress.finalized) {
      return false;
    }

    progress.comment = comment;
    progress.updatedAt = new Date().toISOString();
    this.persistProgress(progress);
    return true;
  }

  addAttachments(taskId: string, files: readonly File[]): boolean {
    const task = this.findTask(taskId);

    if (!task || files.length === 0) {
      return false;
    }

    const progress = this.cloneProgress(this.getCurrentProgress(taskId));

    if (progress.finalized) {
      return false;
    }

    const nextAttachments = files.map((file, index) => this.createAttachmentFromFile(file, taskId, index));

    progress.attachments = [...progress.attachments, ...nextAttachments];
    progress.updatedAt = new Date().toISOString();
    this.persistProgress(progress);
    return true;
  }

  removeAttachment(taskId: string, attachmentId: string): boolean {
    const task = this.findTask(taskId);

    if (!task) {
      return false;
    }

    const progress = this.cloneProgress(this.getCurrentProgress(taskId));

    if (progress.finalized) {
      return false;
    }

    const attachmentToRemove = progress.attachments.find((attachment) => attachment.id === attachmentId);

    if (!attachmentToRemove) {
      return false;
    }

    this.revokePreviewUrl(attachmentToRemove.previewUrl);
    progress.attachments = progress.attachments.filter((attachment) => attachment.id !== attachmentId);
    progress.updatedAt = new Date().toISOString();
    this.persistProgress(progress);
    return true;
  }

  finalizeTask(taskId: string): boolean {
    const task = this.findTask(taskId);

    if (!task) {
      return false;
    }

    const progress = this.cloneProgress(this.getCurrentProgress(taskId));

    if (progress.finalized) {
      return true;
    }

    const normalizedCompletedIds = this.normalizeCompletedSubtaskIds(task, progress.completedSubtaskIds);

    if (!this.canFinalizeTask(task, normalizedCompletedIds)) {
      return false;
    }

    progress.completedSubtaskIds = normalizedCompletedIds;
    progress.finalized = true;
    progress.updatedAt = new Date().toISOString();
    this.persistProgress(progress);
    return true;
  }

  canCompleteSubtask(task: TaskExecutionDefinition, completedSubtaskIds: readonly string[], subtaskId: string): boolean {
    const normalizedCompletedIds = new Set(this.normalizeCompletedSubtaskIds(task, completedSubtaskIds));
    const subtasks = this.buildSubtaskView(task.subtasks, normalizedCompletedIds, true);
    const targetSubtask = this.findSubtaskView(subtasks, subtaskId);
    return Boolean(targetSubtask?.enabled);
  }

  private buildTaskListItem(task: TaskExecutionDefinition, progress: TaskProgressState): TaskListItem {
    const normalizedCompletedIds = this.normalizeCompletedSubtaskIds(task, progress.completedSubtaskIds);
    const totalSubtasks = this.countSubtasks(task.subtasks);
    const completedSubtasks = normalizedCompletedIds.length;
    const canFinalize = this.canFinalizeTask(task, normalizedCompletedIds);
    const status = this.resolveTaskStatus(task, completedSubtasks, canFinalize, progress.finalized);

    return {
      id: task.id,
      title: task.title,
      client: task.client,
      completedSubtasks,
      totalSubtasks,
      status: status.label,
      statusTone: status.tone,
      assignedToUserId: task.assigneeId,
      assignedTo: task.assigneeName,
      assignedInitials: task.assigneeInitials
    };
  }

  private buildTaskExecutionItem(task: TaskExecutionDefinition, progress: TaskProgressState): TaskExecutionItem {
    const normalizedCompletedIds = this.normalizeCompletedSubtaskIds(task, progress.completedSubtaskIds);
    const completedSubtaskSet = new Set(normalizedCompletedIds);
    const totalSubtasks = this.countSubtasks(task.subtasks);
    const completedSubtasks = normalizedCompletedIds.length;
    const canFinalize = this.canFinalizeTask(task, normalizedCompletedIds);
    const status = this.resolveTaskStatus(task, completedSubtasks, canFinalize, progress.finalized);

    return {
      id: task.id,
      title: task.title,
      client: task.client,
      summary: task.summary,
      status: status.label,
      statusTone: status.tone,
      assigneeId: task.assigneeId,
      assigneeName: task.assigneeName,
      assigneeInitials: task.assigneeInitials,
      completedSubtasks,
      totalSubtasks,
      progressPercent: totalSubtasks ? Math.round((completedSubtasks / totalSubtasks) * 100) : 0,
      comment: progress.comment,
      attachments: progress.attachments.map((attachment) => ({ ...attachment })),
      finalized: progress.finalized,
      canFinalize,
      updatedAt: progress.updatedAt,
      subtasks: this.buildSubtaskView(task.subtasks, completedSubtaskSet, true)
    };
  }

  private buildSubtaskView(
    subtasks: readonly TaskExecutionSubtaskDefinition[],
    completedSubtaskIds: ReadonlySet<string>,
    parentEnabled: boolean
  ): TaskExecutionSubtaskView[] {
    const view: TaskExecutionSubtaskView[] = [];
    let previousRequiredCompleted = true;

    for (const subtask of subtasks) {
      const enabled = parentEnabled && previousRequiredCompleted;
      const completed = enabled && completedSubtaskIds.has(subtask.id);
      const children = this.buildSubtaskView(subtask.children, completedSubtaskIds, enabled && completed);

      view.push({
        ...subtask,
        completed,
        enabled,
        blocked: !enabled,
        children
      });

      if ((subtask.required ?? true) && !completed) {
        previousRequiredCompleted = false;
      }
    }

    return view;
  }

  private normalizeCompletedSubtaskIds(
    task: TaskExecutionDefinition,
    completedSubtaskIds: Iterable<string>
  ): string[] {
    const candidateIds = new Set(completedSubtaskIds);
    const normalizedIds: string[] = [];

    const visit = (subtasks: readonly TaskExecutionSubtaskDefinition[], parentEnabled: boolean) => {
      let previousRequiredCompleted = true;

      for (const subtask of subtasks) {
        const enabled = parentEnabled && previousRequiredCompleted;
        const completed = enabled && candidateIds.has(subtask.id);

        if (completed) {
          normalizedIds.push(subtask.id);
        }

        visit(subtask.children, enabled && completed);

        if ((subtask.required ?? true) && !completed) {
          previousRequiredCompleted = false;
        }
      }
    };

    visit(task.subtasks, true);
    return normalizedIds;
  }

  private canFinalizeTask(task: TaskExecutionDefinition, completedSubtaskIds: readonly string[]): boolean {
    const normalizedIds = new Set(this.normalizeCompletedSubtaskIds(task, completedSubtaskIds));
    return this.countRequiredSubtasks(task.subtasks) === normalizedIds.size;
  }

  private countSubtasks(subtasks: readonly TaskExecutionSubtaskDefinition[]): number {
    return subtasks.reduce((count, subtask) => count + 1 + this.countSubtasks(subtask.children), 0);
  }

  private countRequiredSubtasks(subtasks: readonly TaskExecutionSubtaskDefinition[]): number {
    return subtasks.reduce((count, subtask) => {
      const ownCount = subtask.required === false ? 0 : 1;
      return count + ownCount + this.countRequiredSubtasks(subtask.children);
    }, 0);
  }

  private resolveTaskStatus(
    task: TaskExecutionDefinition,
    completedSubtasks: number,
    canFinalize: boolean,
    finalized: boolean
  ): { label: TaskListItem['status']; tone: TaskListItem['statusTone'] } {
    if (finalized) {
      return { label: 'Finalizada', tone: 'success' };
    }

    if (canFinalize && completedSubtasks > 0) {
      return { label: 'Lista para finalizar', tone: 'success' };
    }

    if (completedSubtasks > 0) {
      return { label: 'En progreso', tone: 'progress' };
    }

    return { label: task.status, tone: task.statusTone };
  }

  private createAttachmentFromFile(file: File, taskId: string, index: number): TaskAttachment {
    const kind = this.resolveAttachmentKind(file.type);
    const previewUrl = kind === 'image' || kind === 'video' ? URL.createObjectURL(file) : null;

    return {
      id: `${taskId}-${Date.now()}-${index}`,
      fileName: file.name,
      fileType: file.type || 'application/octet-stream',
      kind,
      previewUrl,
      size: file.size
    };
  }

  private resolveAttachmentKind(fileType: string): TaskAttachmentKind {
    if (fileType.startsWith('image/')) {
      return 'image';
    }

    if (fileType.startsWith('video/')) {
      return 'video';
    }

    return 'other';
  }

  private persistProgress(progress: TaskProgressState): void {
    const nextProgressByTaskId = {
      ...this.progressStateSubject.value,
      [progress.taskId]: this.cloneProgress(progress)
    };

    this.progressStateSubject.next(nextProgressByTaskId);
    this.taskProgressStorageService.saveProgress(progress);
  }

  private getCurrentProgress(taskId: string): TaskProgressState {
    return this.getProgressForTask(taskId, this.progressStateSubject.value);
  }

  private getProgressForTask(taskId: string, progressByTaskId: Record<string, TaskProgressState>): TaskProgressState {
    return progressByTaskId[taskId] ? this.cloneProgress(progressByTaskId[taskId]) : this.createEmptyProgress(taskId);
  }

  private createEmptyProgress(taskId: string): TaskProgressState {
    return {
      taskId,
      completedSubtaskIds: [],
      comment: '',
      attachments: [],
      finalized: false,
      updatedAt: ''
    };
  }

  private buildProgressRecord(progressList: readonly TaskProgressState[]): Record<string, TaskProgressState> {
    return progressList.reduce<Record<string, TaskProgressState>>((record, progress) => {
      record[progress.taskId] = this.cloneProgress(progress);
      return record;
    }, {});
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

  private findTask(taskId: string): TaskExecutionDefinition | undefined {
    return this.taskDefinitions.find((task) => task.id === taskId);
  }

  private findSubtaskView(subtasks: readonly TaskExecutionSubtaskView[], subtaskId: string): TaskExecutionSubtaskView | null {
    for (const subtask of subtasks) {
      if (subtask.id === subtaskId) {
        return subtask;
      }

      const match = this.findSubtaskView(subtask.children, subtaskId);

      if (match) {
        return match;
      }
    }

    return null;
  }

  private canUserAccessTask(task: TaskExecutionDefinition, user: MockUserProfile): boolean {
    return user.role === 'admin' || task.assigneeId === user.id;
  }

  private revokePreviewUrl(previewUrl: string | null | undefined): void {
    if (previewUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl);
    }
  }
}