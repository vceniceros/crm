type CrmRuntimeConfig = {
  crmApiBaseUrl?: string;
};

declare global {
  var __CRM_RUNTIME_CONFIG__: CrmRuntimeConfig | undefined;
}

function resolveCrmApiBaseUrl(): string {
  const runtimeConfig = globalThis.__CRM_RUNTIME_CONFIG__;
  const runtimeBaseUrl = runtimeConfig?.crmApiBaseUrl?.trim();

  if (runtimeBaseUrl) {
    return runtimeBaseUrl.replace(/\/$/, '');
  }

  return 'http://localhost:8010';
}

export const crmApiConfig = {
  baseUrl: resolveCrmApiBaseUrl()
} as const;