// Import the required modules
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, addDoc } from 'firebase/firestore';
import fs from 'fs'; // Import the filesystem module
import { setupFirebase } from './firebaseSetup.js';

const firebaseConfig = {
    apiKey: "AIzaSyAWulWywVWz526T26RsJrIs3VKSgo582zM",
    authDomain: "dths-test.firebaseapp.com",
    databaseURL: "https://dhts-test.firebaseio.com",
    projectId: "dhts-test",
    storageBucket: "dths-test.appspot.com",
    messagingSenderId: "981442331599",
    appId: "1:981442331599:web:964d73ed0c2f0c229848ba",
    measurementId: "G-WM1C854YT1"
};

// const firebaseConfig = {
//     apiKey: dotenv.env['FWEB_API_KEY'],
//     appId: dotenv.env['FWEB_APP_ID'],
//     // messagingSenderId: dotenv.env['FWEB_MESSAGING_SENDER_ID'],
//     projectId: dotenv.env['FWEB_PROJECT_ID'],
//     authDomain: dotenv.env['FWEB_AUTH_DOMAIN'],
//     // storageBucket: dotenv.env['FWEB_STORAGE_BUCKET'],
//     measurementId: dotenv.env['FWEB_MEASUREMENT_ID'],
// };

// Initialize Firebase
const db = setupFirebase(firebaseConfig);

async function importCollection(filePath, collectionName) {
 // Read the JSON file
 const jsonData = fs.readFileSync(filePath);
 const data = JSON.parse(jsonData);

 // Loop through each document and add it to Firestore
 for (const doc of data) {
  try {
   await addDoc(collection(db, collectionName), doc);
   console.log(`Document with ID ${doc.id} added to ${collectionName}.`);
  } catch (e) {
   console.error(`Error adding document with ID ${doc.id}:`, e);
  }
 }
}

// Usage
importCollection('exported.json', 'users')
 .then(() => {
  console.log('Import completed.');
 })
 .catch((e) => {
  console.error('Error importing collection:', e);
 });
