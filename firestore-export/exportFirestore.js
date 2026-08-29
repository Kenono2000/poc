// npm install firebase

// Import the required modules
import { initializeApp } from 'firebase/app';
import {
 getFirestore,
 collection,
 getDocs,
 query,
 limit,
} from 'firebase/firestore';
import fs from 'fs'; // Import the filesystem module
import { setupFirebase } from './firebaseSetup.js';
import { convertTimestamps } from './utils.js';
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
async function exportCollection(collectionName) {
 const colRef = collection(db, collectionName);
 const q = query(colRef, limit(10000));
 const snapshot = await getDocs(q);

 let data = [];
 snapshot.forEach((doc) => {
  const docData = { id: doc.id, ...doc.data() };

  // Convert Firestore Timestamp to JavaScript Date and then to Dart DateTime format
  convertTimestamps(docData);

  data.push(docData);
 });

 return data;
}

// Usage
exportCollection('users')
 .then((data) => {
  const jsonData = JSON.stringify(data, null, 2); // Pretty print JSON
  fs.writeFileSync('exported.json', jsonData); // Write to a JSON file
  console.log('Data exported to exported.json');
 })
 .catch((error) => {
  console.error('Error exporting collection:', error);
 });
