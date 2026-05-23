import { Injectable, OnDestroy, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { crmMediaConfig } from '../config/crm-api.config';

export class UnsupportedRecordingFormatError extends Error {
  constructor() {
    super('Este navegador no soporta un formato de grabacion compatible.');
  }
}

@Injectable()
export class VideoRecorderService implements OnDestroy {
  readonly isRecording = signal(false);
  readonly elapsedSeconds = signal(0);

  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: BlobPart[] = [];
  private elapsedTimer: ReturnType<typeof setInterval> | null = null;
  private stopTimer: ReturnType<typeof setTimeout> | null = null;
  private emitCancelled = false;

  startRecording(previewEl: HTMLVideoElement): Observable<Blob> {
    return new Observable<Blob>((subscriber) => {
      this.cancel();
      const mimeType = this.resolveMimeType();
      if (!mimeType) {
        subscriber.error(new UnsupportedRecordingFormatError());
        return undefined;
      }

      navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: true
      })
        .then((stream) => {
          this.stream = stream;
          previewEl.srcObject = stream;
          this.chunks = [];
          this.emitCancelled = false;
          this.recorder = new MediaRecorder(stream, { mimeType });
          this.recorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              this.chunks.push(event.data);
            }
          };
          this.recorder.onerror = () => {
            this.cleanupTracks();
            subscriber.error(new Error('No se pudo grabar el video.'));
          };
          this.recorder.onstop = () => {
            const blob = new Blob(this.chunks, { type: mimeType });
            this.cleanupTracks();
            if (!this.emitCancelled) {
              subscriber.next(blob);
              subscriber.complete();
            }
          };
          this.recorder.start(250);
          this.isRecording.set(true);
          this.elapsedSeconds.set(0);
          this.elapsedTimer = setInterval(() => this.elapsedSeconds.update((value) => value + 1), 1000);
          this.stopTimer = setTimeout(() => this.stopRecording(), crmMediaConfig.video.maxDurationSeconds * 1000);
        })
        .catch((error) => {
          this.cleanupTracks();
          subscriber.error(error instanceof Error ? error : new Error('No se pudo acceder a la camara.'));
        });

      return () => this.cancel();
    });
  }

  stopRecording(): void {
    this.emitCancelled = false;
    if (this.recorder && this.recorder.state !== 'inactive') {
      this.recorder.stop();
      return;
    }
    this.cleanupTracks();
  }

  cancel(): void {
    this.emitCancelled = true;
    if (this.recorder && this.recorder.state !== 'inactive') {
      this.recorder.stop();
      return;
    }
    this.cleanupTracks();
  }

  ngOnDestroy(): void {
    this.cancel();
  }

  private resolveMimeType(): string | null {
    const candidates = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm',
      'video/mp4'
    ];
    return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) ?? null;
  }

  private cleanupTracks(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.isRecording.set(false);
    if (this.elapsedTimer) {
      clearInterval(this.elapsedTimer);
      this.elapsedTimer = null;
    }
    if (this.stopTimer) {
      clearTimeout(this.stopTimer);
      this.stopTimer = null;
    }
  }
}
