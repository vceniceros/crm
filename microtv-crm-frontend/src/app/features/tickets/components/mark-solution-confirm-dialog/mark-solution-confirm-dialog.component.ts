import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogTitle } from '@angular/material/dialog';

@Component({
  selector: 'app-mark-solution-confirm-dialog',
  standalone: true,
  imports: [MatButtonModule, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogTitle],
  templateUrl: './mark-solution-confirm-dialog.component.html',
  styleUrl: './mark-solution-confirm-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MarkSolutionConfirmDialogComponent {}
