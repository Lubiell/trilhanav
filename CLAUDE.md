# TrilhaNav

App de navegação off-road no estilo do DMD2 (roadbook PDF/OpenRally, GPX, odômetro de rali), feito como PWA de um arquivo só, com versão APK (Capacitor). Dono: Jefferson (conta GitHub **Lubiell**). Repositório independente: não reaproveitar nada dos outros repos dele.

## Estado (v2.6.3, 23/11/2026)

Roteiro combinado: **7 de 7 etapas feitas**, mergeadas na `main` pelo PR #1 (merge commit `4de6888`). **Nada disto rodou em celular real.**

**v2.6.3 (23/11/2026, PR #3):** o dono pediu "tirar as funções de trilha" (escolheu: rali/off-road) e janelas sem "Fechar". Rali/trilha **escondido por padrão**, não apagado: `body.notrail .trail{display:none}`; `TRAIL` = `tn_trailOn` (Ajustes › Aparência, `#sTrail`, recarrega a página) ou `?trilha=1` na URL (**todos os testes antigos abrem com `?trilha=1`**; o `t23` testa o padrão sem). Sem trilha: abre no Mapa; somem Roadbook (barra), TOTAL/PARCIAL (painel lateral), Dividir, Altimetria, Waypoints, Cronômetro, Voltar à trilha, Zerar parcial (Mais), seções Odômetro/Roadbook e partes de Navegação/zonas nos Ajustes, teclas de rali (`TRAIL_KEYS`) e mostradores `TRAIL_DASH`. CAP e Velocidade ficam (o CAP segue o Ir para). Janelas: sem botão "Fechar"; toque no fundo fecha e repassa o toque ao botão embaixo (`elementFromPoint`), menos no `dlgAsk`; Voltar do Android (`MainActivity` → `window.tnBack()`) fecha a janela de cima, sem janela manda o app para segundo plano (`moveTaskToBack`).

**v2.6.2 (23/11/2026, PR #3, sobre a 2.6.1):** o dono pediu "não usar Waze nem Google Maps, usar os mapas baixados no próprio app": saíram os botões/opções do Waze e do Google Maps; o "Ir para" usa `anyRoute` (Valhalla quando há rede e `netOk`, senão ou se falhar `offNavReq` = A* `offlineRouteTo` sobre a camada `roads` do mapa offline, z14→z12, até `RT_MAXT`=100 tiles, curva custa +40 m para não zigue-zaguear em malha; `offNavRoute` gera as manobras no formato do Valhalla; sem ligação, botão "Seguir em linha reta"); toque longo no mapa = destino; "Trilha, ir para" e postos também caem no offline (recentes/favoritos sem internet). Voz: com o microfone do capacete ligado (`TrilhaVoiceService.onHeadset()`), o TTS sai com `USAGE_VOICE_COMMUNICATION` (pelo SCO; antes saía como navegação e podia não chegar ao fone — [Provável] causa do "não consegui ouvir"); foco com redução pedido *antes* de falar; sem voz pt-BR cai na voz padrão; `ttsStatus`/`installVoice` e o "Testar voz" com diagnóstico; navegador destrava a voz no 1º toque. Música: "trocar" vira próxima; volume +/− nas teclas do guidão (`mediaVolUp`/`mediaVolDown`). `t23`. **Chave:** a 2.6.1 foi assinada com uma chave de depuração perdida; a 2.6.2 saiu do workflow do GitHub (chave nova a cada compilação): o dono desinstalou a 2.6.1 antes. Ver pendência da chave.

**v2.6.1 (17/11/2026):** assistente pelo microfone do fone/intercom Bluetooth (`cfg.voiceBt`, padrão ligado por escolha do dono, sabendo que a música fica com qualidade de ligação): `TrilhaVoiceService` com `AudioRecord` próprio (VOICE_COMMUNICATION + `setPreferredDevice`), canal SCO por `setCommunicationDevice` (Android 12+) ou `startBluetoothSco`, rechecado a cada 15 s; solta o microfone em ligação/escuta do Google. Nunca testado com fone de verdade. APK 2.6.1 publicado (a 2.5.0 saiu do branch `apk`).

**v2.6.0 (17/11/2026):** aviso de queda (spec aprovada: `crashArm`/`sendSms` no nativo, decisão no app `onImpact`/`sosPos`/`sosCount`/`sosSend`, `t21`); ligação do WhatsApp (`TrilhaNotifService.handleCall` → evento `wacall`, `waCallAction` aciona os botões da notificação; `t22`); autonomia (`rangeKm`, `fuelKm`, `fillUp`); Painel personalizável (`DASH`, `tn_dashSel`, `cfg.dashBig`); ícone novo (`icon.svg` + `make-icons.py`, também `--pwa`); tema dia mais contrastado. APK 2.6.0 publicado (a 2.4.0 saiu do branch `apk`).

**v2.5.0 (17/11/2026):** barra com 8 botões + grade "Mais" (`#bMore`/`dlgMore`/`#moreGrid`); repetições tiradas (um só `sRotMode` = `cfg.rot`/`cfg.navRot`; Abrir → `#gOpen` em Arquivos; um só Marcar radar + voz; tema só no `#bDay`); postos (`fuelFind`/`fuelGo`, Overpass `amenity=fuel` 8 km); limite da via (`limCheck`, `maxspeed` por quadrados de 0,05°, só na memória; entra no alerta de velocidade existente); inclinação (`lean`, `devicemotion`). Pesquisa de apps de moto (Detecht, calimoto, EatSleepRIDE, MotoSema, Kurviger). Detecção de queda: spec `docs/specs/2026-11-17-deteccao-de-queda.md` (aprovada e feita na 2.6.0). `t20`; APK 2.5.0 publicado (a 2.3.0 saiu do branch `apk`).

**v2.4.0 (16/11/2026):** mapa gira sozinho durante o "Ir para" (`cfg.navRot`); "Trilha, ir para <lugar>" por voz (`goPlace`/`askPlace`, "encerrar rota"); clima com temperatura na barra de cima e alertas (Open-Meteo, reserva MET Norway; `t19`). **APK 2.4.0 publicado**; a 2.2.0 e a 2.1.0 saíram do branch `apk` (ficam no histórico do git).

**v2.3.0 (16/11/2026, primeiro retorno do celular real):** o dono instalou a 2.2.0 num Samsung e relatou: GPS em "GPS ---" com o GPS ligado; voz tem de ficar sempre ligada; WhatsApp não aparece; contatos. Correções: GPS com novas tentativas + motivo na tela + GPS do WebView como reserva (`t17`); assistente sempre ligado offline (Vosk, `TrilhaVoiceService`, palavra "Trilha", `t18`); agenda completa; WhatsApp por `MessagingStyle` + diagnóstico + `requestRebind`. **APK 2.3.0 publicado (56 MB)**. A causa real do WhatsApp no aparelho dele ainda não é conhecida: o diagnóstico na tela Telefone vai mostrar.

**v2.2.0 (16/11/2026, telefone e voz):** botões Telefone e Voz; atender/recusar/fazer ligação, WhatsApp na tela, música atual e Spotify em segundo plano, comandos de voz, atualização do APK pelo próprio app (`versao.json` no branch `apk`). Spec `docs/specs/2026-11-16-telefone-voz-atualizacao.md` (opção A aprovada). 16 testes passam (`t16` novo, nativo simulado; também no pacote do APK). **APK 2.2.0 publicado.** Ligação, WhatsApp e microfone reais **nunca testados** (sem emulador: o ambiente não tem KVM).

**v2.1.0 (16/11/2026, modo cidade):** "Ir para" (rota por ruas para moto, tipo Waze), radares do OpenStreetMap, ícones SVG e ajustes de interface; spec em `docs/specs/2026-11-16-rota-urbana.md`. Commits na branch de trabalho (PR #2, junto com a v2.0.1). 15 testes passam (`t15` novo, serviços simulados); busca, rota e radares também conferidos contra os serviços reais em 16/11. **APK 2.1.0 publicado** no branch `apk`. Site (`gh-pages`) e `main` continuam na v2.0 até o merge do PR #2.

**v2.0.1 (15/11/2026, caça a erros):** 11 erros confirmados por reprodução e corrigidos, cada um com teste em `dev/t14.py` (ver "Armadilhas já encontradas"). Os 14 testes (`dev/t.py` … `t14.py`) passam em Chrome headless. O **APK 2.0.1 já está publicado** no branch `apk`; o site (`gh-pages`) e a `main` continuam na v2.0 até o PR #2 ser mergeado e publicado. A revisão independente destas correções não terminou (o agente revisor parou por limite de uso): estão verificadas por teste, não por segunda leitura.

| Onde | O que tem |
|---|---|
| `main` | o código da v2.0 |
| `gh-pages` (`79860a0`) | o que o Pages serve em https://lubiell.github.io/trilhanav/. O runtime (`index.html`, `sw.js`, `manifest.json`, `lib/`) é idêntico ao da `main`; só docs, testes e `android-app/` diferem |
| `mapas` (órfão) | mapa de Minas Gerais: `mg/manifest.json` + 30 partes de 45 MB |
| `apk` (órfão) | `trilhanav-2.6.2.apk` (atual, depuração, 56 MB, **chave nova** `ea205c4c…f2df9b`, compilado pelo workflow APK), 2.6.1, 2.0.1, 2.0.0 (as outras só no histórico), `SHA256SUMS`, README e **`versao.json`** (`version`, `code`, `apk`, `sha256`, `notes`: o app ≥2.2.0 lê para se atualizar; atualizar a cada APK novo). Baixar: https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.6.2.apk. SHA-256 `3e8d0cf4060069c64feed3dbbd1fce232e4da5be43c2bc8f6ce288d37344b33e`. Arquivo >50 MB: o GitHub avisa (limite é 100 MB). Da 2.0.0 à 2.6.1 a chave era `16acb7ad…8029` (perdida com o ambiente da sessão que compilou); a 2.6.2 exige desinstalar a 2.6.1 antes |
| `ccr-6d2015d5-vi9zyo` | branch de trabalho das sessões do Claude; reiniciada a partir da `main` a cada PR |
| Google Drive (raiz) | `trilhanav_backup_AAAA-MM-DD_vX.Y.zip` (snapshots do código via `git archive`); pasta `trilhanav/` com o bundle git e referências |

### Arquivos

- `index.html`: app inteiro (HTML + CSS + JS inline, estilo denso). Leaflet e pdf.js vêm do cdnjs (no APK vão locais). `window.TN` expõe internos para os testes.
- `lib/`: `pmtiles.js` 4.5.0, `protomaps-leaflet.js` 5.1.0 (mapa vetorial offline), `leaflet-rotate.js` 0.2.8 e `elevation/` (leaflet-elevation 3.0.1, só handlers Distance/Altitude/Slope, carregados por `import()` relativo a `dist/`: a estrutura `lib/elevation/{dist,src/handlers,images}` não pode mudar). As duas últimas são **GPL-3.0**: ver `NOTICE.md`.
- `sw.js`: cache offline do app (`trilhanav-vN`, hoje `v12`) e dos tiles online já vistos (`trilhanav-tiles`). Rede primeiro; guarda em tempo de uso os arquivos do próprio app, do cdnjs e as fontes do Google. Subir `N` a cada release e listar aqui qualquer arquivo novo de `lib/`.
- `manifest.json`, `icon.svg`, `icon-192.png`, `icon-512.png`.
- `android-app/`: empacotamento do APK (`build-apk.sh`, plugin Java `native/TrilhaNativePlugin.java` + `native/TrilhaNotifService.java` (acesso a notificações), `native/TrilhaVoiceService.java` (assistente Vosk; o `build-apk.sh` baixa o modelo pt para `android-app/vosk-model/`, confere o SHA-256 e põe em `assets/model-pt` com o arquivo `uuid`; só ABIs ARM), `patch-android.py`, ver o README dele). `node_modules/`, `android/`, `www/` e `*.apk` não vão para o git.
- `.github/workflows/apk.yml`: compila o APK no GitHub (Actions → APK → Run workflow, ou tag `v*`); `permissions: contents: read`, sem credencial persistida.
- `dev/`: testes Playwright em Python (ver "Como testar").
- `NOTICE.md`: licenças de terceiros.

### Recursos

- Base (v1.x): odômetro TOTAL/PARCIAL com multiplicador e calibração, CAP até o waypoint, validação automática de waypoint, alertas de fora da trilha e de velocidade, roadbook PDF, tela dividida, gravação e exportação GPX, cronômetro, teclas do controle de guidão configuráveis, simulação de GPS, trava de toque, mapa offline `.pmtiles` no OPFS (download do mapa de MG do branch `mapas`, retomável e com SHA-256, ou instalação por arquivo em partes), botão do Spotify.
- 1) **Bússola**: rumo do aparelho (parado/devagar; compensa inclinação e rotação da tela). Vale o GPS acima de N km/h e ele ensina o ajuste de declinação (só aprende rodando reto acima de 15 km/h). **Correção do odômetro**: ao validar um waypoint o TOTAL passa a ser o km do roadbook (trava de divergência; aprender o multiplicador é opcional).
- 2) **Copiloto por voz** (speechSynthesis; TTS nativo no APK) com aviso antecipado por tempo, e **zonas de velocidade** (waypoints "VEL 40" … "FIM" no GPX, zonas do OpenRally ou criadas à mão, em km do trilho).
- 3) **Rotação real do mapa** (`map.setBearing(360 − rumo)`, rumo para cima) e **perfil de altimetria** sob o mapa (📈).
- 4) **OpenRally** v1.0.x (km oficial, WPs com raios open/clear, perigo, CAP, zonas, parada, neutralização, tulip/notes) e **roadbook automático** de GPX comum (curvas por mudança de rumo + tulipas SVG), lista que rola sozinha.
- 5) **Gerenciador de GPX** com pastas (OPFS, 🗂️), **notas com foto** na gravação (📝; exporta GPX ou ZIP com fotos), **tema dia/noite automático** pelo sol (🌗 cicla automático/dia/noite).
- 6) **Rota de volta à trilha** sem internet (↩️): Dijkstra sobre a camada `roads` do mapa offline (zoom 14+); sem mapa, linha reta.
- 7) **APK**: GPS em segundo plano (serviço em primeiro plano), voz nativa que baixa a música, controle de música e Spotify.
- 8) **Modo cidade (v2.1, botão "Ir para")**: busca de endereço (Photon/komoot; aceita `lat, lon`), rota para moto em pt-BR com até 3 alternativas ordenadas por tempo (Valhalla/FOSSGIS, `costing: motorcycle`, evitar pedágio/rodovias), cartão de manobra no topo (seta, distância, rua, hora de chegada), voz curva a curva (aviso antecipado + na hora), recálculo após 3 posições fora da rota (mín. 8 s entre pedidos), chegada, "De" opcional (guia até o início), favoritos/recentes, Abrir no Waze / Google Maps (APK: `TrilhaNative.openUrl`, só https). O CAP do painel lateral segue a rota. Aviso de privacidade antes do 1º pedido (`tn_netOk`).
- 10) **Telefone, WhatsApp, música e voz (v2.2, só APK)**: `TrilhaNative` ganhou `phoneStatus`, `requestPhone`, `openNotifAccess`, `openAppSettings`, `answerCall`, `endCall` (Android 9+), `placeCall`, `findContacts`, `listen` (SpeechRecognizer pt-BR), `volume`, `spotifyPlay` (MEDIA_BUTTON direto para o pacote do Spotify), `appInfo`, `installApk` (só URL do branch `apk`, confere SHA-256, abre o instalador) e eventos `call` (ringing/offhook/idle + nome da agenda), `whatsapp`, `media`, `update`. No app: `#callBox` (fecha diálogos abertos), `#waCard`, `dlgPhone`, `parseCmd` (intérprete de frases) + `runCmd`, teclas `voice`/`answer`/`hangup`. Mensagens só na memória (20).
- 11) **Assistente de voz sempre ligado (v2.3, só APK)**: `voiceStart/voiceStop/voiceWords`, eventos `heard`/`voice`; gramática = `VBASE` + palavras dos nomes dos favoritos e da agenda (≤800). Age só com "trilha" na frase, logo depois de armado (botão Voz / "trilha" sozinho, 6 s) ou atender/recusar tocando; "ligar para" sem nome → `askName` (Google). Pausas nativas por motivo (`tts`, `call`, `listen`). `cfg.voiceAlways` (padrão ligado). Agenda: `listContacts` → `contactsAll` (só na memória).
- 12) **Mapa gira na rota e "ir para" por voz (v2.4)**: `applyHeading` gira com `cfg.rot || (nav && cfg.navRot)`; `parseCmd` → `go` (`GORE`: ir/vamos/leva/navegar + lugar), `stopnav` ("encerrar/cancelar rota|navegação", checado antes de "encerrar" = desligar), `wx`; `goPlace` usa recentes antes do Photon e começa a rota direto.
- 13) **Clima (v2.4)**: `wxFetch` (Open-Meteo `current`/`minutely_15`/`hourly`, 12 h; se falhar, MET Norway `compact`), posição a 0,01°, a cada 15 min ou 10 km (`wxUpdate`), `wxAlerts` (tempestade, chuva chegando, rajadas ≥60 km/h, ≥35°, ≤5°, neblina; 1 vez/hora por tipo), `wxRoute` (destino na hora de chegada e meio da rota >30 km), `#wx` na barra de cima, `dlgWx`. Só com `tn_netOk`. `cfg.wx`, `cfg.wxVoice`.
- 14) **v2.5**: barra principal (Roadbook, Mapa, Ir para, Painel, Telefone, Voz, Gravar, Mais) e o resto em `#moreGrid` (os ids dos botões não mudaram; a grade fecha sozinha depois do clique); `#chronoTop` mostra o cronômetro rodando. Postos (`dlgFuel`, `fuelLayer`, voz `fuel`). Limite da via: `limCells` (≤40 quadrados, só memória), via mais próxima ≤25 m no sentido do rumo (mão única respeitada), `#limBox`, `cfg.limOn`/`cfg.limTol`; no `checkAlerts` vale zona > via > `cfg.spd`. Inclinação: tan(θ)=v·ω/g com ω = giroscópio projetado na vertical calibrada parada (`lean.g0`); positivo = esquerda.
- 15) **v2.6**: SOS (`cfg.crashOn` padrão desligado, `crashSens` normal 4 g / alta 3 g, `crashName`, `tn_sosC` até 3 contatos; impacto só vale com velocidade ≥25 km/h nos 6 s anteriores; 15 s parado → contagem de 30 s → SMS → 4 s depois, ainda parado, liga para o 1º; cancela por toque, voz `none`/`end`/"estou bem" (sem "Trilha") ou qualquer tecla). WhatsApp: chamada = categoria `call`, extras `android.answerIntent`/`declineIntent`/`hangUpIntent` (CallStyle) ou texto "chamada…"; botões por rótulo (atender/recusar/desligar); `callSt.src='wa'` troca `answerCall`/`endCall` por `waCallAction`; a notificação removida = fim. Autonomia: `cfg.tankL`×`cfg.kmL` − `tn_fuelKm`, avisos em `reserveKm` e na metade.
- 9) **Radares (v2.1)**: `highway=speed_camera` do OSM via Overpass (`maps.mail.ru`), por quadrados de 0,25° ao redor da posição e ao longo da rota, guardados 30 dias; placa (limite + distância) e voz a até `radarDist` m, faixa e placa piscando acima de limite + `radarTol`; na rota mede pela rota, sem rota usa um cone de ±30° e ≤45 m de lado no rumo do GPS; marcar radar à mão. Marcadores no mapa (zoom ≥12).

### Onde o app guarda coisas

- `localStorage` (prefixo `tn_`): `cfg`, `keys`, `odo`, `wpState`, `marks` (pontos de "Marcar aqui", com o índice na lista), `gpxName`, `gpxKey` (caminho+tamanho; zera o progresso ao trocar de GPX), `gpxPath`, `gpx` (texto), `zones_<gpxKey>`, `chrono`, `lastPos`, `recSession`, `navRecent` (destinos; `fav`), `netOk` (aviso de privacidade aceito), `phFav` (contatos favoritos: nome+número), `updT` (última procura de atualização), `sosC` (contatos de emergência), `fuelKm` (km desde o último abastecimento), `dashSel` (mostradores do Painel).
- OPFS: `gpx/` (pastas do usuário; `gpx/Gravações/` = cópias exportadas; `gpx/Abertos/` = GPX grande demais para o localStorage), `notas/<sessão>/` (json + jpg), `mapa-dl/` (partes do mapa baixado, com `manifest.json`), `mapa.pmtiles` (mapa instalado por arquivo), `radares.json` (`tiles` = quadrado→data; `pts` = `[id,lat,lon,limite,rumo]`; id `o…` do OSM, `u…` marcado à mão).

## Fluxo de trabalho e de release

1. Mudança numa branch (`ccr-6d2015d5-vi9zyo`, reiniciada da `main` após cada merge) → PR em rascunho. O repositório **não tem CI de testes**: rodar os testes locais antes; o merge é feito pelo dono ou a pedido dele.
2. Publicar o site depois do merge: `git push origin origin/main:gh-pages` (fast-forward; subir `trilhanav-vN` no `sw.js` se o runtime mudou). A sessão do Claude só alcança o repositório por git push e pelas ferramentas de PR (sem API de Pages/Releases).
3. Backup: `git archive --format=zip --prefix=trilhanav/ -o trilhanav_backup_AAAA-MM-DD_vX.Y.zip HEAD` e subir na raiz do Drive. O conector do Drive recusa arquivo acima de ~3 MB por chamada (por isso o APK e o bundle não sobem).
4. APK: subir a versão em `android-app/package.json` (e `package-lock.json`), `bash android-app/build-apk.sh` (precisa de JDK 21 e Android SDK com licenças). Publicar no branch `apk` com um worktree (sem mexer na árvore de trabalho), atualizando `SHA256SUMS`, README e **`versao.json`** (senão os celulares não veem a versão nova). Conferir o SHA-256 do arquivo baixado do raw.githubusercontent.com.

## Pendências

- **Chave de assinatura fixa (decisão do dono):** cada compilação no GitHub gera chave nova, então cada APK novo exige desinstalar o anterior (apaga trilhas, notas e mapa). Solução proposta: gerar uma keystore, guardar no Drive do dono e num secret do repositório (`DEBUG_KEYSTORE_B64`) e o `apk.yml` usar a mesma sempre. Não pôr a chave no repositório público.

- **Combinado para a 2.7 (17/11/2026), depois do teste do dono na 2.6.0:** primeiro corrigir o que ele relatar (GPS, ligação do WhatsApp, voz, SOS); depois, no mesmo APK: mandar a localização por voz ("Trilha, mandar minha localização para Maria", SMS com o link do mapa e a hora de chegada no Ir para), paradas no caminho no Ir para (Valhalla aceita vários `locations`; voz "Trilha, parar no posto") e histórico de viagens (registro por saída com km, tempo, velocidades, inclinação máxima e a trilha, no aparelho).
0. **Publicar a v2.0.1 + v2.1.0 no site** (só a pedido do dono): merge do PR #2 e `git push origin origin/main:gh-pages`. O APK 2.1.0 já está no branch `apk`. Antes ou depois do merge, vale passar pelo `reviewer` o diff `f370a03..3ae9f0d` (v2.0.1, revisão não terminou) e o da v2.1 (`817642e..HEAD`), que só foi verificado por teste.
1. **Testar em celular real**: a v2.3 (GPS em "GPS ---" corrigido? assistente com vento/capacete, bateria com o microfone sempre ligado, WhatsApp pelo diagnóstico da tela Telefone) e a v2.2 inteira (atender/recusar pelo app e por voz — `endCall`/`acceptRingingCall` são obsoletos e alguns fabricantes bloqueiam —, ligar por nome, WhatsApp com "configurações restritas" do Android 13+, música atual, `spotifyPlay`, o instalador da atualização);  o modo cidade inteiro (voz curva a curva na rua, recálculo, radares, botão Waze no APK) nunca rodou fora do navegador de teste; bússola (a declinação é aprendida pelo GPS; pode variar entre aparelhos), GPS com a tela apagada, voz nativa, controle de música, o APK e o mapa em tela real. O APK foi conferido por dentro (manifest, permissões, assinatura, classes, assets sem CDN), nunca em uso. Em especial, só um aparelho mostra: se a tela de compartilhar abre ao exportar no APK, se o seletor de arquivos do Android deixa escolher `.gpx`/`.pmtiles`, e se o odômetro anda sozinho parado com sinal ruim (o filtro é: desloca ≥3 m ou velocidade >3 km/h).
2. **Licença**: as libs GPL-3.0 obrigam manter o código aberto; o repositório ainda não tem `LICENSE` próprio (decisão do dono).
3. **Segurança, do relatório de 15/11 e ainda não aplicado**: CSP por `<meta>`; SRI (ou cópia local) para o Leaflet/pdf.js do cdnjs e Google Fonts no PWA; cache de tiles do service worker guarda resposta opaca sem limite de tamanho; `window.TN` exposto em produção; `distributionSha256Sum` no Gradle wrapper e ações do workflow por SHA. O pdf.js 3.11 é vulnerável (CVE-2024-4367) e está só mitigado com `isEvalSupported:false`; migrar para 4.2.67+ exige adaptar a carga (ESM).
4. **Origem compartilhada**: `localStorage`, OPFS e a permissão de GPS são por origem (`lubiell.github.io`), não por caminho. Qualquer outro site de Pages da mesma conta alcança os dados do TrilhaNav. Se houver outros, usar domínio próprio.
5. **APK de depuração**: `debuggable` e assinado com a chave de depuração; cada compilação no GitHub gera uma chave nova (atualizar por cima exige desinstalar e apaga trilhas, notas e mapa offline). Para distribuir a outras pessoas é preciso `assembleRelease` com keystore própria.
6. **Interface em celular, achados cosméticos do QA de 15/11**: corrigidos na v2.1 a altimetria ao girar, as tulipas de Largada/Chegada, a altura de botões/campos (≥40 px) e o "aqui" quebrando linha. Ainda abertos: tela dividida + altimetria em retrato fica espremida; `user-scalable=no` impede zoom. Não foram vistos: 412×915, teclado virtual real, banner de alerta sobre o conteúdo.
7. Ideias ainda não feitas: paradas intermediárias na rota da cidade, limite de velocidade da via (o Valhalla não devolve na rota), rota da cidade offline (precisaria de um roteador embarcado), busca de endereço offline, controle de câmeras GoPro/Insta360 pelo guidão, exportar o roadbook automático como OpenRally, preferir menos curvas no caminho de volta, redimensionar o gráfico de altimetria quando o mapa aparece (ao girar a tela já redimensiona).

Referência de lógica de tripmaster: mattogodoy/open-rally-computer (GPL-3: não copiar código sem manter o nosso aberto).

## Armadilhas já encontradas

- **Microfone do fone Bluetooth**: o Android só grava dele com o canal de voz (SCO/HFP) ligado, e aí a música também sai por esse canal, em mono. Não dá para ter as duas coisas; por isso existe o ajuste `voiceBt`. O `SpeechService` do Vosk não deixa escolher o microfone: a captura é própria.

- **Ligação do WhatsApp** não passa pelo estado do telefone (o `call` do Android não dispara): só a notificação de chamada mostra. Acionar o botão da notificação (`PendingIntent.send`) no Android 14+ precisa de `MODE_BACKGROUND_ACTIVITY_START_ALLOWED`; o WhatsApp pode mudar os rótulos ou o formato da notificação. Nunca testado num aparelho.
- **SOS**: a mensagem de chamada do WhatsApp não pode virar "mensagem" (ela é ongoing; `handleCall` vem antes dos filtros).

- **Botões dentro de "Mais"** ficam escondidos até abrir a grade: nos testes, acionar com `document.querySelector('#bX').click()` (os testes antigos foram trocados assim) ou abrir `#bMore` antes.
- **Testes que aceitam o aviso de internet** passam a buscar clima de verdade: simular `api.open-meteo.com` e `api.met.no` (o `t15` caiu nisso).
- **Inclinação de moto não sai do acelerômetro** (numa curva a gravidade + força centrípeta ficam no plano da moto): precisa do giroscópio × velocidade.

- **Open-Meteo** limita por IP por dia: daqui (IP do proxy compartilhado) responde 429 "Daily API request limit exceeded"; no celular cada um tem o seu. Por isso o MET Norway de reserva (CORS `*`, funciona com o User-Agent do navegador). Os avisos oficiais do INMET (`apiprevmet3.inmet.gov.br`) não responderam daqui: não usados.

- **Plugin de GPS em segundo plano** (`@capacitor-community/background-geolocation` 1.3.1): chamado antes de o serviço ligar responde "Service not running."; localização desligada vem como `NOT_AUTHORIZED` com a mensagem "Location services disabled."; vários erros são silenciosos. O app tenta de novo e tem o GPS do WebView como reserva (`t17`).
- **Vosk sem palavra de ativação** transforma conversa em comandos ("vou passar no posto" → "pausar"): por isso "trilha". O assistente tem de pausar enquanto o app fala (o aviso "diga atender" atenderia sozinho). Teste do reconhecimento: venv no scratchpad com `vosk` + `gTTS` (voz do Google, só as frases de comando) + ffmpeg para ruído.

- **Diálogo modal + tela de ligação**: `<dialog>` aberto com `showModal()` fica na camada de cima e deixa o resto inerte; a `#callBox` fecha os diálogos abertos ao aparecer.
- **Android manda o estado do telefone duas vezes** (com e sem número); entre tocando → em ligação o nome tem de ser mantido.
- **Microfone em segundo plano**: o Android só deixa com serviço em primeiro plano do tipo microfone, iniciado com o app na tela. O assistente Vosk (`TrilhaVoiceService`) tem esse serviço; a escuta do Google (`listen`) não, então só funciona com o app na tela.
- **Testar o pacote do APK (`www/`) com o Capacitor simulado**: o `lib/capacitor.js` real carrega por cima do simulado; o `t16` bloqueia esse arquivo.

- **Valhalla**: devolve as alternativas na ordem do custo dele, não do tempo (ordenar por `time`); o `pt-BR` deixa a rotatória e algumas frases em inglês (`ptTxt` troca pelo texto do tipo da manobra). Os serviços públicos (Photon, Valhalla, Overpass) pedem ≤1 pedido/s: tudo passa por `politeFetch` (fila por host). Nos testes, simular com `page.route` (ver `t15`), nunca bater no serviço real em laço.
- **Overpass**: `overpass-api.de` cortou a conexão e outros espelhos deram 403/timeout em 16/11; o `maps.mail.ru` funcionou (CORS `*`, ~20 s por área).
- Estado do modo cidade e dos radares é `var` (não `let`): `updateNav`/`checkAlerts` podem rodar antes do bloco ser executado.

- Linhas de lista com botões dentro de `<label>`: tocar no texto dispara o primeiro botão. Usar `div.lr`.
- `map.fitBounds` com a aba Mapa oculta (tamanho 0) dá zoom `NaN` e exceção; só enquadrar com o mapa visível (`fitTrack`/`mapShown`).
- Atalhos de teclado não valem em `input/textarea/select` nem com `e.code` vazio (teclado virtual).
- Texto vindo de GPX/OpenRally/backup nunca entra em `innerHTML` sem `esc()`; desenhos do OpenRally só em `<img src="data:…">`.
- Decodificador MVT próprio (`mvtRoads`): depois das feições de uma camada é preciso `p=end`, senão as chaves/valores dela são relidos como camada.
- Gradle no ambiente da sessão: o Maven Central responde 429 a `HEAD` e o Gradle mostra "Could not find". Solução (init script local com o espelho do Google) no README de `android-app/`.
- **Trilha gravada tem paradas**: os pontos amontoados inflavam o km e viravam curvas falsas. `cleanTrack` (em `loadGPX`) junta o que fica ≥30 s a menos de 20 m (precisa de `<time>`) e deixa ≥10 m entre pontos. Não medir distância nem curva no trilho cru.
- **Trocar de GPX**: o "começar do zero" (`wpState`, `wpIdx`, `marks`) tem de ser gravado na hora, não só na memória, senão ao reabrir o GPX novo herda o progresso do anterior. A chave do GPX (`gpxKey`) tem de ser a mesma ao abrir e ao reabrir.
- **Pontos inseridos à mão na lista de waypoints** ("Marcar aqui") precisam ser guardados e reinseridos no mesmo índice: `wpState` é alinhado por posição.
- **Odômetro**: a 1ª posição do GPS costuma ser imprecisa (rede); só vale como ponto de partida com precisão ≤50 m.
- **Service worker**: `r.clone()` tem de ser chamado antes de devolver a resposta (dentro do `.then` do `caches.open` o corpo já está em uso e nada é gravado). Recurso de outro domínio só entra no cache se o pedido for CORS (`crossorigin` no `<link>`); resposta opaca tem `ok=false`. Para testar offline de verdade, cortar a rede **e** limpar o cache HTTP (`Network.clearBrowserCache`), senão o cache do navegador esconde o que falta.
- **APK**: o WebView não baixa arquivos (`<a download>` não faz nada); exportação vai por `TrilhaNative.shareFile` (tela de compartilhar). `FLAG_KEEP_SCREEN_ON` no `MainActivity` mantém a tela ligada.
- **Celular deitado** (altura ≤480 px): o painel lateral precisa da media query de paisagem para caber os quatro mostradores; conferir em 740×360 e 568×320 ao mexer no `#side`.
- Nomes de waypoint viram zona de velocidade só por palavra inteira (`ZRE` com `\p{L}`): "Nivel 50" e "Travel 40" não são zonas.
- Patches grandes no `index.html` foram feitos por script Python com `assert count == 1` por trecho; manter esse cuidado, o arquivo tem linhas longas.

## Como testar

```
cd trilhanav && python3 -m http.server 8765 &
cd dev && for t in t t2 t3 t4 t5 t6 t7 t8 t9 t10 t11 t12 t14 t15 t16 t17 t18 t19 t20 t21 t22 t23; do python3 $t.py; done
```

Precisa do pacote Python `playwright` (os testes usam `/usr/bin/google-chrome`) e de Pillow nos testes t9. Fixtures que **não** ficam no repositório (gerar e colocar em `dev/` antes de rodar; apagar depois):

- `rb.pdf` (t2, t8, t12, t13, t14): um PDF qualquer.
- `small.pmtiles` e `small.pmtiles.part1..3` (t3, t7, t12): mapa pequeno em 3 partes (`split -b 2M --numeric-suffixes=1 -a 1`).
- `dl/` (t4): `manifest.json` (`id`, `label`, `size`, `parts[{f,size,sha256}]`) + as 3 partes.
- `roads.pmtiles` (t10): z14 com uma malha de estradas, um rio e uma só ponte, tiles recortados com buffer de 64 (como o Planetiler).

`t5` bússola/odômetro, `t6` copiloto/zonas, `t7` rotação/altimetria, `t8` OpenRally/roadbook automático, `t9` gerenciador/notas/tema, `t10` rota de volta, `t11` integração do APK (Capacitor simulado), `t12` correções das revisões (backup malicioso, teclas ao digitar, MVT malformado, GPX por pasta, etc.), `t21` aviso de queda/autonomia/painel/ícone, `t22` ligação do WhatsApp, `t20` barra + Mais, repetições, postos, limite da via, inclinação, `t19` mapa girando na rota, "ir para" por voz e clima (Open-Meteo/MET Norway simulados), `t17` partida do GPS no APK (serviço não pronto, desligado, mudo, notificação travada), `t18` assistente sempre ligado/agenda/diagnóstico do WhatsApp, `t16` telefone/WhatsApp/música/voz/atualização (nativo simulado; também roda no pacote do APK: `python3 t16.py http://localhost:8766/index.html`), `t15` modo cidade e radares (Photon/Valhalla/Overpass simulados; ícones, privacidade, voz, recálculo, chegada, radar na rota e sem rota, OPFS, cartão em retrato/deitado, altimetria ao girar), `t14` os erros da caça de 15/11 (troca de GPX, marcas, paradas no trilho, odômetro, retorno em linha reta, zonas pelo nome, exportação no APK, paisagem em celular e offline real com service worker).

`t13` testa o pacote web do APK: `bash android-app/build-apk.sh --www-only`, servir `android-app/www` na porta 8766 (`python3 -m http.server 8766` dentro dela) e rodar `python3 t13.py` (também precisa de `rb.pdf` e `t.gpx` em `dev/`).

## Mapa offline de Minas Gerais

Gerado com `go-pmtiles` (`go install github.com/protomaps/go-pmtiles@latest`), 1,4 GB, zoom 15:

```
go-pmtiles extract https://build.protomaps.com/AAAAMMDD.pmtiles mg.pmtiles --bbox=-51.05,-22.93,-39.85,-14.23 --maxzoom=15
```

Usar o build diário mais recente (o `build.protomaps.com` responde a `curl -r` com 206; testado em 15/11/2026).

O app baixa o mapa do branch órfão **`mapas`** (pasta `mg/`: `manifest.json` + 30 partes de 45 MB, lidas por `raw.githubusercontent.com`, que libera CORS). Para atualizar o mapa: gerar o `.pmtiles`, `split -b 45M -d -a 3`, refazer o `manifest.json` (`id`, `label`, `size`, `parts[{f,size,sha256}]`) com `id` novo e enviar em pushes de até 6 partes. No app as partes ficam em `mapa-dl/` no OPFS e são lidas sem juntar (`PartsSource`).

A rota de volta (`↩️`) usa a camada `roads` desse mesmo arquivo: precisa do mapa offline instalado e de zoom 14 ou mais.
