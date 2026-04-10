import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { combineLatest } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import { ClientItem } from '../../../../core/models/client.model';
import { MockAccessControlService } from '../../../../core/services/mock-access-control.service';
import { MockClientsService } from '../../../../core/services/mock-clients.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { LocationLinkService } from '../../../../shared/services/location-link.service';
import { CreateClientDialogComponent } from '../create-client-dialog/create-client-dialog.component';
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
  private readonly locationLinkService = inject(LocationLinkService);
  private readonly mockAccessControlService = inject(MockAccessControlService);
  private readonly mockClientsService = inject(MockClientsService);

  readonly viewModel$ = combineLatest({
    page: this.mockClientsService.clientsPage$,
    canCreate: this.mockAccessControlService.canCreateClients()
  });

  openCreateClientDialog(): void {
    this.dialog
      .open<CreateClientDialogComponent, undefined, ClientItem>(CreateClientDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '42rem'
      })
      .afterClosed()
      .subscribe();
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
}