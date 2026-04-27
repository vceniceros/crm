export type CrmRuntimeSeedLoginAccount = {
  label: string;
  email: string;
  password: string;
  roleLabel: string;
};

type CrmRuntimeConfig = {
  crmApiBaseUrl?: string;
  devMode?: boolean | string;
  devLoginAccounts?: unknown;
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

export const crmApiConfig = {
  baseUrl: resolveCrmApiBaseUrl(runtimeConfig)
} as const;