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

const firebaseConfig = {
    apiKey: "AIzaSyBj1ZkLdONxWszZlqjj5uxmJxQHvSN8MvM",
    authDomain: "dhts-412ec.firebaseapp.com",
    databaseURL: "https://dhts-412ec.firebaseio.com",
    projectId: "dhts-412ec",
    storageBucket: "dths-412ec.appspot.com",
    messagingSenderId: "957485492369",
    appId: "1:957485492369:web:5fab5eeebcb6facd713730",
    measurementId: "G-KL1EN6Q1XC"
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
