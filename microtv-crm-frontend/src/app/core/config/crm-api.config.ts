export type CrmRuntimeSeedLoginAccount = {
  label: string;
  email: string;
  password: string;
  roleLabel: string;
};

type CrmRuntimeConfig = {
  crmApiBaseUrl?: string;
  vapidPublicKey?: string;
  devMode?: boolean | string;
  devLoginAccounts?: unknown;
  mediaPublicUrl?: string;
  imageMaxWidth?: number | string;
  imageMaxHeight?: number | string;
  imageQuality?: number | string;
  imageMaxUploadMb?: number | string;
  imageTargetFormat?: string;
  videoMaxSizeMb?: number | string;
  videoMaxDurationSeconds?: number | string;
  videoMaxUploadMb?: number | string;
  mapStyleUrl?: string;
  mapDefaultLat?: number | string;
  mapDefaultLon?: number | string;
  mapDefaultZoom?: number | string;
};

declare global {
  var __CRM_RUNTIME_CONFIG__: CrmRuntimeConfig | undefined;
}

const runtimeConfig = globalThis.__CRM_RUNTIME_CONFIG__;

function resolveCrmApiBaseUrl(config: CrmRuntimeConfig | undefined): string {
  const runtimeBaseUrl = config?.crmApiBaseUrl?.trim();

  if (runtimeBaseUrl) {
    return runtimeBaseUrl.replace(/\/$/, '');
  }

  return 'http://localhost:8010';
}

function resolveDevMode(rawValue: boolean | string | undefined): boolean {
  if (typeof rawValue === 'boolean') {
    return rawValue;
  }

  if (typeof rawValue === 'string') {
    return rawValue.trim().toLowerCase() === 'true';
  }

  return false;
}

function resolveNumber(rawValue: number | string | undefined, fallback: number): number {
  if (typeof rawValue === 'number' && Number.isFinite(rawValue)) {
    return rawValue;
  }

  if (typeof rawValue === 'string') {
    const parsed = Number(rawValue.trim());
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function resolveMediaPublicUrl(rawValue: string | undefined): string {
  const normalized = (rawValue ?? '/media').trim();
  if (!normalized) {
    return '/media';
  }

  const withSlash = normalized.startsWith('/') ? normalized : `/${normalized}`;
  return withSlash.replace(/\/+$/, '') || '/media';
}

function resolveString(rawValue: string | undefined, fallback = ''): string {
  if (typeof rawValue !== 'string') {
    return fallback;
  }

  const normalized = rawValue.trim();
  return normalized || fallback;
}

function resolveMapStyleUrl(rawValue: string | undefined): string {
  const normalized = resolveString(rawValue);
  if (!normalized) {
    return '';
  }

  if (/^https?:\/\//i.test(normalized) || normalized.startsWith('/')) {
    return normalized;
  }

  return `https://${normalized.replace(/^\/+/, '')}`;
}

function resolveImageTargetFormat(rawValue: string | undefined): 'jpeg' | 'png' | 'webp' | 'avif' {
  const normalized = (rawValue ?? 'webp').trim().toLowerCase();
  if (normalized === 'jpeg' || normalized === 'jpg') {
    return 'jpeg';
  }
  if (normalized === 'png') {
    return 'png';
  }
  if (normalized === 'avif') {
    return 'avif';
  }
  return 'webp';
}

function resolveDevLoginAccounts(rawValue: unknown): CrmRuntimeSeedLoginAccount[] {
  if (!Array.isArray(rawValue)) {
    return [];
  }

  return rawValue
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }

      const candidate = item as Record<string, unknown>;
      const label = typeof candidate['label'] === 'string' ? candidate['label'].trim() : '';
      const email = typeof candidate['email'] === 'string' ? candidate['email'].trim() : '';
      const password = typeof candidate['password'] === 'string' ? candidate['password'] : '';
      const roleLabel = typeof candidate['roleLabel'] === 'string' ? candidate['roleLabel'].trim() : '';

      if (!label || !email || !password || !roleLabel) {
        return null;
      }

      return { label, email, password, roleLabel };
    })
    .filter((item): item is CrmRuntimeSeedLoginAccount => item !== null);
}

const devMode = resolveDevMode(runtimeConfig?.devMode);

export const crmRuntimeConfig = {
  devMode,
  devLoginAccounts: devMode ? resolveDevLoginAccounts(runtimeConfig?.devLoginAccounts) : []
} as const;

export const crmMediaConfig = {
  publicUrl: resolveMediaPublicUrl(runtimeConfig?.mediaPublicUrl),
  image: {
    maxWidth: Math.max(64, Math.round(resolveNumber(runtimeConfig?.imageMaxWidth, 1280))),
    maxHeight: Math.max(64, Math.round(resolveNumber(runtimeConfig?.imageMaxHeight, 720))),
    quality: Math.min(1, Math.max(0.1, resolveNumber(runtimeConfig?.imageQuality, 0.82))),
    maxUploadMb: Math.max(1, Math.round(resolveNumber(runtimeConfig?.imageMaxUploadMb, 10))),
    targetFormat: resolveImageTargetFormat(runtimeConfig?.imageTargetFormat)
  },
  video: {
    maxSizeMb: Math.max(1, Math.round(resolveNumber(runtimeConfig?.videoMaxUploadMb ?? runtimeConfig?.videoMaxSizeMb, 80))),
    maxUploadMb: Math.max(1, Math.round(resolveNumber(runtimeConfig?.videoMaxUploadMb ?? runtimeConfig?.videoMaxSizeMb, 80))),
    maxDurationSeconds: Math.max(1, Math.round(resolveNumber(runtimeConfig?.videoMaxDurationSeconds, 60)))
  }
} as const;

export const crmApiConfig = {
  baseUrl: resolveCrmApiBaseUrl(runtimeConfig)
} as const;

export const crmPushConfig = {
  vapidPublicKey: runtimeConfig?.vapidPublicKey?.trim() ?? ''
} as const;

export const crmMapConfig = {
  styleUrl: resolveMapStyleUrl(runtimeConfig?.mapStyleUrl),
  defaultLat: Math.min(90, Math.max(-90, resolveNumber(runtimeConfig?.mapDefaultLat, -34.6037))),
  defaultLon: Math.min(180, Math.max(-180, resolveNumber(runtimeConfig?.mapDefaultLon, -58.3816))),
  defaultZoom: Math.min(20, Math.max(1, resolveNumber(runtimeConfig?.mapDefaultZoom, 12)))
} as const;
