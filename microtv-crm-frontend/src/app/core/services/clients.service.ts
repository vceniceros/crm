import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { BehaviorSubject, Observable, catchError, finalize, map, shareReplay, tap, throwError } from 'rxjs';

import { crmApiConfig } from '../config/crm-api.config';
import { ClientItem, ClientsPageData } from '../models/client.model';
import { CreateClientFormValue } from '../models/create-client.model';
import { AuthSessionService } from './auth-session.service';

interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

interface ClientResponseDto {
  client_id: string;
  business_name: string;
  tax_id: string;
  email: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
  location: ClientLocationDto | null;
}

interface ClientLocationDto {
  latitude: number;
  longitude: number;
  address_label: string | null;
  formatted_address: string | null;
}

interface CreateClientRequestDto {
  business_name: string;
  tax_id: string;
  email: string | null;
  phone: string | null;
  location: ClientLocationRequestDto | null;
}

interface UpdateClientRequestDto extends CreateClientRequestDto {
  is_active: boolean;
}

interface ClientLocationRequestDto {
  latitude: number;
  longitude: number;
  address_label: string | null;
  formatted_address: string | null;
}

@Injectable({ providedIn: 'root' })
export class ClientsService {
  private readonly http = inject(HttpClient);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly clientsSubject = new BehaviorSubject<ClientItem[]>([]);
  private readonly isLoadingSubject = new BehaviorSubject(false);
  private readonly errorMessageSubject = new BehaviorSubject<string | null>(null);

  readonly clients$ = this.clientsSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly isLoading$ = this.isLoadingSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly errorMessage$ = this.errorMessageSubject.asObservable().pipe(
    shareReplay({ bufferSize: 1, refCount: true })
  );
  readonly clientsPage$ = this.clients$.pipe(
    map((items): ClientsPageData => ({
      pageTitle: 'Clientes',
      pageSubtitle: 'Base operativa real de clientes para tareas, tickets y seguimiento comercial.',
      items
    })),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  refresh(): Observable<void> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para consultar clientes.');
    }

    this.isLoadingSubject.next(true);
    this.errorMessageSubject.next(null);

    return this.http.get<ClientResponseDto[]>(this.buildUrl('/clients'), { headers }).pipe(
      tap((clients) => this.clientsSubject.next(clients.map((client) => this.mapClient(client)))),
      map(() => void 0),
      catchError((error) => this.handleRequestError(error, 'No se pudo cargar el listado real de clientes.')),
      finalize(() => this.isLoadingSubject.next(false))
    );
  }

  createClient(payload: CreateClientFormValue): Observable<ClientItem> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para crear clientes.');
    }

    const requestPayload: CreateClientRequestDto = {
      business_name: payload.razonSocial.trim(),
      tax_id: payload.cuit.trim(),
      email: payload.email.trim() || null,
      phone: payload.telefono.trim() || null,
      location: this.mapLocationRequest(payload)
    };

    return this.http.post<ClientResponseDto>(this.buildUrl('/clients'), requestPayload, { headers }).pipe(
      map((client) => this.mapClient(client)),
      tap((client) => {
        this.errorMessageSubject.next(null);
        this.clientsSubject.next([client, ...this.clientsSubject.getValue()]);
      }),
      catchError((error) => this.handleRequestError(error, 'No se pudo crear el cliente.'))
    );
  }

  getClientById(clientId: string): Observable<ClientItem> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para consultar el cliente.');
    }

    return this.http.get<ClientResponseDto>(this.buildUrl(`/clients/${encodeURIComponent(clientId)}`), { headers }).pipe(
      map((client) => this.mapClient(client)),
      catchError((error) => this.handleRequestError(error, 'No se pudo cargar el cliente.'))
    );
  }

  updateClient(clientId: string, payload: CreateClientFormValue): Observable<ClientItem> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para actualizar clientes.');
    }

    const requestPayload: UpdateClientRequestDto = {
      business_name: payload.razonSocial.trim(),
      tax_id: payload.cuit.trim(),
      email: payload.email.trim() || null,
      phone: payload.telefono.trim() || null,
      is_active: payload.isActive,
      location: this.mapLocationRequest(payload)
    };

    return this.http.put<ClientResponseDto>(this.buildUrl(`/clients/${encodeURIComponent(clientId)}`), requestPayload, { headers }).pipe(
      map((client) => this.mapClient(client)),
      tap((client) => {
        this.errorMessageSubject.next(null);
        const nextClients = this.clientsSubject
          .getValue()
          .filter((currentClient) => String(currentClient.id) !== clientId);

        if (client.isActive) {
          this.clientsSubject.next([client, ...nextClients]);
          return;
        }

        this.clientsSubject.next(nextClients);
      }),
      catchError((error) => this.handleRequestError(error, 'No se pudo actualizar el cliente.'))
    );
  }

  deleteClient(clientId: string): Observable<void> {
    const headers = this.buildAuthHeaders();
    if (!headers) {
      return this.failRequest('No hay una sesión autenticada válida para eliminar clientes.');
    }

    return this.http.delete<void>(this.buildUrl(`/clients/${encodeURIComponent(clientId)}`), { headers }).pipe(
      tap(() => {
        this.errorMessageSubject.next(null);
        this.clientsSubject.next(this.clientsSubject.getValue().filter((client) => String(client.id) !== clientId));
      }),
      catchError((error) => this.handleRequestError(error, 'No se pudo eliminar el cliente.'))
    );
  }

  clearError(): void {
    this.errorMessageSubject.next(null);
  }

  private mapClient(client: ClientResponseDto): ClientItem {
    return {
      id: client.client_id,
      razonSocial: client.business_name,
      cuit: client.tax_id,
      email: client.email,
      telefono: client.phone,
      isActive: client.is_active,
      location: this.mapLocation(client.location)
    };
  }

  private mapLocation(location: ClientLocationDto | null): ClientItem['location'] {
    if (!location) {
      return null;
    }

    return {
      latitude: location.latitude,
      longitude: location.longitude,
      addressLabel: location.address_label?.trim() || location.formatted_address?.trim() || undefined
    };
  }

  private mapLocationRequest(payload: CreateClientFormValue): ClientLocationRequestDto | null {
    if (!payload.location) {
      return null;
    }

    const addressLabel = payload.location.addressLabel?.trim() || null;
    return {
      latitude: payload.location.latitude,
      longitude: payload.location.longitude,
      address_label: addressLabel,
      formatted_address: addressLabel
    };
  }

  private buildAuthHeaders(): HttpHeaders | null {
    const accessToken = this.authSessionService.sessionSnapshot()?.tokens.access_token;
    if (!accessToken) {
      return null;
    }

    return new HttpHeaders({
      Authorization: `Bearer ${accessToken}`
    });
  }

  private buildUrl(path: string): string {
    return `${crmApiConfig.baseUrl}${path}`;
  }

  private handleRequestError(error: unknown, fallbackMessage: string): Observable<never> {
    const message = this.resolveErrorMessage(error, fallbackMessage);
    this.errorMessageSubject.next(message);
    return throwError(() => new Error(message));
  }

  private failRequest(message: string): Observable<never> {
    this.errorMessageSubject.next(message);
    return throwError(() => new Error(message));
  }

  private resolveErrorMessage(error: unknown, fallbackMessage: string): string {
    const apiMessage = (error as { error?: ApiErrorEnvelope })?.error?.error?.message;
    if (typeof apiMessage === 'string' && apiMessage.trim()) {
      return apiMessage;
    }

    return fallbackMessage;
  }
}