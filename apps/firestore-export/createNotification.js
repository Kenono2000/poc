#!/usr/bin/env node
/**
 * Create a notification document for a user:
 *   users/{userId}/notifications/{autoId}
 *
 * Usage:
 *   node createNotification.js <userId> [collectionName] [options]
 *   node createNotification.js --help
 *
 * The user ID must be supplied explicitly (first argument or
 * NOTIFICATION_USER_ID); there is no hardcoded default account. The message
 * fields fall back to environment variables and then to sample defaults, so
 * every value can be overridden without editing this file.
 *
 * Exit codes:
 *   0 - notification created
 *   1 - configuration or Firestore write failure
 *   2 - invalid or missing command-line arguments
 */
import { addDoc, collection, doc, Timestamp } from 'firebase/firestore';
// Importing firebaseSetup.js also loads `.env` (via dotenv) before getDb() runs.
import { getDb } from './firebaseSetup.js';
import { resolveTimeoutMs, withTimeout } from './utils.js';

const DEFAULT_COLLECTION = 'notifications';
const DEFAULT_WRITE_TIMEOUT_MS = 30_000;

/** Sample payload defaults; override with flags or NOTIFICATION_* env vars. */
const DEFAULT_FIELDS = Object.freeze({
  channelId: '2SE4OLb3BISZgZJ82DIh',
  content: 'Happy Monday!',
  sender: 'users/tu1001-m',
  senderFirstName: 'tu1001-Man',
  senderlastName: 'Last-tu1001',
  targetUserFirstName: 'tu12-Woman',
  type: 'message',
  viewed: false,
});

/** Maps CLI flag -> notification field name. */
const FIELD_FLAGS = Object.freeze({
  '--channel-id': 'channelId',
  '--content': 'content',
  '--sender': 'sender',
  '--sender-first-name': 'senderFirstName',
  '--sender-last-name': 'senderlastName',
  '--target-user-first-name': 'targetUserFirstName',
  '--type': 'type',
});

/** Maps notification field name -> environment variable. */
const FIELD_ENV_VARS = Object.freeze({
  channelId: 'NOTIFICATION_CHANNEL_ID',
  content: 'NOTIFICATION_CONTENT',
  sender: 'NOTIFICATION_SENDER',
  senderFirstName: 'NOTIFICATION_SENDER_FIRST_NAME',
  senderlastName: 'NOTIFICATION_SENDER_LAST_NAME',
  targetUserFirstName: 'NOTIFICATION_TARGET_USER_FIRST_NAME',
  type: 'NOTIFICATION_TYPE',
  viewed: 'NOTIFICATION_VIEWED',
});

const EXIT_OK = 0;
const EXIT_FAILURE = 1;
const EXIT_USAGE = 2;

/** Thrown for invalid command-line arguments; mapped to exit code 2. */
class UsageError extends Error {}

const USAGE = `Usage: node createNotification.js <userId> [collectionName] [options]

Create a notification document under users/<userId>/<collectionName>.

Arguments:
  userId                  Target user ID (required unless NOTIFICATION_USER_ID is set).
  collectionName          Subcollection name (default: ${DEFAULT_COLLECTION}).

Options:
  --content <text>             Notification body (default: "${DEFAULT_FIELDS.content}").
  --channel-id <id>            Channel/document ID (default: "${DEFAULT_FIELDS.channelId}").
  --type <type>                Notification type (default: "${DEFAULT_FIELDS.type}").
  --sender <path>              Sender reference path (default: "${DEFAULT_FIELDS.sender}").
  --sender-first-name <name>   Sender first name (default: "${DEFAULT_FIELDS.senderFirstName}").
  --sender-last-name <name>    Sender last name.
  --target-user-first-name <n> Target user first name.
  --viewed <true|false>        Mark the notification viewed (default: false).
  -h, --help                   Show this help message.

Examples:
  node createNotification.js YOUR_USER_ID
  node createNotification.js YOUR_USER_ID notifications --content "Happy Monday!" --type message
  $env:NOTIFICATION_USER_ID="YOUR_USER_ID"; node createNotification.js --content "Hello!"

Environment:
  NOTIFICATION_USER_ID, NOTIFICATION_COLLECTION
  NOTIFICATION_CHANNEL_ID, NOTIFICATION_CONTENT, NOTIFICATION_SENDER,
  NOTIFICATION_SENDER_FIRST_NAME, NOTIFICATION_SENDER_LAST_NAME,
  NOTIFICATION_TARGET_USER_FIRST_NAME, NOTIFICATION_TYPE, NOTIFICATION_VIEWED
  FIRESTORE_WRITE_TIMEOUT_MS (default: ${DEFAULT_WRITE_TIMEOUT_MS})
  Firebase credentials: FIREBASE_* (see .env.example).
  Set USE_EMULATOR=true (or FIRESTORE_EMULATOR_HOST=host:port) to write to the
  Firestore emulator instead of production.
`;

/**
 * Parse a boolean flag value.
 * @param {string} raw
 * @param {string} flagName
 * @returns {boolean}
 */
function parseBoolean(raw, flagName) {
  if (/^(1|true|yes|on)$/i.test(raw)) {
    return true;
  }
  if (/^(0|false|no|off)$/i.test(raw)) {
    return false;
  }
  throw new UsageError(`${flagName} expects true or false, received "${raw}".`);
}

/**
 * Parse process arguments.
 *
 * @param {string[]} argv Arguments after the script name.
 * @returns {{ userId: string, collectionName: string, fields: Record<string, string | boolean>, help: boolean }}
 */
function parseArgs(argv) {
  /** @type {Record<string, string | boolean>} */
  const fields = {};
  const positional = [];
  let help = false;

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === '--help' || arg === '-h') {
      help = true;
      continue;
    }

    if (arg === '--viewed') {
      const value = argv[index + 1];
      if (value === undefined) {
        throw new UsageError('--viewed requires a value (true or false).');
      }
      fields.viewed = parseBoolean(value, '--viewed');
      index += 1;
      continue;
    }

    const fieldName = FIELD_FLAGS[arg];
    if (fieldName) {
      const value = argv[index + 1];
      if (value === undefined) {
        throw new UsageError(`${arg} requires a value.`);
      }
      fields[fieldName] = value;
      index += 1;
      continue;
    }

    if (arg.startsWith('-')) {
      throw new UsageError(`Unknown option: ${arg}`);
    }

    positional.push(arg);
  }

  if (positional.length > 2) {
    throw new UsageError(
      `Too many arguments (${positional.length}); expected <userId> [collectionName].`
    );
  }

  const userId = (positional[0] ?? process.env.NOTIFICATION_USER_ID ?? '').trim();
  const collectionName = (
    positional[1] ??
    process.env.NOTIFICATION_COLLECTION ??
    DEFAULT_COLLECTION
  ).trim();

  if (!help && userId === '') {
    throw new UsageError(
      'Missing userId. Pass it as the first argument or set NOTIFICATION_USER_ID.'
    );
  }

  if (collectionName === '' || collectionName.includes('/')) {
    throw new UsageError(
      `"${collectionName}" is not a valid subcollection name (expected a single path segment).`
    );
  }

  return { userId, collectionName, fields, help };
}

/**
 * Resolve the notification payload from flags, environment, and defaults.
 * @param {Record<string, string | boolean>} flagFields
 * @returns {{ channelId: string, content: string, sender: string, senderFirstName: string, senderlastName: string, targetUserFirstName: string, type: string, viewed: boolean }}
 */
function buildPayload(flagFields) {
  /** @type {Record<string, string | boolean>} */
  const merged = { ...DEFAULT_FIELDS };

  for (const [fieldName, envName] of Object.entries(FIELD_ENV_VARS)) {
    const value = process.env[envName];
    if (value === undefined || value.trim() === '') {
      continue;
    }
    if (fieldName === 'viewed') {
      merged.viewed = parseBoolean(value.trim(), envName);
    } else {
      merged[fieldName] = value.trim();
    }
  }

  for (const [fieldName, value] of Object.entries(flagFields)) {
    merged[fieldName] = value;
  }

  return /** @type {{ channelId: string, content: string, sender: string, senderFirstName: string, senderlastName: string, targetUserFirstName: string, type: string, viewed: boolean }} */ (
    merged
  );
}

/**
 * Create the notification document.
 * @param {string} userId
 * @param {string} collectionName
 * @param {Record<string, unknown>} payload
 * @returns {Promise<string>} The new document ID.
 */
async function createNotification(userId, collectionName, payload) {
  const db = getDb();
  const userRef = doc(db, 'users', userId);
  const notificationsRef = collection(userRef, collectionName);

  const notification = {
    ...payload,
    created: Timestamp.now(),
  };

  const docRef = await withTimeout(
    addDoc(notificationsRef, notification),
    resolveTimeoutMs(process.env, 'FIRESTORE_WRITE_TIMEOUT_MS', DEFAULT_WRITE_TIMEOUT_MS),
    'Creating the notification'
  );
  return docRef.id;
}

async function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    if (error instanceof UsageError) {
      console.error(`[notify] ${error.message}`);
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
    const payload = buildPayload(options.fields);
    const documentId = await createNotification(options.userId, options.collectionName, payload);
    console.log(
      `[notify] Created notification users/${options.userId}/${options.collectionName}/${documentId}`
    );
    console.log(`[notify] content: ${JSON.stringify(payload.content)} type: ${payload.type}`);
    process.exit(EXIT_OK);
  } catch (error) {
    console.error(
      '[notify] Failed to create notification:',
      error instanceof Error ? error.message : error
    );
    process.exit(EXIT_FAILURE);
  }
}

await main();
