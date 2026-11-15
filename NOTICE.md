# Bibliotecas de terceiros

O TrilhaNav embarca estas bibliotecas (cópias fixas em `lib/`, sem `npm install` no app):

| Biblioteca | Versão | Licença | Uso |
|---|---|---|---|
| Leaflet | 1.9.4 (cdnjs) | BSD-2-Clause | mapa |
| pdf.js | 3.11.174 (cdnjs) | Apache-2.0 | roadbook em PDF |
| PMTiles | 4.5.0 | BSD-3-Clause | leitura do mapa offline |
| protomaps-leaflet | 5.1.0 | BSD-3-Clause | desenho do mapa vetorial offline |
| leaflet-rotate (Raruto) | 0.2.8 | **GPL-3.0** | rotação do mapa (`lib/leaflet-rotate.js`, licença em `lib/leaflet-rotate.LICENSE`) |
| @raruto/leaflet-elevation | 3.0.1 | **GPL-3.0** | perfil de altimetria (`lib/elevation/`, licença em `lib/elevation/LICENSE`) |

**Atenção — GPL-3.0:** quem distribui um programa que incorpora código GPL-3.0 precisa oferecer o código-fonte
do conjunto sob a mesma licença. Enquanto o repositório do TrilhaNav for público, isso está atendido. Não
publique o app (nem o APK) em loja ou em repositório fechado sem rever isso. O repositório ainda não tem um
arquivo `LICENSE` próprio: a escolha da licença é do dono do projeto.
