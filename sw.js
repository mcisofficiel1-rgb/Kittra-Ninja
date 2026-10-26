// KITTRA V23 FINAL - Service Worker Anti-Dormeur + PWA
const CACHE_NAME = 'kittra-v23-final';
const URLS_TO_CACHE = ['/', '/index.html', '/manifest.json', '/kittra.json'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('KITTRA V23 Cache ouvert');
      return cache.addAll(URLS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(keys.map(k => { if(k !== CACHE_NAME) return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Ne cache pas les API, toujours frais
  if(event.request.url.includes('/etat') || event.request.url.includes('/ping') || event.request.url.includes('/scan') || event.request.url.includes('/api/')){
    event.respondWith(fetch(event.request).catch(()=>caches.match('/index.html')));
    return;
  }
  event.respondWith(
    caches.match(event.request).then(res => {
      return res || fetch(event.request);
    })
  );
});

// PING ANTI-DORMEUR toutes les 3 min même si onglet fermé
setInterval(() => {
  fetch('/ping').catch(()=>{});
  console.log('KITTRA V23 PING anti-dormeur');
}, 180000); // 3 min

// Notification si trade
self.addEventListener('push', event => {
  const data = event.data ? event.data.text() : 'KITTRA V23 Trade';
  event.waitUntil(
    self.registration.showNotification('KITTRA V23', {
      body: data,
      icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='45' fill='red'/></svg>",
      vibrate: [200,100,200]
    })
  );
});
