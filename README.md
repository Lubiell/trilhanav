# TrilhaNav — APK

Branch órfã só com o APK (mesmo esquema do branch `mapas`). O código-fonte está no `main` e o projeto do APK em `android-app/`.

| Arquivo | Versão | Compilado de | Tamanho |
|---|---|---|---|
| **`trilhanav-2.1.0.apk`** (atual) | 2.1.0 (versionCode 20100) | commit `48f8b7b` da branch `ccr-6d2015d5-vi9zyo` (PR #2) | 5,4 MB |
| `trilhanav-2.0.1.apk` | 2.0.1 (versionCode 20001) | commit `3ae9f0d` (PR #2) | 5,4 MB |
| `trilhanav-2.0.0.apk` | 2.0.0 (versionCode 20000) | commit `dc6f6af` (PR #1) | 5,4 MB |

**Baixar no celular (2.1.0):** https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.1.0.apk

SHA-256 em `SHA256SUMS`:
- 2.1.0: `3a94d96504728376a3f66fc7c517dd666de6abda5cd8d9840f83a3043548ca16`
- 2.0.1: `3f64a0b853de886f3ff42e69206c320d53154f25146d24dd8c5414801c5157fb`
- 2.0.0: `cff10d0ac662927d5b4bd99b53aed322a6fbdb0b06e5e11a8265449394d73437`

## O que mudou na 2.1.0

- **Ir para (modo cidade, tipo Waze):** busque um endereço, escolha entre até 3 rotas de moto (tempo, km, por onde passa) e siga com
  voz em português curva a curva, cartão com a próxima manobra e hora de chegada, recálculo quando sai da rota e aviso de chegada.
  Favoritos e recentes, evitar pedágio/rodovias, "De" opcional, e botões para abrir o mesmo destino no **Waze** ou no **Google Maps**.
  Precisa de internet para buscar e calcular (serviços públicos do OpenStreetMap); o app avisa antes do primeiro uso.
- **Radares:** os radares cadastrados no OpenStreetMap da região por onde você anda (e da rota) são baixados e guardados no
  aparelho; placa com limite e distância, voz "Radar em 300 metros, limite 60" e alerta se passar do limite. Dá para marcar um radar
  à mão. A base é colaborativa: pode faltar radar.
- **Visual:** ícones novos na barra, "Ir para" ao lado de Mapa, botões maiores nos diálogos, desenhos de largada/chegada no roadbook,
  gráfico de altimetria que se ajusta ao girar o celular.

## O que mudou na 2.0.1

Correções da caça a erros de 15/11/2026: trilha gravada com paradas não gera mais curvas falsas nem infla o km; trocar de GPX
não herda os waypoints validados do anterior; "Marcar aqui" não desalinha a lista ao reabrir; a primeira posição imprecisa do GPS
não soma distância ao odômetro; o retorno em linha reta não repete "Rota recalculada"; com o celular deitado os quatro
mostradores cabem na tela. No APK: **exportar** (GPX, ZIP, backup) abre a tela de compartilhar do Android (antes não fazia
nada) e a **tela fica ligada** enquanto o app está aberto.

## Antes de instalar

- É um APK **de depuração** (assinado com a chave de depuração, `debuggable`): serve para instalar no seu celular, não para distribuir a outras pessoas nem para a Play Store.
- Precisa permitir "instalar apps desconhecidos" para o navegador/gerenciador de arquivos que baixou o APK.
- O 2.1.0, o 2.0.1 e o 2.0.0 têm a mesma chave de depuração (certificado `16acb7ad…8029`), então cada um atualiza por cima do anterior sem perder dados. Se o Android recusar ("app não instalado" / assinatura diferente), desinstale o anterior antes: isso apaga trilhas, notas e o mapa offline guardados no app.
- Ao abrir, permita a localização (escolha "o tempo todo" para a gravação seguir com a tela apagada) e as notificações.
- **Nunca rodou num aparelho de verdade**: foi conferido por dentro (manifest, permissões, assinatura, classes, assets), não em uso.
- Contém `leaflet-rotate` e `leaflet-elevation` (GPL-3.0): o código-fonte completo é o do repositório (ver `NOTICE.md`).
