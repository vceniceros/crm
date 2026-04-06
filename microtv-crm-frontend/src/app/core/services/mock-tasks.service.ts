import { Injectable } from '@angular/core';
import { map, of, shareReplay } from 'rxjs';

import { TaskListItem, TasksPageData, TasksTableData } from '../models/task.model';
import tasksData from '../../../mocks/tasks-data.json';

@Injectable({ providedIn: 'root' })
export class MockTasksService {
  readonly tasksPage$ = of(tasksData as TasksPageData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );

  readonly tasksTable$ = this.select((data) => data.tasksTable);
  readonly pendingTasks$ = this.select((data) => data.tasksTable.items);

  private select<T>(project: (data: TasksPageData) => T) {
    return this.tasksPage$.pipe(map(project));
  }
}

export type { TaskListItem, TasksPageData, TasksTableData };