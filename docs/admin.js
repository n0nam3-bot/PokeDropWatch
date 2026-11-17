import { subscriptionBackendUrl, isSubscriptionBackendConfigured } from './subscription-backend-config.js';

(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const frame = $('adminBackendFrame');
  const CHANNEL = 'pokedrop-watch-verification-v1';
  const SESSION_KEY = 'pokedropAdminSession';
  const pending = new Map();
  let bridgeReady = false;
  let readyResolve;
  const bridgeReadyPromise = new Promise(resolve => { readyResolve = resolve; });
  let sessionToken = sessionStorage.getItem(SESSION_KEY) || '';
  let allSubscribers = [];
  let resetSessionToken = '';

  const CATEGORY_LABELS = {
    tcg: 'Trading cards & TCG', plush: 'Plush', collectibles: 'Collectibles & figures',
    games: 'Video games', accessories: 'Accessories & apparel', news: 'News'
  };
  const RETAILER_LABELS = {
    all: 'All retailers', 'pokemon-center': 'Pokémon Center', target: 'Target',
    walmart: 'Walmart', 'best-buy': 'Best Buy', gamestop: 'GameStop',
    amazon: 'Amazon', pokebeach: 'PokéBeach'
  };
  const categoryLabel = value => CATEGORY_LABELS[value] || String(value || 'Unknown');
  const retailerLabel = value => RETAILER_LABELS[value] || String(value || 'Unknown');

  function statusBox(id, message, kind = 'info') {
    const element = $(id);
    element.textContent = message;
    element.className = `form-status ${kind}`;
  }

  function setLoginStatus(message, kind = 'info') { statusBox('adminLoginStatus', message, kind); }
  function setActionStatus(message, kind = 'info') { statusBox('adminActionStatus', message, kind); }
  function prettyDate(value) {
    if (!value) return 'Date unavailable';
    const date = typeof value.toDate === 'function' ? value.toDate() : new Date(value);
    return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  }

  function waitForBridge() {
    if (bridgeReady) return Promise.resolve();
    return Promise.race([
      bridgeReadyPromise,
      new Promise((_, reject) => setTimeout(() => reject(new Error('The admin service has not loaded. Check the Apps Script /exec URL in docs/subscription-backend-config.js and redeploy Apps Script.')), 20000))
    ]);
  }

  async function callBackend(action, payload = {}) {
    await waitForBridge();
    const requestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(requestId);
        reject(new Error('The admin service did not respond. Check Apps Script → Executions.'));
      }, 30000);
      pending.set(requestId, result => {
        clearTimeout(timer);
        if (result?.ok) resolve(result);
        else reject(new Error(result?.message || 'The admin request failed.'));
      });
      frame.contentWindow.postMessage({ channel: CHANNEL, requestId, action, payload }, '*');
    });
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
    } else if (item.status === 'rejected' || item.status === 'unsubscribed') {
      addButton('Approve', 'active', 'Previously closed application approved');
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
    const result = await callBackend('adminListSubscribers', { sessionToken });
    allSubscribers = Array.isArray(result.subscribers) ? result.subscribers : [];
    allSubscribers.sort((a, b) => Date.parse(b.createdAt || '') - Date.parse(a.createdAt || ''));
    renderStats();
    renderList();
    $('adminIdentity').textContent = result.email || '';
  }

  async function changeStatus(uid, nextStatus, note, button) {
    button.disabled = true;
    try {
      const result = await callBackend('adminUpdateSubscriber', { sessionToken, uid, status: nextStatus, note });
      setActionStatus(result.message || `Subscriber status updated to ${nextStatus}.`, 'success');
      await loadSubscribers();
    } catch (error) {
      setActionStatus(error?.message || 'The status could not be updated.', 'error');
      if (/session expired/i.test(error?.message || '')) signOut(false);
      button.disabled = false;
    }
  }

  function showAdmin() {
    $('adminLoginPanel').hidden = true;
    $('adminResetPanel').hidden = true;
    $('adminDashboard').hidden = false;
  }
  function showLogin() {
    $('adminLoginPanel').hidden = false;
    $('adminDashboard').hidden = true;
  }
  async function signOut(remote = true) {
    const oldToken = sessionToken;
    sessionToken = '';
    sessionStorage.removeItem(SESSION_KEY);
    allSubscribers = [];
    if (remote && oldToken && bridgeReady) {
      try { await callBackend('adminLogout', { sessionToken: oldToken }); } catch { /* Local sign-out still succeeds. */ }
    }
    showLogin();
  }

  function setupResetFlow() {
    $('forgotPasswordButton').addEventListener('click', () => {
      $('adminResetPanel').hidden = false;
      $('resetAdminEmail').value = $('adminEmailInput').value.trim();
      $('resetCodeFields').hidden = true;
      statusBox('adminResetStatus', 'A reset code will only be sent if this email matches the configured administrator account.', 'info');
    });
    $('cancelAdminResetButton').addEventListener('click', () => {
      $('adminResetPanel').hidden = true;
      resetSessionToken = '';
    });
    $('requestAdminResetButton').addEventListener('click', async () => {
      const button = $('requestAdminResetButton');
      button.disabled = true;
      try {
        const result = await callBackend('requestAdminPasswordReset', { email: $('resetAdminEmail').value.trim().toLowerCase() });
        resetSessionToken = result.sessionToken;
        $('resetCodeFields').hidden = false;
        statusBox('adminResetStatus', result.message, 'success');
        $('adminResetCode').focus({ preventScroll: true });
      } catch (error) {
        statusBox('adminResetStatus', error?.message || 'A reset code could not be sent.', 'error');
      } finally {
        button.disabled = false;
      }
    });
    $('completeAdminResetButton').addEventListener('click', async () => {
      const button = $('completeAdminResetButton');
      button.disabled = true;
      try {
        const result = await callBackend('completeAdminPasswordReset', {
          sessionToken: resetSessionToken,
          code: $('adminResetCode').value.trim(),
          newPassword: $('adminNewPassword').value
        });
        statusBox('adminResetStatus', result.message, 'success');
        $('adminPasswordInput').value = '';
        $('adminEmailInput').value = $('resetAdminEmail').value.trim();
        $('adminResetPanel').hidden = true;
        $('adminLoginPanel').hidden = false;
        resetSessionToken = '';
      } catch (error) {
        statusBox('adminResetStatus', error?.message || 'The password could not be changed.', 'error');
      } finally {
        button.disabled = false;
      }
    });
    $('adminResetCode').addEventListener('input', event => {
      event.target.value = event.target.value.replace(/\D/g, '').slice(0, 6);
    });
  }

  async function init() {
    if (!isSubscriptionBackendConfigured()) {
      $('adminLoginButton').disabled = true;
      $('requestAdminResetButton').disabled = true;
      setLoginStatus('The admin email service is not configured. Add the Apps Script /exec URL to docs/subscription-backend-config.js.', 'warning');
      $('adminSetupNotice').hidden = false;
      return;
    }
    // Register the listener before navigating the iframe. Apps Script can emit
    // its ready message immediately after load; assigning src first can race it.
    window.addEventListener('message', event => {
      if (event.source !== frame.contentWindow || event.data?.channel !== CHANNEL) return;
      const message = event.data;
      if (message.ready) {
        bridgeReady = true;
        readyResolve();
      } else if (message.requestId && pending.has(message.requestId)) {
        const resolve = pending.get(message.requestId);
        pending.delete(message.requestId);
        resolve(message.result || { ok: false, message: 'The admin service returned an empty response.' });
      }
    });
    frame.src = subscriptionBackendUrl;

    $('adminLoginForm').addEventListener('submit', async event => {
      event.preventDefault();
      const button = $('adminLoginButton');
      button.disabled = true;
      try {
        const result = await callBackend('adminLogin', {
          email: $('adminEmailInput').value.trim().toLowerCase(),
          password: $('adminPasswordInput').value
        });
        sessionToken = result.sessionToken;
        sessionStorage.setItem(SESSION_KEY, sessionToken);
        await loadSubscribers();
        showAdmin();
        setActionStatus('Administrator session active. It expires one hour after sign-in.', 'success');
      } catch (error) {
        setLoginStatus(error?.message || 'Unable to sign in.', 'error');
      } finally {
        button.disabled = false;
      }
    });

    $('adminSignOut').addEventListener('click', () => signOut(true));
    $('subscriberFilter').addEventListener('change', renderList);
    setupResetFlow();

    if (sessionToken) {
      try {
        await loadSubscribers();
        showAdmin();
      } catch (_error) {
        sessionToken = '';
        sessionStorage.removeItem(SESSION_KEY);
        showLogin();
      }
    } else {
      showLogin();
    }
  }

  init().catch(error => setLoginStatus(error?.message || 'Admin page could not initialize.', 'error'));
})();
