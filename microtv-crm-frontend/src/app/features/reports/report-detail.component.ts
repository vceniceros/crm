import { NgClass } from '@angular/common';
import { Component, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';

import { AuthSessionService } from '../../core/services/auth-session.service';
import { RechartsHostComponent } from './components/recharts-host.component';
import {
  fallbackReadableLabel,
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
  private readonly route = inject(ActivatedRoute);
  private readonly reportsService = inject(ReportsService);
  private readonly authSessionService = inject(AuthSessionService);

  report: ReportCardDefinition | null = null;
  reportId: ReportId | null = null;
  loading = false;
  errorMessage: string | null = null;
  payload: ReportPayload | null = null;
  filtersLoading = false;
  filtersErrorMessage: string | null = null;
  exportingPdf = false;
  pdfGeneratedAtLabel = '';

  quickDate: 'today' | 'week' | 'month' | 'last-month' | 'year' | 'custom' = 'month';
  dateFrom = '';
  dateTo = '';
  filterUser = '';
  filterTechnician = '';
  filterClient = '';
  filterStatus = '';
  filterPriority = '';
  filterCategory = '';
  filterLocation = '';
  filterRole = '';
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
    locations: [],
    roles: [],
    warehouses: [],
    technicians: [],
    actionTypes: []
  };

  readonly statusOptions = STATUS_OPTIONS;
  readonly priorityOptions = PRIORITY_OPTIONS;

  constructor() {
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

  get displayedRows(): Record<string, unknown>[] {
    return this.exportingPdf ? this.filteredRows : this.pagedRows;
  }

  get currentUserLabel(): string {
    const session = this.authSessionService.sessionSnapshot();
    return session?.user.display_name?.trim() || session?.user.email || 'Usuario CRM';
  }

  get appliedFilterSummary(): string[] {
    const items: string[] = [];
    if (this.dateFrom || this.dateTo) {
      items.push(`Rango: ${this.dateFrom || 'inicio'} a ${this.dateTo || 'hoy'}`);
    }
    if (this.filterStatus) {
      items.push(`Estado: ${formatReportStatus(this.filterStatus)}`);
    }
    if (this.filterPriority) {
      items.push(`Prioridad: ${formatReportPriority(this.filterPriority)}`);
    }
    if (this.filterClient) {
      items.push(`Cliente: ${this.labelForOption(this.filterCatalogs.clients, this.filterClient)}`);
    }
    if (this.filterCategory) {
      items.push(`Categoría: ${this.labelForOption(this.filterCatalogs.categories, this.filterCategory)}`);
    }
    if (this.filterLocation) {
      items.push(`Ubicación: ${this.labelForOption(this.filterCatalogs.locations, this.filterLocation)}`);
    }
    if (this.filterTechnician) {
      items.push(`Técnico: ${this.labelForOption(this.filterCatalogs.technicians, this.filterTechnician)}`);
    }
    if (this.filterUser) {
      items.push(`Usuario: ${this.labelForOption(this.filterCatalogs.users, this.filterUser)}`);
    }
    if (this.filterRole) {
      items.push(`Rol: ${this.labelForOption(this.filterCatalogs.roles, this.filterRole)}`);
    }
    if (this.filterRequester) {
      items.push(`Solicitante: ${this.labelForOption(this.filterCatalogs.users, this.filterRequester)}`);
    }
    if (this.filterApprover) {
      items.push(`Aprobador: ${this.labelForOption(this.filterCatalogs.users, this.filterApprover)}`);
    }
    if (this.filterActionType) {
      items.push(`Acción: ${this.labelForOption(this.filterCatalogs.actionTypes, this.filterActionType)}`);
    }
    return items;
  }

  get showsStatusFilter(): boolean {
    return this.reportId === 'tickets-by-priority'
      || this.reportId === 'tickets-by-status'
      || this.reportId === 'tickets-by-client'
      || this.reportId === 'deposit-requests-status'
      || this.reportId === 'tasks-by-status'
      || this.reportId === 'tasks-by-technician';
  }

  get showsPriorityFilter(): boolean {
    return this.reportId === 'tickets-by-priority'
      || this.reportId === 'my-tickets'
      || this.reportId === 'my-tasks'
      || this.reportId === 'executive-performance'
      || this.reportId === 'executive-by-category'
      || this.reportId === 'executive-by-client';
  }

  get showsClientFilter(): boolean {
    return this.reportId === 'tickets-by-client'
      || this.reportId === 'my-tickets'
      || this.reportId === 'my-tasks'
      || this.reportId === 'executive-performance'
      || this.reportId === 'executive-by-category'
      || this.reportId === 'executive-by-priority'
      || this.reportId === 'executive-by-client';
  }

  get showsCategoryFilter(): boolean {
    return this.reportId === 'my-tickets'
      || this.reportId === 'my-tasks'
      || this.reportId === 'executive-performance'
      || this.reportId === 'executive-by-priority'
      || this.reportId === 'executive-by-client'
      || this.reportId === 'stock-critical';
  }

  get showsLocationFilter(): boolean {
    return this.reportId === 'my-tickets';
  }

  get showsTechnicianFilter(): boolean {
    return this.reportId === 'tasks-by-status' || this.reportId === 'tasks-by-technician';
  }

  get showsUserFilter(): boolean {
    return this.reportId === 'activity-by-user'
      || this.reportId === 'executive-performance'
      || this.reportId === 'executive-by-category'
      || this.reportId === 'executive-by-priority'
      || this.reportId === 'executive-by-client';
  }

  get showsRoleFilter(): boolean {
    return this.reportId === 'executive-performance'
      || this.reportId === 'executive-by-category'
      || this.reportId === 'executive-by-priority'
      || this.reportId === 'executive-by-client';
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

  applyQuickRange(mode: 'today' | 'week' | 'month' | 'last-month' | 'year' | 'custom'): void {
    this.quickDate = mode;
    const now = new Date();

    if (mode === 'custom') {
      return;
    }

    if (mode === 'today') {
      this.dateFrom = this.toDateInput(now);
      this.dateTo = this.toDateInput(now);
      return;
    }

    if (mode === 'week') {
      const first = new Date(now);
      const weekDay = (now.getDay() + 6) % 7;
      first.setDate(now.getDate() - weekDay);
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

    if (mode === 'year') {
      const first = new Date(now.getFullYear(), 0, 1);
      const last = new Date(now.getFullYear(), 11, 31);
      this.dateFrom = this.toDateInput(first);
      this.dateTo = this.toDateInput(last);
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

  async exportPdf(): Promise<void> {
    if (!this.reportId || !this.report || !this.payload || this.exportingPdf || typeof window === 'undefined') {
      return;
    }

    this.exportingPdf = true;
    this.pdfGeneratedAtLabel = new Date().toLocaleString('es-AR');

    try {
      const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import('html2canvas'), import('jspdf')]);
      await this.waitForRender();

      const pdf = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
      const sections = [
        document.getElementById('report-export-header'),
        document.getElementById('report-export-kpis'),
        document.getElementById('report-export-chart'),
        document.getElementById('report-export-table')
      ].filter((section): section is HTMLElement => section instanceof HTMLElement);

      let isFirstPage = true;
      for (const section of sections) {
        const canvas = await html2canvas(section, {
          backgroundColor: '#ffffff',
          scale: 2,
          useCORS: true
        });
        isFirstPage = this.appendCanvasToPdf(pdf, canvas, isFirstPage);
      }

      pdf.save(`${this.reportId}_${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (error) {
      this.errorMessage = error instanceof Error ? error.message : 'No se pudo generar el PDF del reporte.';
    } finally {
      this.exportingPdf = false;
    }
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

    if (reportId === 'my-tickets') {
      filters.group_by = 'status';
      filters.priority = this.filterPriority || undefined;
      filters.client_id = this.filterClient || undefined;
      filters.category_id = this.filterCategory || undefined;
      filters.location_id = this.filterLocation || undefined;
    }

    if (reportId === 'my-tasks') {
      filters.group_by = 'time-series';
      filters.priority = this.filterPriority || undefined;
      filters.client_id = this.filterClient || undefined;
      filters.category_id = this.filterCategory || undefined;
    }

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

    if (reportId === 'executive-performance') {
      filters.group_by = 'user';
      filters.user_id = this.filterUser || undefined;
      filters.role_key = this.filterRole || undefined;
      filters.client_id = this.filterClient || undefined;
      filters.category_id = this.filterCategory || undefined;
      filters.priority = this.filterPriority || undefined;
    }

    if (reportId === 'executive-by-category') {
      filters.group_by = 'category';
      filters.user_id = this.filterUser || undefined;
      filters.role_key = this.filterRole || undefined;
      filters.client_id = this.filterClient || undefined;
      filters.priority = this.filterPriority || undefined;
    }

    if (reportId === 'executive-by-priority') {
      filters.group_by = 'priority';
      filters.user_id = this.filterUser || undefined;
      filters.role_key = this.filterRole || undefined;
      filters.client_id = this.filterClient || undefined;
      filters.category_id = this.filterCategory || undefined;
    }

    if (reportId === 'executive-by-client') {
      filters.group_by = 'client';
      filters.user_id = this.filterUser || undefined;
      filters.role_key = this.filterRole || undefined;
      filters.category_id = this.filterCategory || undefined;
      filters.priority = this.filterPriority || undefined;
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
    this.filterLocation = '';
    this.filterRole = '';
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
      locations: [],
      roles: [],
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

    if (this.isNumericMetric(columnKey) && typeof value === 'number') {
      return value.toFixed(2);
    }

    if (columnKey === 'primary_role' && typeof value === 'string') {
      return fallbackReadableLabel(value);
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

  private labelForOption(options: ReportOption[], id: string): string {
    return options.find((option) => option.id === id)?.label ?? id;
  }

  private isNumericMetric(columnKey: string): boolean {
    return columnKey.includes('hours') || columnKey.includes('rate') || columnKey.includes('comments_per_ticket');
  }

  private async waitForRender(): Promise<void> {
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  }

  private appendCanvasToPdf(pdf: import('jspdf').jsPDF, canvas: HTMLCanvasElement, isFirstPage: boolean): boolean {
    const margin = 20;
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const usableWidth = pageWidth - margin * 2;
    const usableHeight = pageHeight - margin * 2;
    const scale = usableWidth / canvas.width;
    const sliceHeight = Math.max(1, Math.floor(usableHeight / scale));

    let offsetY = 0;
    let firstPage = isFirstPage;
    while (offsetY < canvas.height) {
      if (!firstPage) {
        pdf.addPage();
      }

      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = Math.min(sliceHeight, canvas.height - offsetY);
      const context = pageCanvas.getContext('2d');
      if (context) {
        context.drawImage(
          canvas,
          0,
          offsetY,
          canvas.width,
          pageCanvas.height,
          0,
          0,
          canvas.width,
          pageCanvas.height
        );
      }

      const renderedHeight = pageCanvas.height * scale;
      pdf.addImage(pageCanvas.toDataURL('image/png'), 'PNG', margin, margin, usableWidth, renderedHeight, undefined, 'FAST');

      offsetY += pageCanvas.height;
      firstPage = false;
    }

    return firstPage;
  }
}
