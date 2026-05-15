import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { BehaviorSubject, switchMap } from 'rxjs';

import { formatInventoryRequestStatus } from '../../../../core/models/inventory-flow.model';
import { InventoryFlowService } from '../../../../core/services/inventory-flow.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';

@Component({
  selector: 'app-inventory-requests-page',
  standalone: true,
  imports: [AsyncPipe, DatePipe, MatButtonModule, MatCardModule, MatIconModule, PageTitleComponent, RouterLink],
  templateUrl: './inventory-requests-page.component.html',
  styleUrl: './inventory-requests-page.component.scss'
})
export class InventoryRequestsPageComponent {
  private readonly inventoryFlowService = inject(InventoryFlowService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly refreshSubject = new BehaviorSubject(0);

  readonly requests$ = this.refreshSubject.pipe(switchMap(() => this.inventoryFlowService.listOpenRequests()));

  approve(requestId: string): void {
    this.inventoryFlowService
      .reviewRequest(requestId, { status: 'APPROVED', review_notes: null })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: () => this.refreshSubject.next(this.refreshSubject.value + 1), error: () => undefined });
  }

  reject(requestId: string): void {
    this.inventoryFlowService
      .reviewRequest(requestId, { status: 'REJECTED', review_notes: null })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: () => this.refreshSubject.next(this.refreshSubject.value + 1), error: () => undefined });
  }

  sourceRoute(sourceType: string, sourceReferenceId: string): string[] {
    return sourceType === 'TASK' ? ['/tasks', sourceReferenceId] : ['/tickets', sourceReferenceId];
  }

  sourceLabel(sourceType: string): string {
    return sourceType === 'TASK' ? 'Pedido' : 'Ticket';
  }

  sourceActionLabel(sourceType: string): string {
    return sourceType === 'TASK' ? 'Abrir pedido' : 'Abrir ticket';
  }

  requestTitle(request: { request_reason: string | null; items: Array<{ product_name: string; quantity_requested: number }> }): string {
    const reason = request.request_reason?.trim();
    if (reason) {
      return reason;
    }

    const firstItem = request.items[0];
    if (!firstItem) {
      return 'Solicitud de materiales';
    }

    const suffix = request.items.length > 1 ? ` y ${request.items.length - 1} item(s) más` : '';
    return `${firstItem.product_name} x${firstItem.quantity_requested}${suffix}`;
  }

  shortId(value: string | null | undefined): string {
    return value ? value.slice(0, 8) : 'sin ID';
  }

  readonly formatInventoryRequestStatus = formatInventoryRequestStatus;
}
