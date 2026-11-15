# TrilhaNav como APK (Capacitor)

Empacota o app (`../index.html` e `../lib`) num APK Android. O que muda em relação ao PWA:

- **GPS com a tela apagada**: o `@capacitor-community/background-geolocation` roda um serviço em primeiro plano
  (notificação fixa "TrilhaNav: GPS ativo"). No navegador o GPS para quando a tela apaga.
- **Voz do copiloto nativa** (TTS do Android, abaixa a música enquanto fala) e **controle de música**
  (⏮ ⏯ ⏭ e abrir o Spotify) pelo plugin `TrilhaNative` (`native/TrilhaNativePlugin.java`).
- **Funciona sem internet na primeira abertura**: Leaflet, pdf.js e as fontes vão dentro do APK
  (`build-apk.sh` troca os links do CDN por cópias locais). Os mapas continuam sendo o `.pmtiles` offline.

O código do app é o mesmo do PWA: tudo que é nativo fica atrás de `NATIVE` no `index.html` e não faz nada no navegador.

## Compilar

Precisa de Node 22, JDK 21 e do Android SDK (plataforma 36) com as licenças aceitas (`sdkmanager --licenses`).

```
cd android-app
npm ci --ignore-scripts
ANDROID_HOME=$HOME/android-sdk bash build-apk.sh        # gera trilhanav-<versão>.apk
bash build-apk.sh --www-only                            # só monta www/ (não precisa de SDK)
```

O APK sai assinado com a chave de **depuração** e com a flag `debuggable`: serve para instalar no seu celular (permita
"instalar apps desconhecidos"), não para distribuir a outras pessoas nem para a Play Store. Cada compilação no GitHub gera uma
chave de depuração nova, então atualizar por cima exige desinstalar antes (e isso apaga trilhas, notas e o mapa offline do app). Para publicar numa loja é preciso uma chave de assinatura própria.

Também dá para compilar no GitHub: **Actions → APK → Run workflow**; o APK fica nos artefatos da execução.

## Permissões

Localização (fina e aproximada), serviço em primeiro plano do tipo localização, notificações (Android 13+).
Na primeira abertura o app pede a localização; escolha **"Permitir o tempo todo"** se quiser que a trilha continue
sendo gravada com o app em segundo plano.

## Licenças

Capacitor e o plugin de GPS são MIT. O app carrega `leaflet-rotate` e `leaflet-elevation` (GPL-3.0), então o APK
só pode ser distribuído com o código-fonte aberto (ver `../NOTICE.md`).

## Não verificado

O lado Java (`native/`) e o serviço de GPS só são exercitados num aparelho Android de verdade. Os testes `dev/t11.py`
cobrem o lado do app com um Capacitor simulado.
