import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

export type ContextHelpAction = 'show' | 'hide';

@Injectable({ providedIn: 'root' })
export class ContextHelpService {
  private readonly requestsSubject = new Subject<ContextHelpAction>();

  readonly requests$: Observable<ContextHelpAction> = this.requestsSubject.asObservable();

  requestReveal(): void {
    this.requestsSubject.next('show');
  }

  requestHide(): void {
    this.requestsSubject.next('hide');
  }
}