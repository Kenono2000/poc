const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------
// 1. SET YOUR BOOKMARKS PATH
// Uncomment the path for your specific Operating System:
// ---------------------------------------------------------

// WINDOWS (Default Profile):
const bookmarksPath = path.join(process.env.LOCALAPPDATA, 'Google', 'Chrome', 'User Data', 'Default', 'Bookmarks');

// MACOS (Default Profile):
// const bookmarksPath = path.join(process.env.HOME, 'Library', 'Application Support', 'Google', 'Chrome', 'Default', 'Bookmarks');

// LINUX (Default Profile):
// const bookmarksPath = path.join(process.env.HOME, '.config', 'google-chrome', 'Default', 'Bookmarks');

// ---------------------------------------------------------

try {
 // 2. Create a backup before making any destructive changes
 fs.copyFileSync(bookmarksPath, `${bookmarksPath}.backup`);
 console.log('✅ Backup created successfully at:', `${bookmarksPath}.backup`);

 // 3. Read and parse the Bookmarks JSON
 const rawData = fs.readFileSync(bookmarksPath, 'utf8');
 const bookmarks = JSON.parse(rawData);

 // 4. The Recursive Sorting Function
 // List of folders to skip
 const foldersToSkip = ['Chrome', 'MTC', 'ACER'];

 function sortChildren(node) {
  // Base case: If there are no children, stop recursing
  if (!node.children || !Array.isArray(node.children)) {
   return;
  }

  // Recurse first: go all the way down to the deepest folders
  node.children.forEach((child) => {
   if (child.type === 'folder' && !foldersToSkip.includes(child.name)) {
    sortChildren(child);
   }
  });

  // Separate the children into Folders (sortable and non-sortable) and URLs
  const sortableFolders = node.children.filter((child) => child.type === 'folder' && !foldersToSkip.includes(child.name));
  const skippedFolders = node.children.filter((child) => child.type === 'folder' && foldersToSkip.includes(child.name));
  const urls = node.children.filter((child) => child.type === 'url');

  // Sorting helper: Case-insensitive alphabetical sort
  const sortAlphabetically = (a, b) => {
   const nameA = (a.name || '').toLowerCase();
   const nameB = (b.name || '').toLowerCase();
   return nameA.localeCompare(nameB);
  };

  // Sort only the sortable folders and URLs
  sortableFolders.sort(sortAlphabetically);
  urls.sort(sortAlphabetically);

  // Reassign the sorted arrays back to the node (Sortable Folders listed first, then URLs, then Skipped Folders at the end)
  node.children = [...sortableFolders, ...urls, ...skippedFolders];
 }

 // 5. Apply sorting to Chrome's primary root directories
 const roots = bookmarks.roots;
 if (roots) {
  if (roots.bookmark_bar) sortChildren(roots.bookmark_bar); // The main bookmarks bar
  if (roots.other) sortChildren(roots.other); // "Other Bookmarks" folder
  if (roots.synced) sortChildren(roots.synced); // Mobile/Synced bookmarks
 }

 // 6. Write the beautifully sorted JSON back to the file
 // Chrome uses 3 spaces for indentation in this specific file
 fs.writeFileSync(bookmarksPath, JSON.stringify(bookmarks, null, 3), 'utf8');
 console.log('🚀 Bookmarks successfully sorted!');
} catch (error) {
 console.error('❌ An error occurred:', error.message);
}
