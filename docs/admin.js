import {
  firebaseReady,
  auth,
  db,
  api,
  watchAuth
} from './firebase-client.js';

(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let allSubscribers = [];

  const CATEGORY_LABELS = {
    tcg: 'Trading cards & TCG',
    plush: 'Plush',
    collectibles: 'Collectibles & figures',
    games: 'Video games',
    accessories: 'Accessories & apparel',
    news: 'News'
  };
  const RETAILER_LABELS = {
    all: 'All retailers',
    'pokemon-center': 'Pokémon Center',
    target: 'Target',
    walmart: 'Walmart',
    'best-buy': 'Best Buy',
    gamestop: 'GameStop',
    amazon: 'Amazon',
    pokebeach: 'PokéBeach'
  };
  const categoryLabel = value => CATEGORY_LABELS[value] || String(value || 'Unknown');
  const retailerLabel = value => RETAILER_LABELS[value] || String(value || 'Unknown');

  function setLoginStatus(message, kind = 'info') {
    $('adminLoginStatus').textContent = message;
    $('adminLoginStatus').className = `form-status ${kind}`;
  }

  function setActionStatus(message, kind = 'info') {
    $('adminActionStatus').textContent = message;
    $('adminActionStatus').className = `form-status ${kind}`;
  }

  function prettyDate(value) {
    if (!value) return 'Date unavailable';
    const date = typeof value.toDate === 'function' ? value.toDate() : new Date(value);
    return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  }

  function renderStats() {
    const count = status => allSubscribers.filter(item => item.status === status).length;
    $('pendingCount').textContent = count('pending');
    $('activeCount').textContent = count('active');
    $('otherCount').textContent = allSubscribers.length - count('pending') - count('active');
  }

  function createSubscriberCard(item) {
    const card = document.createElement('article');
    card.className = 'subscriber-card';
    const info = document.createElement('div');
    info.className = 'subscriber-info';
    const email = document.createElement('strong');
    email.textContent = item.email || 'Email not available';
    const meta = document.createElement('p');
    meta.textContent = `Applied: ${prettyDate(item.createdAt)} · Categories: ${(item.categories || []).map(categoryLabel).join(', ') || 'None'} · Retailers: ${(item.retailers || []).map(retailerLabel).join(', ') || 'None'}`;
    const badge = document.createElement('span');
    badge.className = `subscriber-badge status-${item.status || 'unknown'}`;
    badge.textContent = (item.status || 'unknown').replaceAll('_', ' ');
    info.append(email, meta, badge);
    const actions = document.createElement('div');
    actions.className = 'subscriber-actions';
    const addButton = (label, nextStatus, note) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = label === 'Approve' || label === 'Reactivate' ? 'small-primary' : 'small-secondary';
      button.textContent = label;
      button.addEventListener('click', () => changeStatus(item.uid, nextStatus, note, button));
      actions.append(button);
    };
    if (item.status === 'pending') {
      addButton('Approve', 'active', 'Application approved');
      addButton('Reject', 'rejected', 'Application rejected');
    } else if (item.status === 'active') {
      addButton('Suspend', 'suspended', 'Subscription suspended');
      addButton('Remove', 'removed', 'Subscription removed by administrator');
    } else if (item.status === 'suspended') {
      addButton('Reactivate', 'active', 'Subscription reactivated');
      addButton('Remove', 'removed', 'Subscription removed by administrator');
    } else if (item.status === 'rejected') {
      addButton('Approve', 'active', 'Previously rejected application approved');
      addButton('Remove', 'removed', 'Application removed by administrator');
    }
    card.append(info, actions);
    return card;
  }

  function renderList() {
    const target = $('subscriberList');
    target.replaceChildren();
    const filter = $('subscriberFilter').value;
    const records = allSubscribers.filter(item => filter === 'all' || item.status === filter);
    if (!records.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No records in this category.';
      target.append(empty);
      return;
    }
    records.forEach(item => target.append(createSubscriberCard(item)));
  }

  async function loadSubscribers() {
    const snapshot = await api.getDocs(api.collection(db, 'subscribers'));
    allSubscribers = snapshot.docs.map(record => ({ uid: record.id, ...record.data() }));
    allSubscribers.sort((a, b) => {
      const dateA = a.createdAt?.toMillis?.() || Date.parse(a.createdAt || '') || 0;
      const dateB = b.createdAt?.toMillis?.() || Date.parse(b.createdAt || '') || 0;
      return dateB - dateA;
    });
    renderStats();
    renderList();
  }

  async function changeStatus(uid, nextStatus, note, button) {
    button.disabled = true;
    try {
      await api.updateDoc(api.doc(db, 'subscribers', uid), {
        status: nextStatus,
        adminNote: note,
        adminActionAt: api.serverTimestamp(),
        updatedAt: api.serverTimestamp()
      });
      setActionStatus(`Subscriber status updated to “${nextStatus}”.`, 'success');
      await loadSubscribers();
    } catch (error) {
      setActionStatus(error?.message || 'The status could not be updated.', 'error');
      button.disabled = false;
    }
  }

  function showAdmin(user) {
    $('adminLoginPanel').hidden = true;
    $('adminDashboard').hidden = false;
    $('adminSetupNotice').hidden = true;
    $('adminIdentity').textContent = user.email;
  }

  function showLogin() {
    $('adminLoginPanel').hidden = false;
    $('adminDashboard').hidden = true;
  }

  async function init() {
    if (!firebaseReady) {
      $('adminLoginButton').disabled = true;
      setLoginStatus('Firebase is not configured. Complete ./FIREBASE_SETUP.html before using administration.', 'warning');
      return;
    }
    $('adminSetupNotice').hidden = true;
    $('adminLoginForm').addEventListener('submit', async event => {
      event.preventDefault();
      const email = $('adminEmailInput').value.trim().toLowerCase();
      const password = $('adminPasswordInput').value;
      $('adminLoginButton').disabled = true;
      try {
        await api.signInWithEmailAndPassword(auth, email, password);
        setLoginStatus('Signed in. Loading subscriber records…', 'success');
      } catch (error) {
        const message = error?.code === 'auth/invalid-credential'
          ? 'Email or password is incorrect. Confirm the admin account was created in Firebase Authentication with Email/Password enabled.'
          : (error?.message || 'Unable to sign in.');
        setLoginStatus(message, 'error');
      } finally {
        $('adminLoginButton').disabled = false;
      }
    });

    $('adminSignOut').addEventListener('click', async () => {
      await api.signOut(auth);
      showLogin();
      setLoginStatus('You have signed out.', 'info');
    });
    $('subscriberFilter').addEventListener('change', renderList);

    watchAuth(async user => {
      if (!user) {
        showLogin();
        return;
      }
      try {
        await loadSubscribers();
        showAdmin(user);
      } catch (error) {
        await api.signOut(auth);
        showLogin();
        setLoginStatus('This account is not authorized to administer PokéDrop Watch. Confirm its email matches the administrator address in the deployed Firestore Rules.', 'error');
      }
    });
  }

  init().catch(error => setLoginStatus(error?.message || 'Admin page could not initialize.', 'error'));
})();
