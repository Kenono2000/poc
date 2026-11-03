#!/usr/bin/env node
/**
 * sortChromeBookmarks.js
 *
 * Alphabetically sorts Google Chrome bookmarks in place:
 *   - folders first (case-insensitive by name), then URLs, then protected folders
 *   - recurses through bookmark_bar, other and synced roots
 *   - protected folders (e.g. Chrome, MTC, ACER) keep their position at the end
 *
 * Safety:
 *   - aborts if the Bookmarks file is missing or unreadable
 *   - writes a timestamped `.backup` copy before touching the original
 *   - creates the canonical `Bookmarks.backup` once (first pristine snapshot)
 *   - rewrites the file with Chrome's 3-space indentation
 *
 * Usage:
 *   node sortChromeBookmarks.js            # sort the Default profile
 *   node sortChromeBookmarks.js --dry-run  # show what would change
 *   CHROME_PROFILE="Profile 1" node sortChromeBookmarks.js
 *   BOOKMARKS_PATH="C:\\path\\Bookmarks" node sortChromeBookmarks.js
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Folders whose contents are intentionally left unsorted (and pushed last). */
const PROTECTED_FOLDERS = ['Chrome', 'MTC', 'ACER'];

/** Chrome writes its Bookmarks file with 3-space indentation. */
const INDENT = 3;

const dryRun = process.argv.includes('--dry-run');

/**
 * Resolve the Chrome bookmarks file for the current OS / profile.
 * @returns {string} absolute path to the Bookmarks JSON file
 */
function resolveBookmarksPath() {
  if (process.env.BOOKMARKS_PATH) {
    return path.resolve(process.env.BOOKMARKS_PATH);
  }

  const profile = process.env.CHROME_PROFILE || 'Default';

  if (process.platform === 'win32') {
    const localAppData = process.env.LOCALAPPDATA;
    if (!localAppData) {
      throw new Error('LOCALAPPDATA is not defined; set BOOKMARKS_PATH explicitly.');
    }
    return path.join(localAppData, 'Google', 'Chrome', 'User Data', profile, 'Bookmarks');
  }

  if (process.platform === 'darwin') {
    return path.join(
      process.env.HOME || '',
      'Library',
      'Application Support',
      'Google',
      'Chrome',
      profile,
      'Bookmarks'
    );
  }

  // Linux / other POSIX
  return path.join(process.env.HOME || '', '.config', 'google-chrome', profile, 'Bookmarks');
}

/** Case-insensitive alphabetical comparison that tolerates missing names. */
function compareByName(a, b) {
  const nameA = (a.name || '').toLowerCase();
  const nameB = (b.name || '').toLowerCase();
  return nameA.localeCompare(nameB);
}

/**
 * Recursively sort a bookmark folder node.
 * @param {object} node bookmark folder object (has `children`)
 */
function sortChildren(node) {
  if (!node || !Array.isArray(node.children)) {
    return;
  }

  // Depth-first: sort descendants first.
  for (const child of node.children) {
    if (child.type === 'folder' && !PROTECTED_FOLDERS.includes(child.name)) {
      sortChildren(child);
    }
  }

  const sortableFolders = node.children.filter(
    (child) => child.type === 'folder' && !PROTECTED_FOLDERS.includes(child.name)
  );
  const skippedFolders = node.children.filter(
    (child) => child.type === 'folder' && PROTECTED_FOLDERS.includes(child.name)
  );
  const urls = node.children.filter((child) => child.type === 'url');
  const others = node.children.filter(
    (child) => child.type !== 'folder' && child.type !== 'url'
  );

  sortableFolders.sort(compareByName);
  urls.sort(compareByName);

  // Folders first, then URLs, then unknown node types, then protected folders.
  node.children = [...sortableFolders, ...urls, ...others, ...skippedFolders];
}

/**
 * Create safety copies of the Bookmarks file.
 * @param {string} bookmarksPath
 */
function backupBookmarks(bookmarksPath) {
  const stamp = new Date()
    .toISOString()
    .replace(/[-:T]/g, '')
    .slice(0, 14);
  const timestamped = `${bookmarksPath}.backup-${stamp}`;
  fs.copyFileSync(bookmarksPath, timestamped);
  console.log(`✅ Timestamped backup: ${timestamped}`);

  const canonical = `${bookmarksPath}.backup`;
  if (!fs.existsSync(canonical)) {
    fs.copyFileSync(bookmarksPath, canonical);
    console.log(`✅ Initial backup:     ${canonical}`);
  } else {
    console.log(`ℹ️  Existing backup kept: ${canonical}`);
  }
}

/** Entry point. */
function main() {
  const bookmarksPath = resolveBookmarksPath();

  if (!fs.existsSync(bookmarksPath)) {
    console.error(`❌ Bookmarks file not found: ${bookmarksPath}`);
    console.error(
      '   Close Chrome, verify the profile name, or set BOOKMARKS_PATH to the real file.'
    );
    process.exitCode = 1;
    return;
  }

  // Read + parse before writing anything.
  let bookmarks;
  try {
    bookmarks = JSON.parse(fs.readFileSync(bookmarksPath, 'utf8'));
  } catch (error) {
    console.error(`❌ Unable to read/parse ${bookmarksPath}: ${error.message}`);
    process.exitCode = 1;
    return;
  }

  if (!bookmarks || typeof bookmarks !== 'object' || !bookmarks.roots) {
    console.error('❌ Unexpected Bookmarks structure: missing "roots" object.');
    process.exitCode = 1;
    return;
  }

  if (!dryRun) {
    try {
      backupBookmarks(bookmarksPath);
    } catch (error) {
      console.error(`❌ Backup failed, aborting to avoid data loss: ${error.message}`);
      process.exitCode = 1;
      return;
    }
  }

  const roots = bookmarks.roots;
  if (roots.bookmark_bar) sortChildren(roots.bookmark_bar);
  if (roots.other) sortChildren(roots.other);
  if (roots.synced) sortChildren(roots.synced);

  const output = JSON.stringify(bookmarks, null, INDENT);

  if (dryRun) {
    console.log(`🔎 Dry run: would rewrite ${bookmarksPath} (${output.length} bytes).`);
    return;
  }

  try {
    fs.writeFileSync(bookmarksPath, output, 'utf8');
  } catch (error) {
    console.error(`❌ Failed to write ${bookmarksPath}: ${error.message}`);
    console.error('   Make sure Chrome is closed and the file is not read-only.');
    process.exitCode = 1;
    return;
  }

  console.log(`🚀 Chrome bookmarks sorted successfully: ${bookmarksPath}`);
}

try {
  main();
} catch (error) {
  console.error(`❌ Fatal error: ${error.message}`);
  process.exitCode = 1;
}
