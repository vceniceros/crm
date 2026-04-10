import { Injectable } from '@angular/core';
import { map, of, shareReplay, tap } from 'rxjs';

import { ClientOption } from '../models/client.model';
import { CreateTaskFormValue, TaskCreationMockData } from '../models/create-task.model';
import { TaskTemplateOption } from '../models/task-template-option.model';
import taskCreationData from '../../../mocks/task-creation-data.json';

@Injectable({ providedIn: 'root' })
export class MockTaskCreationService {
  readonly taskCreationData$ = of(taskCreationData as TaskCreationMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );

  readonly clients$ = this.select((data) => data.clients);
  readonly templates$ = this.select((data) => data.templates);

  createTask(payload: CreateTaskFormValue) {
    return of(payload).pipe(tap((value) => console.log('Create task mock payload', value)));
  }

  private select<T>(project: (data: TaskCreationMockData) => T) {
    return this.taskCreationData$.pipe(map(project));
  }
}

export type { ClientOption, CreateTaskFormValue, TaskCreationMockData, TaskTemplateOption };