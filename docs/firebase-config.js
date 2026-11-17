// Firebase web-app configuration is public browser configuration, not a secret.
// The private administrator email belongs only in the deployed Firestore rules,
// never in this public file.
export const firebaseConfig = {
  apiKey: 'AIzaSyDYii-b7PW8iX3RMM7EhqnzF2vB7XDRJOs',
  authDomain: 'project-4868291462124176670.firebaseapp.com',
  projectId: 'project-4868291462124176670',
  appId: '1:828639177624:web:e5f7383e38aba5d608d9ed',
  messagingSenderId: '828639177624'
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
