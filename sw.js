const V='trilhanav-v25';
const CORE=['./','index.html','manifest.json','icon.svg','lib/pmtiles.js','lib/protomaps-leaflet.js','lib/leaflet-rotate.js',
'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>Promise.all(CORE.map(u=>c.add(u).catch(()=>{})))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V&&k!=='trilhanav-tiles').map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
/* o que entra no cache em tempo de uso: arquivos do próprio app, cdnjs e as fontes do Google (pedidas com CORS) */
const keepable=u=>u.startsWith(self.location.origin)||/^https:\/\/(cdnjs\.cloudflare\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)\//.test(u);
/* no máximo TILE_MAX tiles online guardados (resposta opaca pode ocupar bem mais que o tamanho real na cota): ao passar, apaga os mais antigos */
const TILE_MAX=3000;let trimBusy=false;
let putN=0;
async function trimTiles(c){if(trimBusy||++putN%50)return;trimBusy=true;   /* confere a cada 50 tiles novos */try{const ks=await c.keys();for(let i=0;i<ks.length-TILE_MAX;i++)await c.delete(ks[i])}finally{trimBusy=false}}
const isTile=u=>/tile\.openstreetmap\.org|opentopomap\.org|arcgisonline\.com/.test(u);
self.addEventListener('fetch',e=>{const u=e.request.url;if(e.request.method!=='GET')return;
  if(u.includes('raw.githubusercontent.com'))return;
  if(isTile(u)){e.respondWith(caches.open('trilhanav-tiles').then(async c=>{const hit=await c.match(u);if(hit)return hit;try{const r=await fetch(e.request);if(r.ok||r.type==='opaque'){c.put(u,r.clone()).then(()=>trimTiles(c)).catch(()=>{})}return r}catch(err){return new Response('',{status:504})}}));return}
  /* rede primeiro. A cópia para o cache é tirada ANTES de devolver a resposta: depois o corpo já está em uso e o clone falha (era por isso que nada entrava no cache em tempo de uso, nem as fontes) */
  e.respondWith(fetch(e.request).then(r=>{if(r.ok&&keepable(u)){const cp=r.clone();caches.open(V).then(c=>c.put(e.request,cp)).catch(()=>{})}return r}).catch(()=>caches.match(e.request).then(h=>h||(e.request.mode==='navigate'?caches.match('index.html'):Response.error()))))});
