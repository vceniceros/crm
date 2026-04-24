import { NgClass } from '@angular/common';
import { Component, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';

import { RechartsHostComponent } from './components/recharts-host.component';
import {
  formatReportActionType,
  formatReportDateTime,
  formatReportPriority,
  formatReportStatus,
  PRIORITY_OPTIONS,
  REPORT_CARDS,
  REPORT_COLUMNS,
  STATUS_OPTIONS,
  ReportCardDefinition,
  ReportColumn,
  ReportFilterCatalogs,
  ReportId,
  ReportOption,
  ReportPayload,
  ReportRequestFilters,
  ReportSeriesPoint
} from './report.types';
import { ReportsService } from './reports.service';

@Component({
  selector: 'app-report-detail',
  standalone: true,
  imports: [FormsModule, NgClass, RechartsHostComponent, RouterLink],
  templateUrl: './report-detail.component.html',
  styleUrl: './report-detail.component.scss'
})
export class ReportDetailComponent implements OnDestroy {
  readonly destroy$ = new Subject<void>();

  report: ReportCardDefinition | null = null;
  reportId: ReportId | null = null;
  loading = false;
  errorMessage: string | null = null;
  payload: ReportPayload | null = null;
  filtersLoading = false;
  filtersErrorMessage: string | null = null;

  quickDate: 'week' | 'month' | 'last-month' | 'custom' = 'month';
  dateFrom = '';
  dateTo = '';
  filterUser = '';
  filterTechnician = '';
  filterClient = '';
  filterStatus = '';
  filterPriority = '';
  filterCategory = '';
  filterWarehouse = '';
  filterRequester = '';
  filterApprover = '';
  filterActionType = '';
  onlyCritical = true;

  tableSearch = '';
  page = 1;
  pageSize = 10;
  filterCatalogs: ReportFilterCatalogs = {
    users: [],
    clients: [],
    categories: [],
    warehouses: [],
    technicians: [],
    actionTypes: []
  };

  readonly statusOptions = STATUS_OPTIONS;
  readonly priorityOptions = PRIORITY_OPTIONS;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly reportsService: ReportsService
  ) {
    this.route.paramMap.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      const reportId = params.get('reportId') as ReportId | null;
      this.reportId = reportId;
      this.report = REPORT_CARDS.find((card) => card.id === reportId) ?? null;

      this.applyDefaultFilters();

      if (!this.report || !this.report.enabled) {
        this.payload = null;
        this.errorMessage = 'Este reporte todavía no está disponible en el MVP.';
        return;
      }

      this.loadFilterCatalogs(reportId);
      this.loadReport();
    });
  }

  get columns(): ReportColumn[] {
    if (!this.reportId) {
      return [];
    }

    return REPORT_COLUMNS[this.reportId] ?? [];
  }

  get series(): ReportSeriesPoint[] {
    return this.payload?.series ?? [];
  }

  get pagedRows(): Record<string, unknown>[] {
    const from = (this.page - 1) * this.pageSize;
    return this.filteredRows.slice(from, from + this.pageSize);
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
  }

  get filteredRows(): Record<string, unknown>[] {
    const rows = this.payload?.rows ?? [];
    const term = this.tableSearch.trim().toLowerCase();
    if (!term) {
      return rows;
    }

    return rows.filter((row) =>
      Object.values(row).some((value) => {
        if (value === null || value === undefined) {
          return false;
        }

        return String(value).toLowerCase().includes(term);
      })
    );
  }

  get chartHint(): string | null {
    if (this.reportId === 'tickets-by-client') {
      return 'Visualización limitada al top 10 de clientes. La tabla mantiene el detalle completo.';
    }

    if (this.reportId === 'stock-critical') {
      return 'Top 10 productos críticos graficados. La tabla mantiene el detalle completo.';
    }

    if (this.reportId === 'tasks-by-technician') {
      return 'Visualización limitada al top 10 de técnicos con mayor carga.';
    }

    return null;
  }

  get chartEmptyMessage(): string {
    if (this.reportId === 'stock-critical') {
      return 'No hay historial real de movimientos suficiente para reconstruir la evolución del stock. Se mantiene el estado actual en la tabla.';
    }

    return 'No hay datos para el gráfico en el rango seleccionado.';
  }

  get statusSelectOptions(): ReportOption[] {
    return this.statusOptions.map((status) => ({ id: status, label: formatReportStatus(status) }));
  }

  get prioritySelectOptions(): ReportOption[] {
    return this.priorityOptions.map((priority) => ({ id: priority, label: formatReportPriority(priority) }));
  }

  updateReport(): void {
    this.page = 1;
    this.loadReport();
  }

  applyQuickRange(mode: 'week' | 'month' | 'last-month' | 'custom'): void {
    this.quickDate = mode;
    const now = new Date();

    if (mode === 'custom') {
      return;
    }

    if (mode === 'week') {
      const first = new Date(now);
      first.setDate(now.getDate() - 6);
      this.dateFrom = this.toDateInput(first);
      this.dateTo = this.toDateInput(now);
      return;
    }

    if (mode === 'month') {
      const first = new Date(now.getFullYear(), now.getMonth(), 1);
      this.dateFrom = this.toDateInput(first);
      this.dateTo = this.toDateInput(now);
      return;
    }

    const firstLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const endLastMonth = new Date(now.getFullYear(), now.getMonth(), 0);
    this.dateFrom = this.toDateInput(firstLastMonth);
    this.dateTo = this.toDateInput(endLastMonth);
  }

  nextPage(): void {
    if (this.page < this.totalPages) {
      this.page += 1;
    }
  }

  previousPage(): void {
    if (this.page > 1) {
      this.page -= 1;
    }
  }

  exportCsv(): void {
    if (!this.columns.length || !this.filteredRows.length) {
      return;
    }

    const separator = ';';
    const header = this.columns.map((column) => this.escapeCsv(column.label)).join(separator);
    const body = this.filteredRows.map((row) => this.columns.map((column) => this.escapeCsv(this.formatCell(row, column.key))).join(separator));
    const csv = [header, ...body].join('\n');

    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${this.reportId ?? 'report'}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadReport(): void {
    if (!this.reportId) {
      return;
    }

    this.loading = true;
    this.errorMessage = null;

    this.reportsService
      .loadReport(this.reportId, this.buildFilters(this.reportId))
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (payload) => {
          this.payload = payload;
          this.loading = false;
        },
        error: (error: unknown) => {
          this.errorMessage = error instanceof Error ? error.message : 'No se pudo cargar el reporte.';
          this.payload = null;
          this.loading = false;
        }
      });
  }

  private loadFilterCatalogs(reportId: ReportId | null): void {
    if (!reportId) {
      this.filterCatalogs = this.emptyCatalogs();
      return;
    }

    this.filtersLoading = true;
    this.filtersErrorMessage = null;
    this.filterCatalogs = this.emptyCatalogs();

    this.reportsService
      .loadFilterCatalogs(reportId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (catalogs) => {
          this.filterCatalogs = catalogs;
          this.filtersLoading = false;
        },
        error: (error: unknown) => {
          this.filtersErrorMessage = error instanceof Error ? error.message : 'No se pudieron cargar las opciones de filtros.';
          this.filtersLoading = false;
        }
      });
  }

  private buildFilters(reportId: ReportId): ReportRequestFilters {
    const filters: ReportRequestFilters = {
      date_from: this.dateFrom || undefined,
      date_to: this.dateTo || undefined
    };

    if (reportId === 'tickets-by-status') {
      filters.group_by = 'status';
      filters.status = this.filterStatus || undefined;
    }

    if (reportId === 'tickets-by-priority') {
      filters.group_by = 'priority';
      filters.priority = this.filterPriority || undefined;
      filters.status = this.filterStatus || undefined;
    }

    if (reportId === 'tickets-by-client') {
      filters.group_by = 'client';
      filters.client_id = this.filterClient || undefined;
      filters.status = this.filterStatus || undefined;
    }

    if (reportId === 'tasks-by-status') {
      filters.group_by = 'status';
      filters.status = this.filterStatus || undefined;
      filters.technician_id = this.filterTechnician || undefined;
    }

    if (reportId === 'tasks-by-technician') {
      filters.group_by = 'technician';
      filters.technician_id = this.filterTechnician || undefined;
      filters.status = this.filterStatus || undefined;
    }

    if (reportId === 'stock-critical') {
      filters.category = this.filterCategory || undefined;
      filters.warehouse_id = this.filterWarehouse || undefined;
      filters.only_critical = this.onlyCritical;
    }

    if (reportId === 'deposit-requests-status') {
      filters.status = this.filterStatus || undefined;
      filters.requester = this.filterRequester || undefined;
      filters.approver = this.filterApprover || undefined;
    }

    if (reportId === 'activity-by-user') {
      filters.user_id = this.filterUser || undefined;
      filters.action_type = this.filterActionType || undefined;
    }

    return filters;
  }

  private applyDefaultFilters(): void {
    this.page = 1;
    this.tableSearch = '';
    this.filterUser = '';
    this.filterTechnician = '';
    this.filterClient = '';
    this.filterStatus = '';
    this.filterPriority = '';
    this.filterCategory = '';
    this.filterWarehouse = '';
    this.filterRequester = '';
    this.filterApprover = '';
    this.filterActionType = '';
    this.onlyCritical = true;
    this.applyQuickRange('month');
  }

  private emptyCatalogs(): ReportFilterCatalogs {
    return {
      users: [],
      clients: [],
      categories: [],
      warehouses: [],
      technicians: [],
      actionTypes: []
    };
  }

  formatCell(row: Record<string, unknown>, columnKey: string): string {
    const value = row[columnKey];

    if (columnKey === 'action') {
      return formatReportActionType(typeof value === 'string' ? value : null);
    }

    if (columnKey === 'status') {
      return formatReportStatus(typeof value === 'string' ? value : null);
    }

    if (columnKey === 'priority') {
      return formatReportPriority(typeof value === 'string' ? value : null);
    }

    if (['created_at', 'closed_at', 'due_at', 'updated_at', 'dispatched_at', 'date'].includes(columnKey)) {
      return formatReportDateTime(value);
    }

    return value === null || value === undefined ? '' : String(value);
  }

  private toDateInput(value: Date): string {
    return value.toISOString().slice(0, 10);
  }

  private escapeCsv(value: unknown): string {
    const normalized = value === null || value === undefined ? '' : String(value);
    const escaped = normalized.replaceAll('"', '""');
    return `"${escaped}"`;
  }
}
