const CACHE = 'pokedrop-shell-v4';
const SHELL = [
  './', './index.html', './admin.html', './styles.css', './app.js',
  './subscriptions.js', './admin.js', './firebase-client.js', './firebase-config.js', './FIREBASE_SETUP.html',
  './pokeball.svg', './manifest.webmanifest'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', event => event.waitUntil(
  caches.keys().then(keys => Promise.all(
    keys.filter(key => key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim())
));

// Network-first keeps GitHub Pages updates and owner-edited Firebase config
// from being hidden behind an older cached copy. The cached shell is fallback
// only when the device is offline.
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || url.pathname.endsWith('/data/state.json')) return;
  if (event.request.method !== 'GET') return;

  event.respondWith(fetch(event.request).then(response => {
    if (response && response.ok) {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(event.request, copy));
    }
    return response;
  }).catch(async () => {
    const cached = await caches.match(event.request);
    if (cached) return cached;
    if (event.request.mode === 'navigate') {
      const home = await caches.match('./index.html');
      if (home) return home;
    }
    return new Response('This page is unavailable offline.', {
      status: 503,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  }));
});
