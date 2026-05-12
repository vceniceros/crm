import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface ImageViewerDialogData {
  imageUrl: string;
  altText: string;
}

@Component({
  selector: 'app-image-viewer-dialog',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatIconModule],
  templateUrl: './image-viewer-dialog.component.html',
  styleUrl: './image-viewer-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ImageViewerDialogComponent {
  readonly data = inject<ImageViewerDialogData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<ImageViewerDialogComponent>);

  close(): void {
    this.dialogRef.close();
  }
}
