import { inject, Injectable } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import { LocationPickerDialogData, LocationSelectionResult } from '../../core/models/location.model';
import { LocationPickerDialogComponent } from '../ui/location-picker-dialog/location-picker-dialog.component';

@Injectable({ providedIn: 'root' })
export class LocationPickerService {
  private readonly dialog = inject(MatDialog);

  open(data: LocationPickerDialogData = {}) {
    return this.dialog
      .open<LocationPickerDialogComponent, LocationPickerDialogData, LocationSelectionResult>(LocationPickerDialogComponent, {
        autoFocus: false,
        maxWidth: 'calc(100vw - 1rem)',
        width: '52rem',
        data
      })
      .afterClosed();
  }
}