/* Retired compatibility stub.
 * PokéDrop Watch v1.4.0 does not use Firebase Authentication or browser-side
 * Firestore access. Admin login, email codes, and subscriber management use
 * the private Google Apps Script bridge; Firestore is accessed server-side
 * with a service account. This file remains only so stale imports fail safely.
 */
export const firebaseReady = false;
export const auth = null;
export const db = null;
export const api = Object.freeze({});
export function watchAuth(callback) {
  if (typeof callback === 'function') callback(null);
  return () => {};
}
