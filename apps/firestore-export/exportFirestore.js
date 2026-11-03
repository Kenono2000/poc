#!/usr/bin/env node
/**
 * Export one or more Firestore collections into a single JSON file.
 *
 * Usage:
 *   node exportFirestore.js [--out <file>] [collection ...]
 *   node exportFirestore.js --help
 *
 * Defaults: writes `exported.json`, exports the `users` collection.
 * Each collection is paged (500 documents per read) up to 10,000 documents and
 * every Firestore Timestamp is converted to an ISO-8601 string (see utils.js).
 * Reads use the "server" source, so an unreachable backend fails instead of
 * silently exporting stale/empty cached data. The combined JSON contains
 * per-collection counts and the file's own size metadata.
 *
 * Exit codes:
 *   0 - success
 *   1 - configuration, connection, or write failure
 *   2 - invalid command-line usage
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { getApp } from 'firebase/app';
import {
  collection,
  documentId,
  getDocsFromServer,
  limit,
  orderBy,
  query,
  startAfter,
} from 'firebase/firestore';
// Importing firebaseSetup.js also loads `.env` (via dotenv) before getDb() runs.
import { getDb } from './firebaseSetup.js';
import { convertTimestamps } from './utils.js';

const DEFAULT_OUT_FILE = 'exported.json';
const DEFAULT_COLLECTIONS = ['users'];
const MAX_DOCS_PER_COLLECTION = 10_000;
const PAGE_SIZE = 500;

const EXIT_OK = 0;
const EXIT_FAILURE = 1;
const EXIT_USAGE = 2;

/** Thrown for invalid command-line arguments; mapped to exit code 2. */
class UsageError extends Error {}

const USAGE = `Usage: node exportFirestore.js [--out <file>] [collection ...]

Export Firestore collections to a single combined JSON file.

Options:
  --out <file>   Output file path (default: ${DEFAULT_OUT_FILE}).
                 Accepts both "--out file.json" and "--out=file.json".
  -h, --help     Show this help message.

Arguments:
  collection ... One or more top-level collection names.
                 Default: ${DEFAULT_COLLECTIONS.join(', ')} (max ${MAX_DOCS_PER_COLLECTION.toLocaleString()} docs per collection).

Examples:
  node exportFirestore.js
  node exportFirestore.js --out backup/users.json users requests
  node exportFirestore.js --out=backup/all.json users notifications

Environment:
  Requires the FIREBASE_* variables documented in .env.example.
  Set USE_EMULATOR=true (or FIRESTORE_EMULATOR_HOST=host:port) to read from
  the Firestore emulator instead of production.
`;

/**
 * Parse process arguments into an options object.
 * @param {string[]} argv Arguments after the script name.
 * @returns {{ outFile: string, collections: string[], help: boolean }}
 */
function parseArgs(argv) {
  /** @type {{ outFile: string, collections: string[], help: boolean }} */
  const options = {
    outFile: DEFAULT_OUT_FILE,
    collections: [],
    help: false,
  };
  const positional = [];

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === '--help' || arg === '-h') {
      options.help = true;
      continue;
    }

    if (arg === '--out') {
      const value = argv[index + 1];
      if (value === undefined || value === '' || value.startsWith('-')) {
        throw new UsageError('--out requires a file path (e.g. --out exported.json).');
      }
      options.outFile = value;
      index += 1;
      continue;
    }

    if (arg.startsWith('--out=')) {
      const value = arg.slice('--out='.length);
      if (value === '') {
        throw new UsageError('--out requires a file path (e.g. --out=exported.json).');
      }
      options.outFile = value;
      continue;
    }

    if (arg.startsWith('-')) {
      throw new UsageError(`Unknown option: ${arg}`);
    }

    positional.push(arg);
  }

  // Deduplicate collection names while preserving the order the user gave.
  const seen = new Set();
  for (const rawName of positional) {
    const name = rawName.trim();
    if (name === '') {
      throw new UsageError('Collection names cannot be empty.');
    }
    if (name.includes('/')) {
      throw new UsageError(
        `"${name}" is not a top-level collection name (subcollection paths are not supported).`
      );
    }
    if (seen.has(name)) {
      console.warn(`[export] Ignoring duplicate collection "${name}".`);
      continue;
    }
    seen.add(name);
    options.collections.push(name);
  }

  if (options.collections.length === 0) {
    options.collections = [...DEFAULT_COLLECTIONS];
  }

  return options;
}

/**
 * Read every document of a collection, paging through it until the collection
 * is exhausted or MAX_DOCS_PER_COLLECTION is reached.
 *
 * @param {import('firebase/firestore').Firestore} db
 * @param {string} collectionName
 * @returns {Promise<{ name: string, count: number, truncated: boolean, documents: Record<string, unknown>[] }>}
 */
async function exportCollection(db, collectionName) {
  /** @type {Record<string, unknown>[]} */
  const documents = [];
  /** @type {import('firebase/firestore').QueryDocumentSnapshot | null} */
  let lastDocument = null;

  while (documents.length < MAX_DOCS_PER_COLLECTION) {
    const pageSize = Math.min(PAGE_SIZE, MAX_DOCS_PER_COLLECTION - documents.length);
    const constraints = [orderBy(documentId()), limit(pageSize)];
    if (lastDocument) {
      constraints.push(startAfter(lastDocument));
    }

    const snapshot = await getDocsFromServer(query(collection(db, collectionName), ...constraints));
    if (snapshot.empty) {
      break;
    }

    for (const docSnapshot of snapshot.docs) {
      // Convert the whole (possibly nested) document to JSON-safe values.
      documents.push(convertTimestamps({ id: docSnapshot.id, ...docSnapshot.data() }));
    }

    console.log(
      `[export] ${collectionName}: fetched ${documents.length} document(s) so far`
    );

    lastDocument = snapshot.docs[snapshot.docs.length - 1];
    if (snapshot.size < pageSize) {
      break;
    }
  }

  const truncated = documents.length >= MAX_DOCS_PER_COLLECTION;
  if (truncated) {
    console.warn(
      `[export] ${collectionName}: stopped at the ${MAX_DOCS_PER_COLLECTION.toLocaleString()} document limit for this collection.`
    );
  }

  return { name: collectionName, count: documents.length, truncated, documents };
}

/**
 * Serialise the export payload, including the exact byte size of the file.
 *
 * JSON cannot know its own size before serialisation, and adding the size
 * changes the number of digits. Re-serialise until the declared size matches
 * the serialised length; this converges in two or three passes.
 *
 * @param {Record<string, unknown>} payload
 * @param {string} fileName Base name written into the metadata.
 * @returns {{ json: string, sizeBytes: number }}
 */
function serializeExport(payload, fileName) {
  let sizeBytes = 0;
  let json = '';

  for (let attempt = 0; attempt < 5; attempt += 1) {
    json = `${JSON.stringify({ ...payload, file: { name: fileName, sizeBytes } }, null, 2)}\n`;
    const actualSize = Buffer.byteLength(json, 'utf8');
    if (actualSize === sizeBytes) {
      return { json, sizeBytes: actualSize };
    }
    sizeBytes = actualSize;
  }

  return { json, sizeBytes };
}

/**
 * Human-readable byte size for logging.
 * @param {number} bytes
 * @returns {string}
 */
function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Run the export using the parsed options.
 * @param {{ outFile: string, collections: string[] }} options
 * @returns {Promise<void>}
 */
async function runExport(options) {
  const db = getDb();
  const projectId = getApp().options.projectId ?? 'unknown';

  console.log(
    `[export] Project "${projectId}", collections: ${options.collections.join(', ')}`
  );

  const results = [];
  for (const collectionName of options.collections) {
    results.push(await exportCollection(db, collectionName));
  }

  const outPath = path.resolve(options.outFile);
  const payload = {
    exportedAt: new Date().toISOString(),
    projectId,
    collections: results.map((result) => ({
      name: result.name,
      count: result.count,
      ...(result.truncated ? { truncated: true } : {}),
      documents: result.documents,
    })),
    totals: {
      collections: results.length,
      documents: results.reduce((sum, result) => sum + result.count, 0),
    },
  };

  await fs.mkdir(path.dirname(outPath), { recursive: true });
  const { json, sizeBytes } = serializeExport(payload, path.basename(outPath));
  await fs.writeFile(outPath, json, 'utf8');

  const { size } = await fs.stat(outPath);
  for (const result of results) {
    console.log(`[export] ${result.name}: ${result.count} document(s)`);
  }
  console.log(
    `[export] Wrote ${outPath} (${formatBytes(size)}) with ${
      payload.totals.documents
    } document(s) across ${payload.totals.collections} collection(s).`
  );
  if (size !== sizeBytes) {
    console.warn(
      `[export] File size mismatch (stat: ${size} bytes, declared: ${sizeBytes} bytes).`
    );
  }
}

async function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    if (error instanceof UsageError) {
      console.error(`[export] ${error.message}`);
      console.error(USAGE);
      process.exit(EXIT_USAGE);
    }
    throw error;
  }

  if (options.help) {
    console.log(USAGE);
    process.exit(EXIT_OK);
  }

  try {
    await runExport(options);
    process.exit(EXIT_OK);
  } catch (error) {
    console.error('[export] Export failed:', error instanceof Error ? error.message : error);
    process.exit(EXIT_FAILURE);
  }
}

await main();
