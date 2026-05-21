import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, output, viewChild, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { crmMediaConfig } from '../../../core/config/crm-api.config';
import { VideoRecorderService } from '../../../core/services/video-recorder.service';

@Component({
  selector: 'app-video-recorder',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule],
  providers: [VideoRecorderService],
  templateUrl: './video-recorder.component.html',
  styleUrl: './video-recorder.component.scss'
})
export class VideoRecorderComponent implements OnDestroy {
  private readonly preview = viewChild<ElementRef<HTMLVideoElement>>('preview');
  readonly recordingComplete = output<Blob>();
  readonly cancelled = output<void>();
  readonly errorMessage = signal<string | null>(null);
  readonly maxSeconds = crmMediaConfig.video.maxDurationSeconds;

  constructor(readonly recorder: VideoRecorderService) {}

  start(): void {
    const preview = this.preview()?.nativeElement;
    if (!preview) {
      return;
    }
    this.errorMessage.set(null);
    this.recorder.startRecording(preview).subscribe({
      next: (blob) => this.recordingComplete.emit(blob),
      error: (error: Error) => this.errorMessage.set(error.message || 'No se pudo grabar el video.')
    });
  }

  stop(): void {
    this.recorder.stopRecording();
  }

  cancel(): void {
    this.recorder.cancel();
    this.cancelled.emit();
  }

  remainingSeconds(): number {
    return Math.max(0, this.maxSeconds - this.recorder.elapsedSeconds());
  }

  ngOnDestroy(): void {
    this.recorder.stopRecording();
  }
}
