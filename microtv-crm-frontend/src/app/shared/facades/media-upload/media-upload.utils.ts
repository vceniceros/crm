export function validateFile(file: File, typeMessage: string, supports: (file: File) => boolean): void {
  if (!supports(file)) {
    throw new Error(typeMessage);
  }
}

export function hasAnyExtension(fileName: string, extensions: readonly string[]): boolean {
  const normalized = fileName.toLowerCase();
  return extensions.some((extension) => normalized.endsWith(extension));
}
