import { MediaUploadContext, MediaUploadStrategy } from './media-upload.types';
import { hasAnyExtension, validateFile } from './media-upload.utils';
import { mediaVideoMaxBytes } from '../../../core/utils/media-upload-optimization';

const VIDEO_MIME_TYPES = new Set(['video/mp4', 'video/webm', 'video/quicktime']);
const VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov'];

export class VideoUploadStrategy implements MediaUploadStrategy {
  readonly kind = 'video' as const;
  readonly acceptPattern = 'video/mp4,video/webm,video/quicktime';

  supports(file: File): boolean {
    return VIDEO_MIME_TYPES.has(file.type) || hasAnyExtension(file.name, VIDEO_EXTENSIONS);
  }

  validate(file: File): void {
    const maxBytes = mediaVideoMaxBytes();
    const maxMb = Math.max(1, Math.round(maxBytes / (1024 * 1024)));
    validateFile(
      file,
      maxBytes,
      `El video supera el límite de ${maxMb} MB.`,
      'Formato de video no soportado.',
      (candidate) => this.supports(candidate)
    );
  }
}
