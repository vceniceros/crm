import { Injectable } from '@angular/core';
import { BehaviorSubject, map, of, shareReplay } from 'rxjs';

import { ClientItem, ClientsPageData } from '../models/client.model';
import { CreateClientFormValue } from '../models/create-client.model';
import clientsData from '../../../mocks/clients-data.json';

@Injectable({ providedIn: 'root' })
export class MockClientsService {
  private readonly pageData = clientsData as ClientsPageData;
  private readonly clientsSubject = new BehaviorSubject<ClientItem[]>(this.pageData.items);
  private nextClientId =
    this.pageData.items.reduce((maxId, client) => Math.max(maxId, this.toNumericId(client.id)), 0) + 1;

  readonly clients$ = this.clientsSubject.asObservable();
  readonly clientsPage$ = this.clients$.pipe(
    map((items) => ({
      pageTitle: this.pageData.pageTitle,
      pageSubtitle: this.pageData.pageSubtitle,
      items
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  createClient(payload: CreateClientFormValue) {
    const client: ClientItem = {
      id: this.nextClientId++,
      razonSocial: payload.razonSocial.trim(),
      cuit: payload.cuit.trim(),
      email: payload.email.trim() || null,
      telefono: payload.telefono.trim() || null,
      isActive: true,
      location: payload.location
    };

    this.clientsSubject.next([client, ...this.clientsSubject.getValue()]);
    return of(client);
  }

  private toNumericId(clientId: number | string): number {
    return typeof clientId === 'number' ? clientId : Number.parseInt(clientId, 10) || 0;
  }
}

export type { ClientItem, ClientsPageData, CreateClientFormValue };