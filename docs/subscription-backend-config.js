// Public deployment URL for the standalone Google Apps Script verification bridge.
// This URL is public by design. The service-account key and HMAC secret remain
// private in the Apps Script project's Script Properties.
export const subscriptionBackendUrl = 'https://script.google.com/macros/s/AKfycbyDXJsIvIsM6hRyZ3xPoGnnokkBbRATUU5tFwkLk6g0oAgih2KqhrhSotJ_lZOhvh4/exec';

export function isSubscriptionBackendConfigured() {
  return /^https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec(?:\?.*)?$/.test(subscriptionBackendUrl);
}
