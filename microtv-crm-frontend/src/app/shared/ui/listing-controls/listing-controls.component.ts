import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatNativeDateModule } from '@angular/material/core';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { ListingViewMode } from '../../services/listing-view-preference.service';

export interface ListingStatusOption {
  value: string;
  label: string;
}

export interface ListingCategoryOption {
  value: string;
  label: string;
}

export interface ListingAssetOption {
  value: string;
  label: string;
}

export type ListingSortDirection = 'asc' | 'desc';

@Component({
  selector: 'app-listing-controls',
  standalone: true,
  imports: [MatButtonModule, MatDatepickerModule, MatFormFieldModule, MatIconModule, MatInputModule, MatNativeDateModule, MatSelectModule],
  templateUrl: './listing-controls.component.html',
  styleUrl: './listing-controls.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ListingControlsComponent {
  readonly searchValue = input('');
  readonly searchPlaceholder = input('Buscar');
  readonly selectedStatus = input('all');
  readonly statusOptions = input<readonly ListingStatusOption[]>([{ value: 'all', label: 'Todos los estados' }]);
  readonly selectedCategory = input('all');
  readonly categoryOptions = input<readonly ListingCategoryOption[]>([]);
  readonly selectedAsset = input('');
  readonly assetOptions = input<readonly ListingAssetOption[]>([]);
  readonly showAssetFilter = input(false);
  readonly selectedDate = input<Date | null>(null);
  readonly showDateFilter = input(false);
  readonly viewMode = input<ListingViewMode>('table');
  readonly sortDirection = input<ListingSortDirection>('desc');

  readonly searchChanged = output<string>();
  readonly statusChanged = output<string>();
  readonly categoryChanged = output<string>();
  readonly assetChanged = output<string>();
  readonly dateChanged = output<Date | null>();
  readonly viewModeChanged = output<ListingViewMode>();
  readonly sortDirectionChanged = output<ListingSortDirection>();

  onSearchInput(value: string): void {
    this.searchChanged.emit(value);
  }

  onStatusSelect(value: string): void {
    this.statusChanged.emit(value);
  }

  onCategorySelect(value: string): void {
    this.categoryChanged.emit(value);
  }

  onAssetSelect(value: string): void {
    this.assetChanged.emit(value);
  }

  onDateSelect(value: Date | null): void {
    this.dateChanged.emit(value);
  }

  clearDate(): void {
    this.dateChanged.emit(null);
  }

  setViewMode(mode: ListingViewMode): void {
    this.viewModeChanged.emit(mode);
  }

  toggleSortDirection(): void {
    this.sortDirectionChanged.emit(this.sortDirection() === 'asc' ? 'desc' : 'asc');
  }
}
