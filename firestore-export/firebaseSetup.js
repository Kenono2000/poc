import { initializeApp } from 'firebase/app';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';

export function setupFirebase(config, useEmulator = false, host = '127.0.0.1', port = 8080) {
 const app = initializeApp(config);
 const db = getFirestore(app);
 if (useEmulator) {
  connectFirestoreEmulator(db, host, port);
 }
 return db;
}