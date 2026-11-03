/**
 * Shared helpers for the firestore-export scripts.
 *
 * Firestore returns rich value types (Timestamp, GeoPoint, DocumentReference,
 * Bytes, ...). JSON cannot represent them, so export scripts run documents
 * through `convertTimestamps` first.
 */

/** Default timeout for a Firestore server operation (milliseconds). */
export const DEFAULT_OPERATION_TIMEOUT_MS = 30_000;

/**
 * A Firestore Timestamp (or anything timestamp-like) exposes `toDate()`.
 * @param {unknown} value
 * @returns {boolean}
 */
export function isTimestampLike(value) {
  return value !== null && typeof value === 'object' && typeof value.toDate === 'function';
}

/**
 * Convert a timestamp-like value to an ISO-8601 string.
 * @param {{ toDate: () => Date }} value
 * @returns {string | null} ISO string, or `null` when the date is invalid.
 */
function timestampToIso(value) {
  const date = value.toDate();
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

/**
 * Deeply convert Firestore Timestamps to ISO-8601 strings.
 *
 * Recursion notes:
 *  - Walks the whole document tree: plain objects/maps and arrays are visited
 *    at any depth, so nested maps and arrays of arrays are handled.
 *  - The input is never mutated. A converted copy is returned for objects and
 *    arrays (where practical); primitives, `null` and `undefined` are returned
 *    as-is. That makes it safe to call on a document spread such as
 *    `{ id: doc.id, ...doc.data() }` without touching Firestore's cache.
 *  - No cycle guard is included: Firestore document data is always acyclic and
 *    JSON-serialisable. Passing an arbitrary cyclic object would recurse until
 *    the stack overflows.
 *  - Objects that are not Timestamp-like are treated as maps; this includes
 *    `Date` instances (converted to ISO) and Firestore-only types such as
 *    GeoPoint/DocumentReference, which are copied field-by-field.
 *
 * @param {unknown} value Value to convert.
 * @returns {unknown} Converted copy (objects/arrays) or the original primitive.
 */
export function convertTimestamps(value) {
  // Null-safe: JSON.stringify would turn undefined into a dropped key anyway,
  // but callers may inspect the return value, so pass both through untouched.
  if (value === null || value === undefined) {
    return value;
  }

  if (typeof value !== 'object') {
    return value;
  }

  if (isTimestampLike(value)) {
    return timestampToIso(/** @type {{ toDate: () => Date }} */ (value));
  }

  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value.toISOString();
  }

  if (Array.isArray(value)) {
    return value.map((item) => convertTimestamps(item));
  }

  /** @type {Record<string, unknown>} */
  const converted = {};
  for (const [key, item] of Object.entries(value)) {
    converted[key] = convertTimestamps(item);
  }
  return converted;
}

/**
 * Reject when a promise does not settle within `timeoutMs`.
 *
 * The Firestore web SDK queues writes while the backend is unreachable, so
 * `writeBatch().commit()` (and `addDoc`) can stay pending indefinitely instead
 * of rejecting. A timeout keeps the command-line scripts from hanging forever
 * and turns an unreachable backend into a clear, non-zero exit.
 *
 * @template T
 * @param {Promise<T>} promise Operation to await.
 * @param {number} timeoutMs Maximum wait in milliseconds.
 * @param {string} description Used in the timeout error message.
 * @returns {Promise<T>} The operation result, or a rejected promise on timeout.
 */
export function withTimeout(promise, timeoutMs, description) {
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let timer;

  const timeout = new Promise((_resolve, reject) => {
    timer = setTimeout(() => {
      reject(
        new Error(
          `${description} timed out after ${timeoutMs}ms. Is the Firestore emulator running ` +
            'and is the Firebase project configuration correct?'
        )
      );
    }, timeoutMs);
  });

  return Promise.race([promise, timeout]).finally(() => {
    if (timer) {
      clearTimeout(timer);
    }
  });
}

/**
 * Read a per-operation timeout (in milliseconds) from the environment.
 *
 * @param {NodeJS.ProcessEnv} env Environment to read from (normally process.env).
 * @param {string} [envName='FIRESTORE_WRITE_TIMEOUT_MS'] Variable name.
 * @param {number} [defaultMs=DEFAULT_OPERATION_TIMEOUT_MS] Fallback value.
 * @returns {number} Timeout in milliseconds.
 * @throws {Error} When the variable is set to something other than a positive number.
 */
export function resolveTimeoutMs(env, envName = 'FIRESTORE_WRITE_TIMEOUT_MS', defaultMs = DEFAULT_OPERATION_TIMEOUT_MS) {
  const raw = env[envName];
  if (raw === undefined || raw.trim() === '') {
    return defaultMs;
  }
  const timeoutMs = Number(raw);
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    throw new Error(
      `${envName} must be a positive number of milliseconds, received "${raw}".`
    );
  }
  return timeoutMs;
}
