/* O site do TrilhaNav deixou de ser um app (PWA): este service worker só apaga o cache antigo e se desliga. */
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>/^trilhanav-/.test(k)).map(k=>caches.delete(k))))
  .then(()=>self.registration.unregister()).then(()=>self.clients.matchAll()).then(cs=>cs.forEach(c=>c.navigate(c.url))))});
