# TrilhaNav

App de navegação off-road no estilo do DMD2 (roadbook PDF/OpenRally, GPX, odômetro de rali), feito como PWA de um arquivo só, com versão APK (Capacitor). Dono: Jefferson (conta GitHub **Lubiell**). Repositório independente: não reaproveitar nada dos outros repos dele.

## Estado (v2.0, 15/11/2026)

- `index.html`: app inteiro (HTML + CSS + JS inline). Leaflet e pdf.js vêm do cdnjs (no APK vão locais).
- `lib/`: `pmtiles.js` 4.5.0, `protomaps-leaflet.js` 5.1.0 (mapa vetorial offline), `leaflet-rotate.js` 0.2.8 e `elevation/` (leaflet-elevation 3.0.1, só handlers Distance/Altitude/Slope; carrega os handlers por `import()` relativo à pasta `dist/`, então a estrutura `lib/elevation/{dist,src/handlers,images}` não pode mudar). As duas últimas são **GPL-3.0**: ver `NOTICE.md`.
- `sw.js`: cache offline do app e dos tiles online já vistos. Subir a versão `trilhanav-vN` a cada release e listar aqui qualquer arquivo novo de `lib/`.
- `manifest.json`, `icon.svg`, `icon-192.png`, `icon-512.png`.
- `android-app/`: empacotamento como APK (ver `android-app/README.md`). `node_modules/`, `android/`, `www/` e `*.apk` não vão para o git.
- `.github/workflows/apk.yml`: compila o APK no GitHub (manual ou por tag `v*`).
- `dev/`: testes Playwright em Python (ver "Como testar").

### Recursos (testados só em Chrome headless, nunca em celular real)

- Base (v1.x): odômetro TOTAL/PARCIAL com multiplicador e calibração, CAP até o waypoint, validação automática de waypoint, alertas de fora da trilha e de velocidade, roadbook PDF, tela dividida, gravação e exportação GPX, cronômetro, teclas do controle de guidão configuráveis, simulação de GPS, trava de toque, mapa offline `.pmtiles` no OPFS (download do mapa de MG do branch `mapas`, retomável e com SHA-256, ou instalação por arquivo em partes), botão do Spotify.
- 1) **Bússola**: rumo do aparelho (parado/devagar, compensa inclinação e rotação da tela; vale o GPS acima de N km/h e ele ensina o ajuste de declinação). **Correção do odômetro**: ao validar um waypoint o TOTAL passa a ser o km do roadbook (trava de divergência; aprender o multiplicador é opcional).
- 2) **Copiloto por voz** (speechSynthesis; TTS nativo no APK) com aviso antecipado por tempo, e **zonas de velocidade** (waypoints "VEL 40" … "FIM" no GPX, zonas do OpenRally ou criadas à mão).
- 3) **Rotação real do mapa** (`map.setBearing`, rumo para cima) e **perfil de altimetria** sob o mapa (botão 📈).
- 4) **OpenRally** v1.0.x (km oficial, WPs com raios open/clear, perigo, CAP, zonas, parada, neutralização, tulip/notes) e **roadbook automático** de GPX comum (curvas por mudança de rumo + tulipas SVG), lista que rola sozinha.
- 5) **Gerenciador de GPX** com pastas (OPFS, botão 🗂️), **notas com foto** na gravação (📝; exporta GPX ou ZIP com fotos), **tema dia/noite automático** pelo sol (🌗 cicla automático/dia/noite).
- 6) **Rota de volta à trilha** sem internet (↩️): Dijkstra sobre a camada `roads` do mapa offline; sem mapa, linha reta.
- 7) **APK**: GPS em segundo plano, voz nativa, controle de música e Spotify (`android-app/`).

## Pendências

1. **Publicado** em https://lubiell.github.io/trilhanav/ (só por esse link https o GPS e o mapa offline funcionam). O Pages publica o branch **`gh-pages`**; a sessão do Claude só alcança o repositório por git push (sem API de Pages/Releases).
2. **Testar em celular real**: nada disto foi feito (bússola, GPS em segundo plano, voz, mídia, APK, mapa em tela real). Pode haver diferenças entre aparelhos, principalmente na bússola.
3. **Backup**: toda modificação vai também para o Google Drive dele (`trilhanav_backup_AAAA-MM-DD_vX.Y.zip`).
4. **Licença**: as libs GPL-3.0 obrigam manter o código aberto; o repositório ainda não tem `LICENSE` próprio (decisão do dono).
5. Ideias ainda não feitas: busca de endereço offline, controle de câmeras GoPro/Insta360 pelo guidão, exportar o roadbook automático como OpenRally, preferir menos curvas no caminho de volta.

Referência de lógica de tripmaster: mattogodoy/open-rally-computer (GPL-3: não copiar código sem manter o nosso aberto).

## Como testar

```
cd trilhanav && python3 -m http.server 8765 &
cd dev && for t in t t2 t3 t4 t5 t6 t7 t8 t9 t10 t11; do python3 $t.py; done
```

Precisa do pacote Python `playwright` (os testes usam `/usr/bin/google-chrome`) e de Pillow nos testes t9. Fixtures que **não** ficam no repositório (gerar e colocar em `dev/` antes de rodar; apagar depois):

- `rb.pdf` (t2, t8): um PDF qualquer.
- `small.pmtiles` e `small.pmtiles.part1..3` (t3, t7): mapa pequeno em 3 partes (`split -b 2M --numeric-suffixes=1 -a 1`).
- `dl/` (t4): `manifest.json` (`id`, `label`, `size`, `parts[{f,size,sha256}]`) + as 3 partes.
- `roads.pmtiles` (t10): z14 com uma malha de estradas, um rio e uma só ponte, tiles recortados com buffer de 64 (como o Planetiler).

`t5` bússola/odômetro, `t6` copiloto/zonas, `t7` rotação/altimetria, `t8` OpenRally/roadbook automático, `t9` gerenciador/notas/tema, `t10` rota de volta, `t11` integração do APK (Capacitor simulado).

## Mapa offline de Minas Gerais

Gerado com `go-pmtiles` (`go install github.com/protomaps/go-pmtiles@latest`), 1,4 GB, zoom 15:

```
go-pmtiles extract https://build.protomaps.com/AAAAMMDD.pmtiles mg.pmtiles --bbox=-51.05,-22.93,-39.85,-14.23 --maxzoom=15
```

Usar o build diário mais recente.

O app baixa o mapa do branch órfão **`mapas`** (pasta `mg/`: `manifest.json` + 30 partes de 45 MB, lidas por `raw.githubusercontent.com`, que libera CORS). Para atualizar o mapa: gerar o `.pmtiles`, `split -b 45M -d -a 3`, refazer o `manifest.json` (`id`, `label`, `size`, `parts[{f,size,sha256}]`) com `id` novo e enviar em pushes de até 6 partes. No app as partes ficam em `mapa-dl/` no OPFS e são lidas sem juntar (`PartsSource`).

A rota de volta (`↩️`) usa a camada `roads` desse mesmo arquivo: precisa do mapa offline instalado e de zoom 14 ou mais.
