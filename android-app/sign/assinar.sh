#!/usr/bin/env bash
# Assina o APK do workflow com a chave fixa do TrilhaNav (a chave e a senha ficam SÓ no Google Drive do dono,
# pasta "TrilhaNav - chave do APK (NAO APAGAR)"; nunca no repositório).
#   bash android-app/sign/assinar.sh entrada.apk saida.apk trilhanav_chave_apk.p12 senha.txt
# Baixa o apksig 8.13.2 do Maven do Google (SHA-256 conferido), compila o Signer.java e assina (v2+v3, .so em 16 KB).
# No fim confere a assinatura e mostra o SHA-256 do certificado: tem de ser c7654768…5da8dd1.
set -euo pipefail
[ $# -eq 4 ] || { echo "uso: $0 entrada.apk saida.apk chave.p12 senha.txt"; exit 2; }
AQUI="$(cd "$(dirname "$0")" && pwd)"
CACHE="${TMPDIR:-/tmp}/trilhanav-sign"; mkdir -p "$CACHE"
JAR="$CACHE/apksig-8.13.2.jar"; SHA=c070ed1394629d74641aa0906f60b2ffa1ee77e6366a1f93437f59717b1aeb89
if ! echo "$SHA  $JAR" | sha256sum -c --quiet >/dev/null 2>&1; then
  curl -fsSL -o "$JAR" https://dl.google.com/dl/android/maven2/com/android/tools/build/apksig/8.13.2/apksig-8.13.2.jar
  echo "$SHA  $JAR" | sha256sum -c --quiet
fi
javac -nowarn -d "$CACHE" -cp "$JAR" "$AQUI/Signer.java" 2>&1 | grep -v -e JAVA_TOOL_OPTIONS -e '^Note:' || true
java -cp "$JAR:$CACHE" Signer "$1" "$2" "$3" "$4" 2>&1 | grep -v JAVA_TOOL_OPTIONS
