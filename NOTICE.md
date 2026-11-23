# Bibliotecas de terceiros

O TrilhaNav embarca estas bibliotecas (cópias fixas em `lib/`, sem `npm install` no app):

| Biblioteca | Versão | Licença | Uso |
|---|---|---|---|
| Leaflet | 1.9.4 (cdnjs) | BSD-2-Clause | mapa |
| PMTiles | 4.5.0 | BSD-3-Clause | leitura do mapa offline |
| protomaps-leaflet | 5.1.0 | BSD-3-Clause | desenho do mapa vetorial offline |
| leaflet-rotate (Raruto) | 0.2.8 | **GPL-3.0** | rotação do mapa (`lib/leaflet-rotate.js`, licença em `lib/leaflet-rotate.LICENSE`) |

**Atenção — GPL-3.0:** quem distribui um programa que incorpora código GPL-3.0 precisa oferecer o código-fonte
do conjunto sob a mesma licença. Enquanto o repositório do TrilhaNav for público, isso está atendido. Não
publique o app (nem o APK) em loja ou em repositório fechado sem rever isso. O repositório ainda não tem um
arquivo `LICENSE` próprio: a escolha da licença é do dono do projeto.

## Reconhecimento de voz (APK, desde a 2.3.0)

| Componente | Versão | Licença | Uso |
|---|---|---|---|
| Vosk (`com.alphacephei:vosk-android`) | 0.3.75 | Apache-2.0 | assistente de voz sempre ligado, sem internet |
| Modelo `vosk-model-small-pt-0.3` (alphacephei.com) | 0.3 | Apache-2.0 | português, dentro do APK (`assets/model-pt`) |
| JNA (dependência do Vosk) | 5.18.1 | Apache-2.0 / LGPL-2.1 (dupla) | ponte Java ↔ biblioteca nativa |

## Dados e serviços externos (modo cidade e radares)

Usados só quando o usuário busca um endereço, pede uma rota ou liga os radares (o app mostra um aviso antes do primeiro uso).

| Serviço | Uso | Termos |
|---|---|---|
| OpenStreetMap (dados) | ruas, endereços, radares (`highway=speed_camera`) | © colaboradores do OpenStreetMap, ODbL 1.0 (crédito no mapa e nos Ajustes) |
| Photon (komoot), photon.komoot.io | busca de endereço | serviço público gratuito, uso moderado; sem garantia |
| Valhalla (FOSSGIS), valhalla1.openstreetmap.de | rota para moto em pt-BR | máx. 1 pedido/s, sem garantia de disponibilidade |
| Overpass API (espelho mail.ru) | radares por área | serviço público; os radares ficam guardados no aparelho |
| Open-Meteo (open-meteo.com) | clima: temperatura, chuva de 15 em 15 min, rajadas, próximas 12 h | gratuito para uso não comercial; dados CC BY 4.0 (crédito na tela do clima) |
| MET Norway (api.met.no) | clima, reserva quando o Open-Meteo falha | dados CC BY 4.0 (crédito na tela do clima) |
| Google Maps (link no SMS do aviso de queda) | só o endereço `maps.google.com/?q=lat,lon` no texto do SMS | nenhum dado é enviado pelo TrilhaNav ao Google |
| Waze / Google Maps | só abre o app deles com o destino (link universal) | nenhum dado é enviado pelo TrilhaNav |

## Formatos

- **OpenRally** (cross-country, v1.0.x): o TrilhaNav lê arquivos nesse formato (`<wpt><extensions>` no namespace
  `openrally.org`). A especificação é de openrally.org/openrally no GitHub, sob CC BY 4.0. Nenhum código ou
  arquivo dela é copiado aqui; as fixtures de `dev/t8.py` foram escritas do zero seguindo o XSD.
