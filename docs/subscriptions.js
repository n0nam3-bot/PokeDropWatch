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
  const statusBox = $('subscriptionStatus');
  const accountBox = $('subscriptionAccount');
  const unsubscribeConfirm = $('unsubscribeConfirm');
  let currentUser = null;
  let currentRecord = null;

  function status(message, kind = 'info') {
    statusBox.textContent = message;
    statusBox.className = `form-status ${kind}`;
  }

  function selectedValues(name) {
    return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value);
  }

  function currentPreferences() {
    const categories = selectedValues('category');
    const retailers = selectedValues('retailer');
    if (!categories.length) throw new Error('Choose at least one notification category.');
    return {
      categories,
      retailers: retailers.length ? retailers : ['all']
    };
  }

  function applyPreferencesToForm(record) {
    const categories = record?.categories || ['tcg', 'plush', 'collectibles', 'games', 'accessories', 'news'];
    const retailers = record?.retailers || ['all'];
    document.querySelectorAll('input[name="category"]').forEach(input => { input.checked = categories.includes(input.value); });
    document.querySelectorAll('input[name="retailer"]').forEach(input => { input.checked = retailers.includes(input.value); });
  }

  function renderAccount(user, record) {
    currentUser = user;
    currentRecord = record;
    if (!user || !record) {
      accountBox.hidden = true;
      return;
    }
    accountBox.hidden = false;
    $('subscriberEmail').textContent = user.email || 'Verified account';
    const stateText = ({
      pending: 'Application pending administrator approval',
      active: 'Approved — email alerts are active',
      rejected: 'Application not approved',
      suspended: 'Notifications are temporarily paused',
      unsubscribed: 'You are unsubscribed',
      removed: 'This subscription was removed by the administrator'
    })[record.status] || 'Subscription status unavailable';
    $('subscriberState').textContent = stateText;
    const mayEdit = ['pending', 'active', 'suspended'].includes(record.status);
    $('savePreferencesButton').hidden = !mayEdit;
    $('subscriberSignOutButton').hidden = false;
    applyPreferencesToForm(record);
  }

  async function loadOwnRecord(user) {
    if (!user || !user.emailVerified) {
      renderAccount(null, null);
      return null;
    }
    const snapshot = await api.getDoc(api.doc(db, 'subscribers', user.uid));
    const record = snapshot.exists() ? snapshot.data() : null;
    renderAccount(user, record);
    return record;
  }

  async function storeApplication(user, preferences) {
    if (!user.emailVerified) throw new Error('Email verification was not completed. Please request a new sign-in link.');
    const ref = api.doc(db, 'subscribers', user.uid);
    const snapshot = await api.getDoc(ref);
    const now = api.serverTimestamp();
    if (!snapshot.exists()) {
      await api.setDoc(ref, {
        email: user.email,
        status: 'pending',
        categories: preferences.categories,
        retailers: preferences.retailers,
        createdAt: now,
        updatedAt: now
      });
      return 'Your email is verified and your application has been submitted for administrator approval.';
    }

    const previous = snapshot.data();
    if (['unsubscribed', 'rejected'].includes(previous.status)) {
      await api.updateDoc(ref, {
        status: 'pending',
        categories: preferences.categories,
        retailers: preferences.retailers,
        updatedAt: now,
        reappliedAt: now
      });
      return 'Your email is verified and your new application is pending administrator approval.';
    }
    await api.updateDoc(ref, {
      categories: preferences.categories,
      retailers: preferences.retailers,
      updatedAt: now
    });
    return previous.status === 'active'
      ? 'Your notification preferences have been updated.'
      : `Your application is currently ${previous.status || 'pending'}. Your preferences have been saved.`;
  }

  async function handleIncomingLink() {
    const url = new URL(window.location.href);
    if (!url.searchParams.has('oobCode') && !url.searchParams.has('mode')) return;
    try {
      const result = await completeEmailLink();
      if (!result) return;
      if (result.mode === 'unsubscribe') {
        const snapshot = await api.getDoc(api.doc(db, 'subscribers', result.user.uid));
        if (!snapshot.exists() || ['unsubscribed', 'removed'].includes(snapshot.data().status)) {
          status('No active notification subscription was found for this verified email. No changes were made.', 'info');
          unsubscribeConfirm.hidden = true;
          return;
        }
        currentUser = result.user;
        unsubscribeConfirm.hidden = false;
        status('Email ownership verified. Confirm below to stop notifications for this address.', 'success');
        return;
      }
      const preferences = result.payload || currentPreferences();
      const message = await storeApplication(result.user, preferences);
      status(message, 'success');
      await loadOwnRecord(result.user);
    } catch (error) {
      status(error?.message || 'The email link could not be completed. Request a new link and try again.', 'error');
    }
  }

  async function init() {
    if (!firebaseReady) {
      status('Subscription setup is not finished. The site owner must configure Firebase by following ./FIREBASE_SETUP.html.', 'warning');
      $('subscribeButton').disabled = true;
      $('unsubscribeButton').disabled = true;
      return;
    }

    $('subscribeForm').addEventListener('submit', async event => {
      event.preventDefault();
      const email = $('subscribeEmail').value.trim().toLowerCase();
      $('subscribeButton').disabled = true;
      try {
        const preferences = currentPreferences();
        if (currentUser?.email?.toLowerCase() === email && currentUser.emailVerified && currentRecord) {
          const message = await storeApplication(currentUser, preferences);
          await loadOwnRecord(currentUser);
          status(message, 'success');
        } else {
          await requestEmailLink(email, 'subscribe', preferences);
          status('Check your inbox for a secure sign-in link. Your application is not submitted until you open that link.', 'success');
        }
      } catch (error) {
        status(error?.message || 'Unable to start your application. Please try again later.', 'error');
      } finally {
        $('subscribeButton').disabled = false;
      }
    });

    $('unsubscribeForm').addEventListener('submit', async event => {
      event.preventDefault();
      const email = $('unsubscribeEmail').value.trim().toLowerCase();
      $('unsubscribeButton').disabled = true;
      try {
        await requestEmailLink(email, 'unsubscribe');
        status('If this address uses PokéDrop Watch, a secure confirmation link has been sent. Opening the link will not unsubscribe it by itself; a final confirmation is required.', 'success');
      } catch (error) {
        status(error?.message || 'Unable to send a verification link. Please try again later.', 'error');
      } finally {
        $('unsubscribeButton').disabled = false;
      }
    });

    $('confirmUnsubscribeButton').addEventListener('click', async () => {
      if (!currentUser?.emailVerified) {
        status('Verify the email address before unsubscribing.', 'error');
        return;
      }
      try {
        await api.updateDoc(api.doc(db, 'subscribers', currentUser.uid), {
          status: 'unsubscribed',
          unsubscribedAt: api.serverTimestamp(),
          updatedAt: api.serverTimestamp()
        });
        unsubscribeConfirm.hidden = true;
        status('You have been unsubscribed. No further product alerts will be sent to this address.', 'success');
        await loadOwnRecord(currentUser);
      } catch (error) {
        status(error?.message || 'Unsubscription could not be completed. Please contact the site administrator.', 'error');
      }
    });

    $('savePreferencesButton').addEventListener('click', () => {
      if (currentUser?.email) $('subscribeEmail').value = currentUser.email;
      $('subscribeForm').requestSubmit();
    });

    document.querySelectorAll('input[name="retailer"]').forEach(input => input.addEventListener('change', () => {
      if (input.value === 'all' && input.checked) {
        document.querySelectorAll('input[name="retailer"]').forEach(other => { if (other !== input) other.checked = false; });
      } else if (input.checked) {
        const all = document.querySelector('input[name="retailer"][value="all"]');
        if (all) all.checked = false;
      }
    }));

    $('subscriberSignOutButton').addEventListener('click', async () => {
      await api.signOut(auth);
      currentUser = null;
      currentRecord = null;
      renderAccount(null, null);
      status('You have signed out.', 'info');
    });

    watchAuth(async user => {
      if (user?.emailVerified) {
        try { await loadOwnRecord(user); } catch { /* Firestore rules keep non-owner records private. */ }
      } else {
        renderAccount(null, null);
      }
    });
    await handleIncomingLink();
    if (new URLSearchParams(window.location.search).get('unsubscribe') === '1') {
      $('unsubscribeEmail').focus({ preventScroll: true });
      $('subscriptions').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  init().catch(error => status(error?.message || 'Subscription interface could not initialize.', 'error'));
})();
