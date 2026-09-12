// Import the required modules
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, addDoc } from 'firebase/firestore';
import fs from 'fs'; // Import the filesystem module
import { setupFirebase } from './firebaseSetup.js';
import dotenv from 'dotenv';

dotenv.config();

const firebaseConfig = {
    apiKey: process.env.FIREBASE_API_KEY,
    authDomain: process.env.FIREBASE_AUTH_DOMAIN,
    databaseURL: process.env.FIREBASE_DATABASE_URL,
    projectId: process.env.FIREBASE_PROJECT_ID,
    storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.FIREBASE_APP_ID,
    measurementId: process.env.FIREBASE_MEASUREMENT_ID
};

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
