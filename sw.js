// KITTRA V17.4 ULTIME - Service Worker Eternel Anti-Dormeur
const CACHE_NAME = 'kittra-v17-4-ultime';
const VAULT = 'TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG';

self.addEventListener('install', e => {
  console.log('KITTRA V17.4 INSTALL - Gardien');
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  console.log('KITTRA V17.4 ACTIVATE - Eternel');
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;
  
  // V17.4 BOOST: Ne JAMAIS cacher les routes critiques
  if(url.includes('/api/') || url.includes('/ping') || url.includes('/health')) {
    return e.respondWith(
      fetch(e.request)
        .then(res => {
          console.log('KITTRA LIVE:', url);
          return res;
        })
        .catch(() => new Response(JSON.stringify({
          status: "KITTRA V17.4 OFFLINE mais VAULT SECURE",
          vault: VAULT,
          capital: "SECURE",
          error: "API dort, mais coffre TRON intact"
        }), {headers: {'Content-Type': 'application/json'}}))
    );
  }

  // Pour le reste: Network first puis cache
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

// V17.4 BOOST: Garde en vie en arrière plan
self.addEventListener('periodicsync', e => {
  if(e.tag === 'kittra-keepalive') {
    e.waitUntil(fetch('/ping'));
  }
});

console.log('KITTRA V17.4 SW ULTIME CHARGÉ - Vault:', VAULT);
