// KITTRA V26 NINJA FINAL - Service Worker Anti-Dormeur + PWA + BYBIT
const CACHE_NAME = 'kittra-v26-ninja';
const URLS_TO_CACHE = ['/', '/index.html', '/manifest.json', '/kittra.json'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('KITTRA V26 Cache ouvert BYBIT');
      return cache.addAll(URLS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(keys.map(k => {
        if (k !== CACHE_NAME) return caches.delete(k);
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = event.request.url;
  // V26 - Ne cache JAMAIS les API trading / bybit / telegram - toujours frais
  if (
    url.includes('/etat') ||
    url.includes('/ping') ||
    url.includes('/scan-ninja') ||
    url.includes('/test-telegram') ||
    url.includes('/bilan') ||
    url.includes('/profit') ||
    url.includes('/api/')
  ) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/index.html'))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then(res => {
      return res || fetch(event.request);
    })
  );
});

// PING ANTI-DORMEUR V26 - toutes les 2 min 30 (Render dort à 15min)
setInterval(() => {
  fetch('/ping').then(r => r.json()).then(d => {
    console.log('KITTRA V26 PING anti-dormeur BYBIT', d.bybit || d.ok);
  }).catch(() => {});
}, 150000); // 2.5 min

// PING DE SECOURS - /etat toutes les 5 min pour garder Bybit frais
setInterval(() => {
  fetch('/etat').catch(() => {});
  console.log('KITTRA V26 ETAT refresh');
}, 300000); // 5 min

// Notification PUSH si trade Bybit
self.addEventListener('push', event => {
  const data = event.data ? event.data.text() : 'KITTRA V26 Trade BYBIT';
  event.waitUntil(
    self.registration.showNotification('KITTRA V26 BYBIT', {
      body: data,
      icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='45' fill='red'/></svg>",
      badge: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='45' fill='red'/></svg>",
      vibrate: [200, 100, 200],
      tag: 'kittra-v26-trade'
    })
  );
});
