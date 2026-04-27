import { Injectable } from '@angular/core';
import { map, of, shareReplay, tap } from 'rxjs';

import { MaterialOption, MaterialsMockData } from '../models/material.model';
import { TaskTemplateDraft, TaskTemplateRecord, TaskTemplatesMockData } from '../models/task-template.model';
import materialsData from '../../../mocks/materials-data.json';
import taskTemplatesData from '../../../mocks/task-templates-data.json';

@Injectable({ providedIn: 'root' })
export class MockTaskTemplateService {
  readonly materialsData$ = of(materialsData as MaterialsMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly taskTemplatesData$ = of(taskTemplatesData as TaskTemplatesMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );

  readonly materials$ = this.materialsData$.pipe(map((data) => data.materials));
  readonly templates$ = this.taskTemplatesData$.pipe(map((data) => data.templates));

  createTemplate(payload: TaskTemplateDraft) {
    const createdTemplate: TaskTemplateRecord = {
      id: this.generateTemplateId(),
      ...payload
    };

    return of(createdTemplate).pipe(tap((value) => console.log('Create template mock payload', value)));
  }

  private generateTemplateId(): string {
    return `TPL-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
  }
}

export type { MaterialOption, TaskTemplateDraft, TaskTemplateRecord };