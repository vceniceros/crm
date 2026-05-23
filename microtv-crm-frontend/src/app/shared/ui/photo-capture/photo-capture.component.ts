import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, OnDestroy, output, viewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { InAppPhotoCaptureService } from '../../../core/services/in-app-photo-capture.service';

@Component({
  selector: 'app-photo-capture',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule],
  providers: [InAppPhotoCaptureService],
  templateUrl: './photo-capture.component.html',
  styleUrl: './photo-capture.component.scss'
})
export class PhotoCaptureComponent implements AfterViewInit, OnDestroy {
  private readonly preview = viewChild<ElementRef<HTMLVideoElement>>('preview');
  readonly photoCaptured = output<File>();
  readonly cancelled = output<void>();

  constructor(readonly photoCapture: InAppPhotoCaptureService) {}

  ngAfterViewInit(): void {
    void this.startPreview();
  }

  async capture(): Promise<void> {
    try {
      const file = await this.photoCapture.capturePhoto();
      this.photoCaptured.emit(file);
    } catch {
      // The service exposes a localized inline error message.
    }
  }

  cancel(): void {
    this.photoCapture.stopTracks();
    this.cancelled.emit();
  }

  ngOnDestroy(): void {
    this.photoCapture.stopTracks();
  }

  private async startPreview(): Promise<void> {
    const preview = this.preview()?.nativeElement;
    if (!preview) {
      return;
    }

    try {
      await this.photoCapture.startPreview(preview);
      await this.capture();
    } catch {
      // The service exposes a localized inline error message.
    }
  }
}
