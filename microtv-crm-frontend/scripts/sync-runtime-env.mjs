import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const projectRoot = resolve(import.meta.dirname, '..');
const envPath = resolve(projectRoot, '.env');
const envExamplePath = resolve(projectRoot, '.env.example');
const runtimeConfigPath = resolve(projectRoot, 'public', 'runtime-config.js');

const defaultDevLoginAccounts = [
  {
    label: 'Admin MicroTV',
    email: 'admin@ycc.local',
    password: 'changeme-secure-password',
    roleLabel: 'admin -> admin'
  },
  {
    label: 'Operador YCC Brothers',
    email: 'operador.crm@yccbrothers.com',
    password: 'Passw0rd!',
    roleLabel: 'operador_deposito -> deposito'
  },
  {
    label: 'Auxiliar Deposito YCC',
    email: 'deposito.aux@yccbrothers.com',
    password: 'Passw0rd!',
    roleLabel: 'operador_deposito -> deposito'
  },
  {
    label: 'Ejecutivo YCC Brothers',
    email: 'ejecutivo.crm@yccbrothers.com',
    password: 'Passw0rd!',
    roleLabel: 'ejecutivo -> ejecutivo'
  },
  {
    label: 'Tecnico de Campo YCC',
    email: 'tecnico.campo@yccbrothers.com',
    password: 'Passw0rd!',
    roleLabel: 'tecnico_campo -> tecnico'
  }
];

function parseEnvFile(filePath) {
  const values = {};

  try {
    const raw = readFileSync(filePath, 'utf8');
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) {
        continue;
      }

      const separatorIndex = trimmed.indexOf('=');
      if (separatorIndex === -1) {
        continue;
      }

      const key = trimmed.slice(0, separatorIndex).trim();
      const value = trimmed.slice(separatorIndex + 1).trim().replace(/^(['"])(.*)\1$/, '$2');
      if (key) {
        values[key] = value;
      }
    }
  } catch {
    return values;
  }

  return values;
}

function parseBoolean(value, fallback = false) {
  if (typeof value !== 'string') {
    return fallback;
  }

  const normalized = value.trim().toLowerCase();
  if (normalized === 'true') {
    return true;
  }
  if (normalized === 'false') {
    return false;
  }
  return fallback;
}

function parseNumber(value, fallback) {
  if (typeof value !== 'string') {
    return fallback;
  }

  const parsed = Number(value.trim());
  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return parsed;
}

function parseMediaPublicUrl(value) {
  if (typeof value !== 'string') {
    return '/media';
  }

  const normalized = value.trim();
  if (!normalized) {
    return '/media';
  }

  const withSlash = normalized.startsWith('/') ? normalized : `/${normalized}`;
  return withSlash.replace(/\/+$/, '') || '/media';
}

function parseDevLoginAccounts(rawValue) {
  if (typeof rawValue !== 'string' || !rawValue.trim()) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue);
    if (!Array.isArray(parsed)) {
      return null;
    }

    const normalized = parsed
      .map((item) => {
        if (!item || typeof item !== 'object') {
          return null;
        }

        const candidate = item;
        const label = typeof candidate.label === 'string' ? candidate.label.trim() : '';
        const email = typeof candidate.email === 'string' ? candidate.email.trim() : '';
        const password = typeof candidate.password === 'string' ? candidate.password : '';
        const roleLabel = typeof candidate.roleLabel === 'string' ? candidate.roleLabel.trim() : '';

        if (!label || !email || !password || !roleLabel) {
          return null;
        }

        return { label, email, password, roleLabel };
      })
      .filter((item) => item !== null);

    return normalized;
  } catch {
    return null;
  }
}

const envValues = {
  ...parseEnvFile(envExamplePath),
  ...parseEnvFile(envPath),
};

const crmApiBaseUrl = (envValues.CRM_API_BASE_URL || 'http://localhost:8010').replace(/\/$/, '');
const devMode = parseBoolean(envValues.DEV_MODE, false);
const devLoginAccounts = devMode
  ? (parseDevLoginAccounts(envValues.DEV_LOGIN_ACCOUNTS_JSON) ?? defaultDevLoginAccounts)
  : [];
const mediaPublicUrl = parseMediaPublicUrl(envValues.CRM_MEDIA_PUBLIC_URL);
const imageMaxWidth = parseNumber(envValues.IMAGE_MAX_WIDTH, 1280);
const imageMaxHeight = parseNumber(envValues.IMAGE_MAX_HEIGHT, 1280);
const imageQuality = parseNumber(envValues.IMAGE_QUALITY, 0.75);
const imageTargetFormat = (envValues.IMAGE_TARGET_FORMAT || 'webp').trim().toLowerCase() || 'webp';
const videoMaxSizeMb = parseNumber(envValues.VIDEO_MAX_SIZE_MB, 50);
const vapidPublicKey = (envValues.VAPID_PUBLIC_KEY || '').trim();
const mapStyleUrl = (envValues.NEXT_PUBLIC_MAP_STYLE_URL || '').trim();
const mapDefaultLat = parseNumber(envValues.NEXT_PUBLIC_MAP_DEFAULT_LAT, -34.6037);
const mapDefaultLon = parseNumber(envValues.NEXT_PUBLIC_MAP_DEFAULT_LON, -58.3816);
const mapDefaultZoom = parseNumber(envValues.NEXT_PUBLIC_MAP_DEFAULT_ZOOM, 12);

const runtimeConfigContents = `globalThis.__CRM_RUNTIME_CONFIG__ = ${JSON.stringify(
  {
    crmApiBaseUrl,
    devMode,
    devLoginAccounts,
    mediaPublicUrl,
    imageMaxWidth,
    imageMaxHeight,
    imageQuality,
    imageTargetFormat,
    videoMaxSizeMb,
    vapidPublicKey,
    mapStyleUrl,
    mapDefaultLat,
    mapDefaultLon,
    mapDefaultZoom,
  },
  null,
  2
)};\n`;

mkdirSync(dirname(runtimeConfigPath), { recursive: true });
writeFileSync(runtimeConfigPath, runtimeConfigContents, 'utf8');

console.log(`Runtime config generated at ${runtimeConfigPath}`);
