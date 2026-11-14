const V='trilhanav-v2';
const CORE=['./','index.html','manifest.json','icon.svg','lib/pmtiles.js','lib/protomaps-leaflet.js',
'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>Promise.all(CORE.map(u=>c.add(u).catch(()=>{})))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V&&k!=='trilhanav-tiles').map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
const isTile=u=>/tile\.openstreetmap\.org|opentopomap\.org|arcgisonline\.com/.test(u);
self.addEventListener('fetch',e=>{const u=e.request.url;if(e.request.method!=='GET')return;
  if(isTile(u)){e.respondWith(caches.open('trilhanav-tiles').then(async c=>{const hit=await c.match(u);if(hit)return hit;try{const r=await fetch(e.request);if(r.ok||r.type==='opaque')c.put(u,r.clone());return r}catch(err){return new Response('',{status:504})}}));return}
  e.respondWith(fetch(e.request).then(r=>{if(r.ok&&(u.startsWith(self.location.origin)||u.includes('cdnjs')||u.includes('fonts.')))caches.open(V).then(c=>c.put(e.request,r.clone()));return r}).catch(()=>caches.match(e.request).then(h=>h||caches.match('index.html'))))});
