# TrilhaNav — APK

Branch órfã só com o APK (mesmo esquema do branch `mapas`). O código-fonte está no `main` e o projeto do APK em `android-app/`.

| Arquivo | Versão | Compilado de | Tamanho |
|---|---|---|---|
| **`trilhanav-2.0.1.apk`** (atual) | 2.0.1 (versionCode 20001) | commit `3ae9f0d` da branch `ccr-6d2015d5-vi9zyo` (PR #2) | 5,4 MB |
| `trilhanav-2.0.0.apk` | 2.0.0 (versionCode 20000) | commit `dc6f6af` (PR #1) | 5,4 MB |

**Baixar no celular (2.0.1):** https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.0.1.apk

SHA-256 em `SHA256SUMS`:
- 2.0.1: `3f64a0b853de886f3ff42e69206c320d53154f25146d24dd8c5414801c5157fb`
- 2.0.0: `cff10d0ac662927d5b4bd99b53aed322a6fbdb0b06e5e11a8265449394d73437`

## O que mudou na 2.0.1

Correções da caça a erros de 15/11/2026: trilha gravada com paradas não gera mais curvas falsas nem infla o km; trocar de GPX
não herda os waypoints validados do anterior; "Marcar aqui" não desalinha a lista ao reabrir; a primeira posição imprecisa do GPS
não soma distância ao odômetro; o retorno em linha reta não repete "Rota recalculada"; com o celular deitado os quatro
mostradores cabem na tela. No APK: **exportar** (GPX, ZIP, backup) abre a tela de compartilhar do Android (antes não fazia
nada) e a **tela fica ligada** enquanto o app está aberto.

## Antes de instalar

- É um APK **de depuração** (assinado com a chave de depuração, `debuggable`): serve para instalar no seu celular, não para distribuir a outras pessoas nem para a Play Store.
- Precisa permitir "instalar apps desconhecidos" para o navegador/gerenciador de arquivos que baixou o APK.
- O 2.0.1 foi assinado com a mesma chave de depuração do 2.0.0 (mesma máquina), então deve atualizar por cima. Se o Android recusar ("app não instalado" / assinatura diferente), desinstale o anterior antes: isso apaga trilhas, notas e o mapa offline guardados no app.
- Ao abrir, permita a localização (escolha "o tempo todo" para a gravação seguir com a tela apagada) e as notificações.
- **Nunca rodou num aparelho de verdade**: foi conferido por dentro (manifest, permissões, assinatura, classes, assets), não em uso.
- Contém `leaflet-rotate` e `leaflet-elevation` (GPL-3.0): o código-fonte completo é o do repositório (ver `NOTICE.md`).
