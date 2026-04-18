import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const projectRoot = resolve(import.meta.dirname, '..');
const envPath = resolve(projectRoot, '.env');
const envExamplePath = resolve(projectRoot, '.env.example');
const runtimeConfigPath = resolve(projectRoot, 'public', 'runtime-config.js');

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

const envValues = {
  ...parseEnvFile(envExamplePath),
  ...parseEnvFile(envPath),
};

const crmApiBaseUrl = (envValues.CRM_API_BASE_URL || 'http://localhost:8010').replace(/\/$/, '');
const runtimeConfigContents = `globalThis.__CRM_RUNTIME_CONFIG__ = ${JSON.stringify({ crmApiBaseUrl }, null, 2)};\n`;

mkdirSync(dirname(runtimeConfigPath), { recursive: true });
writeFileSync(runtimeConfigPath, runtimeConfigContents, 'utf8');

console.log(`Runtime config generated at ${runtimeConfigPath}`);