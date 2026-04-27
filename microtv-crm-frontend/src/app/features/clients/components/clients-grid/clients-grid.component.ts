import { Component, input, output } from '@angular/core';

import { ClientItem } from '../../../../core/models/client.model';
import { ClientCardComponent } from '../client-card/client-card.component';

@Component({
  selector: 'app-clients-grid',
  standalone: true,
  imports: [ClientCardComponent],
  templateUrl: './clients-grid.component.html',
  styleUrl: './clients-grid.component.scss'
})
export class ClientsGridComponent {
  readonly clients = input.required<readonly ClientItem[]>();
  readonly canEdit = input(false);
  readonly canDelete = input(false);
  readonly editClient = output<ClientItem>();
  readonly deleteClient = output<ClientItem>();
  readonly openLocation = output<ClientItem>();
  readonly openExternalMaps = output<ClientItem>();
}