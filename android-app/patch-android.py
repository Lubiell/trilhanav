"""Aplica no projeto Android gerado pelo Capacitor: plugin nativo do TrilhaNav, permissões, strings e cores.
Idempotente. uso: python3 patch-android.py android"""
import os, re, shutil, sys

adir = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
main = os.path.join(adir, 'app', 'src', 'main')

# 1) código nativo
pkg = os.path.join(main, 'java', 'io', 'github', 'lubiell', 'trilhanav')
os.makedirs(pkg, exist_ok=True)
for f in ('MainActivity.java', 'TrilhaNativePlugin.java'):
    shutil.copy(os.path.join(here, 'native', f), os.path.join(pkg, f))

# 2) manifest: permissões e visibilidade do Spotify
mf = os.path.join(main, 'AndroidManifest.xml')
s = open(mf, encoding='utf-8').read()
perms = ['ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION', 'FOREGROUND_SERVICE', 'FOREGROUND_SERVICE_LOCATION', 'POST_NOTIFICATIONS', 'WAKE_LOCK']
s = s.replace('android:allowBackup="true"', 'android:allowBackup="false"')   # o Auto Backup levaria trilhas, notas e fotos para a conta Google
add = ''.join(f'    <uses-permission android:name="android.permission.{p}" />\n' for p in perms if f'android.permission.{p}"' not in s)
if '<queries>' not in s:
    add += '    <queries>\n        <package android:name="com.spotify.music" />\n        <package android:name="com.google.android.apps.youtube.music" />\n    </queries>\n'
if add:
    s = s.replace('</manifest>', add + '</manifest>')
open(mf, 'w', encoding='utf-8').write(s)

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
