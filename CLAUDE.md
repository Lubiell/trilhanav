# TrilhaNav

App de navegação off-road no estilo do DMD2 (roadbook PDF/OpenRally, GPX, odômetro de rali), feito como PWA de um arquivo só, com versão APK (Capacitor). Dono: Jefferson (conta GitHub **Lubiell**). Repositório independente: não reaproveitar nada dos outros repos dele.

## Estado final (v2.0, 15/11/2026)

Roteiro combinado: **7 de 7 etapas feitas**, mergeadas na `main` pelo PR #1 (merge commit `4de6888`). Os 13 testes (`dev/t.py` … `t13.py`) passaram em Chrome headless com este conteúdo. **Nada disto rodou em celular real.**

| Onde | O que tem |
|---|---|
| `main` | o código da v2.0 |
| `gh-pages` (`79860a0`) | o que o Pages serve em https://lubiell.github.io/trilhanav/. O runtime (`index.html`, `sw.js`, `manifest.json`, `lib/`) é idêntico ao da `main`; só docs, testes e `android-app/` diferem |
| `mapas` (órfão) | mapa de Minas Gerais: `mg/manifest.json` + 30 partes de 45 MB |
| `apk` (órfão) | `trilhanav-2.0.0.apk` (depuração), `SHA256SUMS`, README. Baixar: https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.0.0.apk. SHA-256 `cff10d0ac662927d5b4bd99b53aed322a6fbdb0b06e5e11a8265449394d73437` |
| `ccr-6d2015d5-vi9zyo` | branch de trabalho das sessões do Claude; reiniciada a partir da `main` a cada PR |
| Google Drive (raiz) | `trilhanav_backup_AAAA-MM-DD_vX.Y.zip` (snapshots do código via `git archive`); pasta `trilhanav/` com o bundle git e referências |

### Arquivos

- `index.html`: app inteiro (HTML + CSS + JS inline, estilo denso). Leaflet e pdf.js vêm do cdnjs (no APK vão locais). `window.TN` expõe internos para os testes.
- `lib/`: `pmtiles.js` 4.5.0, `protomaps-leaflet.js` 5.1.0 (mapa vetorial offline), `leaflet-rotate.js` 0.2.8 e `elevation/` (leaflet-elevation 3.0.1, só handlers Distance/Altitude/Slope, carregados por `import()` relativo a `dist/`: a estrutura `lib/elevation/{dist,src/handlers,images}` não pode mudar). As duas últimas são **GPL-3.0**: ver `NOTICE.md`.
- `sw.js`: cache offline do app (`trilhanav-vN`) e dos tiles online já vistos (`trilhanav-tiles`). Subir `N` a cada release e listar aqui qualquer arquivo novo de `lib/`.
- `manifest.json`, `icon.svg`, `icon-192.png`, `icon-512.png`.
- `android-app/`: empacotamento do APK (`build-apk.sh`, plugin Java `native/TrilhaNativePlugin.java`, `patch-android.py`, ver o README dele). `node_modules/`, `android/`, `www/` e `*.apk` não vão para o git.
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

### Onde o app guarda coisas

- `localStorage` (prefixo `tn_`): `cfg`, `keys`, `odo`, `wpState`, `gpxName`, `gpxKey` (caminho+tamanho; zera o progresso ao trocar de GPX), `gpxPath`, `gpx` (texto), `zones_<gpxKey>`, `chrono`, `lastPos`, `recSession`.
- OPFS: `gpx/` (pastas do usuário; `gpx/Gravações/` = cópias exportadas; `gpx/Abertos/` = GPX grande demais para o localStorage), `notas/<sessão>/` (json + jpg), `mapa-dl/` (partes do mapa baixado, com `manifest.json`), `mapa.pmtiles` (mapa instalado por arquivo).

## Fluxo de trabalho e de release

1. Mudança numa branch (`ccr-6d2015d5-vi9zyo`, reiniciada da `main` após cada merge) → PR em rascunho. O repositório **não tem CI de testes**: rodar os testes locais antes; o merge é feito pelo dono ou a pedido dele.
2. Publicar o site depois do merge: `git push origin origin/main:gh-pages` (fast-forward; subir `trilhanav-vN` no `sw.js` se o runtime mudou). A sessão do Claude só alcança o repositório por git push e pelas ferramentas de PR (sem API de Pages/Releases).
3. Backup: `git archive --format=zip --prefix=trilhanav/ -o trilhanav_backup_AAAA-MM-DD_vX.Y.zip HEAD` e subir na raiz do Drive. O conector do Drive recusa arquivo acima de ~3 MB por chamada (por isso o APK e o bundle não sobem).
4. APK: `bash android-app/build-apk.sh` (precisa de JDK 21 e Android SDK com licenças). Publicar no branch `apk` com `git worktree add --orphan` (sem mexer na árvore de trabalho), atualizando o `SHA256SUMS` e o README.

## Pendências

1. **Testar em celular real**: bússola (a declinação é aprendida pelo GPS; pode variar entre aparelhos), GPS com a tela apagada, voz nativa, controle de música, o APK e o mapa em tela real. O APK foi conferido por dentro (manifest, permissões, assinatura, classes, assets sem CDN), nunca em uso.
2. **Licença**: as libs GPL-3.0 obrigam manter o código aberto; o repositório ainda não tem `LICENSE` próprio (decisão do dono).
3. **Segurança, do relatório de 15/11 e ainda não aplicado**: CSP por `<meta>`; SRI (ou cópia local) para o Leaflet/pdf.js do cdnjs e Google Fonts no PWA; cache de tiles do service worker guarda resposta opaca sem limite de tamanho; `window.TN` exposto em produção; `distributionSha256Sum` no Gradle wrapper e ações do workflow por SHA. O pdf.js 3.11 é vulnerável (CVE-2024-4367) e está só mitigado com `isEvalSupported:false`; migrar para 4.2.67+ exige adaptar a carga (ESM).
4. **Origem compartilhada**: `localStorage`, OPFS e a permissão de GPS são por origem (`lubiell.github.io`), não por caminho. Qualquer outro site de Pages da mesma conta alcança os dados do TrilhaNav. Se houver outros, usar domínio próprio.
5. **APK de depuração**: `debuggable` e assinado com a chave de depuração; cada compilação no GitHub gera uma chave nova (atualizar por cima exige desinstalar e apaga trilhas, notas e mapa offline). Para distribuir a outras pessoas é preciso `assembleRelease` com keystore própria.
6. Ideias ainda não feitas: busca de endereço offline, controle de câmeras GoPro/Insta360 pelo guidão, exportar o roadbook automático como OpenRally, preferir menos curvas no caminho de volta, redimensionar o gráfico de altimetria quando o mapa aparece.

Referência de lógica de tripmaster: mattogodoy/open-rally-computer (GPL-3: não copiar código sem manter o nosso aberto).

## Armadilhas já encontradas

- Linhas de lista com botões dentro de `<label>`: tocar no texto dispara o primeiro botão. Usar `div.lr`.
- `map.fitBounds` com a aba Mapa oculta (tamanho 0) dá zoom `NaN` e exceção; só enquadrar com o mapa visível (`fitTrack`/`mapShown`).
- Atalhos de teclado não valem em `input/textarea/select` nem com `e.code` vazio (teclado virtual).
- Texto vindo de GPX/OpenRally/backup nunca entra em `innerHTML` sem `esc()`; desenhos do OpenRally só em `<img src="data:…">`.
- Decodificador MVT próprio (`mvtRoads`): depois das feições de uma camada é preciso `p=end`, senão as chaves/valores dela são relidos como camada.
- Gradle no ambiente da sessão: o Maven Central responde 429 a `HEAD` e o Gradle mostra "Could not find". Solução (init script local com o espelho do Google) no README de `android-app/`.
- Patches grandes no `index.html` foram feitos por script Python com `assert count == 1` por trecho; manter esse cuidado, o arquivo tem linhas longas.

## Como testar

```
cd trilhanav && python3 -m http.server 8765 &
cd dev && for t in t t2 t3 t4 t5 t6 t7 t8 t9 t10 t11 t12; do python3 $t.py; done
```

Precisa do pacote Python `playwright` (os testes usam `/usr/bin/google-chrome`) e de Pillow nos testes t9. Fixtures que **não** ficam no repositório (gerar e colocar em `dev/` antes de rodar; apagar depois):

- `rb.pdf` (t2, t8, t12, t13): um PDF qualquer.
- `small.pmtiles` e `small.pmtiles.part1..3` (t3, t7, t12): mapa pequeno em 3 partes (`split -b 2M --numeric-suffixes=1 -a 1`).
- `dl/` (t4): `manifest.json` (`id`, `label`, `size`, `parts[{f,size,sha256}]`) + as 3 partes.
- `roads.pmtiles` (t10): z14 com uma malha de estradas, um rio e uma só ponte, tiles recortados com buffer de 64 (como o Planetiler).

`t5` bússola/odômetro, `t6` copiloto/zonas, `t7` rotação/altimetria, `t8` OpenRally/roadbook automático, `t9` gerenciador/notas/tema, `t10` rota de volta, `t11` integração do APK (Capacitor simulado), `t12` correções das revisões (backup malicioso, teclas ao digitar, MVT malformado, GPX por pasta, etc.).

`t13` testa o pacote web do APK: `bash android-app/build-apk.sh --www-only`, servir `android-app/www` na porta 8766 (`python3 -m http.server 8766` dentro dela) e rodar `python3 t13.py` (também precisa de `rb.pdf` e `t.gpx` em `dev/`).

## Mapa offline de Minas Gerais

Gerado com `go-pmtiles` (`go install github.com/protomaps/go-pmtiles@latest`), 1,4 GB, zoom 15:

```
go-pmtiles extract https://build.protomaps.com/AAAAMMDD.pmtiles mg.pmtiles --bbox=-51.05,-22.93,-39.85,-14.23 --maxzoom=15
```

Usar o build diário mais recente (o `build.protomaps.com` responde a `curl -r` com 206; testado em 15/11/2026).

O app baixa o mapa do branch órfão **`mapas`** (pasta `mg/`: `manifest.json` + 30 partes de 45 MB, lidas por `raw.githubusercontent.com`, que libera CORS). Para atualizar o mapa: gerar o `.pmtiles`, `split -b 45M -d -a 3`, refazer o `manifest.json` (`id`, `label`, `size`, `parts[{f,size,sha256}]`) com `id` novo e enviar em pushes de até 6 partes. No app as partes ficam em `mapa-dl/` no OPFS e são lidas sem juntar (`PartsSource`).

A rota de volta (`↩️`) usa a camada `roads` desse mesmo arquivo: precisa do mapa offline instalado e de zoom 14 ou mais.
