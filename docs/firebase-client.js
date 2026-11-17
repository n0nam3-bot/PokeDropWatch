import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.0.0/firebase-app.js';
import {
  getAuth,
  isSignInWithEmailLink,
  sendSignInLinkToEmail,
  signInWithEmailLink,
  onAuthStateChanged,
  signOut
} from 'https://www.gstatic.com/firebasejs/12.0.0/firebase-auth.js';
import {
  getFirestore,
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  orderBy,
  serverTimestamp,
  setDoc,
  updateDoc
} from 'https://www.gstatic.com/firebasejs/12.0.0/firebase-firestore.js';
import { firebaseConfig, isFirebaseConfigured } from './firebase-config.js';

export const firebaseReady = isFirebaseConfigured();
const firebaseApp = firebaseReady ? initializeApp(firebaseConfig) : null;
export const auth = firebaseReady ? getAuth(firebaseApp) : null;
export const db = firebaseReady ? getFirestore(firebaseApp) : null;
export const api = {
  isSignInWithEmailLink,
  sendSignInLinkToEmail,
  signInWithEmailLink,
  onAuthStateChanged,
  signOut,
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  orderBy,
  serverTimestamp,
  setDoc,
  updateDoc
};

const STORAGE_EMAIL = 'pokedrop.auth.email';
const STORAGE_MODE = 'pokedrop.auth.mode';
const STORAGE_PAYLOAD = 'pokedrop.auth.payload';

function encodePayload(value) {
  if (!value) return '';
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  let binary = '';
  bytes.forEach(byte => { binary += String.fromCharCode(byte); });
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

function decodePayload(value) {
  if (!value) return null;
  try {
    const base64 = value.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - value.length % 4) % 4);
    const binary = atob(base64);
    const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return null;
  }
}

export async function requestEmailLink(email, mode, payload = null) {
  if (!firebaseReady) throw new Error('Firebase has not been configured yet.');
  const normalizedEmail = String(email || '').trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
    throw new Error('Enter a valid email address.');
  }

  const lastSent = Number(localStorage.getItem(`pokedrop.link.cooldown.${normalizedEmail}`) || 0);
  const waitMs = 60_000 - (Date.now() - lastSent);
  if (waitMs > 0) throw new Error(`Please wait ${Math.ceil(waitMs / 1000)} seconds before requesting another link.`);

  const continuation = new URL(window.location.href);
  continuation.search = '';
  continuation.hash = '';
  continuation.searchParams.set('pokedropAction', mode);
  if (payload) continuation.searchParams.set('pokedropData', encodePayload(payload));

  localStorage.setItem(STORAGE_EMAIL, normalizedEmail);
  localStorage.setItem(STORAGE_MODE, mode);
  if (payload) localStorage.setItem(STORAGE_PAYLOAD, JSON.stringify(payload));
  else localStorage.removeItem(STORAGE_PAYLOAD);
  localStorage.setItem(`pokedrop.link.cooldown.${normalizedEmail}`, String(Date.now()));

  await api.sendSignInLinkToEmail(auth, normalizedEmail, {
    url: continuation.toString(),
    handleCodeInApp: true
  });
  return true;
}

export async function completeEmailLink() {
  if (!firebaseReady || !api.isSignInWithEmailLink(auth, window.location.href)) return null;
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('pokedropAction') || localStorage.getItem(STORAGE_MODE) || 'subscribe';
  const payload = decodePayload(params.get('pokedropData'))
    || JSON.parse(localStorage.getItem(STORAGE_PAYLOAD) || 'null');
  let email = localStorage.getItem(STORAGE_EMAIL);
  if (!email) email = window.prompt('Confirm the email address that received this sign-in link:') || '';
  email = email.trim().toLowerCase();
  if (!email) throw new Error('Email address is required to finish verification.');

  const credential = await api.signInWithEmailLink(auth, email, window.location.href);
  localStorage.removeItem(STORAGE_EMAIL);
  localStorage.removeItem(STORAGE_MODE);
  localStorage.removeItem(STORAGE_PAYLOAD);
  const cleanUrl = `${window.location.pathname}${window.location.hash}`;
  window.history.replaceState({}, document.title, cleanUrl);
  return { user: credential.user, mode, payload };
}

export function watchAuth(callback) {
  if (!firebaseReady) return () => {};
  return api.onAuthStateChanged(auth, callback);
}

export function categoryLabel(value) {
  return ({ tcg: 'Pokémon TCG', plush: 'Plush', collectibles: 'Collectibles', games: 'Games', accessories: 'Accessories & apparel', news: 'News' })[value] || value;
}

export function retailerLabel(value) {
  return ({
    all: 'All retailers',
    'pokemon-center': 'Pokémon Center',
    target: 'Target',
    walmart: 'Walmart',
    'best-buy': 'Best Buy',
    gamestop: 'GameStop',
    amazon: 'Amazon',
    pokebeach: 'PokéBeach'
  })[value] || value;
}

export { serverTimestamp };
