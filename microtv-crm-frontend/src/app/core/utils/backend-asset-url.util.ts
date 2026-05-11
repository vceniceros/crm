const DEFAULT_REWRITABLE_SAME_ORIGIN_PATHS: readonly string[] = ['/media/', '/avatars/', '/images/'];

interface ResolveBackendAssetUrlOptions {
  rewritableSameOriginPaths?: readonly string[];
}

export function resolveBackendAssetUrl(
  rawUrl: string | null | undefined,
  baseUrl: string,
  options: ResolveBackendAssetUrlOptions = {}
): string | null {
  const normalized = rawUrl?.trim();
  if (!normalized) {
    return null;
  }

  if (/^(blob:|data:)/i.test(normalized)) {
    return normalized;
  }

  if (/^https?:/i.test(normalized)) {
    return rewriteSameOriginAbsoluteAssetUrl(normalized, baseUrl, options);
  }

  const backendOrigin = resolveBackendOrigin(baseUrl);
  const slashNormalized = normalized.replace(/\\/g, '/');
  const lowerPath = slashNormalized.toLowerCase();
  const publicMarker = '/public/';
  const publicIndex = lowerPath.lastIndexOf(publicMarker);
  const normalizedPath = stripBackendPathPrefix(
    (publicIndex >= 0 ? slashNormalized.slice(publicIndex + publicMarker.length) : slashNormalized)
      .replace(/^\/?public\//i, '')
      .replace(/^\/+/, ''),
    backendOrigin
  );

  if (!normalizedPath || /^[a-z]:\//i.test(normalizedPath)) {
    return null;
  }

  if (!normalizedPath.includes('/') && !normalizedPath.includes('.')) {
    return null;
  }

  return `${backendOrigin}/${normalizedPath}`;
}

export function resolveBackendOrigin(baseUrl: string): string {
  const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
  const normalizedBaseUrl = (baseUrl || '').trim();

  if (!normalizedBaseUrl) {
    return browserOrigin;
  }

  try {
    const parsed = new URL(normalizedBaseUrl, browserOrigin);
    const normalizedPath = parsed.pathname.replace(/\/+$/, '');
    return normalizedPath ? `${parsed.origin}${normalizedPath}` : parsed.origin;
  } catch {
    return browserOrigin;
  }
}

function rewriteSameOriginAbsoluteAssetUrl(
  rawUrl: string,
  baseUrl: string,
  options: ResolveBackendAssetUrlOptions
): string {
  const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';

  try {
    const backend = new URL(resolveBackendOrigin(baseUrl), browserOrigin);
    const absolute = new URL(rawUrl);

    if (absolute.origin !== backend.origin) {
      return rawUrl;
    }

    const backendPath = backend.pathname.replace(/\/+$/, '');
    if (!backendPath || backendPath === '/') {
      return rawUrl;
    }

    if (absolute.pathname.startsWith(`${backendPath}/`)) {
      return absolute.toString();
    }

    const rewritablePaths = options.rewritableSameOriginPaths ?? DEFAULT_REWRITABLE_SAME_ORIGIN_PATHS;
    if (rewritablePaths.some((prefix) => absolute.pathname.startsWith(prefix))) {
      absolute.pathname = `${backendPath}${absolute.pathname}`;
      return absolute.toString();
    }

    return rawUrl;
  } catch {
    return rawUrl;
  }
}

function stripBackendPathPrefix(normalizedPath: string, backendOrigin: string): string {
  const backendPathPrefix = backendPathPrefixFromOrigin(backendOrigin);
  if (!backendPathPrefix) {
    return normalizedPath;
  }

  const lowerPath = normalizedPath.toLowerCase();
  const lowerPrefix = `${backendPathPrefix.toLowerCase()}/`;

  if (lowerPath === backendPathPrefix.toLowerCase()) {
    return '';
  }

  if (lowerPath.startsWith(lowerPrefix)) {
    return normalizedPath.slice(backendPathPrefix.length + 1);
  }

  return normalizedPath;
}

function backendPathPrefixFromOrigin(backendOrigin: string): string {
  const browserOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';

  try {
    const parsed = new URL(backendOrigin, browserOrigin);
    return parsed.pathname.replace(/^\/+|\/+$/g, '');
  } catch {
    return '';
  }
}
