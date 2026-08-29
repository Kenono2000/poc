import { collection, query, where, getDocs, doc, updateDoc } from 'firebase/firestore';
import { setupFirebase } from './firebaseSetup.js';
import 'dotenv/config';

// --- Configuration ---
const firebaseConfig = {
 apiKey: process.env.FWEB_API_KEY || 'AIzaSyAWulWywVWz526T26RsJrIs3VKSgo582zM',
 authDomain: 'dths-test.firebaseapp.com',
 projectId: 'dths-test',
};

const db = setupFirebase(firebaseConfig, false);

// --- Core Logic ---

/**
 * Generic helper to fetch documents from a collection with filters
 */
async function fetchDocuments(colName, constraints = []) {
 try {
  const colRef = collection(db, colName);
  const q = query(colRef, ...constraints);
  const snapshot = await getDocs(q);

  return snapshot.docs.map((doc) => ({
   id: doc.id,
   ...doc.data(),
  }));
 } catch (error) {
  console.error(`Error fetching from ${colName}:`, error);
  throw error;
 }
}

/**
 * Filter requests by user
 */
async function getRequests(userId) {
 const userDocRef = doc(db, 'users', userId);
 const constraints = [where('user', '==', userDocRef)];

 return await fetchDocuments('requests', constraints);
}

async function setRequestsStatusActive(requests) {
 const updatePromises = requests.map((request) => {
  const requestDocRef = doc(db, 'requests', request.id);
  return updateDoc(requestDocRef, { status: 'active' });
 });

 await Promise.all(updatePromises);
}

// --- Execution ---

(async () => {
 try {
  const TEST_USER_ID = 'LHQPLNsYQsOIwS1NjYANcQAoKnv1';

  const requests = await getRequests(TEST_USER_ID);
  console.log(`\n--- Requests for ${TEST_USER_ID} ---`);

  if (!requests.length) {
   console.log('No matching requests found.');
   process.exit(0);
  }

  await setRequestsStatusActive(requests);
  console.log(`Updated ${requests.length} request(s) to status: active`);

  const updatedRequests = requests.map((request) => ({
   ...request,
   status: 'active',
  }));

  console.table(updatedRequests);
  process.exit(0);
 } catch (error) {
  console.error('Execution failed:', error.message);
  process.exit(1);
 }
})();
