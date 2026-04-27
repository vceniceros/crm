export function validateFile(file: File, maxBytes: number, sizeMessage: string, typeMessage: string, supports: (file: File) => boolean): void {
  if (!supports(file)) {
    throw new Error(typeMessage);
  }

  if (file.size > maxBytes) {
    throw new Error(sizeMessage);
  }
}

export function hasAnyExtension(fileName: string, extensions: readonly string[]): boolean {
  const normalized = fileName.toLowerCase();
  return extensions.some((extension) => normalized.endsWith(extension));
}
