// Avalia uma expressão JavaScript dentro do WebView do app no emulador (Chrome DevTools Protocol pela porta 9222,
// encaminhada pelo adb para o webview_devtools_remote_<pid>). Só funciona em APK de depuração (o build-apk.sh usa assembleDebug).
//   node dev/emu/cdp.mjs "navigator.connection.type"   → imprime o resultado em JSON
const expr = process.argv[2];
const ms = +(process.argv[3] || 15000);
const fail = m => { console.log(JSON.stringify({ erro: String(m) })); process.exit(0); };
setTimeout(() => fail('tempo esgotado'), ms);
let list;
try { list = await (await fetch('http://127.0.0.1:9222/json')).json(); } catch (e) { fail('sem DevTools: ' + e.message); }
const t = list.find(p => p.type === 'page' && /localhost/.test(p.url)) || list.find(p => p.type === 'page');
if (!t) fail('nenhuma página no WebView');
const ws = new WebSocket(t.webSocketDebuggerUrl);
ws.onerror = e => fail('websocket: ' + (e.message || 'erro'));
ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate',
  params: { expression: expr, awaitPromise: true, returnByValue: true, userGesture: true } }));
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id !== 1) return;
  const r = m.result || {};
  if (r.exceptionDetails) fail('exceção: ' + ((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text));
  console.log(JSON.stringify({ valor: r.result ? r.result.value : null }));
  process.exit(0);
};
