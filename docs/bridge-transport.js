/*
 * Google Apps Script iframe message compatibility layer.
 *
 * Apps Script web apps can deliver their HTML through a googleusercontent.com
 * frame. When that happens, the message source may be a nested frame rather
 * than the outer iframe element that the page originally created. The
 * existing application listeners intentionally expect the outer iframe's
 * WindowProxy. Relay only this app's channel from trusted Google Apps Script
 * origins and normalize the source before the application listeners run.
 */
(() => {
  'use strict';

  const CHANNEL = 'pokedrop-watch-verification-v1';
  const FRAME_IDS = ['adminBackendFrame', 'subscriptionBackendFrame'];

  function isTrustedAppsScriptOrigin(origin) {
    try {
      const url = new URL(origin);
      if (url.protocol !== 'https:') return false;
      const host = url.hostname.toLowerCase();
      return host === 'script.google.com'
        || host === 'script.googleusercontent.com'
        || host === 'googleusercontent.com'
        || host.endsWith('.googleusercontent.com');
    } catch (_error) {
      return false;
    }
  }

  window.addEventListener('message', event => {
    const message = event.data;
    if (!message || message.channel !== CHANNEL) return;
    if (!isTrustedAppsScriptOrigin(event.origin)) return;

    const frame = FRAME_IDS
      .map(id => document.getElementById(id))
      .find(candidate => candidate && candidate.isConnected);
    if (!frame) return;

    // Messages already originating from the expected iframe are handled
    // normally. Only normalize nested Apps Script frame messages.
    if (event.source === frame.contentWindow) return;

    const relayed = new MessageEvent('message', {
      data: message,
      origin: event.origin,
      lastEventId: event.lastEventId,
      source: frame.contentWindow
    });
    window.dispatchEvent(relayed);
    event.stopImmediatePropagation();
  });

})();
