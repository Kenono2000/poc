/**
 * Shared Firebase/Firestore bootstrap for the scripts in this folder.
 *
 * Design notes:
 *  - Every value comes from the environment; nothing project-specific is
 *    hardcoded here. `dotenv/config` is imported so a local `.env` file works
 *    for every script that imports this module.
 *  - `getDb()` is lazy: it validates configuration and initializes the
 *    Firebase app exactly once, then returns the cached Firestore instance.
 *  - Emulator support is opt-in via `USE_EMULATOR=true` or by setting
 *    `FIRESTORE_EMULATOR_HOST` (for example when scripts are launched by
 *    `firebase emulators:exec`). The default emulator address is
 *    127.0.0.1:8080.
 */
import 'dotenv/config';
import { getApp, getApps, initializeApp } from 'firebase/app';
import { connectFirestoreEmulator, getFirestore } from 'firebase/firestore';

/**
 * Environment variables that must be present before the app can start.
 * @type {readonly string[]}
 */
export const REQUIRED_ENV_VARS = Object.freeze([
  'FIREBASE_API_KEY',
  'FIREBASE_AUTH_DOMAIN',
  'FIREBASE_PROJECT_ID',
  'FIREBASE_STORAGE_BUCKET',
  'FIREBASE_MESSAGING_SENDER_ID',
  'FIREBASE_APP_ID',
]);

/**
 * Optional environment variables passed through to the Firebase config when set.
 * @type {readonly string[]}
 */
export const OPTIONAL_ENV_VARS = Object.freeze([
  'FIREBASE_DATABASE_URL',
  'FIREBASE_MEASUREMENT_ID',
]);

/** Optional environment variable -> Firebase config key. */
const OPTIONAL_CONFIG_KEYS = Object.freeze({
  FIREBASE_DATABASE_URL: 'databaseURL',
  FIREBASE_MEASUREMENT_ID: 'measurementId',
});

/** Default emulator host when only `USE_EMULATOR=true` is provided. */
export const DEFAULT_EMULATOR_HOST = '127.0.0.1';
/** Default emulator Firestore port. */
export const DEFAULT_EMULATOR_PORT = 8080;

/** @type {import('firebase/firestore').Firestore | null} */
let cachedDb = null;

/**
 * Read an environment variable and normalise it to a trimmed string.
 * @param {NodeJS.ProcessEnv} env
 * @param {string} name
 * @returns {string}
 */
function envValue(env, name) {
  const raw = env[name];
  return typeof raw === 'string' ? raw.trim() : '';
}

/**
 * Build a Firebase config object from environment variables.
 *
 * @param {NodeJS.ProcessEnv} [env=process.env]
 * @returns {{ apiKey: string, authDomain: string, projectId: string, storageBucket: string, messagingSenderId: string, appId: string, databaseURL?: string, measurementId?: string }}
 * @throws {Error} When one or more required variables are missing, naming each one.
 */
export function loadFirebaseConfig(env = process.env) {
  const missing = REQUIRED_ENV_VARS.filter((name) => envValue(env, name) === '');

  if (missing.length > 0) {
    throw new Error(
      `Missing required Firebase environment variable(s): ${missing.join(', ')}. ` +
        'Create a .env file (copy .env.example) or export these variables, then retry.'
    );
  }

  /** @type {Record<string, string>} */
  const config = {
    apiKey: envValue(env, 'FIREBASE_API_KEY'),
    authDomain: envValue(env, 'FIREBASE_AUTH_DOMAIN'),
    projectId: envValue(env, 'FIREBASE_PROJECT_ID'),
    storageBucket: envValue(env, 'FIREBASE_STORAGE_BUCKET'),
    messagingSenderId: envValue(env, 'FIREBASE_MESSAGING_SENDER_ID'),
    appId: envValue(env, 'FIREBASE_APP_ID'),
  };

  for (const [name, configKey] of Object.entries(OPTIONAL_CONFIG_KEYS)) {
    const value = envValue(env, name);
    if (value !== '') {
      config[configKey] = value;
    }
  }

  return /** @type {typeof config & { databaseURL?: string, measurementId?: string }} */ (config);
}

/**
 * Parse a `host:port` value (optionally with a protocol or trailing path).
 *
 * @param {string} raw
 * @param {string} [sourceName='FIRESTORE_EMULATOR_HOST'] Used in error messages.
 * @returns {{ host: string, port: number }}
 */
export function parseEmulatorHost(raw, sourceName = 'FIRESTORE_EMULATOR_HOST') {
  const cleaned = raw
    .trim()
    .replace(/^[a-z][a-z0-9+.-]*:\/\//i, '')
    .replace(/\/.*$/, '');

  if (cleaned === '') {
    throw new Error(
      `${sourceName} is set but empty; expected "host:port" (e.g. 127.0.0.1:8080).`
    );
  }

  let host = cleaned;
  let port = DEFAULT_EMULATOR_PORT;
  const separator = cleaned.lastIndexOf(':');

  if (separator > 0) {
    host = cleaned.slice(0, separator);
    const portText = cleaned.slice(separator + 1);
    port = Number.parseInt(portText, 10);
    if (!/^\d+$/.test(portText) || !Number.isInteger(port) || port < 1 || port > 65535) {
      throw new Error(
        `${sourceName} has an invalid port in "${raw}"; expected "host:port" with port 1-65535.`
      );
    }
  }

  if (host === '') {
    throw new Error(`${sourceName} has an invalid host in "${raw}"; expected "host:port".`);
  }

  return { host, port };
}

/**
 * Decide whether and where to connect a Firestore emulator.
 *
 * Emulator mode is enabled by `USE_EMULATOR=true` (values: 1/true/yes/on) or by
 * defining `FIRESTORE_EMULATOR_HOST=host:port`. When only `USE_EMULATOR` is set
 * the default `127.0.0.1:8080` is used.
 *
 * @param {NodeJS.ProcessEnv} [env=process.env]
 * @returns {{ host: string, port: number } | null} `null` means "use production".
 */
export function resolveEmulator(env = process.env) {
  const useEmulatorFlag = /^(1|true|yes|on)$/i.test(envValue(env, 'USE_EMULATOR'));
  const emulatorHost = envValue(env, 'FIRESTORE_EMULATOR_HOST');

  if (emulatorHost !== '') {
    return parseEmulatorHost(emulatorHost);
  }

  if (useEmulatorFlag) {
    return { host: DEFAULT_EMULATOR_HOST, port: DEFAULT_EMULATOR_PORT };
  }

  return null;
}

/**
 * Get the shared Firestore instance, initializing the Firebase app on first use.
 *
 * @returns {import('firebase/firestore').Firestore}
 * @throws {Error} When required environment variables are missing or the
 *   emulator host value is malformed.
 */
export function getDb() {
  if (cachedDb) {
    return cachedDb;
  }

  const app = getApps().length > 0 ? getApp() : initializeApp(loadFirebaseConfig());
  const db = getFirestore(app);

  const emulator = resolveEmulator();
  if (emulator) {
    connectFirestoreEmulator(db, emulator.host, emulator.port);
    console.log(`[firebase] Using Firestore emulator at ${emulator.host}:${emulator.port}`);
  }

  cachedDb = db;
  return cachedDb;
}
