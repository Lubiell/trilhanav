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

yes | sdkmanager --licenses >/dev/null 2>&1
sdkmanager --install emulator platform-tools "$IMG" >/dev/null
echo no | avdmanager create avd -n tn -k "$IMG" -d pixel_6 --force >/dev/null
emulator -avd tn -no-window -no-audio -no-boot-anim -no-snapshot -gpu swiftshader_indirect -memory 4096 -partition-size 8192 \
  >"$OUT/emulador.log" 2>&1 &
adb wait-for-device
for i in $(seq 1 120); do [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && break; sleep 5; done
adb shell getprop ro.build.version.release
adb shell settings put global window_animation_scale 0; adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
adb root >/dev/null 2>&1; sleep 3; adb wait-for-device
python3 dev/emu/drive.py
rc=$?
adb emu kill >/dev/null 2>&1 || true
exit $rc
