import { CommonModule } from '@angular/common';
import { Component, input } from '@angular/core';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-upload-progress',
  standalone: true,
  imports: [CommonModule, MatProgressBarModule, MatProgressSpinnerModule],
  templateUrl: './upload-progress.component.html',
  styleUrl: './upload-progress.component.scss'
})
export class UploadProgressComponent {
  readonly progress = input<number | null>(null);
  readonly status = input<string | null>(null);
}
