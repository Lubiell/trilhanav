"""Conduz o TrilhaNav no emulador (adb + uiautomator) e confere o que só o Android de verdade mostra.
Escreve dev/emu/out/relatorio.txt (OK/FALHA por item), prints, logcat, dumpsys e os textos vistos na tela.
Chamado pelo dev/emu/run.sh (variáveis NOVO e ANTERIOR)."""
import os, re, subprocess, time, xml.etree.ElementTree as ET

OUT = 'dev/emu/out'
PKG = 'io.github.lubiell.trilhanav'
NOVO, ANT = os.environ.get('NOVO', '2.7.8'), os.environ.get('ANTERIOR', '2.7.7')
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

def grant():
    for p in ['ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION', 'POST_NOTIFICATIONS', 'READ_PHONE_STATE', 'READ_CALL_LOG', 'ANSWER_PHONE_CALLS',
              'CALL_PHONE', 'READ_CONTACTS', 'RECORD_AUDIO', 'SEND_SMS']:
        sh('pm grant %s android.permission.%s' % (PKG, p))

def app_du():
    out = sh('du -sk /data/data/%s/app_webview 2>/dev/null' % PKG)
    m = re.match(r'\s*(\d+)', out)
    return int(m.group(1)) if m else -1

def storage_bytes():
    """localStorage do WebView (LevelDB): chaves e valores em Latin-1 ou UTF-16"""
    d = '/data/data/%s/app_webview/Default/Local Storage/leveldb' % PKG
    raw = subprocess.run(['adb', 'exec-out', 'sh', '-c', 'cat "%s"/*.log "%s"/*.ldb 2>/dev/null' % (d, d)], capture_output=True, timeout=60).stdout
    return raw + raw.replace(b'\x00', b'')

def main():
    os.makedirs(OUT, exist_ok=True)
    save('aparelho.txt', sh('getprop ro.product.model') + sh('getprop ro.build.version.release') + sh('getprop ro.product.cpu.abilist')
         + sh('dumpsys webviewupdate | grep -i "current webview package"'))

    # ---------- versão anterior instalada e aberta (como no celular do dono) ----------
    r = adb('install', 'dev/emu/apk/trilhanav-%s.apk' % ANT, t=400)
    check('instala a %s (a que está no celular)' % ANT, 'Success' in r, r[-300:])
    grant(); launch(); time.sleep(35)
    shot('01-%s-aberta' % ANT)
    check('a %s abre' % ANT, bool(pid()))
    sh('am force-stop ' + PKG); time.sleep(2)

    # ---------- atualização por cima ----------
    r = adb('install', '-r', 'dev/emu/apk/trilhanav-%s.apk' % NOVO, t=400)
    check('a %s instala por cima da %s (mesma chave, sem desinstalar)' % (NOVO, ANT), 'Success' in r, r[-300:])
    vn = re.search(r'versionName=(\S+)', sh('dumpsys package ' + PKG))
    check('versão instalada é a %s' % NOVO, bool(vn) and vn.group(1) == NOVO, vn.group(1) if vn else '?')
    abi = re.search(r'primaryCpuAbi=(\S+)', sh('dumpsys package ' + PKG))
    save('abi.txt', abi.group(1) if abi else '?')
    grant()

    # ---------- abre a nova ----------
    adb('logcat', '-c'); du0 = app_du()
    launch()
    seen = watch(40, 'textos-abertura.txt')
    shot('02-%s-aberta' % NOVO)
    check('a %s abre e continua aberta' % NOVO, bool(pid()), 'pid=' + pid())
    log = adb('logcat', '-d', t=120); save('logcat-abertura.txt', log)
    fatal = [l for l in log.splitlines() if 'FATAL EXCEPTION' in l or ('AndroidRuntime' in l and ' E ' in l)]
    check('sem travamento nativo (FATAL EXCEPTION) no logcat', not fatal, ' / '.join(fatal[:3]))
    jserr = [l for l in log.splitlines() if 'Uncaught' in l]
    check('sem erro de JavaScript no console do WebView', not jserr, ' / '.join(jserr[:3]))
    check('o mapa aparece (tela com os botões do app)', any(s in seen for s in ('Mais', 'Ir para', 'Mapa')), ', '.join(seen[:25]))

    # ---------- voz e áudio: parado, o app não pode abaixar a música de ninguém ----------
    time.sleep(10)
    svc = sh('dumpsys activity services ' + PKG); save('servicos.txt', svc)
    check('assistente de voz (TrilhaVoiceService) rodando', 'TrilhaVoiceService' in svc)
    vlog = [l for l in adb('logcat', '-d', t=120).splitlines() if re.search(r'vosk|Vosk|TrilhaVoice|UnsatisfiedLink', l)]
    save('logcat-voz.txt', '\n'.join(vlog))
    check('modelo de voz (Vosk) carregou sem erro de biblioteca', not any('UnsatisfiedLink' in l for l in vlog), ' / '.join(vlog[-3:]))
    au = sh('dumpsys audio', t=120); save('dumpsys-audio.txt', au)
    stack = au[au.find('Audio Focus stack entries'):][:1500] if 'Audio Focus stack entries' in au else ''
    focus_ev = [l for l in au.splitlines() if PKG in l and re.search(r'requestAudioFocus|abandonAudioFocus|focus', l, re.I)]
    check('parado, o app não pede foco de áudio (a música dos outros apps não abaixa)', PKG not in stack and not focus_ev, ' / '.join(focus_ev[:3]) or stack[:300])
    mode = re.findall(r'(?:mMode|Audio mode|mode)\s*[:=]\s*(\S+)', au)
    sco = [l.strip() for l in au.splitlines() if re.search(r'sco|communication device', l, re.I)][:8]
    save('audio-modo-sco.txt', 'modos: %s\n%s' % (mode[:6], '\n'.join(sco)))
    check('áudio em modo normal (sem canal de ligação/SCO aberto pelo app)', not any('IN_COMMUNICATION' in m or m == '3' for m in mode[:3]), str(mode[:3]))

    # ---------- migração do microfone do capacete (localStorage) ----------
    st = storage_bytes()
    check('migração 2.7.8 rodou (tn_mig278 gravado)', b'tn_mig278' in st)
    i = st.rfind(b'"voiceBt":')   # o LevelDB acrescenta: o último valor gravado é o que vale
    ult = st[i + 10:i + 15] if i >= 0 else b''
    check('ajuste guardado com o microfone do capacete desligado', ult.startswith(b'false'), 'último valor gravado: %r' % ult)

    # ---------- download automático do mapa no Wi-Fi ----------
    net = sh('dumpsys connectivity | grep -iE "Active default network|NetworkAgentInfo.*(WIFI|CELLULAR)" | head -5'); save('rede.txt', net)
    toast = [s for s in seen if 'Baixando o mapa' in s or 'Wi-Fi' in s]
    time.sleep(60)
    du1 = app_du()
    check('mapa de MG começou a baixar sozinho (Wi-Fi do emulador)', du1 - du0 > 40000 or bool(toast),
          'app_webview %d KB -> %d KB; aviso: %s' % (du0, du1, toast[:1]))
    # Ajustes → texto do mapa offline e do armazenamento
    tap('Mais', exact=True); shot('03-mais')
    tap('Ajustes', exact=True); time.sleep(2)
    nodes = dump('ajustes')
    txt = [s for s, _ in nodes]
    save('textos-ajustes.txt', '\n'.join(txt))
    shot('04-ajustes')
    prog = [s for s in txt if re.search(r'Baixando mapa|Instalado|Mapa de|Download|Conferindo', s)]
    check('Ajustes mostra o mapa baixando/instalado', bool(prog), ' / '.join(prog[:2]))
    for _ in range(6):   # rola até o Armazenamento
        sh('input swipe 540 1800 540 500 300'); time.sleep(1)
    nodes = dump('ajustes-fim'); txt2 = [s for s, _ in nodes]; shot('05-ajustes-armazenamento')
    sto = [s for s in txt2 if re.search(r'permanente|Espaço do app|Mapa offline:|Radares:|Erro', s)]
    save('textos-armazenamento.txt', '\n'.join(txt2))
    check('Ajustes → Armazenamento aparece', bool(sto), ' / '.join(sto[:4]))
    sh('input keyevent KEYCODE_BACK'); time.sleep(1.5)

    # ---------- Sair do app ----------
    shot('06-antes-de-sair')
    ok = tap('Mais', exact=True) and tap('Sair do app', exact=True)
    shot('07-pergunta-sair')
    perg = [s for s, _ in dump()]
    check('"Sair do app" pergunta antes', any('Sair do TrilhaNav' in s for s in perg), ', '.join(perg[:15]))
    tap('Sair', exact=True); time.sleep(6)
    shot('08-depois-de-sair')
    p = pid(); svc2 = sh('dumpsys activity services ' + PKG); save('servicos-depois-de-sair.txt', svc2)
    check('depois de "Sair": processo fechado', not p, 'pid=' + p)
    check('depois de "Sair": serviço de voz parado', 'TrilhaVoiceService' not in svc2)
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
