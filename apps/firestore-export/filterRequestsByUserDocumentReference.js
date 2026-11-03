#!/usr/bin/env node
/**
 * Find all documents in the `requests` collection whose `user` field is a
 * DocumentReference to users/{userId}, then set their status to "active" using
 * batched writes.
 *
 * Usage:
 *   node filterRequestsByUserDocumentReference.js <userId> [options]
 *   node filterRequestsByUserDocumentReference.js --help
 *
 * The user ID comes from the first argument or FILTER_USER_ID; nothing is
 * hardcoded and all Firebase configuration comes from the environment
 * (see .env.example). The query uses the "server" source so an unreachable
 * backend fails instead of silently matching stale cached data. Updates are
 * batched, and a timeout prevents an offline write from hanging forever.
 *
 * Exit codes:
 *   0 - success (including "no requests found")
 *   1 - configuration, query, or write failure
 *   2 - invalid or missing command-line arguments
 */
import { collection, doc, getDocsFromServer, query, where, writeBatch } from 'firebase/firestore';
// Importing firebaseSetup.js also loads `.env` (via dotenv) before getDb() runs.
import { getDb } from './firebaseSetup.js';
import { resolveTimeoutMs, withTimeout } from './utils.js';

const REQUESTS_COLLECTION = 'requests';
const TARGET_STATUS = 'active';
const BATCH_SIZE = 500;

const EXIT_OK = 0;
const EXIT_FAILURE = 1;
const EXIT_USAGE = 2;

/** Thrown for invalid command-line arguments; mapped to exit code 2. */
class UsageError extends Error {}

const USAGE = `Usage: node filterRequestsByUserDocumentReference.js <userId> [options]

Find requests where "user" is a DocumentReference to users/<userId> and set
their status to "${TARGET_STATUS}" with batched writes (${BATCH_SIZE} per batch).

Arguments:
  userId          Target user ID (required unless FILTER_USER_ID is set).

Options:
  --dry-run       Print matching requests without updating anything.
  -h, --help      Show this help message.

Examples:
  node filterRequestsByUserDocumentReference.js YOUR_USER_ID
  node filterRequestsByUserDocumentReference.js YOUR_USER_ID --dry-run
  FILTER_USER_ID=YOUR_USER_ID node filterRequestsByUserDocumentReference.js

Environment:
  FILTER_USER_ID   Default user ID when no positional argument is given.
  Firebase credentials: FIREBASE_* (see .env.example).
  Set USE_EMULATOR=true (or FIRESTORE_EMULATOR_HOST=host:port) to use the
  Firestore emulator instead of production.
  FIRESTORE_WRITE_TIMEOUT_MS overrides the per-batch wait (default: 30000).
`;

/**
 * Parse process arguments.
 * @param {string[]} argv Arguments after the script name.
 * @returns {{ userId: string, dryRun: boolean, help: boolean }}
 */
function parseArgs(argv) {
  let dryRun = false;
  let help = false;
  const positional = [];

  for (const arg of argv) {
    if (arg === '--help' || arg === '-h') {
      help = true;
    } else if (arg === '--dry-run') {
      dryRun = true;
    } else if (arg.startsWith('-')) {
      throw new UsageError(`Unknown option: ${arg}`);
    } else {
      positional.push(arg);
    }
  }

  if (positional.length > 1) {
    throw new UsageError(
      `Too many arguments (${positional.length}); expected a single userId.`
    );
  }

  const userId = (positional[0] ?? process.env.FILTER_USER_ID ?? '').trim();

  if (!help && userId === '') {
    throw new UsageError(
      'Missing userId. Pass it as the first argument or set FILTER_USER_ID.'
    );
  }

  if (userId.includes('/')) {
    throw new UsageError(
      `"${userId}" is not a valid user document ID (it must not contain "/").`
    );
  }

  return { userId, dryRun, help };
}

/**
 * Query requests whose `user` field points at users/{userId}.
 *
 * @param {import('firebase/firestore').Firestore} db
 * @param {string} userId
 * @returns {Promise<{ id: string, previousStatus: string }[]>}
 */
async function findRequests(db, userId) {
  const userRef = doc(db, 'users', userId);
  const requestQuery = query(
    collection(db, REQUESTS_COLLECTION),
    where('user', '==', userRef)
  );
  const snapshot = await getDocsFromServer(requestQuery);

  return snapshot.docs.map((requestDoc) => {
    const data = requestDoc.data();
    return {
      id: requestDoc.id,
      previousStatus: typeof data.status === 'string' ? data.status : '(unset)',
    };
  });
}

/**
 * Set status to TARGET_STATUS for every request, batched by BATCH_SIZE.
 *
 * @param {import('firebase/firestore').Firestore} db
 * @param {{ id: string }[]} requests
 * @returns {Promise<number>} Number of documents updated.
 */
async function setRequestsStatusActive(db, requests) {
  const batchTimeoutMs = resolveTimeoutMs(process.env);
  let updated = 0;

  for (let start = 0; start < requests.length; start += BATCH_SIZE) {
    const chunk = requests.slice(start, start + BATCH_SIZE);
    const batch = writeBatch(db);

    for (const request of chunk) {
      batch.update(doc(db, REQUESTS_COLLECTION, request.id), { status: TARGET_STATUS });
    }

    try {
      await withTimeout(
        batch.commit(),
        batchTimeoutMs,
        `Batch update of ${REQUESTS_COLLECTION} (documents ${start}-${
          start + chunk.length - 1
        })`
      );
    } catch (error) {
      throw new Error(
        `Batch update failed for ${REQUESTS_COLLECTION} index(es) ${start}-${
          start + chunk.length - 1
        }: ${error instanceof Error ? error.message : String(error)}`
      );
    }

    updated += chunk.length;
    console.log(
      `[filter] Updated ${updated}/${requests.length} request(s) to status "${TARGET_STATUS}"`
    );
  }

  return updated;
}

async function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    if (error instanceof UsageError) {
      console.error(`[filter] ${error.message}`);
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
    const db = getDb();
    console.log(
      `[filter] Searching ${REQUESTS_COLLECTION} where user == users/${options.userId}`
    );

    const requests = await findRequests(db, options.userId);

    if (requests.length === 0) {
      console.log(`[filter] No requests found for user ${options.userId}.`);
      process.exit(EXIT_OK);
    }

    console.log(`[filter] Found ${requests.length} matching request(s).`);

    if (options.dryRun) {
      console.table(
        requests.map((request) => ({
          id: request.id,
          previousStatus: request.previousStatus,
          newStatus: `${TARGET_STATUS} (dry run)`,
        }))
      );
      console.log('[filter] Dry run: no documents were updated.');
      process.exit(EXIT_OK);
    }

    const updated = await setRequestsStatusActive(db, requests);

    console.table(
      requests.map((request) => ({
        id: request.id,
        previousStatus: request.previousStatus,
        newStatus: TARGET_STATUS,
      }))
    );
    console.log(`[filter] Updated ${updated} request(s) to status "${TARGET_STATUS}".`);
    process.exit(EXIT_OK);
  } catch (error) {
    console.error(
      '[filter] Execution failed:',
      error instanceof Error ? error.message : error
    );
    process.exit(EXIT_FAILURE);
  }
}

await main();
