const CACHE = 'pokedrop-shell-v15';
const SHELL = [
  './', './index.html', './admin.html', './notify.html', './styles.css', './theme-overrides.css',
  './app.js', './page-enhancements.js', './subscriptions.js', './admin.js', './bridge-transport.js',
  './subscription-backend-config.js', './SOURCE_HEALTH.html', './pokeball.svg', './manifest.webmanifest',
  './assets/icons/pokeball-8bit.png', './assets/icons/ultraball-8bit.png', './assets/icons/masterball-8bit.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', event => event.waitUntil(
  caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith('pokedrop-shell-') && key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim())
));

// Always request current HTML and scripts from GitHub Pages first; cache only
// successful responses for offline use. State JSON always comes directly from network.
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || url.pathname.endsWith('/data/state.json')) return;
  if (event.request.method !== 'GET') return;
  event.respondWith(fetch(new Request(event.request, { cache: 'no-store' })).then(response => {
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
