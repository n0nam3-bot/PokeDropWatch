// Public deployment URL for the standalone Google Apps Script verification bridge.
// This URL is public by design. The service-account key and HMAC secret remain
// private in the Apps Script project's Script Properties.
export const subscriptionBackendUrl = 'PASTE_APPS_SCRIPT_WEB_APP_URL';

export function isSubscriptionBackendConfigured() {
  return /^https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec(?:\?.*)?$/.test(subscriptionBackendUrl);
}
