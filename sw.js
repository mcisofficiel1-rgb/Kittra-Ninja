```javascript
// sw.js - Ninja furtif
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => console.log("🔒 KITTRA VAULT NINJA ACTIF"));
self.addEventListener('fetch', e => e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));
```