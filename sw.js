// KITTRA V22.2 NINJA - Service Worker ULTIME SCAN ALL 40s - 2 MODES
const CACHE_NAME = 'kittra-v22-2-scan-all-puissance';
const VAULT = 'TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG';
const VERSION = 'V22.2';
const SCAN_INTERVAL = 40 * 1000; // 40s comme main.py
const PING_INTERVAL = 4 * 60 * 1000; // 4 min anti-dormeur

console.log(`🔥 KITTRA ${VERSION} SW PUISSANCE CHARGÉ - Vault:`, VAULT);

self.addEventListener('install', e => {
  console.log(`🚀 KITTRA ${VERSION} INSTALL - 2 MODES MOLO/BALEINE - SCAN ALL 40s`);
  self.skipWaiting();
  // Pré-cache HLM V22.2
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(['/','/index.html']).catch(()=>{});
    })
  );
});

self.addEventListener('activate', e => {
  console.log(`⚡ KITTRA ${VERSION} ACTIVATE - Eternel SCAN ALL 40s - Gardien mcisofficiel1`);
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => {
        console.log(`🗑️ Suppression ancien cache: ${k}`);
        return caches.delete(k);
      })
    )).then(() => {
      self.clients.claim();
      // LANCE ANTI-DORMEUR V22.2 IMMEDIAT
      startKeepAlive();
    })
  );
});

// ===== COEUR V22.2 - NE JAMAIS CACHER LES ROUTES CRITIQUES =====
self.addEventListener('fetch', e => {
  const url = e.request.url;
  
  // V22.2 BOOST: Routes critiques = JAMAIS en cache, toujours LIVE
  if(url.includes('/api/') || url.includes('/ping') || url.includes('/health') || url.includes('/set_mode')) {
    return e.respondWith(
      fetch(e.request, {cache:'no-store', headers:{'Cache-Control':'no-cache','X-Kittra-Version':VERSION,'X-Kittra-Mode':'SCAN-ALL'}})
        .then(res => {
          console.log(`🔍 KITTRA ${VERSION} LIVE FETCH:`, url.split('/').pop());
          return res;
        })
        .catch(() => {
          // Si API dort, on renvoie Vault secure mais on alerte
          return new Response(JSON.stringify({ 
            status: `KITTRA ${VERSION} OFFLINE mais VAULT SECURE + SCAN ALL EN ATTENTE`, 
            vault: VAULT, 
            capital: "SECURE", 
            mode: "BALEINE_FURTIF",
            scan_interval: "40s",
            error: "API dort, mais coffre TRON intact + Service Worker garde en vie",
            retry_in: "40s"
          }), {headers: {'Content-Type': 'application/json','X-Kittra-SW':VERSION}})
        )
    );
  }
  
  // Pour le HLM V22.2: Network first, puis cache, puis offline
  e.respondWith(
    fetch(e.request)
      .then(res => {
        // Sauvegarde que si c'est HLM, pas API
        if(res.ok && !url.includes('/api/')) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return res;
      })
      .catch(() => {
        return caches.match(e.request).then(cached => {
          if(cached) {
            console.log(`📦 CACHE HIT V22.2:`, url);
            return cached;
          }
          // Offline total - HLM minimal V22.2
          return new Response(`
            <html><body style="background:#000;color:#f
