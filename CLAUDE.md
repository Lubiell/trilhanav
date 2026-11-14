# TrilhaNav

App de navegação off-road no estilo do DMD2 (roadbook PDF, GPX, odômetro de rali), feito como PWA de um arquivo só. Dono: Jefferson (conta GitHub **Lubiell**). Repositório independente: não reaproveitar nada dos outros repos dele.

## Estado (v1.1, 13/11/2026)

- `index.html`: app inteiro (HTML + CSS + JS inline). Leaflet e pdf.js vêm do cdnjs.
- `lib/`: `pmtiles.js` 4.5.0 e `protomaps-leaflet.js` 5.1.0 (mapa vetorial offline).
- `sw.js`: cache offline do app e dos tiles online já vistos. Subir a versão `trilhanav-vN` a cada release.
- `manifest.json`, `icon.svg`, `icon-192.png`, `icon-512.png`.
- `dev/`: testes Playwright (`t.py` GPS/odômetro/alertas/teclas, `t2.py` PDF e tela dividida, `t3.py` mapa offline em partes) e `t.gpx`.

Pronto e testado só em Chrome headless (nunca em celular real): odômetro TOTAL/PARCIAL com multiplicador e calibração, CAP até o waypoint, validação automática de waypoint, alertas de fora da trilha e de velocidade, roadbook PDF, tela dividida, gravação e exportação GPX, cronômetro, teclas do controle de guidão configuráveis, simulação de GPS, trava de toque, dia/noite, mapa offline `.pmtiles` instalado no OPFS (aceita arquivo em partes `.part1..N`), botão que abre o Spotify.

## Pendências

1. **Publicado** em 14/11/2026: repo `Lubiell/trilhanav` (branch `main`), GitHub Pages em https://lubiell.github.io/trilhanav/. Só por esse link https o GPS e o mapa offline funcionam.
2. **Testar em celular real**: ainda não foi feito.
3. **Backup**: toda modificação vai também para o Google Drive dele (`trilhanav_backup_AAAA-MM-DD_vX.Y.zip`).

## Roteiro combinado (ele pediu "tudo")

1. CAP com bússola do aparelho (rumo parado/devagar) e correção automática do odômetro ao validar waypoint.
2. Copiloto por voz (speechSynthesis) e zonas de velocidade com aviso antecipado.
3. Perfil de altimetria (Raruto/leaflet-elevation) e rotação correta do mapa (Raruto/leaflet-rotate) no lugar do `transform` atual.
4. Ler OpenRally GPX (github.com/openrally/openrally, pasta `cross-country`) e gerar roadbook automático a partir de um GPX comum.
5. Gerenciador de GPX com pastas, notas/fotos na gravação, dia/noite automático.
6. Rota offline de volta à trilha (referência: Carreau/brx).
7. Versão APK com Capacitor + `@capacitor-community/background-geolocation` (GPS com tela apagada) e controle de mídia do Spotify.

Referência de lógica de tripmaster: mattogodoy/open-rally-computer (GPL-3: não copiar código sem manter o nosso aberto).

## Como testar

```
cd trilhanav && python3 -m http.server 8765 &
cd dev && python3 t.py && python3 t2.py && python3 t3.py
```

`t2.py` precisa de um `rb.pdf` qualquer e `t3.py` de `small.pmtiles.part1..3` (gerar com o comando abaixo e `split -b 4M`).

## Mapa offline de Minas Gerais

Gerado com `go-pmtiles` (`go install github.com/protomaps/go-pmtiles@latest`), 1,4 GB, zoom 15:

```
go-pmtiles extract https://build.protomaps.com/AAAAMMDD.pmtiles mg.pmtiles --bbox=-51.05,-22.93,-39.85,-14.23 --maxzoom=15
```

Usar o build diário mais recente. Para entregar pelo chat, dividir em partes de 340 MB (`split -b 340M`); o app junta as partes na instalação.
