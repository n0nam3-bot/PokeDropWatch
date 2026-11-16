// Firebase web-app configuration is public browser configuration, not a secret.
// The private administrator email belongs only in the deployed Firestore rules,
// never in this public file.
export const firebaseConfig = {
  apiKey: 'PASTE_FIREBASE_WEB_API_KEY',
  authDomain: 'YOUR_PROJECT_ID.firebaseapp.com',
  projectId: 'YOUR_PROJECT_ID',
  appId: 'PASTE_FIREBASE_WEB_APP_ID',
  messagingSenderId: 'PASTE_FIREBASE_MESSAGING_SENDER_ID'
};

export function isFirebaseConfigured() {
  return Boolean(
    firebaseConfig.apiKey && !firebaseConfig.apiKey.startsWith('PASTE_')
    && firebaseConfig.authDomain && !firebaseConfig.authDomain.startsWith('YOUR_')
    && firebaseConfig.projectId && firebaseConfig.projectId !== 'YOUR_PROJECT_ID'
    && firebaseConfig.appId && !firebaseConfig.appId.startsWith('PASTE_')
    && firebaseConfig.messagingSenderId && !firebaseConfig.messagingSenderId.startsWith('PASTE_')
  );
}
