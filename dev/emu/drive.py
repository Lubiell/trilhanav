"""Conduz o TrilhaNav no emulador (adb + uiautomator) e confere o que só o Android de verdade mostra.
Escreve dev/emu/out/relatorio.txt (OK/FALHA por item), prints, logcat, dumpsys e os textos vistos na tela.
Chamado pelo dev/emu/run.sh (variáveis NOVO e ANTERIOR)."""
import json, os, re, subprocess, time, xml.etree.ElementTree as ET

OUT = 'dev/emu/out'
PKG = 'io.github.lubiell.trilhanav'
NOVO, ANT = os.environ.get('NOVO', '2.7.8'), os.environ.get('ANTERIOR', '2.7.7')
BRANCH_APK = 'dev/emu/apk/trilhanav-branch.apk'   # compilado do código do branch pelo workflow (assinado com a chave de depuração)
R = []

def adb(*a, t=180):
    try:
        r = subprocess.run(['adb', *a], capture_output=True, timeout=t)
        return r.stdout.decode('utf-8', 'ignore') + r.stderr.decode('utf-8', 'ignore')
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'

def sh(cmd, t=180): return adb('shell', cmd, t=t)

def save(name, txt):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f: f.write(txt)

def check(nome, ok, extra=''):
    line = ('OK    ' if ok else 'FALHA ') + nome + (('  | ' + extra.replace('\n', ' ')[:400]) if extra else '')
    print(line, flush=True); R.append(line)

def shot(name):
    try:
        png = subprocess.run(['adb', 'exec-out', 'screencap', '-p'], capture_output=True, timeout=60).stdout
        with open(os.path.join(OUT, name + '.png'), 'wb') as f: f.write(png)
    except Exception as e:
        print('print falhou', name, e)

def dump(name=None):
    sh('uiautomator dump /sdcard/ui.xml >/dev/null 2>&1', t=60)
    x = adb('exec-out', 'cat', '/sdcard/ui.xml', t=60)
    if name: save(name + '.xml', x)
    nodes = []
    try:
        for n in ET.fromstring(x[x.find('<?xml'):] if '<?xml' in x else x).iter('node'):
            b = [int(v) for v in re.findall(r'-?\d+', n.get('bounds', ''))]
            s = (n.get('text') or '').strip() or (n.get('content-desc') or '').strip()
            if len(b) == 4 and s: nodes.append((s, b))
    except Exception:
        pass
    return nodes

def tap(label, exact=False, nodes=None):
    for s, b in (nodes if nodes is not None else dump()):
        if (s == label) if exact else (label in s):
            sh('input tap %d %d' % ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)); time.sleep(1.5); return True
    return False

def pid(): return sh('pidof ' + PKG).strip()

def launch():
    sh('monkey -p %s -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1' % PKG)

def watch(secs, name):
    """junta os textos que aparecem na tela (toasts inclusive) durante secs segundos"""
    seen, t0 = [], time.time()
    while time.time() - t0 < secs:
        for s, _ in dump():
            if s not in seen: seen.append(s)
        time.sleep(1)
    save(name, '\n'.join(seen))
    return seen

def grant(mic=False):
    for p in ['ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION', 'POST_NOTIFICATIONS', 'READ_PHONE_STATE', 'READ_CALL_LOG', 'ANSWER_PHONE_CALLS',
              'CALL_PHONE', 'READ_CONTACTS', 'SEND_SMS'] + (['RECORD_AUDIO'] if mic else []):
        sh('pm grant %s android.permission.%s' % (PKG, p))
    if not mic: sh('pm revoke %s android.permission.RECORD_AUDIO' % PKG)

def deny_dialogs(secs=12):
    """nega os pedidos de permissão que aparecerem (o do microfone, de propósito)"""
    t0, n = time.time(), 0
    while time.time() - t0 < secs:
        nodes = dump()
        hit = [x for x in nodes if re.search(r"Don.?t allow|Não permitir|^Deny$", x[0])]
        if hit:
            b = hit[0][1]; sh('input tap %d %d' % ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)); n += 1; time.sleep(1.5)
        else:
            time.sleep(1)
    return n

def app_du():
    out = sh('du -sk /data/data/%s/app_webview 2>/dev/null' % PKG)
    m = re.match(r'\s*(\d+)', out)
    return int(m.group(1)) if m else -1

def storage_bytes():
    """localStorage do WebView (LevelDB): chaves e valores em Latin-1 ou UTF-16"""
    d = '/data/data/%s/app_webview/Default/Local Storage/leveldb' % PKG
    raw = subprocess.run(['adb', 'exec-out', 'sh', '-c', 'cat "%s"/*.log "%s"/*.ldb 2>/dev/null' % (d, d)], capture_output=True, timeout=60).stdout
    return raw + raw.replace(b'\x00', b'')

def js(expr, ms=15000):
    """avalia JavaScript dentro do WebView do app (APK de depuração): devolve o valor ou {'erro': ...}"""
    p = pid()
    if not p: return {'erro': 'app fechado'}
    socks = sh('cat /proc/net/unix | grep -a webview_devtools_remote_%s' % p)
    m = re.search(r'@?(webview_devtools_remote_\d+)', socks)
    if not m: return {'erro': 'sem DevTools no WebView'}
    adb('forward', 'tcp:9222', 'localabstract:' + m.group(1))
    try:
        out = subprocess.run(['node', 'dev/emu/cdp.mjs', expr, str(ms)], capture_output=True, text=True, timeout=ms / 1000 + 10).stdout
        r = json.loads(out.strip().splitlines()[-1])
    except Exception as e:
        return {'erro': repr(e)}
    return r.get('valor') if 'valor' in r else r

def close_dialogs():
    js("document.querySelectorAll('dialog[open]').forEach(d=>d.close()),1")
    time.sleep(1)

def exit_test(tag):
    """Sair do app: pergunta, fecha o processo e para os serviços"""
    close_dialogs()
    shot(tag + '-antes-de-sair')
    r = js("document.querySelector('#bExit').click(),1")
    time.sleep(2)
    perg = [s for s, _ in dump()]
    shot(tag + '-pergunta-sair')
    check('[%s] "Sair do app" pergunta antes' % tag, any('Sair do TrilhaNav' in s for s in perg), ', '.join(perg[:12]) + ' ' + str(r))
    tap('Sair', exact=True); time.sleep(6)
    shot(tag + '-depois-de-sair')
    p = pid(); svc = sh('dumpsys activity services ' + PKG); save(tag + '-servicos-depois-de-sair.txt', svc)
    check('[%s] depois de "Sair": processo fechado' % tag, not p, 'pid=' + p)
    check('[%s] depois de "Sair": nenhum serviço do app rodando (voz, GPS)' % tag, 'ServiceRecord' not in svc, svc[:300])

def open_checks(tag, seen):
    p = pid()
    check('[%s] abre e continua aberto' % tag, bool(p), 'pid=' + p)
    log = adb('logcat', '-d', t=120); save(tag + '-logcat.txt', log)
    fatal = [l for l in log.splitlines() if 'FATAL EXCEPTION' in l or 'Fatal signal' in l]
    check('[%s] sem travamento (FATAL EXCEPTION / Fatal signal) no logcat' % tag, not fatal, ' / '.join(fatal[:3]))
    # só o console do WebView (chromium/Capacitor); o "Uncaught remote exception" do JavaBinder é do sistema, não do app
    jserr = [l for l in log.splitlines() if 'Uncaught' in l and re.search(r'chromium|Console|Capacitor', l)]
    check('[%s] sem erro de JavaScript no console do WebView' % tag, not jserr, ' / '.join(jserr[:3]))
    check('[%s] o mapa aparece com os botões do app' % tag, any(s in seen for s in ('Mais', 'Ir para', 'Mapa')), ', '.join(seen[:20]))

def audio_checks(tag):
    au = sh('dumpsys audio', t=120); save(tag + '-dumpsys-audio.txt', au)
    stack = au[au.find('Audio Focus stack entries'):][:1500] if 'Audio Focus stack entries' in au else ''
    focus_ev = [l for l in au.splitlines() if PKG in l and re.search(r'requestAudioFocus|abandonAudioFocus|focus', l, re.I)]
    check('[%s] parado, o app não pede foco de áudio (a música dos outros apps não abaixa)' % tag, PKG not in stack and not focus_ev, ' / '.join(focus_ev[:3]))
    mode = re.findall(r'(?:mMode|Audio mode|mode)\s*[:=]\s*(\S+)', au)
    check('[%s] áudio em modo normal (sem canal de ligação/SCO aberto pelo app)' % tag, not any('IN_COMMUNICATION' in m or m == '3' for m in mode[:3]), str(mode[:3]))

# rota de teste em L (600 m para leste, vira à direita, 500 m para o sul) perto de BH, no formato do Valhalla (como o t15/t31)
NAVJS = r"""(()=>{const la0=-19.92,lo0=-43.94,K=1/111194.9,KL=1/(111194.9*Math.cos(la0*Math.PI/180)),pts=[];
for(let i=0;i<31;i++)pts.push([la0,lo0+i*20*KL]);const c=pts[30];for(let i=1;i<26;i++)pts.push([c[0]-i*20*K,c[1]]);
const enc=p=>{let o='',pl=0,po=0;for(const [la,lo] of p){const a=Math.round(la*1e6),b=Math.round(lo*1e6);for(let v of [a-pl,b-po]){v=v<0?~(v<<1):v<<1;
  while(v>=0x20){o+=String.fromCharCode((0x20|(v&0x1f))+63);v>>=5}o+=String.fromCharCode(v+63)}pl=a;po=b}return o};
const n=pts.length,man=[{type:1,instruction:'Siga para o leste na Rua A.',verbal_pre_transition_instruction:'Siga para o leste na Rua A.',street_names:['Rua A'],begin_shape_index:0,end_shape_index:30,length:0.6,time:50},
 {type:10,instruction:'Vire à direita na Rua B.',verbal_transition_alert_instruction:'Vire à direita na Rua B.',verbal_pre_transition_instruction:'Vire à direita na Rua B.',street_names:['Rua B'],begin_shape_index:30,end_shape_index:n-1,length:0.5,time:40},
 {type:4,instruction:'Você chegou ao seu destino.',verbal_pre_transition_instruction:'Você chegou ao seu destino.',begin_shape_index:n-1,end_shape_index:n-1,length:0,time:0}];
navStart(parseTrip({legs:[{shape:enc(pts),maneuvers:man}],summary:{length:1.1,time:90}}),{name:'Teste',lat:pts[n-1][0],lon:pts[n-1][1]});
onPos({timestamp:Date.now(),coords:{latitude:pts[5][0],longitude:pts[5][1],altitude:800,accuracy:5,speed:10,heading:90}});return !!nav})()"""

def nav_notif():
    return [l for l in sh('dumpsys notification --noredact', t=60).splitlines() if 'NotificationRecord' in l and PKG in l and 'id=4343' in l]

def nav_test(tag):
    """(2.7.10) cartão de direção compacto e notificação com a próxima manobra em segundo plano"""
    close_dialogs()
    lon = -43.94 + 5 * 20 / (111194.9 * __import__('math').cos(__import__('math').radians(-19.92)))
    adb('emu', 'geo', 'fix', '%.6f' % lon, '-19.92')   # o GPS do emulador no começo da rota de teste
    r = js(NAVJS)
    check('[%s] rota de teste começou' % tag, r is True, repr(r))
    time.sleep(2)
    h = js("Math.round(document.querySelector('#navCard').getBoundingClientRect().height)")
    shot(tag + '-rota')
    check('[%s] cartão de direção compacto (uma faixa, ≤ 80 px)' % tag, isinstance(h, int) and 0 < h <= 80, repr(h))
    sh('input keyevent KEYCODE_HOME'); time.sleep(5)
    hid = js('document.hidden')
    nn = nav_notif()
    full = sh('dumpsys notification --noredact', t=60); save(tag + '-notificacoes.txt', full)
    R.append('INFO  [%s] em segundo plano o WebView diz document.hidden=%r' % (tag, hid)); print(R[-1], flush=True)
    check('[%s] em segundo plano: notificação da rota (canal tn_rota) com a próxima manobra' % tag, bool(nn) and 'tn_rota' in nn[0],
          (nn[0][:300] if nn else 'nenhuma notificação 4343'))
    shot(tag + '-segundo-plano')
    launch(); time.sleep(4)
    check('[%s] de volta ao app: a notificação da rota sai' % tag, not nav_notif())

def main():
    os.makedirs(OUT, exist_ok=True)
    save('aparelho.txt', sh('getprop ro.product.model') + sh('getprop ro.build.version.release') + sh('getprop ro.product.cpu.abilist')
         + sh('dumpsys webviewupdate | grep -i "current webview package"'))

    # ---------- fase 1: a versão anterior publicada, com o microfone (como no celular do dono) ----------
    r = adb('install', 'dev/emu/apk/trilhanav-%s.apk' % ANT, t=400)
    check('instala a %s (a que está no celular)' % ANT, 'Success' in r, r[-300:])
    adb('logcat', '-c'); grant(mic=True); launch(); time.sleep(35)
    shot('01-%s-aberta' % ANT)
    l0 = adb('logcat', '-d', t=120); save('logcat-%s.txt' % ANT, l0)
    sevl = [l for l in l0.splitlines() if 'Undefined instruction' in l or 'SIGILL' in l]
    # no emulador (x86_64) a biblioteca de voz é ARM e roda por tradução; o tradutor não conhece a instrução 0xd50320bf (SEVL, ARMv8)
    # e derruba o app com SIGILL logo que o Vosk carrega. Num celular ARM a instrução existe. Por isso o resto do teste roda sem o microfone.
    save('vosk-emulador.txt', ('Com o microfone liberado, o app caiu ao carregar a voz (limitação do emulador: tradução ARM→x86):\n' + '\n'.join(sevl))
         if sevl else 'Com o microfone liberado, o Vosk não derrubou o app no emulador.')
    R.append('INFO  voz no emulador: ' + ('o tradutor ARM do emulador não roda a biblioteca do Vosk (SIGILL na instrução SEVL); no celular ARM ela roda' if sevl else 'Vosk rodou'))
    print(R[-1], flush=True)
    sh('am force-stop ' + PKG); time.sleep(2)

    # ---------- fase 2: a nova publicada, por cima (sem o microfone) ----------
    T = NOVO
    r = adb('install', '-r', 'dev/emu/apk/trilhanav-%s.apk' % NOVO, t=400)
    check('[%s] instala por cima da %s (mesma chave, sem desinstalar)' % (T, ANT), 'Success' in r, r[-300:])
    vn = re.search(r'versionName=(\S+)', sh('dumpsys package ' + PKG))
    check('[%s] versão instalada é a %s' % (T, NOVO), bool(vn) and vn.group(1) == NOVO, vn.group(1) if vn else '?')
    grant(mic=False)
    adb('logcat', '-c'); launch()
    neg = deny_dialogs(10)
    seen = watch(25, T + '-textos-abertura.txt')
    shot('02-%s-aberta' % T)
    open_checks(T, seen)
    svc = sh('dumpsys activity services ' + PKG); save(T + '-servicos.txt', svc)
    check('[%s] sem o microfone o app segue aberto e o assistente não sobe (pedidos negados: %d)' % (T, neg), bool(pid()) and 'TrilhaVoiceService' not in svc)
    audio_checks(T)
    st = storage_bytes()
    check('[%s] migração rodou (tn_mig278 gravado)' % T, b'tn_mig278' in st)
    i = st.rfind(b'"voiceBt":')   # o LevelDB acrescenta: o último valor gravado é o que vale
    ult = st[i + 10:i + 15] if i >= 0 else b''
    check('[%s] microfone do capacete guardado como desligado' % T, ult.startswith(b'false'), 'último valor gravado: %r' % ult)
    ct = js('navigator.connection&&navigator.connection.type')
    save(T + '-conexao.txt', repr(ct))
    R.append('INFO  [%s] tipo de conexão que o WebView informa: %r' % (T, ct)); print(R[-1], flush=True)
    time.sleep(20)
    oi = js("document.querySelector('#offInfo').textContent")
    R.append('INFO  [%s] Ajustes → Mapa offline: %r' % (T, oi)); print(R[-1], flush=True)
    if not os.path.exists(BRANCH_APK):
        exit_test(T)

    # ---------- fase 3: o APK do código do branch (instalação limpa: outra chave) ----------
    if os.path.exists(BRANCH_APK):
        T = 'branch'
        sh('am force-stop ' + PKG); adb('uninstall', PKG, t=120)
        r = adb('install', BRANCH_APK, t=400)
        check('[branch] instala', 'Success' in r, r[-300:])
        vn = re.search(r'versionName=(\S+)', sh('dumpsys package ' + PKG))
        R.append('INFO  [branch] versão: %s' % (vn.group(1) if vn else '?')); print(R[-1], flush=True)
        grant(mic=False)
        adb('logcat', '-c'); du0 = app_du(); launch()
        neg = deny_dialogs(8)
        seen = watch(20, 'branch-textos-abertura.txt')
        shot('03-branch-aberta')
        open_checks(T, seen)
        audio_checks(T)
        ct = js('navigator.connection&&navigator.connection.type')
        check('[branch] o WebView sabe que é Wi-Fi (navigator.connection.type)', ct == 'wifi', repr(ct))
        vb = js('cfg.voiceBt')
        check('[branch] microfone do capacete ligado por padrão (voz sem mãos, 2.7.9)', vb is True, repr(vb))
        oi, t0 = '', time.time()
        while time.time() - t0 < 120:
            oi = js("document.querySelector('#offInfo').textContent")
            if isinstance(oi, str) and re.search(r'Baixando mapa|Instalado', oi): break
            time.sleep(5)
        du1 = app_du()
        check('[branch] o mapa de MG começa a baixar sozinho no Wi-Fi', isinstance(oi, str) and bool(re.search(r'Baixando mapa|Instalado', oi)),
              '%r; app_webview %d KB -> %d KB' % (oi, du0, du1))
        js("document.querySelector('#bSet').click(),1"); time.sleep(2); shot('04-branch-ajustes')
        sto = js("document.querySelector('#stoInfo')&&document.querySelector('#stoInfo').innerText")
        save('branch-armazenamento.txt', str(sto))
        check('[branch] Ajustes → Armazenamento mostra o mapa', isinstance(sto, str) and 'Mapa offline' in sto, str(sto)[:300])
        nav_test(T)
        exit_test(T)

    save('logcat-final.txt', adb('logcat', '-d', t=120))
    falhas = [l for l in R if l.startswith('FALHA')]
    save('relatorio.txt', '\n'.join(R) + '\n\nRESULTADO: ' + ('tudo certo' if not falhas else '%d falha(s)' % len(falhas)) + '\n')
    print('\nRESULTADO:', 'tudo certo' if not falhas else '%d falha(s)' % len(falhas))
    return 0

if __name__ == '__main__':
    try:
        rc = main()
    except Exception as e:
        R.append('FALHA roteiro parou: %r' % e); save('relatorio.txt', '\n'.join(R)); print(R[-1]); rc = 1
    raise SystemExit(rc)
