import { inject, Injectable } from '@angular/core';
import { combineLatest, map, of, shareReplay, tap } from 'rxjs';

import { CreateTicketFormValue } from '../models/create-ticket.model';
import { InventoryItemOption, InventoryItemsMockData } from '../models/inventory-item.model';
import { TicketCategory, TicketCategoriesMockData } from '../models/ticket-category.model';
import { TicketListItem, TicketPriorityOption, TicketsPageData, TicketsTableData } from '../models/ticket.model';
import { StockDeviceOption, StockDevicesMockData } from '../models/stock-device.model';
import { MockTicketExecutionService } from './mock-ticket-execution.service';
import inventoryItemsData from '../../../mocks/inventory-items-data.json';
import stockDevicesData from '../../../mocks/stock-devices-data.json';
import ticketCategoriesData from '../../../mocks/ticket-categories-data.json';
import ticketsData from '../../../mocks/tickets-data.json';

@Injectable({ providedIn: 'root' })
export class MockTicketsService {
  private readonly mockTicketExecutionService = inject(MockTicketExecutionService);
  readonly ticketPriorities$ = of<TicketPriorityOption[]>([
    { id: 'low', label: 'Baja' },
    { id: 'medium', label: 'Media' },
    { id: 'high', label: 'Alta' },
    { id: 'critical', label: 'Critica' }
  ]).pipe(shareReplay({ bufferSize: 1, refCount: false }));
  private readonly ticketsPageData$ = of(ticketsData as TicketsPageData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly ticketsPage$ = combineLatest([this.ticketsPageData$, this.mockTicketExecutionService.ticketSummaries$]).pipe(
    map(([pageData, items]) => ({
      ...pageData,
      ticketsTable: {
        ...pageData.ticketsTable,
        items
      }
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly categoriesData$ = of(ticketCategoriesData as TicketCategoriesMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly stockDevicesData$ = of(stockDevicesData as StockDevicesMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly inventoryItemsData$ = of(inventoryItemsData as InventoryItemsMockData).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );

  readonly ticketsTable$ = this.select((data) => data.ticketsTable);
  readonly tickets$ = this.select((data) => data.ticketsTable.items);
  readonly categories$ = this.categoriesData$.pipe(map((data) => data.categories));
  readonly stockDevices$ = this.stockDevicesData$.pipe(map((data) => data.devices));
  readonly inventoryItems$ = this.inventoryItemsData$.pipe(map((data) => data.items));

  createTicket(payload: CreateTicketFormValue) {
    return of(payload).pipe(tap((value) => console.log('Create ticket mock payload', value)));
  }

  private select<T>(project: (data: TicketsPageData) => T) {
    return this.ticketsPage$.pipe(map(project));
  }
}

export type { CreateTicketFormValue, InventoryItemOption, StockDeviceOption, TicketCategory, TicketListItem, TicketsPageData, TicketsTableData };