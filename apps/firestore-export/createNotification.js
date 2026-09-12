// To run this script, first make sure you have Node.js installed.
// Then, open your terminal and run the following command to install the Firebase SDK:
// npm install firebase

// Import necessary Firebase functions from the 'firebase/app' and 'firebase/firestore' packages
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, addDoc, connectFirestoreEmulator, doc, setDoc, Timestamp } from 'firebase/firestore';
import 'dotenv/config';
import { setupFirebase } from './firebaseSetup.js';

// const firebaseConfig = {
//     apiKey: process.env.FWEB_API_KEY,
//     appId: process.env.FWEB_APP_ID,
//     messagingSenderId: process.env.FWEB_MESSAGING_SENDER_ID,
//     projectId: process.env.FWEB_PROJECT_ID,
//     authDomain: process.env.FWEB_AUTH_DOMAIN,
//     storageBucket: process.env.FWEB_STORAGE_BUCKET,
//     measurementId: process.env.FWEB_MEASUREMENT_ID
// };
// const app = initializeApp(firebaseConfig);
// const db = getFirestore(app);

const firebaseConfig = {
 apiKey: 'AIzaSyAWulWywVWz526T26RsJrIs3VKSgo582zM',
 authDomain: 'dths-test.firebaseapp.com',
 projectId: 'dths-test',
};
const db = setupFirebase(firebaseConfig, true);

async function addNotificationToUser() {
 try {
  // Hardcoding the user ID as in the original script.
  // In a real application, this might come from a variable or a command-line argument.
  const userId = 'xvwnCTzTxZRwuxSSAgdTNi11Ov13';

  // Reference the user's document
  // This script uses the same path structure as the previous HTML file,
  // which assumes the user document is a standalone document.
  const userRef = doc(db, 'users', userId);

  // Reference the notifications sub-collection within the user's document
  const notificationsCollectionRef = collection(userRef, 'notifications');

  // Define the data for the new notification
  const newNotification = {
   channelId: '2SE4OLb3BISZgZJ82DIh',
   content: 'Happy Monday!',
   created: Timestamp.now(),
   sender: 'users/tu1001-m',
   senderFirstName: 'tu1001-Man',
   senderlastName: 'Last-tu1001',
   targetUserFirstName: 'tu12-Woman',
   type: 'message',
   viewed: false,
  };

  // Add the new document to the collection, with addDoc to auto-generate an ID
  const docRef = await addDoc(notificationsCollectionRef, newNotification);

  console.log(
   '✅ New notification successfully added to user',
   userId,
   'with ID:',
   docRef.id
  );
 } catch (e) {
  // Use console.error for better visibility of errors in the terminal
  console.error('❌ Error adding notification:', e);
 }
}

// Call the main function to start the process
addNotificationToUser();
