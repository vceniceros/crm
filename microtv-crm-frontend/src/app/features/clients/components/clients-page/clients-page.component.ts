import { AsyncPipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { combineLatest } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import { ClientItem } from '../../../../core/models/client.model';
import { MockAccessControlService } from '../../../../core/services/mock-access-control.service';
import { ClientsService } from '../../../../core/services/clients.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { ClientDialogData, CreateClientDialogComponent } from '../create-client-dialog/create-client-dialog.component';
import { ClientLocationDialogComponent } from '../client-location-dialog/client-location-dialog.component';
import { ClientsGridComponent } from '../clients-grid/clients-grid.component';

@Component({
  selector: 'app-clients-page',
  standalone: true,
  imports: [AsyncPipe, MatButtonModule, MatDialogModule, MatIconModule, PageTitleComponent, ClientsGridComponent],
  templateUrl: './clients-page.component.html',
  styleUrl: './clients-page.component.scss'
})
export class ClientsPageComponent {
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly mockAccessControlService = inject(MockAccessControlService);
  private readonly clientsService = inject(ClientsService);

  readonly feedbackMessage = signal<string | null>(null);
  readonly feedbackTone = signal<'success' | 'error'>('success');

  readonly viewModel$ = combineLatest({
    page: this.clientsService.clientsPage$,
    isLoading: this.clientsService.isLoading$,
    errorMessage: this.clientsService.errorMessage$,
    canCreate: this.mockAccessControlService.canCreateClients(),
    canEdit: this.mockAccessControlService.canEditClients(),
    canDelete: this.mockAccessControlService.canDeleteClients()
  });

  constructor() {
    this.clientsService
      .refresh()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        error: () => {
          this.feedbackMessage.set(null);
        }
      });
  }

  openCreateClientDialog(): void {
    this.dialog
      .open<CreateClientDialogComponent, ClientDialogData, ClientItem>(CreateClientDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '52rem',
        data: { mode: 'create' }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((client) => {
        if (!client) {
          return;
        }

        this.feedbackTone.set('success');
        this.feedbackMessage.set(`Cliente ${client.razonSocial} creado correctamente.`);
      });
  }

  openEditClientDialog(client: ClientItem): void {
    this.dialog
      .open<CreateClientDialogComponent, ClientDialogData, ClientItem>(CreateClientDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '52rem',
        data: { mode: 'edit', client }
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((updatedClient) => {
        if (!updatedClient) {
          return;
        }

        this.feedbackTone.set('success');
        this.feedbackMessage.set(`Cliente ${updatedClient.razonSocial} actualizado correctamente.`);
      });
  }

  openLocationDialog(client: ClientItem): void {
    this.dialog.open(ClientLocationDialogComponent, {
      autoFocus: false,
      maxWidth: 'calc(100vw - 1rem)',
      width: '46rem',
      data: { client }
    });
  }

  openExternalMaps(client: ClientItem): void {
    this.locationLinkService.openInGoogleMaps(client.location);
  }

  deleteClient(client: ClientItem): void {
    if (!window.confirm(`¿Eliminar al cliente ${client.razonSocial}?`)) {
      return;
    }

    this.clientsService
      .deleteClient(String(client.id))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.feedbackTone.set('success');
          this.feedbackMessage.set(`Cliente ${client.razonSocial} eliminado correctamente.`);
        },
        error: () => {
          this.feedbackTone.set('error');
        }
      });
  }

  clearFeedback(): void {
    this.feedbackMessage.set(null);
    this.clientsService.clearError();
  }
}