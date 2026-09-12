export function convertTimestamps(obj) {
 if (Array.isArray(obj)) {
  obj.forEach(convertTimestamps);
 } else if (obj && typeof obj === 'object') {
  for (const key in obj) {
   if (obj[key] && typeof obj[key] === 'object' && obj[key].toDate) {
    obj[key] = obj[key].toDate().toISOString();
   } else {
    convertTimestamps(obj[key]);
   }
  }
 }
}