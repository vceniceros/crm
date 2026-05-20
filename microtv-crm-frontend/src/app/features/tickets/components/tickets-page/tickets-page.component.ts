import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Router } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';

import {
  buildGoogleMapsUrlFromTicketLocation,
  formatTicketPriority,
  formatTicketStatus,
  TicketDetail,
  TicketSummary,
  TicketTableItem,
  toLocationLabel,
  toTicketPriorityTone,
  toTicketStatusTone
} from '../../../../core/models/ticket-management.model';
import { UI_HELP_TEXTS } from '../../../../core/config/ui-help-texts.config';
import { AuthSessionService } from '../../../../core/services/auth-session.service';
import { SettingsCategory } from '../../../../core/models/settings-management.model';
import { SettingsManagementService } from '../../../../core/services/settings-management.service';
import { TicketManagementService } from '../../../../core/services/ticket-management.service';
import { ListingCategoryOption, ListingSortDirection, ListingStatusOption, ListingControlsComponent } from '../../../../shared/ui/listing-controls/listing-controls.component';
import { ListingViewMode, ListingViewPreferenceService } from '../../../../shared/services/listing-view-preference.service';
import { ContextHelpCardComponent } from '../../../../shared/ui/context-help-card/context-help-card.component';
import { PageTitleComponent } from '../../../../shared/ui/page-title/page-title.component';
import { CreateTicketDialogComponent } from '../create-ticket-dialog/create-ticket-dialog.component';
import { SurveyLinkDialogComponent } from '../survey-link-dialog/survey-link-dialog.component';
import { TicketsTableComponent } from '../tickets-table/tickets-table.component';

type TicketListContextId = 'assigned' | 'unassigned' | 'tracking' | 'history';

interface TicketListUiState {
  search: string;
  status: string;
  category: string;
  sortDirection: ListingSortDirection;
  viewMode: ListingViewMode;
}

@Component({
  selector: 'app-tickets-page',
  standalone: true,
  imports: [
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    ContextHelpCardComponent,
    ListingControlsComponent,
    PageTitleComponent,
    TicketsTableComponent
  ],
  templateUrl: './tickets-page.component.html',
  styleUrl: './tickets-page.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TicketsPageComponent {
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly destroyRef = inject(DestroyRef);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);
  private readonly authSessionService = inject(AuthSessionService);
  private readonly settingsManagementService = inject(SettingsManagementService);
  private readonly ticketManagementService = inject(TicketManagementService);
  private readonly listingViewPreferenceService = inject(ListingViewPreferenceService);
  readonly helpText = UI_HELP_TEXTS.tickets;

  readonly isHandset = toSignal(
    this.breakpointObserver.observe([Breakpoints.Handset]).pipe(map((state) => state.matches)),
    { initialValue: false }
  );

  readonly isLoading = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);
  readonly selectedTabIndex = signal(0);
  readonly isAssigning = signal(false);
  readonly assigningTicketId = signal<string | null>(null);
  readonly assignedTickets = signal<TicketSummary[]>([]);
  readonly unassignedTickets = signal<TicketSummary[]>([]);
  readonly trackingTickets = signal<TicketSummary[]>([]);
  readonly historyTickets = signal<TicketSummary[]>([]);
  readonly operationalCategories = signal<SettingsCategory[]>([]);

  readonly currentRoles = computed(() => this.authSessionService.sessionSnapshot()?.user.role_keys ?? []);
  readonly currentUserId = computed(() => this.authSessionService.sessionSnapshot()?.user.crm_user_id ?? null);
  readonly canViewHistory = computed(() => this.currentRoles().length > 0);
  readonly assignedRows = computed(() => this.mapTickets(this.assignedTickets()));
  readonly unassignedRows = computed(() => this.mapTickets(this.unassignedTickets(), { forUnassignedTab: true }));
  readonly trackingRows = computed(() => this.mapTickets(this.trackingTickets()));
  readonly historyRows = computed(() => this.mapTickets(this.historyTickets()));
  readonly ticketStatusOptions: readonly ListingStatusOption[] = [
    { value: 'all', label: 'Todos los estados' },
    { value: 'OPEN', label: 'Abierto' },
    { value: 'IN_PROGRESS', label: 'En gestion' },
    { value: 'ON_HOLD', label: 'En espera' },
    { value: 'RESOLVED', label: 'Resuelto' },
    { value: 'PENDING_APPROVAL', label: 'Pendiente de aprobacion' },
    { value: 'CLOSED', label: 'Cerrado' }
  ];
  readonly categoryOptions = computed<readonly ListingCategoryOption[]>(() => [
    { value: 'all', label: 'Todas las categorias' },
    ...this.operationalCategories()
      .filter((category) => category.is_active)
      .map((category) => ({ value: category.category_id, label: category.name }))
  ]);
  readonly listUiState = signal<Record<TicketListContextId, TicketListUiState>>({
    assigned: this.buildInitialListUiState('assigned'),
    unassigned: this.buildInitialListUiState('unassigned'),
    tracking: this.buildInitialListUiState('tracking'),
    history: this.buildInitialListUiState('history')
  });
  readonly assignedVisibleRows = computed(() => this.applyTicketListState(this.assignedRows(), 'assigned'));
  readonly unassignedVisibleRows = computed(() => this.applyTicketListState(this.unassignedRows(), 'unassigned'));
  readonly trackingVisibleRows = computed(() => this.applyTicketListState(this.trackingRows(), 'tracking'));
  readonly historyVisibleRows = computed(() => this.applyTicketListState(this.historyRows(), 'history'));
  readonly canSelfAssignUnassignedTickets = computed(() => {
    return this.currentRoles().length > 0;
  });

  constructor() {
    this.loadCategories();
    this.refresh();
  }

  loadCategories(): void {
    this.settingsManagementService
      .listCategories('operational')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (categories) => this.operationalCategories.set(categories),
        error: () => this.operationalCategories.set([])
      });
  }

  refresh(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.successMessage.set(null);

    let pendingRequests = 4;
    const onRequestCompleted = () => {
      pendingRequests -= 1;
      if (pendingRequests <= 0) {
        this.isLoading.set(false);
      }
    };

    this.ticketManagementService
      .listAssignedTickets()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (tickets) => {
          this.assignedTickets.set(this.sortTickets(tickets));
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });

    this.ticketManagementService
      .listUnassignedTickets()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (tickets) => {
          this.unassignedTickets.set(this.sortTickets(tickets));
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });

    this.ticketManagementService
      .listTrackingTickets()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (tickets) => {
          this.trackingTickets.set(this.sortTickets(tickets));
          onRequestCompleted();
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          onRequestCompleted();
        }
      });

    if (this.canViewHistory()) {
      this.ticketManagementService
        .listTicketHistory()
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (tickets) => {
            this.historyTickets.set(this.sortTickets(tickets));
            onRequestCompleted();
          },
          error: (error: Error) => {
            this.errorMessage.set(error.message);
            onRequestCompleted();
          }
        });
      return;
    }

    this.historyTickets.set([]);
  }

  openCreateTicketDialog(): void {
    this.dialog
      .open<CreateTicketDialogComponent, undefined, TicketDetail>(CreateTicketDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1.5rem)',
        width: '58rem'
      })
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((ticket) => {
        if (ticket) {
          this.successMessage.set(`Ticket ${ticket.ticket_number} creado correctamente.`);
          this.refresh();
          void this.router.navigate(['/tickets', ticket.ticket_id]);
        }
      });
  }

  onTabIndexChange(index: number): void {
    this.selectedTabIndex.set(index);
  }

  selfAssignTicket(ticketId: string): void {
    if (!ticketId || this.isAssigning()) {
      return;
    }

    const ticket = this.unassignedTickets().find((item) => item.ticket_id === ticketId);
    const currentUserId = this.currentUserId();
    if (!ticket || !currentUserId || !ticket.assigned_role_id || !this.canSelfAssignUnassignedTickets()) {
      return;
    }

    this.isAssigning.set(true);
    this.assigningTicketId.set(ticketId);
    this.errorMessage.set(null);

    this.ticketManagementService
      .assignTicket(ticketId, {
        assigned_role_id: ticket.assigned_role_id,
        assigned_user_id: currentUserId,
        notes: null
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updatedTicket) => {
          this.successMessage.set(`Ticket ${updatedTicket.ticket_number} asignado correctamente.`);
          this.refresh();
          this.isAssigning.set(false);
          this.assigningTicketId.set(null);
        },
        error: (error: Error) => {
          this.errorMessage.set(error.message);
          this.isAssigning.set(false);
          this.assigningTicketId.set(null);
        }
      });
  }

  listState(context: TicketListContextId): TicketListUiState {
    return this.listUiState()[context];
  }

  onListSearchChanged(context: TicketListContextId, value: string): void {
    this.updateListState(context, { search: value });
  }

  onListStatusChanged(context: TicketListContextId, value: string): void {
    this.updateListState(context, { status: value });
  }

  onListCategoryChanged(context: TicketListContextId, value: string): void {
    this.updateListState(context, { category: value });
  }

  onListSortDirectionChanged(context: TicketListContextId, value: ListingSortDirection): void {
    this.updateListState(context, { sortDirection: value });
  }

  onListViewModeChanged(context: TicketListContextId, value: ListingViewMode): void {
    this.listingViewPreferenceService.setView(this.buildViewPreferenceKey(context), value);
    this.updateListState(context, { viewMode: value });
  }

  private sortTickets(tickets: TicketSummary[]): TicketSummary[] {
    return [...tickets].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  }

  private mapTickets(tickets: readonly TicketSummary[], options?: { forUnassignedTab?: boolean }): TicketTableItem[] {
    return tickets.map((ticket) => ({
      ticketId: ticket.ticket_id,
      ticketNumber: ticket.ticket_number,
      title: ticket.title,
      client: ticket.client_name,
      location: toLocationLabel(ticket.location),
      mapsUrl: buildGoogleMapsUrlFromTicketLocation(ticket.location),
      statusKey: ticket.status,
      status: formatTicketStatus(ticket.status),
      statusTone: toTicketStatusTone(ticket.status),
      priority: formatTicketPriority(ticket.priority),
      priorityTone: toTicketPriorityTone(ticket.priority),
      categoryId: ticket.category_id,
      categoryName: ticket.category_name,
      assignedTo: ticket.assigned_user_display_name || ticket.assigned_role_label || 'Sin asignar',
      assignedUserId: ticket.assigned_user_id,
      assignedRoleId: ticket.assigned_role_id,
      assignedRoleKey: ticket.assigned_role_key,
      collaborators: ticket.collaborators ?? [],
      isExecutiveApprovedClosed: ticket.status === 'CLOSED',
      hasSurveyGenerated: Boolean(ticket.survey_generated_at),
      surveyStatusLabel: ticket.survey_status_label ?? null,
      surveyCompletedAt: ticket.survey_completed_at ?? null,
      selfAssignable: Boolean(options?.forUnassignedTab) && !ticket.assigned_user_id && Boolean(ticket.assigned_role_id),
      createdAtRaw: ticket.created_at,
      createdAt: this.formatDate(ticket.created_at),
      updatedAtRaw: ticket.updated_at,
      updatedAt: this.formatDate(ticket.updated_at)
    }));
  }

  private updateListState(context: TicketListContextId, partial: Partial<TicketListUiState>): void {
    this.listUiState.update((state) => ({
      ...state,
      [context]: {
        ...state[context],
        ...partial
      }
    }));
  }

  private applyTicketListState(rows: readonly TicketTableItem[], context: TicketListContextId): TicketTableItem[] {
    const state = this.listUiState()[context];
    const searchTerm = state.search.trim().toLowerCase();

    const filteredRows = rows.filter((row) => {
      const statusMatches = state.status === 'all' || row.statusKey === state.status;
      if (!statusMatches) {
        return false;
      }

      const categoryMatches = state.category === 'all' || row.categoryId === state.category;
      if (!categoryMatches) {
        return false;
      }

      if (!searchTerm) {
        return true;
      }

      return [row.ticketNumber, row.client, row.title, row.categoryName ?? ''].some((value) => value.toLowerCase().includes(searchTerm));
    });

    const direction = state.sortDirection === 'asc' ? 1 : -1;
    return [...filteredRows].sort((left, right) => left.updatedAtRaw.localeCompare(right.updatedAtRaw) * direction);
  }

  private buildInitialListUiState(context: TicketListContextId): TicketListUiState {
    const fallbackView: ListingViewMode = this.isHandset() ? 'cards' : 'table';

    return {
      search: '',
      status: 'all',
      category: 'all',
      sortDirection: 'desc',
      viewMode: this.listingViewPreferenceService.getView(this.buildViewPreferenceKey(context), fallbackView)
    };
  }

  private buildViewPreferenceKey(context: TicketListContextId): string {
    return `tickets.${context}`;
  }

  private formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // -------------------------------------------------------------------------
  // Survey generation — history tab actions
  // -------------------------------------------------------------------------

  readonly satisfactionFormGenerating = signal<string | null>(null); // ticketId

  readonly canGenerateSatisfactionForms = computed(() => {
    const roles = this.currentRoles();
    return roles.includes('admin') || roles.includes('ejecutivo');
  });

  onGenerateTicketSurvey(ticketId: string): void {
    if (this.satisfactionFormGenerating()) return;
    this.satisfactionFormGenerating.set(ticketId);
    this.errorMessage.set(null);

    this.ticketManagementService
      .generateTicketSurvey(ticketId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.satisfactionFormGenerating.set(null);
          const link = this.buildSurveyLink(response.survey_path, response.public_link_token);
          this.dialog.open(SurveyLinkDialogComponent, {
            autoFocus: false,
            maxWidth: 'calc(100vw - 1.5rem)',
            width: '34rem',
            data: {
              title: 'Encuesta generada correctamente',
              message: 'Compartí este link seguro con el cliente.',
              surveyUrl: link,
              details: 'El link expira y no requiere login del cliente.',
              copyEnabled: true
            }
          });
          this.successMessage.set('Encuesta de satisfacción generada.');
          this.refresh();
        },
        error: (err: Error) => {
          this.satisfactionFormGenerating.set(null);
          this.errorMessage.set(err.message ?? 'Error al generar el formulario.');
        }
      });
  }

  onViewSurvey(ticketId: string): void {
    this.errorMessage.set(null);
    this.ticketManagementService
      .getSatisfactionFormStatus(ticketId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (status) => {
          if (status.has_response) {
            this.ticketManagementService
              .getSatisfactionResponse(ticketId)
              .pipe(takeUntilDestroyed(this.destroyRef))
              .subscribe({
                next: (response) => {
                  this.dialog.open(SurveyLinkDialogComponent, {
                    autoFocus: false,
                    maxWidth: 'calc(100vw - 1.5rem)',
                    width: '42rem',
                    data: {
                      title: 'Respuesta de encuesta',
                      message: 'Esta encuesta ya fue respondida por el cliente.',
                      details: `Enviada: ${this.formatDate(response.submitted_at)}.`,
                      surveyResponse: response,
                      copyEnabled: false
                    }
                  });
                },
                error: (err: Error) => {
                  this.errorMessage.set(err.message ?? 'No se pudo cargar la respuesta de la encuesta.');
                }
              });
            return;
          }

          const statusLabel = status.status_label || 'desconocido';
          const expiresAt = this.formatDate(status.expires_at);
          const details = status.has_response
            ? `Estado: ${statusLabel}. La encuesta ya fue respondida.`
            : `Estado: ${statusLabel}. Expira: ${expiresAt}.`;
          this.dialog.open(SurveyLinkDialogComponent, {
            autoFocus: false,
            maxWidth: 'calc(100vw - 1.5rem)',
            width: '34rem',
            data: {
              title: 'Estado de encuesta',
              message: 'Esta encuesta ya fue generada para el ticket.',
              details,
              copyEnabled: false
            }
          });
        },
        error: (err: Error) => {
          this.errorMessage.set(err.message ?? 'No se pudo consultar el estado de la encuesta.');
        }
      });
  }

  // -------------------------------------------------------------------------
  // Ticket history export
  // -------------------------------------------------------------------------

  readonly exportingTicketId = signal<string | null>(null);

  onExportTicketHistory(ticketId: string): void {
    if (this.exportingTicketId()) return;
    this.exportingTicketId.set(ticketId);
    this.errorMessage.set(null);

    this.ticketManagementService
      .exportTicketHistory(ticketId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          this.exportingTicketId.set(null);
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          const ticket = this.historyTickets().find((t) => t.ticket_id === ticketId);
          const dateSuffix = new Date().toISOString().slice(0, 10).replace(/-/g, '');
          a.download = ticket ? `ticket_${ticket.ticket_number}_${dateSuffix}.zip` : `ticket_historial_${dateSuffix}.zip`;
          a.click();
          URL.revokeObjectURL(url);
        },
        error: (err: Error) => {
          this.exportingTicketId.set(null);
          this.errorMessage.set(err.message ?? 'Error al exportar el historial del ticket.');
        }
      });
  }

  private buildSurveyLink(surveyPath: string | null | undefined, token: string): string {
    const normalizedPath = (surveyPath || '').trim();
    if (normalizedPath) {
      const path = normalizedPath.startsWith('/') ? normalizedPath : `/${normalizedPath}`;
      return `${window.location.origin}${path}`;
    }
    return `${window.location.origin}/survey/${token}`;
  }
}
