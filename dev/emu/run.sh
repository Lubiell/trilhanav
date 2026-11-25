#!/usr/bin/env bash
# Sobe o emulador Android (API 34, x86_64 com tradução ARM, Wi-Fi do emulador), baixa os APKs publicados no branch apk,
# confere o SHA-256 de cada um e roda o dev/emu/drive.py. Roda no GitHub Actions (precisa de /dev/kvm).
#   NOVO=2.7.8 ANTERIOR=2.7.7 bash dev/emu/run.sh
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=dev/emu/out; mkdir -p "$OUT" dev/emu/apk
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
export PATH="$SDK/cmdline-tools/latest/bin:$SDK/platform-tools:$SDK/emulator:$PATH"
IMG="system-images;android-34;google_apis;x86_64"

RAW=https://raw.githubusercontent.com/Lubiell/trilhanav/apk
curl -fsSL -o dev/emu/apk/SHA256SUMS "$RAW/SHA256SUMS"
for v in "$ANTERIOR" "$NOVO"; do
  curl -fsSL -o "dev/emu/apk/trilhanav-$v.apk" "$RAW/trilhanav-$v.apk"
  (cd dev/emu/apk && grep " trilhanav-$v.apk\$" SHA256SUMS | sha256sum -c -) || { echo "SHA-256 da $v não confere"; exit 1; }
done

echo "== $(date +%T) SDK em $SDK; baixando o emulador e o Android 14"
yes 2>/dev/null | timeout 300 sdkmanager --licenses >/dev/null 2>&1
timeout 900 sdkmanager --install emulator platform-tools "$IMG" >/dev/null || { echo "sdkmanager falhou"; exit 1; }
echo no | timeout 120 avdmanager create avd -n tn -k "$IMG" -d pixel_6 --force >/dev/null || { echo "avdmanager falhou"; exit 1; }
echo "== $(date +%T) emulador: $(command -v emulator); $(emulator -version 2>&1 | head -1)"
emulator -avd tn -no-window -no-audio -no-boot-anim -no-snapshot -no-metrics -gpu swiftshader_indirect -memory 4096 -partition-size 8192 \
  >"$OUT/emulador.log" 2>&1 &
EMU=$!
# espera o Android ligar (até 8 min), sem travar se o emulador fechar sozinho (a 1ª tentativa ficou parada no "adb wait-for-device")
ok=0
for i in $(seq 1 96); do
  if ! kill -0 "$EMU" 2>/dev/null; then echo "o emulador fechou sozinho:"; tail -60 "$OUT/emulador.log"; exit 1; fi
  [ "$(timeout 10 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && { ok=1; break; }
  [ "$i" = 12 ] && { echo "== 1 min: começo do log do emulador"; head -30 "$OUT/emulador.log"; }
  sleep 5
done
[ "$ok" = 1 ] || { echo "o Android não ligou em 8 min:"; tail -60 "$OUT/emulador.log"; timeout 10 adb devices; exit 1; }
echo "== $(date +%T) Android $(timeout 10 adb shell getprop ro.build.version.release | tr -d '\r') ligado"
timeout 20 adb shell settings put global window_animation_scale 0; timeout 20 adb shell settings put global transition_animation_scale 0
timeout 20 adb shell settings put global animator_duration_scale 0
timeout 30 adb root >/dev/null 2>&1; sleep 3; timeout 60 adb wait-for-device
timeout 1500 python3 dev/emu/drive.py
rc=$?
adb emu kill >/dev/null 2>&1 || true
exit $rc
