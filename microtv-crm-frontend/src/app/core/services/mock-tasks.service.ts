import { inject, Injectable } from '@angular/core';
import { combineLatest, map, of, shareReplay } from 'rxjs';

import { TaskListItem, TasksPageData, TasksTableData } from '../models/task.model';
import { MockTaskExecutionService } from './mock-task-execution.service';
import tasksData from '../../../mocks/tasks-data.json';

@Injectable({ providedIn: 'root' })
export class MockTasksService {
  private readonly mockTaskExecutionService = inject(MockTaskExecutionService);
  private readonly tasksPageData$ = of(tasksData as TasksPageData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly tasksPage$ = combineLatest([this.tasksPageData$, this.mockTaskExecutionService.taskSummaries$]).pipe(
    map(([pageData, items]) => ({
      ...pageData,
      tasksTable: {
        ...pageData.tasksTable,
        items
      }
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  readonly tasksTable$ = this.select((data) => data.tasksTable);
  readonly pendingTasks$ = this.select((data) => data.tasksTable.items);

  private select<T>(project: (data: TasksPageData) => T) {
    return this.tasksPage$.pipe(map(project));
  }
}

export type { TaskListItem, TasksPageData, TasksTableData };