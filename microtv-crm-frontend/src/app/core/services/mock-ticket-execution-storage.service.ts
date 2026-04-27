import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

import { TicketAttachment } from '../models/ticket-attachment.model';
import { TicketExecutionState } from '../models/ticket-execution.model';

const TICKET_EXECUTION_STORAGE_KEY = 'microtv-crm.ticket-execution';

@Injectable({ providedIn: 'root' })
export class MockTicketExecutionStorageService {
  private readonly isBrowser: boolean;
  private readonly cache = new Map<string, TicketExecutionState>();
  private initialized = false;

  constructor(@Inject(PLATFORM_ID) platformId: object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  initialize(initialExecution: readonly TicketExecutionState[]): void {
    if (this.initialized) {
      return;
    }

    const persistedExecution = this.readPersistedExecution();
    const sourceExecution = persistedExecution ?? initialExecution.map((state) => this.sanitizeExecutionState(state));

    this.cache.clear();

    for (const state of sourceExecution) {
      this.cache.set(state.ticketId, state);
    }

    if (!persistedExecution) {
      this.writePersistedExecution();
    }

    this.initialized = true;
  }

  getAllExecutionState(): TicketExecutionState[] {
    return Array.from(this.cache.values()).map((state) => this.cloneExecutionState(state));
  }

  getExecutionState(ticketId: string): TicketExecutionState | null {
    const state = this.cache.get(ticketId);
    return state ? this.cloneExecutionState(state) : null;
  }

  saveExecutionState(state: TicketExecutionState): void {
    this.cache.set(state.ticketId, this.sanitizeExecutionState(state));
    this.writePersistedExecution();
  }

  private readPersistedExecution(): TicketExecutionState[] | null {
    if (!this.isBrowser) {
      return null;
    }

    const rawValue = localStorage.getItem(TICKET_EXECUTION_STORAGE_KEY);

    if (!rawValue) {
      return null;
    }

    try {
      const parsedValue = JSON.parse(rawValue);

      if (!Array.isArray(parsedValue)) {
        return null;
      }

      return parsedValue
        .filter((item): item is TicketExecutionState => typeof item?.ticketId === 'string')
        .map((state) => this.sanitizeExecutionState(state));
    } catch {
      return null;
    }
  }

  private writePersistedExecution(): void {
    if (!this.isBrowser) {
      return;
    }

    const payload = Array.from(this.cache.values()).map((state) => this.sanitizeExecutionState(state));
    localStorage.setItem(TICKET_EXECUTION_STORAGE_KEY, JSON.stringify(payload));
  }

  private sanitizeExecutionState(state: TicketExecutionState): TicketExecutionState {
    return {
      ticketId: state.ticketId,
      resolutionComment: state.resolutionComment,
      resolutionUpdatedAt: state.resolutionUpdatedAt,
      attachments: state.attachments.map((attachment) => this.sanitizeAttachment(attachment)),
      inventoryRequests: state.inventoryRequests.map((request) => ({
        ...request,
        items: request.items.map((item) => ({ ...item }))
      })),
      dispatchedItems: state.dispatchedItems.map((item) => ({ ...item })),
      updatedAt: state.updatedAt
    };
  }

  private sanitizeAttachment(attachment: TicketAttachment): TicketAttachment {
    return {
      id: attachment.id,
      fileName: attachment.fileName,
      fileType: attachment.fileType,
      kind: attachment.kind,
      previewUrl: null,
      size: attachment.size ?? null
    };
  }

  private cloneExecutionState(state: TicketExecutionState): TicketExecutionState {
    return {
      ticketId: state.ticketId,
      resolutionComment: state.resolutionComment,
      resolutionUpdatedAt: state.resolutionUpdatedAt,
      attachments: state.attachments.map((attachment) => ({ ...attachment })),
      inventoryRequests: state.inventoryRequests.map((request) => ({
        ...request,
        items: request.items.map((item) => ({ ...item }))
      })),
      dispatchedItems: state.dispatchedItems.map((item) => ({ ...item })),
      updatedAt: state.updatedAt
    };
  }
}