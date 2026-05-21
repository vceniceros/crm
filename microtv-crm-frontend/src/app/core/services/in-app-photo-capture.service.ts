import { Injectable, OnDestroy, signal } from '@angular/core';

import { crmMediaConfig } from '../config/crm-api.config';

@Injectable()
export class InAppPhotoCaptureService implements OnDestroy {
  readonly isCameraActive = signal(false);
  readonly errorMessage = signal<string | null>(null);

  private stream: MediaStream | null = null;
  private previewEl: HTMLVideoElement | null = null;

  async startPreview(videoEl: HTMLVideoElement): Promise<void> {
    this.stopTracks();
    this.errorMessage.set(null);
    this.previewEl = videoEl;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false
      });
      this.stream = stream;
      videoEl.srcObject = stream;
      await videoEl.play().catch(() => undefined);
      this.isCameraActive.set(true);
    } catch (error) {
      this.stopTracks();
      this.errorMessage.set(this.resolveCameraErrorMessage(error));
      throw error;
    }
  }

  async capturePhoto(): Promise<File> {
    const videoEl = this.previewEl;
    if (!videoEl || !this.stream || videoEl.videoWidth <= 0 || videoEl.videoHeight <= 0) {
      this.errorMessage.set('No se pudo capturar la foto.');
      throw new Error('No se pudo capturar la foto.');
    }

    try {
      const { width, height } = this.resolveTargetSize(videoEl.videoWidth, videoEl.videoHeight);
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;

      const context = canvas.getContext('2d');
      if (!context) {
        throw new Error('No se pudo capturar la foto.');
      }

      context.drawImage(videoEl, 0, 0, width, height);
      const blob = await this.canvasToJpegBlob(canvas);
      return new File([blob], `photo-${Date.now()}.jpg`, { type: 'image/jpeg' });
    } catch (error) {
      this.errorMessage.set('No se pudo capturar la foto.');
      throw error instanceof Error ? error : new Error('No se pudo capturar la foto.');
    } finally {
      this.stopTracks();
    }
  }

  stopTracks(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    if (this.previewEl) {
      this.previewEl.srcObject = null;
    }
    this.previewEl = null;
    this.isCameraActive.set(false);
  }

  ngOnDestroy(): void {
    this.stopTracks();
  }

  private resolveTargetSize(sourceWidth: number, sourceHeight: number): { width: number; height: number } {
    const ratio = Math.min(
      crmMediaConfig.image.maxWidth / sourceWidth,
      crmMediaConfig.image.maxHeight / sourceHeight,
      1
    );

    return {
      width: Math.max(1, Math.round(sourceWidth * ratio)),
      height: Math.max(1, Math.round(sourceHeight * ratio))
    };
  }

  private canvasToJpegBlob(canvas: HTMLCanvasElement): Promise<Blob> {
    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
            return;
          }
          reject(new Error('No se pudo capturar la foto.'));
        },
        'image/jpeg',
        crmMediaConfig.image.quality
      );
    });
  }

  private resolveCameraErrorMessage(error: unknown): string {
    if (error instanceof DOMException) {
      if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
        return 'Permiso de camara denegado.';
      }
      if (error.name === 'NotFoundError' || error.name === 'NotReadableError' || error.name === 'OverconstrainedError') {
        return 'Camara no disponible.';
      }
    }

    return 'No se pudo acceder a la camara.';
  }
}
