# TrilhaNav como APK (Capacitor)

Empacota o app (`../index.html` e `../lib`) num APK Android. O que muda em relação ao PWA:

- **GPS com a tela apagada**: o `@capacitor-community/background-geolocation` roda um serviço em primeiro plano
  (notificação fixa "TrilhaNav: GPS ativo"). No navegador o GPS para quando a tela apaga.
- **Voz do copiloto nativa** (TTS do Android, abaixa a música enquanto fala) e **controle de música**
  (⏮ ⏯ ⏭ e abrir o Spotify) pelo plugin `TrilhaNative` (`native/TrilhaNativePlugin.java`).
- **Exportar** (trilha gravada, ZIP com fotos, backup de ajustes): o WebView não baixa arquivos, então o app abre a
  tela de compartilhar do Android (`TrilhaNative.shareFile`), de onde dá para salvar em Arquivos, Drive, WhatsApp etc.
- **Tela sempre ligada** enquanto o app está aberto (`FLAG_KEEP_SCREEN_ON` no `MainActivity`).
- **Funciona sem internet na primeira abertura**: Leaflet e as fontes vão dentro do APK
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
chave de depuração nova; por isso, **antes de publicar, o APK é assinado de novo com a chave fixa** (desde a 2.7.1), e assim
cada versão nova instala por cima da anterior sem apagar trilhas, notas e o mapa offline:

```
bash android-app/sign/assinar.sh trilhanav-X.Y.Z.apk assinado/trilhanav-X.Y.Z.apk trilhanav_chave_apk.p12 senha.txt
```

A chave (`trilhanav_chave_apk.p12`, PKCS12, alias `trilhanav`) e a senha (`trilhanav_chave_apk_senha.txt`) ficam **só no Google
Drive do dono**, pasta "TrilhaNav - chave do APK (NAO APAGAR)"; nunca no repositório (o `.gitignore` barra `*.p12`, `*.jks`,
`senha*.txt`). O script confere a assinatura e mostra o SHA-256 do certificado, que tem de ser
`c7654768ee33ec4489240519181d6062ed8b5f6c2025aaea5b5606bed5da8dd1`. Sem essa chave, a versão seguinte volta a exigir desinstalar.

O APK já compilado fica no branch órfão `apk` (link de download e SHA-256 no README dele).
Também dá para compilar no GitHub: **Actions → APK → Run workflow**; o APK fica nos artefatos da execução.

## Permissões

Localização (fina e aproximada), serviço em primeiro plano do tipo localização, notificações (Android 13+).
Na primeira abertura o app pede a localização; escolha **"Permitir o tempo todo"** se quiser que a trilha continue
sendo gravada com o app em segundo plano.

## Licenças

Capacitor e o plugin de GPS são MIT. O app carrega `leaflet-rotate` (GPL-3.0), então o APK
só pode ser distribuído com o código-fonte aberto (ver `../NOTICE.md`).

## Problemas conhecidos

- **Gradle diz "Could not find" para artefatos que existem** (por exemplo `httpmime`, `commons-io`): o Maven Central pode
  responder 429 a requisições `HEAD` para certos IPs/proxies (o Gradle usa `HEAD` e trata como "não encontrado").
  Solução usada na sessão que gerou o primeiro APK: apontar o Gradle para o espelho do Maven Central do Google num
  init script **local**, fora do repositório, em `~/.gradle/init.d/mirror.gradle`:

  ```groovy
  def mirror = 'https://maven-central.storage-download.googleapis.com/maven2'
  def fix = { repos -> repos.all { r -> if (r instanceof MavenArtifactRepository && r.url.toString().contains('repo.maven.apache.org')) r.url = mirror } }
  beforeSettings { s -> fix(s.pluginManagement.repositories) }
  allprojects { fix(buildscript.repositories); fix(repositories) }
  ```

  No GitHub Actions isso não é preciso.

## Não verificado

O lado Java (`native/`) e o serviço de GPS só são exercitados num aparelho Android de verdade. O que foi conferido no APK
pronto: pacote, versão, permissões, manifest mesclado (serviço de GPS fechado para outros apps, `allowBackup=false`), assinatura,
classes nativas no dex e assets sem CDN. Os testes `dev/t11.py` cobrem o lado do app com um Capacitor simulado e `dev/t13.py`
o pacote web (`bash build-apk.sh --www-only`, `python3 -m http.server 8766` dentro de `www/`).
