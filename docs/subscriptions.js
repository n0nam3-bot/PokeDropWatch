import './bridge-transport.js';
import { subscriptionBackendUrl, isSubscriptionBackendConfigured } from './subscription-backend-config.js';

(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const frame = $('subscriptionBackendFrame');
  const codePanel = $('verificationCodePanel');
  const statusBox = $('subscriptionStatus');
  let bridgeReady = false;
  let activeFlow = null;
  let readyResolver;
  const readyPromise = new Promise(resolve => { readyResolver = resolve; });
  const pending = new Map();

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
    return { categories, retailers: retailers.length ? retailers : ['all'] };
  }

  function validBackendConfig() {
    return isSubscriptionBackendConfigured();
  }

  function waitForBridge() {
    if (bridgeReady) return Promise.resolve();
    return Promise.race([
      readyPromise,
      new Promise((_, reject) => setTimeout(() => reject(new Error('The email verification bridge did not announce that it loaded. Confirm that Index.html is updated in the deployed Apps Script version and that SITE_ORIGIN is https://n0nam3-bot.github.io.')), 20000))
    ]);
  }

  async function callBackend(action, payload) {
    await waitForBridge();
    const requestId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(requestId);
        reject(new Error('Apps Script did not confirm this verification request. No email delivery was confirmed. Update the Apps Script Index.html and deploy a new version before retrying.'));
      }, 30000);
      pending.set(requestId, result => {
        clearTimeout(timer);
        if (result?.ok) resolve(result);
        else reject(new Error(result?.message || 'The verification request failed.'));
      });
      try {
        frame.contentWindow.postMessage({
          channel: 'pokedrop-watch-verification-v1',
          requestId,
          action,
          payload
        }, '*');
      } catch (error) {
        clearTimeout(timer);
        pending.delete(requestId);
        reject(error);
      }
    });
  }

  async function requestCode(flow) {
    if (!validBackendConfig()) throw new Error('The owner has not configured the email verification service yet. The owner-only setup guide is in the GitHub repository.');
    const result = await callBackend('requestCode', {
      email: flow.email,
      operation: flow.operation,
      categories: flow.preferences?.categories || [],
      retailers: flow.preferences?.retailers || ['all'],
      website: flow.website || ''
    });
    activeFlow = { ...flow, sessionToken: result.sessionToken };
    $('verificationCodeHeading').textContent = flow.operation === 'unsubscribe' ? 'Confirm your unsubscribe' : 'Verify your email address';
    $('verificationCodeMessage').textContent = `A six-digit code was sent to ${flow.email}. Enter it below on this page. The code expires in 10 minutes.`;
    $('verificationCodeInput').value = '';
    codePanel.hidden = false;
    status(result.message, 'success');
    $('verificationCodeInput').focus({ preventScroll: true });
  }

  function showSetupState() {
    status('Email verification is not configured. The site owner must deploy the Apps Script email service and add its /exec URL to docs/subscription-backend-config.js. The owner-only setup guide is in the GitHub repository.', 'warning');
    $('subscribeButton').disabled = true;
    $('unsubscribeButton').disabled = true;
  }

  function init() {
    if (!validBackendConfig()) {
      showSetupState();
      return;
    }

    window.addEventListener('message', event => {
      if (event.source !== frame.contentWindow) return;
      const message = event.data || {};
      if (message.channel !== 'pokedrop-watch-verification-v1') return;
      if (message.ready) {
        bridgeReady = true;
        readyResolver();
        return;
      }
      if (message.requestId && pending.has(message.requestId)) {
        const resolve = pending.get(message.requestId);
        pending.delete(message.requestId);
        resolve(message.result || { ok: false, message: 'The verification service returned an empty response.' });
      }
    });
    frame.addEventListener('load', () => {
      // Readiness is confirmed by the Apps Script postMessage, not by an iframe
      // load event (Google can also load an error document with HTTP 200).
    });
    frame.src = subscriptionBackendUrl;

    $('subscribeForm').addEventListener('submit', async event => {
      event.preventDefault();
      const button = $('subscribeButton');
      button.disabled = true;
      try {
        const preferences = currentPreferences();
        const email = $('subscribeEmail').value.trim().toLowerCase();
        await requestCode({
          operation: 'subscribe',
          email,
          preferences,
          website: $('subscribeWebsite').value
        });
      } catch (error) {
        status(error?.message || 'Unable to send a verification code. Please try again later.', 'error');
      } finally {
        button.disabled = false;
      }
    });

    $('unsubscribeForm').addEventListener('submit', async event => {
      event.preventDefault();
      const button = $('unsubscribeButton');
      button.disabled = true;
      try {
        const email = $('unsubscribeEmail').value.trim().toLowerCase();
        await requestCode({ operation: 'unsubscribe', email, preferences: null, website: '' });
      } catch (error) {
        status(error?.message || 'Unable to send a verification code. Please try again later.', 'error');
      } finally {
        button.disabled = false;
      }
    });

    $('verifyCodeButton').addEventListener('click', async () => {
      if (!activeFlow?.sessionToken) {
        status('Request a new verification code first.', 'error');
        return;
      }
      const button = $('verifyCodeButton');
      button.disabled = true;
      try {
        const result = await callBackend('verifyCode', {
          sessionToken: activeFlow.sessionToken,
          code: $('verificationCodeInput').value.trim()
        });
        status(result.message, 'success');
        codePanel.hidden = true;
        activeFlow = null;
      } catch (error) {
        status(error?.message || 'The code could not be verified.', 'error');
      } finally {
        button.disabled = false;
      }
    });

    $('resendCodeButton').addEventListener('click', async () => {
      if (!activeFlow) return;
      const button = $('resendCodeButton');
      button.disabled = true;
      try {
        await requestCode(activeFlow);
      } catch (error) {
        status(error?.message || 'Unable to send another code.', 'error');
      } finally {
        button.disabled = false;
      }
    });

    $('verificationCodeInput').addEventListener('input', event => {
      event.target.value = event.target.value.replace(/\D/g, '').slice(0, 6);
    });
    $('verificationCodeInput').addEventListener('keydown', event => {
      if (event.key === 'Enter') $('verifyCodeButton').click();
    });

    document.querySelectorAll('input[name="retailer"]').forEach(input => input.addEventListener('change', () => {
      if (input.value === 'all' && input.checked) {
        document.querySelectorAll('input[name="retailer"]').forEach(other => { if (other !== input) other.checked = false; });
      } else if (input.checked) {
        const all = document.querySelector('input[name="retailer"][value="all"]');
        if (all) all.checked = false;
      }
    }));
  }

  init();
})();
