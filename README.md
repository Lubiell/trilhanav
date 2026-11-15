# TrilhaNav — APK

Branch órfã só com o APK (mesmo esquema do branch `mapas`). O código-fonte está no `main` / PR #1 e o projeto do APK em `android-app/`.

| Arquivo | Versão | Compilado de | Tamanho |
|---|---|---|---|
| `trilhanav-2.0.0.apk` | 2.0.0 (versionCode 20000) | commit `dc6f6af` da branch `ccr-6d2015d5-vi9zyo` (PR #1) | 5,4 MB |

SHA-256: `cff10d0ac662927d5b4bd99b53aed322a6fbdb0b06e5e11a8265449394d73437` (também em `SHA256SUMS`).

Baixar no celular: https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.0.0.apk

## Antes de instalar

- É um APK **de depuração** (assinado com a chave de depuração, `debuggable`): serve para instalar no seu celular, não para distribuir a outras pessoas nem para a Play Store.
- Precisa permitir "instalar apps desconhecidos" para o navegador/gerenciador de arquivos que baixou o APK.
- Atualizar por cima de um APK compilado com outra chave de depuração exige desinstalar antes, e isso apaga as trilhas, notas e o mapa offline do app.
- Ao abrir, permita a localização (escolha "o tempo todo" para a gravação seguir com a tela apagada) e as notificações.
- **Nunca rodou num aparelho de verdade**: foi conferido por dentro (manifest, permissões, assinatura, classes, assets), não em uso.
- Contém `leaflet-rotate` e `leaflet-elevation` (GPL-3.0): o código-fonte completo é o do repositório (ver `NOTICE.md`).
