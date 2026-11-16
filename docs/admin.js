import {
  firebaseReady,
  auth,
  db,
  api,
  requestEmailLink,
  completeEmailLink,
  watchAuth,
  categoryLabel,
  retailerLabel
} from './firebase-client.js';

(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let allSubscribers = [];

  function setLoginStatus(message, kind = 'info') {
    $('adminLoginStatus').textContent = message;
    $('adminLoginStatus').className = `form-status ${kind}`;
  }

  function setActionStatus(message, kind = 'info') {
    $('adminActionStatus').textContent = message;
    $('adminActionStatus').className = `form-status ${kind}`;
  }

  function isVerifiedAccount(user) {
    return Boolean(user?.emailVerified && user.email);
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
      const dateA = a.createdAt?.toMillis?.() || 0;
      const dateB = b.createdAt?.toMillis?.() || 0;
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
      $('adminLoginButton').disabled = true;
      try {
        await requestEmailLink(email, 'admin');
        setLoginStatus('A secure sign-in link was sent. Open it from this browser to continue.', 'success');
      } catch (error) {
        setLoginStatus(error?.message || 'Unable to send the sign-in link.', 'error');
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

    try {
      const result = await completeEmailLink();
      if (result && result.mode !== 'admin') {
        setLoginStatus('This email link was created for a different page action. Return to the public website to finish it.', 'warning');
      }
    } catch (error) {
      setLoginStatus(error?.message || 'The sign-in link could not be completed.', 'error');
    }

    watchAuth(async user => {
      if (!user) {
        showLogin();
        return;
      }
      if (!isVerifiedAccount(user)) {
        await api.signOut(auth);
        showLogin();
        setLoginStatus('The administrator account must have a verified email address.', 'error');
        return;
      }
      showAdmin(user);
      try {
        await loadSubscribers();
      } catch (error) {
        await api.signOut(auth);
        showLogin();
        setLoginStatus('This account is not authorized to administer PokéDrop Watch. Use the address configured privately in the deployed Firestore rules.', 'error');
      }
    });
  }

  init().catch(error => setLoginStatus(error?.message || 'Admin page could not initialize.', 'error'));
})();
