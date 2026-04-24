import { AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy, PLATFORM_ID, SimpleChanges, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

import React from 'react';
import { createRoot, Root } from 'react-dom/client';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import { ReportSeriesPoint, formatReportDateTime } from '../report.types';

interface ChartDatum {
  date: string;
  [key: string]: string | number;
}

interface DonutDatum {
  name: string;
  value: number;
}

@Component({
  selector: 'app-recharts-host',
  standalone: true,
  template: '<div class="recharts-host" style="height: 320px; width: 100%;"></div>'
})
export class RechartsHostComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) chartKind: 'area' | 'line' | 'bar' | 'horizontal_bar' | 'donut' | 'pie' = 'bar';
  @Input({ required: true }) series: ReportSeriesPoint[] = [];

  private readonly hostRef = inject(ElementRef<HTMLElement>);
  private readonly platformId = inject(PLATFORM_ID);
  private root: Root | null = null;

  ngAfterViewInit(): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const mount = this.hostRef.nativeElement.firstElementChild as HTMLElement | null;
    if (!mount) {
      return;
    }

    this.root = createRoot(mount);
    this.renderChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.root) {
      return;
    }

    if (changes['series'] || changes['chartKind']) {
      this.renderChart();
    }
  }

  ngOnDestroy(): void {
    this.root?.unmount();
  }

  private renderChart(): void {
    if (!this.root) {
      return;
    }

    const chartData = this.toChartData(this.series);
    const donutData = this.toDonutData(this.series);
    const metricKeys = this.extractMetricKeys(chartData);
    const totalValue = donutData.reduce((accumulator, item) => accumulator + item.value, 0);

    const colorPalette = ['var(--accent-blue)', 'var(--brand-red)', '#3E8EDE', '#2F5D8A', '#7A8CA5'];

    const xAxis = React.createElement(XAxis, { dataKey: 'date', tick: { fill: '#5B6678', fontSize: 12 } });
    const yAxis = React.createElement(YAxis, { tick: { fill: '#5B6678', fontSize: 12 } });
    const grid = React.createElement(CartesianGrid, { strokeDasharray: '3 3', stroke: 'rgba(23, 24, 26, 0.1)' });
    const tooltip = React.createElement(Tooltip, {
      content: (props: unknown) =>
        React.createElement(ChartTooltip, {
          ...(props as object),
          chartKind: this.chartKind,
          totalValue
        }),
      wrapperStyle: { outline: 'none' }
    });
    const legend = React.createElement(Legend, { wrapperStyle: { fontSize: '12px' } });

    let chartNode: React.ReactElement;

    if (this.chartKind === 'donut' || this.chartKind === 'pie') {
      const cells = donutData.map((entry, index) =>
        React.createElement(Cell, {
          key: entry.name,
          fill: colorPalette[index % colorPalette.length]
        })
      );

      chartNode = React.createElement(PieChart, {}, [
        tooltip,
        legend,
        React.createElement(
          Pie,
          {
            data: donutData,
            dataKey: 'value',
            nameKey: 'name',
            innerRadius: this.chartKind === 'donut' ? 68 : 0,
            outerRadius: 108,
            paddingAngle: 2,
            stroke: 'rgba(255,255,255,0.95)',
            strokeWidth: 2
          },
          cells
        )
      ]);
    } else if (this.chartKind === 'area') {
      const areas = metricKeys.map((key, index) =>
        React.createElement(Area, {
          key,
          dataKey: key,
          type: 'monotone',
          stroke: colorPalette[index % colorPalette.length],
          fill: colorPalette[index % colorPalette.length],
          fillOpacity: 0.16,
          strokeWidth: 2
        })
      );

      chartNode = React.createElement(AreaChart, { data: chartData }, [grid, xAxis, yAxis, tooltip, legend, ...areas]);
    } else if (this.chartKind === 'line') {
      const lines = metricKeys.map((key, index) =>
        React.createElement(Line, {
          key,
          dataKey: key,
          type: 'monotone',
          stroke: colorPalette[index % colorPalette.length],
          strokeWidth: 2,
          dot: false
        })
      );

      chartNode = React.createElement(LineChart, { data: chartData }, [grid, xAxis, yAxis, tooltip, legend, ...lines]);
    } else if (this.chartKind === 'horizontal_bar') {
      const horizontalXAxis = React.createElement(XAxis, { type: 'number', tick: { fill: '#5B6678', fontSize: 12 } });
      const horizontalYAxis = React.createElement(YAxis, {
        type: 'category',
        dataKey: 'date',
        width: 140,
        tick: { fill: '#5B6678', fontSize: 12 }
      });
      const bars = metricKeys.map((key, index) =>
        React.createElement(Bar, {
          key,
          dataKey: key,
          fill: colorPalette[index % colorPalette.length],
          radius: [0, 6, 6, 0]
        })
      );

      chartNode = React.createElement(BarChart, { data: chartData, layout: 'vertical', margin: { left: 24, right: 12 } }, [
        grid,
        horizontalXAxis,
        horizontalYAxis,
        tooltip,
        legend,
        ...bars
      ]);
    } else {
      const bars = metricKeys.map((key, index) =>
        React.createElement(Bar, {
          key,
          dataKey: key,
          fill: colorPalette[index % colorPalette.length],
          radius: [6, 6, 0, 0]
        })
      );

      chartNode = React.createElement(BarChart, { data: chartData }, [grid, xAxis, yAxis, tooltip, legend, ...bars]);
    }

    const responsive = React.createElement(ResponsiveContainer as unknown as React.ElementType, { width: '100%', height: 320 }, chartNode);
    this.root.render(responsive);
  }

  private toChartData(points: ReportSeriesPoint[]): ChartDatum[] {
    const byDate = new Map<string, ChartDatum>();

    points.forEach((point) => {
      const existing = byDate.get(point.date) ?? { date: point.date };
      existing[point.label] = Number(point.value ?? 0);
      if (point.meta?.['minimum_stock'] !== undefined) {
        existing[`${point.label}__minimum_stock`] = Number(point.meta['minimum_stock']);
      }
      byDate.set(point.date, existing);
    });

    return Array.from(byDate.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }

  private toDonutData(points: ReportSeriesPoint[]): DonutDatum[] {
    return points.map((point) => ({
      name: point.label,
      value: Number(point.value ?? 0)
    }));
  }

  private extractMetricKeys(data: ChartDatum[]): string[] {
    const first = data[0];
    if (!first) {
      return ['value'];
    }

    const keys = Object.keys(first).filter((key) => key !== 'date' && !key.endsWith('__minimum_stock'));
    return keys.length > 0 ? keys : ['value'];
  }
}

function ChartTooltip({
  active,
  payload,
  label,
  chartKind,
  totalValue
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number | string; payload?: Record<string, unknown>; dataKey?: string; color?: string }>;
  label?: string;
  chartKind: 'area' | 'line' | 'bar' | 'horizontal_bar' | 'donut' | 'pie';
  totalValue: number;
}): React.ReactElement | null {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const containerStyle: React.CSSProperties = {
    background: '#fff',
    border: '1px solid rgba(23,24,26,0.12)',
    borderRadius: '12px',
    boxShadow: '0 8px 20px rgba(9,19,38,0.12)',
    padding: '0.65rem 0.8rem',
    fontSize: '12px',
    color: '#17181A'
  };

  if (chartKind === 'donut' || chartKind === 'pie') {
    const item = payload[0];
    const value = Number(item.value ?? 0);
    const percentage = totalValue > 0 ? Math.round((value / totalValue) * 100) : 0;
    return React.createElement('div', { style: containerStyle }, [
      React.createElement('div', { key: 'label', style: { fontWeight: 700, marginBottom: '0.25rem' } }, `Estado/Prioridad: ${item.name ?? ''}`),
      React.createElement('div', { key: 'value' }, `Cantidad: ${value}`),
      React.createElement('div', { key: 'percentage' }, `Porcentaje: ${percentage}%`)
    ]);
  }

  const rows = payload.map((item, index) => {
    const minimumStock = item.dataKey ? item.payload?.[`${item.dataKey}__minimum_stock`] : undefined;
    return React.createElement('div', { key: `${item.name ?? index}`, style: { marginTop: index === 0 ? 0 : '0.35rem' } }, [
      React.createElement(
        'div',
        {
          key: 'name',
          style: { color: item.color ?? '#17181A', fontWeight: 700 }
        },
        `${item.name ?? 'Serie'}: ${item.value ?? 0}`
      ),
      minimumStock !== undefined
        ? React.createElement('div', { key: 'min' }, `Mínimo: ${minimumStock}`)
        : null
    ]);
  });

  return React.createElement('div', { style: containerStyle }, [
    React.createElement('div', { key: 'header', style: { fontWeight: 700, marginBottom: '0.35rem' } }, formatTooltipLabel(label ?? '')),
    ...rows
  ]);
}

function formatTooltipLabel(label: string): string {
  if (!label) {
    return '';
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(label)) {
    return formatReportDateTime(`${label}T00:00:00Z`).slice(0, 10);
  }

  return label;
}
