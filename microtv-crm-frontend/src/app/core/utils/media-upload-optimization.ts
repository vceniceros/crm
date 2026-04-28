import { crmMediaConfig } from '../config/crm-api.config';
import type { Options as ImageCompressionOptions } from 'browser-image-compression';

type SupportedTargetFormat = 'jpeg' | 'png' | 'webp' | 'avif';

const TARGET_FORMAT_TO_MIME: Record<SupportedTargetFormat, string> = {
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
  avif: 'image/avif'
};

const MIME_TO_EXTENSION: Record<string, string> = {
  'image/jpeg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp',
  'image/avif': '.avif'
};

let imageCompressionLoader: Promise<typeof import('browser-image-compression')> | null = null;

export function mediaVideoMaxBytes(): number {
  return Math.max(1, Math.round(crmMediaConfig.video.maxSizeMb)) * 1024 * 1024;
}

export function isImageFile(file: File): boolean {
  return file.type.toLowerCase().startsWith('image/');
}

export function isVideoFile(file: File): boolean {
  return file.type.toLowerCase().startsWith('video/');
}

export async function optimizeImageForUpload(file: File): Promise<File> {
  if (!isImageFile(file)) {
    return file;
  }

  const imageCompression = (await loadImageCompression()).default;

  const targetMime = resolveTargetMime(crmMediaConfig.image.targetFormat);
  const targetMimeSupported = targetMime ? browserSupportsImageMimeType(targetMime) : false;

  const baseOptions: ImageCompressionOptions = {
    maxWidthOrHeight: Math.max(crmMediaConfig.image.maxWidth, crmMediaConfig.image.maxHeight),
    initialQuality: crmMediaConfig.image.quality,
    useWebWorker: true,
    preserveExif: false,
  };

  try {
    if (targetMimeSupported && targetMime) {
      const converted = await imageCompression(file, {
        ...baseOptions,
        fileType: targetMime,
      });
      return normalizeCompressedFile(converted, file.name, targetMime);
    }

    const compressed = await imageCompression(file, baseOptions);
    return normalizeCompressedFile(compressed, file.name, compressed.type || file.type);
  } catch {
    // Fallback seguro: nunca bloquear upload por un fallo de compresion/conversion.
    return file;
  }
}

export async function optimizeImagesForUpload(files: readonly File[]): Promise<File[]> {
  const output: File[] = [];
  for (const file of files) {
    if (isImageFile(file)) {
      output.push(await optimizeImageForUpload(file));
      continue;
    }
    output.push(file);
  }
  return output;
}

function resolveTargetMime(format: SupportedTargetFormat): string {
  if (format === 'avif') {
    // El backend actual valida JPEG/PNG/WEBP; AVIF se degrada a WEBP para compatibilidad.
    return TARGET_FORMAT_TO_MIME.webp;
  }
  return TARGET_FORMAT_TO_MIME[format];
}

function browserSupportsImageMimeType(mimeType: string): boolean {
  if (typeof document === 'undefined') {
    return false;
  }

  try {
    const canvas = document.createElement('canvas');
    const dataUri = canvas.toDataURL(mimeType);
    return dataUri.startsWith(`data:${mimeType}`);
  } catch {
    return false;
  }
}

function normalizeCompressedFile(blob: Blob, originalName: string, fallbackMimeType: string): File {
  const normalizedMimeType = blob.type || fallbackMimeType || 'application/octet-stream';
  const safeFileName = buildSafeFileName(originalName, normalizedMimeType);

  return new File([blob], safeFileName, {
    type: normalizedMimeType,
    lastModified: Date.now(),
  });
}

function buildSafeFileName(originalName: string, mimeType: string): string {
  const rawBaseName = originalName.replace(/\.[^.]+$/, '');
  const safeBaseName = (rawBaseName || 'upload')
    .replace(/[^a-zA-Z0-9_-]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 80) || 'upload';

  const extension = MIME_TO_EXTENSION[mimeType] || inferExtensionFromName(originalName) || '.bin';
  return `${safeBaseName}${extension}`;
}

function inferExtensionFromName(fileName: string): string | null {
  const index = fileName.lastIndexOf('.');
  if (index < 0) {
    return null;
  }

  const extension = fileName.slice(index).toLowerCase();
  if (!extension || extension.length > 10) {
    return null;
  }

  return extension;
}

async function loadImageCompression(): Promise<typeof import('browser-image-compression')> {
  if (imageCompressionLoader === null) {
    imageCompressionLoader = import('browser-image-compression');
  }

  return imageCompressionLoader;
}
