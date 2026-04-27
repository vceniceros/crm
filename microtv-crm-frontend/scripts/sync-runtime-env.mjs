import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const projectRoot = resolve(import.meta.dirname, '..');
const envPath = resolve(projectRoot, '.env');
const envExamplePath = resolve(projectRoot, '.env.example');
const runtimeConfigPath = resolve(projectRoot, 'public', 'runtime-config.js');

const defaultDevLoginAccounts = [
  {
    label: 'Admin MicroTV',
    email: 'admin@ycc.com.ar',
    password: 'b5249a47fc73f4b5618d7b77b9fbe86f1278a96b139d7ee18ba34be181a3809f',
    roleLabel: 'platform_admin -> admin'
  },
  {
    label: 'Operador YCC Brothers',
    email: 'operador.crm@yccbrothers.com',
    password: 'Passw0rd!',
    roleLabel: 'company_operator -> deposito'
  },
  {
    label: 'Auxiliar Deposito YCC',
    email: 'deposito.aux@yccbrothers.com',
    password: 'Passw0rd!',
    roleLabel: 'company_operator -> deposito'
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
    roleLabel: 'company_operator + rol local tecnico_campo -> tecnico'
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

const runtimeConfigContents = `globalThis.__CRM_RUNTIME_CONFIG__ = ${JSON.stringify(
  { crmApiBaseUrl, devMode, devLoginAccounts },
  null,
  2
)};\n`;

mkdirSync(dirname(runtimeConfigPath), { recursive: true });
writeFileSync(runtimeConfigPath, runtimeConfigContents, 'utf8');

console.log(`Runtime config generated at ${runtimeConfigPath}`);