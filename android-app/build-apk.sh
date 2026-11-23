#!/usr/bin/env bash
# Empacota o TrilhaNav como APK de depuração (assinado com a chave de depuração do Android: serve para instalar
# direto no celular, não para a Play Store).
#   bash build-apk.sh --www-only   só monta a pasta www/ (não precisa de SDK)
#   bash build-apk.sh              monta tudo e compila o APK (precisa de JDK 21 e do Android SDK com as licenças aceitas)
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
NM=node_modules

[ -d "$NM" ] || npm ci --ignore-scripts --no-audit --no-fund

# 1) www: cópia do app + bibliotecas e fontes locais
mkdir -p www
find www -mindepth 1 -delete
cp "$ROOT/index.html" "$ROOT/manifest.json" "$ROOT/icon.svg" "$ROOT/icon-192.png" "$ROOT/icon-512.png" www/
cp -r "$ROOT/lib" www/lib
mkdir -p www/lib/leaflet www/fonts/files
cp "$NM/leaflet/dist/leaflet.js" "$NM/leaflet/dist/leaflet.css" www/lib/leaflet/
cp -r "$NM/leaflet/dist/images" www/lib/leaflet/images
cp "$NM/@capacitor/core/dist/capacitor.js" www/lib/capacitor.js
for w in 700 900; do cp "$NM/@fontsource/orbitron/$w.css" "www/fonts/orbitron-$w.css"; cp "$NM"/@fontsource/orbitron/files/orbitron-*-$w-normal.woff2 www/fonts/files/; done
for w in 400 600; do cp "$NM/@fontsource/inter/$w.css" "www/fonts/inter-$w.css"; cp "$NM"/@fontsource/inter/files/inter-*-$w-normal.woff2 www/fonts/files/; done
python3 rewrite-html.py www/index.html
echo "www/ pronto: $(find www -type f | wc -l) arquivos, $(du -sh www | cut -f1)"
[ "${1:-}" = "--www-only" ] && exit 0

# 2) projeto Android (gerado na primeira vez; não vai para o git)
export ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/android-sdk}}"
[ -d "$ANDROID_HOME" ] || { echo "Android SDK não encontrado em $ANDROID_HOME (defina ANDROID_HOME)"; exit 1; }
[ -d android ] || npx cap add android
python3 patch-android.py android
python3 make-icons.py android/app/src/main/res
npx cap sync android

# 3) compilar
# modelo de voz offline (Vosk, português pequeno, Apache-2.0): baixado uma vez, conferido e posto nos assets do APK
VM=vosk-model; VZ="$VM/vosk-model-small-pt-0.3.zip"; VSHA=6e1ce909032e1afa7a88e68a3d628ecafff302bdf195befab308826c395e93b7
mkdir -p "$VM"
[ -f "$VZ" ] || curl -fsSL -o "$VZ" https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
echo "$VSHA  $VZ" | sha256sum -c - >/dev/null || { echo "modelo de voz com SHA-256 errado"; rm -f "$VZ"; exit 1; }
MA=android/app/src/main/assets/model-pt
if [ ! -f "$MA/uuid" ] || [ "$(cat "$MA/uuid")" != "$VSHA" ]; then
  find android/app/src/main/assets -maxdepth 1 -name model-pt -exec rm -r -- {} +
  mkdir -p "$MA"; TMPX="$(mktemp -d)"; unzip -q "$VZ" -d "$TMPX"; cp -r "$TMPX"/vosk-model-small-pt-0.3/. "$MA"/; rm -r -- "$TMPX"
  echo "$VSHA" > "$MA/uuid"   # o StorageService do Vosk só recopia o modelo quando o uuid muda
fi

( cd android && ./gradlew --no-daemon assembleDebug )
VER="$(node -p "require('./package.json').version")"
cp android/app/build/outputs/apk/debug/app-debug.apk "trilhanav-$VER.apk"
echo "APK: $(pwd)/trilhanav-$VER.apk ($(du -h "trilhanav-$VER.apk" | cut -f1))"
