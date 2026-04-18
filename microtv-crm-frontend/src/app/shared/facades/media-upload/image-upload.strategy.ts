import { MediaUploadContext, MediaUploadStrategy } from './media-upload.types';
import { hasAnyExtension, validateFile } from './media-upload.utils';

const IMAGE_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];
const IMAGE_MAX_BYTES = 8 * 1024 * 1024;

export class ImageUploadStrategy implements MediaUploadStrategy {
  readonly kind = 'image' as const;
  readonly acceptPattern = 'image/jpeg,image/png,image/webp';

  supports(file: File): boolean {
    return IMAGE_MIME_TYPES.has(file.type) || hasAnyExtension(file.name, IMAGE_EXTENSIONS);
  }

  validate(file: File): void {
    validateFile(file, IMAGE_MAX_BYTES, 'La imagen supera el límite de 8 MB.', 'Formato de imagen no soportado.', (candidate) => this.supports(candidate));
  }
}
