import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import { CreateTicketFormValue } from '../../../../core/models/create-ticket.model';
import { MockTicketsService } from '../../../../core/services/mock-tickets.service';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { CreateTicketDialogComponent } from '../create-ticket-dialog/create-ticket-dialog.component';
import { TicketsTableComponent } from '../tickets-table/tickets-table.component';

@Component({
  selector: 'app-tickets-page',
  standalone: true,
  imports: [AsyncPipe, MatButtonModule, MatDialogModule, MatIconModule, PageTitleComponent, TicketsTableComponent],
  templateUrl: './tickets-page.component.html',
  styleUrl: './tickets-page.component.scss'
})
export class TicketsPageComponent {
  private readonly dialog = inject(MatDialog);
  private readonly mockTicketsService = inject(MockTicketsService);

  readonly ticketsPage$ = this.mockTicketsService.ticketsPage$;

  openCreateTicketDialog(): void {
    this.dialog
      .open<CreateTicketDialogComponent, undefined, CreateTicketFormValue>(CreateTicketDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '58rem'
      })
      .afterClosed()
      .subscribe((payload) => {
        if (payload) {
          console.log('Create ticket dialog result', payload);
        }
      });
  }
}