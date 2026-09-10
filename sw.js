self.addEventListener('install', e=>{self.skipWaiting()});
self.addEventListener('activate', e=>{self.clients.claim()});
self.addEventListener('fetch', e=>{
  // Ne jamais cacher /api/* et /ping pour que UptimeRobot marche
  if(e.request.url.includes('/api/') || e.request.url.includes('/ping')){
    return e.respondWith(fetch(e.request));
  }
  e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
});
