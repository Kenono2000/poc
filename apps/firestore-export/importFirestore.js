#!/usr/bin/env node
/**
 * Import a previously exported JSON file into Firestore using batched writes.
 *
 * Usage:
 *   node importFirestore.js [file] [collection]
 *   node importFirestore.js --help
 *
 * Defaults: reads `exported.json`. The file may be either:
 *   1. the combined format written by exportFirestore.js
 *      ({ collections: [{ name, documents }], ... }), whose collection names
 *      are used directly, or
 *   2. a legacy plain array of documents, which is written to `collection`
 *      (default: users; override with the second argument).
 *
 * Documents that contain an `id` field are written with that exact document ID
 * (batch.set + doc ref). Documents without an `id` get an auto-generated ID.
 * Writes are chunked into batches of 500 operations, the Firestore limit.
 *
 * Exit codes:
 *   0 - success
 *   1 - read, parse, configuration, or write failure
 *   2 - invalid command-line usage
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { collection, doc, writeBatch } from 'firebase/firestore';
// Importing firebaseSetup.js also loads `.env` (via dotenv) before getDb() runs.
import { getDb } from './firebaseSetup.js';
import { resolveTimeoutMs, withTimeout } from './utils.js';

const DEFAULT_FILE = 'exported.json';
const DEFAULT_COLLECTION = 'users';
const BATCH_SIZE = 500;

const EXIT_OK = 0;
const EXIT_FAILURE = 1;
const EXIT_USAGE = 2;

/** Thrown for invalid command-line arguments; mapped to exit code 2. */
class UsageError extends Error {}

const USAGE = `Usage: node importFirestore.js [file] [collection]

Import a JSON export into Firestore with batched writes (${BATCH_SIZE} documents
per batch). Documents with an "id" field keep that ID; others get an auto ID.

Arguments:
  file           JSON file to import (default: ${DEFAULT_FILE}).
  collection     Collection for a legacy plain-array export file
                 (default: ${DEFAULT_COLLECTION}). Ignored when the file uses
                 the combined export format, which carries its own names.

Options:
  -h, --help     Show this help message.

Examples:
  node importFirestore.js
  node importFirestore.js ./backup/exported.json
  node importFirestore.js legacy-users.json users

Environment:
  Requires the FIREBASE_* variables documented in .env.example.
  Set USE_EMULATOR=true (or FIRESTORE_EMULATOR_HOST=host:port) to write to the
  Firestore emulator instead of production.
  FIRESTORE_WRITE_TIMEOUT_MS overrides the per-batch wait (default: 30000).
`;

/**
 * @typedef {{ name: string, documents: unknown[] }} CollectionImport
 */

/**
 * Parse process arguments.
 * @param {string[]} argv Arguments after the script name.
 * @returns {{ file: string, collection: string, help: boolean }}
 */
function parseArgs(argv) {
  /** @type {{ file: string, collection: string, help: boolean }} */
  const options = { file: DEFAULT_FILE, collection: DEFAULT_COLLECTION, help: false };
  const positional = [];

  for (const arg of argv) {
    if (arg === '--help' || arg === '-h') {
      options.help = true;
      continue;
    }
    if (arg.startsWith('-')) {
      throw new UsageError(`Unknown option: ${arg}`);
    }
    positional.push(arg);
  }

  if (positional.length > 2) {
    throw new UsageError(
      `Too many arguments (${positional.length}); expected [file] [collection].`
    );
  }

  if (positional[0] !== undefined) {
    options.file = positional[0];
  }
  if (positional[1] !== undefined) {
    options.collection = positional[1];
  }

  if (options.collection.trim() === '' || options.collection.includes('/')) {
    throw new UsageError(
      `"${options.collection}" is not a valid top-level collection name.`
    );
  }

  return options;
}

/**
 * Normalize the two supported JSON shapes into a list of collections.
 *
 * @param {unknown} data Parsed JSON content.
 * @param {string} fallbackCollection Collection name for plain-array files.
 * @returns {CollectionImport[]}
 * @throws {Error} When the JSON shape is not supported.
 */
function normalizeImport(data, fallbackCollection) {
  if (Array.isArray(data)) {
    return [{ name: fallbackCollection, documents: data }];
  }

  if (data !== null && typeof data === 'object') {
    const record = /** @type {Record<string, unknown>} */ (data);

    if (Array.isArray(record.collections)) {
      return record.collections.map((entry, index) => {
        if (entry === null || typeof entry !== 'object') {
          throw new Error(`collections[${index}] is not an object.`);
        }
        const collectionEntry = /** @type {Record<string, unknown>} */ (entry);
        if (typeof collectionEntry.name !== 'string' || collectionEntry.name === '') {
          throw new Error(`collections[${index}].name is missing or not a string.`);
        }
        if (!Array.isArray(collectionEntry.documents)) {
          throw new Error(`collections[${index}].documents is not an array.`);
        }
        return { name: collectionEntry.name, documents: collectionEntry.documents };
      });
    }

    // Single-collection object form: { name, documents: [...] }.
    if (typeof record.name === 'string' && Array.isArray(record.documents)) {
      return [{ name: record.name, documents: record.documents }];
    }
  }

  throw new Error(
    'Unsupported JSON shape: expected a plain array of documents, ' +
      'or an object with a "collections" array (as written by exportFirestore.js).'
  );
}

/**
 * Write documents to one collection using batched writes.
 *
 * @param {import('firebase/firestore').Firestore} db
 * @param {string} collectionName
 * @param {unknown[]} documents
 * @returns {Promise<number>} Number of documents written.
 */
async function importCollection(db, collectionName, documents) {
  if (collectionName === '' || collectionName.includes('/')) {
    throw new Error(`Invalid top-level collection name: "${collectionName}".`);
  }

  const collectionRef = collection(db, collectionName);
  const batchTimeoutMs = resolveTimeoutMs(process.env);
  let written = 0;

  for (let start = 0; start < documents.length; start += BATCH_SIZE) {
    const chunk = documents.slice(start, start + BATCH_SIZE);
    const batch = writeBatch(db);

    for (const [offset, item] of chunk.entries()) {
      if (item === null || typeof item !== 'object' || Array.isArray(item)) {
        throw new Error(
          `Document at ${collectionName}[${start + offset}] is not a JSON object.`
        );
      }

      /** @type {Record<string, unknown>} */
      const fields = { .../** @type {Record<string, unknown>} */ (item) };
      const documentId = fields.id;
      delete fields.id;

      if (documentId !== undefined && documentId !== null && documentId !== '') {
        if (typeof documentId !== 'string') {
          throw new Error(
            `Document at ${collectionName}[${start + offset}] has a non-string "id": ${String(
              documentId
            )}`
          );
        }
        batch.set(doc(collectionRef, documentId), fields);
      } else {
        // No id in the export: let Firestore generate one.
        batch.set(doc(collectionRef), fields);
      }
    }

    const first = start;
    const last = start + chunk.length - 1;

    try {
      await withTimeout(
        batch.commit(),
        batchTimeoutMs,
        `Batch write to "${collectionName}" (documents ${first}-${last})`
      );
    } catch (error) {
      throw new Error(
        `Batch write to "${collectionName}" failed for index(es) ${first}-${last}: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    }

    written += chunk.length;
    console.log(
      `[import] ${collectionName}: ${written}/${documents.length} document(s) written`
    );
  }

  return written;
}

/**
 * Read the export file and import every collection it contains.
 * @param {string} filePath
 * @param {string} fallbackCollection
 * @returns {Promise<number>} Total documents written.
 */
async function runImport(filePath, fallbackCollection) {
  const resolvedPath = path.resolve(filePath);

  let text;
  try {
    text = await fs.readFile(resolvedPath, 'utf8');
  } catch (error) {
    throw new Error(
      `Cannot read export file "${resolvedPath}": ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }

  let data;
  try {
    // Strip a UTF-8 BOM (common in JSON files created on Windows) before parsing.
    data = JSON.parse(text.replace(/^\uFEFF/, ''));
  } catch (error) {
    throw new Error(
      `Invalid JSON in "${resolvedPath}": ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }

  const collections = normalizeImport(data, fallbackCollection);
  if (collections.length === 0) {
    console.warn('[import] The export file contains no collections; nothing to do.');
    return 0;
  }

  const db = getDb();
  let total = 0;
  for (const entry of collections) {
    console.log(
      `[import] Importing ${entry.documents.length} document(s) into "${entry.name}"...`
    );
    total += await importCollection(db, entry.name, entry.documents);
  }

  return total;
}

async function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    if (error instanceof UsageError) {
      console.error(`[import] ${error.message}`);
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
    const total = await runImport(options.file, options.collection);
    console.log(`[import] Import completed: ${total} document(s) written.`);
    process.exit(EXIT_OK);
  } catch (error) {
    console.error('[import] Import failed:', error instanceof Error ? error.message : error);
    process.exit(EXIT_FAILURE);
  }
}

await main();
