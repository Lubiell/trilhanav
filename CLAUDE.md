# TrilhaNav

App de navegação de **moto** (Android, APK com Capacitor): mapa offline de MG, "Ir para" com rota por estradas com e sem internet, voz curva a curva, telefone/WhatsApp/música por voz no capacete, radares, clima, postos, SOS. Começou como navegador de rali off-road (roadbook, odômetro de rali); **na v2.7 o dono mandou tirar todo o rali** (o código antigo fica no histórico do git, até a v2.6.3). Dono: Jefferson (conta GitHub **Lubiell**). Repositório independente: não reaproveitar nada dos outros repos dele.

## Estado (v2.7.1, 23/11/2026)

**Nada da 2.6.x/2.7 rodou em celular real** (só Chrome headless e os testes). O dono só testou a 2.2.0 num Samsung.

**v2.7.1:** primeiro retorno do celular do dono na 2.6.3: o download do mapa de MG parava com "Download interrompido: An operation that depends on state cached in an interface object was made but the state had changed since it was read from disk" (`NotReadableError`): reler a parte logo depois de gravar falha no Android dele. Agora o SHA-256 é conferido nos bytes que chegaram pela rede (sem reler o arquivo) e o `PartsSource` refaz a leitura com um `File` novo (`handles`, `staleFile`). `t25` reproduz o erro. E a 2.7.0 não instalou por cima da 2.6.3 ("conflito com um pacote já existente": chave diferente).

**v2.7.0 (PR #3):** a pedido do dono ("faça as 7 melhorias e retire A–F"):
- **Saiu o rali inteiro:** roadbook (PDF/OpenRally/automático), odômetro TOTAL/PARCIAL e calibração, waypoints e validação, zonas de velocidade e copiloto da trilha, voltar à trilha, altimetria, cronômetro, tela dividida, simulação de GPS. `index.html` foi de 229 KB para ~180 KB; **pdf.js** e **leaflet-elevation** (GPL) saíram do app e do APK. GPX continua só para **ver no mapa** (`showGpx`/`hideGpx`, Arquivos e gravações; tocar no nome lá em cima tira). O CAP mostra "sem rota" fora do Ir para. Saiu também o botão duplicado "Abrir o Spotify".
- **Rota sem internet longa:** `offlineRouteTo` = até `RT_MAXT` (100) tiles no z14 (todas as estradas); acima disso, **z14 num raio de `RT_END` (2,5 km) da partida e do destino + vias maiores do z12/z11/z10 num corredor** (`corridorTiles`, até `RT_MAXC` 160 tiles), ligadas por **portais** (`buildRoadGraph(...,portal=40)`: nó do nível detalhado liga ao do nível baixo a ≤40 m). A* em `astarRoute` (entra/sai pelos nós a ≤R0 m; sem nenhum, pelos 6 mais perto a ≤3 km).
- **Busca de endereço sem internet:** `geoSearch` usa o Photon com rede e aviso aceito (8 s de prazo se há mapa offline) e cai para `offSearch`: índice dos `places` do **z10 do mapa inteiro** (montado uma vez, guardado em OPFS `busca.json`, chave `offKey()`; refeito se o mapa mudar) + na hora, no **z14 a 6 km** de você: `places`, `pois` (`POK`: posto, hospital…) e ruas com nome. Decodificador genérico `mvtLayer(buf,layer,gt)` (`mvtRoads` = roads/linhas).
- **CI de testes** (`.github/workflows/testes.yml`): cada PR/push no main roda `dev/t*.py` (um job por teste) e o pacote do APK (t13 + t16 em `www/`). Fixtures por `dev/fixtures.py`.
- **Segurança:** CSP por `<meta>` só na versão web (o `rewrite-html.py` tira no APK: o Capacitor injeta código no WebView), SRI no Leaflet do cdnjs, `window.TN` só com `navigator.webdriver` (testes), cache de tiles do service worker limitado a 3000, ações dos workflows fixadas por SHA, `distributionSha256Sum` do Gradle (8.14.3) no `patch-android.py`.
- Atualização do APK **sempre automática** (sem opção de desligar). Janelas **sem botão "Fechar"** (toque fora fecha e repassa o toque; Voltar do Android fecha a janela ou manda o app para segundo plano).

**v2.6.2–2.6.3:** "Ir para" sem Waze/Google Maps (`anyRoute`: Valhalla com rede, senão mapa offline; toque longo no mapa = destino; "Seguir em linha reta"); voz pelo fone do capacete (TTS com `USAGE_VOICE_COMMUNICATION` quando o microfone do capacete está ligado, foco com redução antes de falar, `ttsStatus`/`installVoice`); música: "trocar", volume nas teclas do guidão. Versões anteriores (2.0–2.6.1): ver o histórico do git e o README do branch `apk`.

| Onde | O que tem |
|---|---|
| `main` | o código: v2.7.0 (merge do PR #3, `902a52e`, 23/11/2026; o PR #2 entrou junto) |
| `gh-pages` | https://lubiell.github.io/trilhanav/: desde a v2.7.0 só uma página de download (lê o `versao.json` e mostra o link do APK mais novo) e um `sw.js` que apaga o app antigo (PWA) do navegador de quem já tinha aberto. O código dessa página não está no `main` (só no `gh-pages`) |
| `mapas` (órfão) | mapa de Minas Gerais: `mg/manifest.json` + 30 partes de 45 MB |
| `apk` (órfão) | `trilhanav-2.7.0.apk` (atual, 54 MB, chave `a78f3f98…`), 2.6.3, 2.0.1, 2.0.0; `SHA256SUMS`, README (histórico das versões) e **`versao.json`** (o app lê para se atualizar; atualizar a cada APK novo). Baixar: https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.7.0.apk, SHA-256 `e75a581f2fc79dba55a8e6df43f91eb2775bd7215a0626b0c8cde3fe05f0167c` |
| `claude/loving-lovelace-yzb96l` | branch de trabalho das sessões do Claude (recomeçado do `main` depois de cada merge) |
| Google Drive (raiz) | `trilhanav_backup_AAAA-MM-DD_vX.Y.zip` (código via `git archive`) |

### Arquivos

- `index.html`: app inteiro (HTML + CSS + JS inline, estilo denso). Leaflet vem do cdnjs (com SRI; no APK vai local). `window.TN` expõe internos só para os testes.
- `lib/`: `pmtiles.js` 4.5.0, `protomaps-leaflet.js` 5.1.0 (mapa vetorial offline), `leaflet-rotate.js` 0.2.8 (**GPL-3.0**, ver `NOTICE.md`).
- `sw.js`: cache offline (`trilhanav-vN`, hoje `v18`) e tiles online já vistos (`trilhanav-tiles`, ≤3000). Subir `N` a cada release.
- `android-app/`: empacotamento do APK (`build-apk.sh`, `rewrite-html.py`, `patch-android.py`, `native/*.java`: `MainActivity` (Voltar), `TrilhaNativePlugin`, `TrilhaNotifService`, `TrilhaVoiceService` (Vosk)). `node_modules/`, `android/`, `www/` e `*.apk` não vão para o git.
- `.github/workflows/apk.yml` (compila o APK; manual ou tag `v*`) e `testes.yml` (CI).
- `dev/`: testes Playwright (ver "Como testar"), `fixtures.py`, `make_testmap.py`, `roads.pmtiles`, `t.gpx`.

### Recursos

- **Mapa**: online (OSM/OpenTopoMap/Esri) e offline `.pmtiles` no OPFS (download do mapa de MG do branch `mapas`, retomável e com SHA-256, ou por arquivo em partes); gira com o rumo (`cfg.rot`/`cfg.navRot`, `map.setBearing(360 − rumo)`); bússola do aparelho parado/devagar, GPS acima de `compSpd`, ajuste aprendido pelo GPS.
- **Ir para**: Photon + Valhalla (moto, pt-BR, até 3 alternativas) com rede; sem rede, busca e rota pelo mapa offline (acima). Cartão de manobra, voz curva a curva, recálculo, chegada, recentes/favoritos, "De" opcional, toque longo no mapa, "Seguir em linha reta". Aviso de privacidade antes do 1º pedido (`tn_netOk`).
- **Voz e telefone (APK)**: TTS nativo que abaixa a música; assistente Vosk sempre ligado com a palavra "Trilha" (`TrilhaVoiceService`, microfone do capacete por SCO com `cfg.voiceBt`); atender/recusar/ligar, WhatsApp (mensagens e chamadas pela notificação), música atual e Spotify, "Trilha, ir para…", clima, postos, autonomia.
- **Radares** (Overpass `maps.mail.ru`), **limite da via** (`maxspeed`), **clima** (Open-Meteo, reserva MET Norway), **postos**, **inclinação** (giroscópio × velocidade), **autonomia**, **SOS** (queda → SMS + ligação; padrão desligado).
- **Gravação** de trilha (GPX, com **notas e fotos**, exporta GPX ou ZIP), **Arquivos** (pastas no OPFS; ver GPX no mapa), **Painel** personalizável (`DASH`), tema dia/noite pelo sol, teclas do controle de guidão, trava de toque.

### Onde o app guarda coisas

- `localStorage` (prefixo `tn_`): `cfg`, `keys`, `odo` (estatísticas da viagem: `maxSpd`, `movSec`, `movKm`), `lastPos`, `recSession`, `navRecent` (`fav`), `netOk`, `phFav`, `updT`, `sosC`, `fuelKm`, `dashSel`. Chaves antigas do rali (`wpState`, `marks`, `gpx*`, `zones_*`, `chrono`) podem sobrar nos aparelhos e são ignoradas.
- OPFS: `gpx/` (pastas; `gpx/Gravações/`), `notas/<sessão>/`, `mapa-dl/` (partes do mapa + `manifest.json`), `mapa.pmtiles`, `radares.json`, `busca.json` (índice de cidades da busca offline).

## Fluxo de trabalho e de release

1. Mudança numa branch nova a partir do `main` → PR em rascunho → a **CI de testes** roda sozinha. Com os testes locais e a CI verdes, o merge é feito (regra do dono no CLAUDE.md global) e conferido no `main`.
2. Site: o dono pediu para **retirar o site (PWA)**; o `gh-pages` passa a ter só uma página com o link do APK. Não publicar o `index.html` lá de novo sem ele pedir.
3. Backup: `git archive --format=zip --prefix=trilhanav/ -o trilhanav_backup_AAAA-MM-DD_vX.Y.zip HEAD` e subir na raiz do Drive (o conector recusa arquivo acima de ~3 MB).
4. APK: subir a versão em `android-app/package.json` (e `package-lock.json`); compilar pelo workflow `apk.yml` (Actions → APK → Run workflow; aqui não há Android SDK). Baixar o artefato, publicar no branch `apk` com um worktree, atualizando `SHA256SUMS`, README e **`versao.json`**, e conferir o SHA-256 do download pelo raw.githubusercontent.com.

## Pendências

- **Chave de assinatura fixa:** cada compilação no GitHub gera chave nova, então cada APK novo exige **desinstalar** o anterior (apaga trilhas, notas e mapa) e a atualização automática não consegue instalar por cima. O dono aprovou ("pode criar a chave"): gerar keystore PKCS12 (`keytool`), guardar **só no Drive dele**, e assinar o APK do workflow aqui com **apksig 8.13.2** (Google Maven, SHA-1 conferido) + um `Signer.java` pequeno (ApkSigner v1+v2+v3 e ApkVerifier). **Bloqueado**: o modo Auto da sessão recusa o `keytool` (credencial); o dono precisa trocar o modo para "Accept edits" e aprovar o comando.
- **Testar em celular real** (prioridade): voz pelo capacete com música, foco de áudio, rota e busca offline numa estrada real (o mapa de MG tem `places`/`pois`/nomes de rua? conferido só no mapa de teste), GPS com a tela apagada, telefone/WhatsApp, SOS, atualização automática.
- **Combinado para depois**: mandar a localização por voz, paradas no caminho no Ir para, histórico de viagens.
- **Licença**: `leaflet-rotate` é GPL-3.0 (código aberto obrigatório); o repositório ainda não tem `LICENSE` próprio (decisão do dono).
- **Origem compartilhada** (`lubiell.github.io`): só importa se o site voltar.
- Ideias: nomes de rua na voz da rota offline (o grafo não guarda o nome da via), busca offline de ruas longe de você (hoje só a 6 km), controle de câmeras pelo guidão.

## Armadilhas já encontradas

- **Microfone do fone Bluetooth**: só grava com o canal de voz (SCO/HFP) ligado, e aí a música também sai por ele, em mono (ajuste `voiceBt`). O `SpeechService` do Vosk não deixa escolher o microfone: a captura é própria. Com o SCO ligado, o TTS tem de sair como `USAGE_VOICE_COMMUNICATION`.
- **Ligação do WhatsApp** não passa pelo estado do telefone: só a notificação de chamada mostra; acionar o botão dela no Android 14+ precisa de `MODE_BACKGROUND_ACTIVITY_START_ALLOWED`. A notificação de chamada não pode virar "mensagem".
- **Botões dentro de "Mais"** ficam escondidos até abrir a grade: nos testes, `document.querySelector('#bX').click()`.
- **Testes que aceitam o aviso de internet** passam a buscar clima de verdade: simular `api.open-meteo.com` e `api.met.no`.
- **Inclinação de moto não sai do acelerômetro**: precisa do giroscópio × velocidade.
- **Open-Meteo** limita por IP por dia (daqui responde 429); por isso o MET Norway de reserva.
- **Plugin de GPS em segundo plano** (`@capacitor-community/background-geolocation` 1.3.1): "Service not running." antes de ligar, `NOT_AUTHORIZED` com localização desligada, erros silenciosos; o app tenta de novo e usa o GPS do WebView de reserva (`t17`). O `startGPS()` fica no início do app (antes ficava no fim da restauração do GPX; ao tirar o rali ele sumiu e o GPS não ligava).
- **Vosk sem palavra de ativação** transforma conversa em comando: por isso "trilha"; o assistente pausa enquanto o app fala.
- **Diálogo modal + tela de ligação**: `showModal()` deixa o resto inerte; a `#callBox` fecha os diálogos abertos.
- **Android manda o estado do telefone duas vezes** (com e sem número).
- **Microfone em segundo plano** só com serviço em primeiro plano do tipo microfone (o Vosk tem; a escuta do Google não).
- **Pacote do APK (`www/`) com o Capacitor simulado**: o `lib/capacitor.js` real carrega por cima; os testes bloqueiam esse arquivo.
- **Valhalla**: alternativas na ordem do custo (ordenar por `time`); o pt-BR deixa frases em inglês (`ptTxt`). Photon/Valhalla/Overpass pedem ≤1 pedido/s (`politeFetch`); nos testes, simular com `page.route`.
- **Overpass**: o `maps.mail.ru` funcionou (CORS `*`); outros espelhos falharam em 16/11.
- Estado do modo cidade e dos radares é `var` (não `let`): `updateNav`/`checkAlerts` podem rodar antes do bloco.
- Linhas de lista com botões dentro de `<label>`: tocar no texto dispara o primeiro botão. Usar `div.lr`.
- `map.fitBounds` com a aba Mapa oculta dá zoom `NaN`; só enquadrar com o mapa visível (`fitTrack`/`mapShown`).
- Atalhos de teclado não valem em `input/textarea/select` nem com `e.code` vazio.
- Texto vindo de GPX/backup/mapa nunca entra em `innerHTML` sem `esc()`.
- **MVT próprio** (`mvtLayer`): depois das feições de uma camada é preciso `p=end`. Ponto (tipo 1) vira "linha" de 1 vértice. O cruzamento de ruas só existe se as duas vias tiverem vértice ali (no OSM têm; no mapa de teste foi preciso pôr).
- **Rota offline**: o centro de uma cidade (ponto do `places`) pode ficar a centenas de metros do vértice de rua mais perto; por isso a entrada/saída cai para os 6 nós mais perto a até 3 km. A mesma estrada em zooms diferentes não coincide (o zoom baixo é simplificado): portais.
- **PMTiles**: o id do tile é Hilbert com `rotate(s, …)` (s = metade atual), como no `make_testmap.py`.
- Gradle no ambiente da sessão: Maven Central responde 429 a `HEAD`; init script com o espelho do Google no README de `android-app/`.
- **OPFS no Android**: reler um arquivo logo depois de gravar (`getFile()` + `arrayBuffer()`) pode dar `NotReadableError` ("state had changed since it was read from disk"); um `File` é uma foto do arquivo. Conferir os bytes recebidos em memória e, ao ler, pegar um `File` novo pelo handle e tentar de novo (`t25`).
- **Odômetro/km**: a 1ª posição do GPS costuma ser imprecisa; só vale como partida com precisão ≤50 m.
- **Service worker**: `r.clone()` antes de devolver a resposta. Recurso de outro domínio só entra no cache se o pedido for CORS. Para testar offline, cortar a rede **e** limpar o cache HTTP.
- **APK**: o WebView não baixa arquivos; exportação por `TrilhaNative.shareFile`. `FLAG_KEEP_SCREEN_ON` no `MainActivity`.
- **Celular deitado** (altura ≤480 px): conferir o `#side` em 740×360 e 568×320.
- **Permissões da sessão**: no modo Auto o `keytool` (credencial) é recusado mesmo com o "ok" do dono no chat; ler `node_modules` é barrado por hook (`guard.sh`).
- Patches grandes no `index.html` por script Python com `assert count == 1` por trecho; o arquivo tem linhas longas. Para apagar blocos, cada unidade de topo do `<script>` começa na coluna 0 e as continuações são recuadas; conferir com `node --check` no script extraído.

## Como testar

```
cd trilhanav && python3 -m http.server 8765 &
cd dev && python3 fixtures.py && for t in t t3 t4 t5 t7 t9 t11 t12 t14 t15 t16 t17 t18 t19 t20 t21 t22 t23 t24 t25; do python3 $t.py; done
python3 fixtures.py --clean
```

Precisa de `playwright` (1.65.2; os testes usam `/usr/bin/google-chrome`) e Pillow. `fixtures.py` gera `rb.pdf`, `small.pmtiles` (+3 partes), `dl/` e `testmap.pmtiles` (de `make_testmap.py`); `roads.pmtiles` (malha z14 com rio e uma ponte) e `t.gpx` ficam no repositório.

`t` fumaça (sem restos de rali), `t3`/`t4` mapa offline por arquivo e por download, `t5` bússola, `t7` rotação do mapa, `t9` Arquivos/notas/tema, `t11` integração do APK, `t12` backup malicioso/teclas/MVT malformado, `t14` 1ª posição, exportar no APK, celular deitado, offline real com service worker, `t15` modo cidade e radares, `t16` telefone/WhatsApp/música/voz/atualização, `t17` partida do GPS no APK, `t18` assistente/agenda, `t19` mapa girando na rota, "ir para" por voz, clima, `t20` barra + Mais, postos, limite da via, inclinação, `t21` SOS/autonomia/painel, `t22` ligação do WhatsApp, `t23` Ir para offline (malha/ponte), música, voz, janelas sem Fechar, sem rali, `t24` busca offline e rota longa offline (`testmap.pmtiles`), `t25` download do mapa num Android que dá `NotReadableError` ao reler.

`t13` testa o pacote web do APK: `bash android-app/build-apk.sh --www-only`, servir `android-app/www` na porta 8766 e rodar `python3 t13.py` (e `python3 t16.py http://localhost:8766/index.html`).

## Mapa offline de Minas Gerais

Gerado com `go-pmtiles` (`go install github.com/protomaps/go-pmtiles@latest`), 1,4 GB, zoom 15:

```
go-pmtiles extract https://build.protomaps.com/AAAAMMDD.pmtiles mg.pmtiles --bbox=-51.05,-22.93,-39.85,-14.23 --maxzoom=15
```

Usar o build diário mais recente (o `build.protomaps.com` responde a `curl -r` com 206).

O app baixa o mapa do branch órfão **`mapas`** (pasta `mg/`: `manifest.json` + 30 partes de 45 MB, por `raw.githubusercontent.com`, que libera CORS). Para atualizar: gerar o `.pmtiles`, `split -b 45M -d -a 3`, refazer o `manifest.json` (`id`, `label`, `size`, `parts[{f,size,sha256}]`) com `id` novo e enviar em pushes de até 6 partes. No app as partes ficam em `mapa-dl/` e são lidas sem juntar (`PartsSource`). A busca e a rota offline usam as camadas `places`, `pois` e `roads` desse arquivo.
