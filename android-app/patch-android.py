"""Aplica no projeto Android gerado pelo Capacitor: plugin nativo do TrilhaNav, permissões, strings e cores.
Idempotente. uso: python3 patch-android.py android"""
import os, re, shutil, sys

adir = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
main = os.path.join(adir, 'app', 'src', 'main')

# 1) código nativo
pkg = os.path.join(main, 'java', 'io', 'github', 'lubiell', 'trilhanav')
os.makedirs(pkg, exist_ok=True)
for f in ('MainActivity.java', 'TrilhaNativePlugin.java', 'TrilhaNotifService.java', 'TrilhaVoiceService.java'):
    shutil.copy(os.path.join(here, 'native', f), os.path.join(pkg, f))

# 2) manifest: permissões e visibilidade do Spotify
mf = os.path.join(main, 'AndroidManifest.xml')
s = open(mf, encoding='utf-8').read()
perms = ['ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION', 'FOREGROUND_SERVICE', 'FOREGROUND_SERVICE_LOCATION', 'POST_NOTIFICATIONS', 'WAKE_LOCK',
         'READ_PHONE_STATE', 'READ_CALL_LOG', 'ANSWER_PHONE_CALLS', 'CALL_PHONE', 'READ_CONTACTS', 'RECORD_AUDIO', 'REQUEST_INSTALL_PACKAGES', 'FOREGROUND_SERVICE_MICROPHONE', 'SEND_SMS', 'MODIFY_AUDIO_SETTINGS']
s = s.replace('android:allowBackup="true"', 'android:allowBackup="false"')   # o Auto Backup levaria trilhas, notas e fotos para a conta Google
add = ''.join(f'    <uses-permission android:name="android.permission.{p}" />\n' for p in perms if f'android.permission.{p}"' not in s)
if '<queries>' not in s:
    add += '    <queries>\n        <package android:name="com.spotify.music" />\n        <package android:name="com.google.android.apps.youtube.music" />\n    </queries>\n'
if add:
    s = s.replace('</manifest>', add + '</manifest>')
# reconhecimento de voz (Android 11+ só enxerga o serviço de voz se ele estiver declarado em <queries>)
if 'android.speech.RecognitionService' not in s:
    s = s.replace('</queries>', '        <intent><action android:name="android.speech.RecognitionService" /></intent>\n    </queries>', 1)
# acesso a notificações: WhatsApp e a música que está tocando (o sistema só liga o serviço se o usuário permitir)
if 'TrilhaNotifService' not in s:
    s = s.replace('</application>', '        <service android:name=".TrilhaNotifService" android:exported="true" android:label="TrilhaNav (WhatsApp e música)" android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">\n            <intent-filter><action android:name="android.service.notification.NotificationListenerService" /></intent-filter>\n        </service>\n    </application>')
# o serviço de GPS do plugin vem com exported=true; só o próprio app o usa, então fecha para outros apps
if 'xmlns:tools=' not in s:
    s = s.replace('<manifest ', '<manifest xmlns:tools="http://schemas.android.com/tools" ', 1)
if 'BackgroundGeolocationService' not in s:
    s = s.replace('</application>', '        <service android:name="com.equimaps.capacitor_background_geolocation.BackgroundGeolocationService" android:exported="false" tools:replace="android:exported" />\n    </application>')
# assistente de voz sempre ligado: serviço em primeiro plano do tipo microfone
if 'TrilhaVoiceService' not in s:
    s = s.replace('</application>', '        <service android:name=".TrilhaVoiceService" android:exported="false" android:foregroundServiceType="microphone" />\n    </application>')
open(mf, 'w', encoding='utf-8').write(s)

# Vosk (reconhecimento de voz offline, Apache-2.0) no app
gf0 = os.path.join(adir, 'app', 'build.gradle')
g0 = open(gf0, encoding='utf-8').read()
if 'com.alphacephei:vosk-android' not in g0:
    g0 = g0.replace("implementation project(':capacitor-android')", "implementation project(':capacitor-android')\n    implementation 'com.alphacephei:vosk-android:0.3.75'", 1)
    open(gf0, 'w', encoding='utf-8').write(g0)
# só bibliotecas nativas de celular (ARM): as de emulador (x86) somavam uns 20 MB ao APK
g0 = open(gf0, encoding='utf-8').read()
if 'abiFilters' not in g0:
    g0 = g0.replace('defaultConfig {', "defaultConfig {\n        ndk { abiFilters 'arm64-v8a', 'armeabi-v7a' }", 1)
    open(gf0, 'w', encoding='utf-8').write(g0)

# versão do APK = versão do package.json
import json
ver = json.load(open(os.path.join(here, 'package.json')))['version']
a, b, c = (int(x) for x in ver.split('.'))
gf = os.path.join(adir, 'app', 'build.gradle')
g = open(gf, encoding='utf-8').read()
g = re.sub(r'versionCode \d+', f'versionCode {a * 10000 + b * 100 + c}', g)
g = re.sub(r'versionName "[^"]*"', f'versionName "{ver}"', g)
open(gf, 'w', encoding='utf-8').write(g)

# 3) nome do canal da notificação do GPS
sx = os.path.join(main, 'res', 'values', 'strings.xml')
t = open(sx, encoding='utf-8').read()
if 'capacitor_background_geolocation_notification_channel_name' not in t:
    t = t.replace('</resources>', '    <string name="capacitor_background_geolocation_notification_channel_name">TrilhaNav (GPS)</string>\n</resources>')
    open(sx, 'w', encoding='utf-8').write(t)

# 4) cor de fundo do ícone adaptativo
cx = os.path.join(main, 'res', 'values', 'ic_launcher_background.xml')
if os.path.exists(cx):
    c = open(cx, encoding='utf-8').read()
    c = re.sub(r'(<color name="ic_launcher_background">)[^<]*(</color>)', r'\g<1>#0d1620\g<2>', c)
    open(cx, 'w', encoding='utf-8').write(c)
print('projeto Android ajustado')
