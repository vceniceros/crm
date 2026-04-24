import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { ListingViewMode } from '../../services/listing-view-preference.service';

export interface ListingStatusOption {
  value: string;
  label: string;
}

export type ListingSortDirection = 'asc' | 'desc';

@Component({
  selector: 'app-listing-controls',
  standalone: true,
  imports: [MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  templateUrl: './listing-controls.component.html',
  styleUrl: './listing-controls.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ListingControlsComponent {
  readonly searchValue = input('');
  readonly searchPlaceholder = input('Buscar');
  readonly selectedStatus = input('all');
  readonly statusOptions = input<readonly ListingStatusOption[]>([{ value: 'all', label: 'Todos los estados' }]);
  readonly viewMode = input<ListingViewMode>('table');
  readonly sortDirection = input<ListingSortDirection>('desc');

  readonly searchChanged = output<string>();
  readonly statusChanged = output<string>();
  readonly viewModeChanged = output<ListingViewMode>();
  readonly sortDirectionChanged = output<ListingSortDirection>();

  onSearchInput(value: string): void {
    this.searchChanged.emit(value);
  }

  onStatusSelect(value: string): void {
    this.statusChanged.emit(value);
  }

  setViewMode(mode: ListingViewMode): void {
    this.viewModeChanged.emit(mode);
  }

  toggleSortDirection(): void {
    this.sortDirectionChanged.emit(this.sortDirection() === 'asc' ? 'desc' : 'asc');
  }
}
