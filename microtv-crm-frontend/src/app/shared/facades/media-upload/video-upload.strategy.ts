import { MediaUploadContext, MediaUploadStrategy } from './media-upload.types';
import { hasAnyExtension, validateFile } from './media-upload.utils';

const VIDEO_MIME_TYPES = new Set(['video/mp4', 'video/webm', 'video/quicktime']);
const VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov'];

export class VideoUploadStrategy implements MediaUploadStrategy {
  readonly kind = 'video' as const;
  readonly acceptPattern = 'video/mp4,video/webm,video/quicktime';

  supports(file: File): boolean {
    const baseMime = file.type.split(';')[0].toLowerCase();
    return VIDEO_MIME_TYPES.has(baseMime) || hasAnyExtension(file.name, VIDEO_EXTENSIONS);
  }

  validate(file: File): void {
    validateFile(file, 'Formato de video no soportado.', (candidate) => this.supports(candidate));
  }
}
