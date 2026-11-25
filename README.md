# TrilhaNav — APK

Branch órfã só com o APK (mesmo esquema do branch `mapas`). O código-fonte está no `main` e o projeto do APK em `android-app/`.

| Arquivo | Versão | Compilado de | Tamanho |
|---|---|---|---|
| **`trilhanav-2.7.7.apk`** (atual) | 2.7.7 (versionCode 20707) | `main` `575ca9d` (merge do PR #16), workflow APK + assinatura com a chave fixa | 56 MB (modelo de voz) |
| `trilhanav-2.7.6.apk` | 2.7.6 (versionCode 20706) | `main` `66bf127` (merge do PR #14), workflow APK + assinatura com a chave fixa | 56 MB (modelo de voz) |
| `trilhanav-2.7.5.apk` | 2.7.5 (versionCode 20705) | `main` `f0ce7f9` (merge do PR #12), workflow APK + assinatura com a chave fixa | 56 MB (modelo de voz) |
| `trilhanav-2.6.3.apk` | 2.6.3 (versionCode 20603) | commit `acec126` da branch `claude/loving-lovelace-yzb96l` (PR #3), workflow APK | 56 MB (modelo de voz) |
| `trilhanav-2.0.1.apk` | 2.0.1 (versionCode 20001) | commit `3ae9f0d` (PR #2) | 5,4 MB |
| `trilhanav-2.0.0.apk` | 2.0.0 (versionCode 20000) | commit `dc6f6af` (PR #1) | 5,4 MB |

**Baixar no celular (2.7.7):** https://raw.githubusercontent.com/Lubiell/trilhanav/apk/trilhanav-2.7.7.apk

(A 2.7.4, a 2.7.3, a 2.7.2, a 2.7.1, a 2.7.0, a 2.6.2, a 2.6.1, a 2.6.0, a 2.5.0, a 2.4.0, a 2.3.0, a 2.2.0 e a 2.1.0 saíram do branch para não pesar o repositório; continuam no histórico do git.)

`versao.json` diz ao app qual é a versão atual (a partir da 2.2.0 o app procura atualização sozinho: baixa daqui, confere o SHA-256 e abre o instalador).

SHA-256 em `SHA256SUMS`:
- 2.7.7: `a4ef3df245dc4b2a9a23593065af04bac197105ebd58d14199375ba6e9b60dbb`
- 2.7.6: `55026d1e755fb3233ef99cf0d9d6f85e6bc3b237f58726f60982f20303dfd538`
- 2.7.5: `9ebb50c17482c4359a290545e3aa4f54186bab2506c589e27fcf43658d0166f9`
- 2.7.4: `dce47849ba71d9fb0302b59874f317d3ee67a72856e4fc8543d0d59a4ca0edca`
- 2.7.3: `75a430f68484cdb3949ea7d2a004f851c2bb39cd4dafb4eb9e0f2261e5bbc40d`
- 2.7.2: `89b65dfbd9b2e50f27a2f478409be3c44e3a75e5813f5f34a8db1ae53bc0604c`
- 2.7.1: `aea6835fa668f52e6c75378a0815fa53edca8f8f215a251ac8ad32ef8447ee54`
- 2.7.0: `e75a581f2fc79dba55a8e6df43f91eb2775bd7215a0626b0c8cde3fe05f0167c`
- 2.6.3: `8a7d786728f1d2dc5ac54dcea0686ac6ce17e56dbf2bf85b4e2cc72849fb8482`
- 2.6.2: `3e8d0cf4060069c64feed3dbbd1fce232e4da5be43c2bc8f6ce288d37344b33e`
- 2.6.1: `83b59b350501925e9252bc48228fe0c79d9c48f12fb9fa8697ac0516b40919da`
- 2.6.0: `34060fe4a02201db5433a453065e2ae27b7cd190a051b34d94bc5edfaf9d99ca`
- 2.5.0: `ffe5a65428cb517b4544d4c5fe6495d88785e0475e64bc3ac7aaa3d3c789a1bb`
- 2.4.0: `eec3f92b604936ab2063c9ab68912bcfc8c2c12665b4152ba0608ad1c019c571`
- 2.3.0: `19c374268dbaed919b28da4e38c2978c35b891d31d6dd0f6d0336c30e9bafef5`
- 2.2.0: `1ac3818a44d91a843d7bbf48e53e3b43b1d1a6acccc90cc9a8f2be91a77a40f2`
- 2.1.0: `3a94d96504728376a3f66fc7c517dd666de6abda5cd8d9840f83a3043548ca16`
- 2.0.1: `3f64a0b853de886f3ff42e69206c320d53154f25146d24dd8c5414801c5157fb`
- 2.0.0: `cff10d0ac662927d5b4bd99b53aed322a6fbdb0b06e5e11a8265449394d73437`

## O que mudou na 2.7.7

- **Mesma chave da 2.7.1 em diante**: atualiza por cima (o app avisa sozinho).
- **Radares e lombadas não somem mais**: se o celular falhasse ao ler os radares guardados ao abrir, o app começava com a lista vazia e, na primeira gravação, apagava os de MG inteiro. Agora ele tenta ler de novo, nunca grava por cima do que não leu, avisa na tela e grava o que ficou pendente quando a leitura volta (e no "Sair do app").
- **Mapa offline**: se o celular falhar ao ler o mapa, o app avisa que os arquivos continuam no aparelho (em vez de "nenhum mapa") e não mistura partes velhas com novas ao baixar de novo.
- **Ajustes → Armazenamento**: mostra se o Android guarda os dados do app de forma permanente, o espaço usado, as partes do mapa, os radares e lombadas guardados e o último erro. Se algo sumir, mande um print dessa tela.

## O que mudou na 2.7.6

- **Mesma chave da 2.7.1 em diante**: atualiza por cima (o app avisa sozinho).
- **Botão "Sair do app"** (em **Mais**): fecha o app de verdade. Pergunta antes; guarda a trilha gravada em Arquivos → Gravações (se não conseguir guardar, avisa e não fecha), encerra a rota, para o GPS em segundo plano e o assistente de voz e tira o app da lista de recentes. O Voltar do Android continua só mandando o app para segundo plano.

## O que mudou na 2.7.5

- **Mesma chave da 2.7.1 em diante**: atualiza por cima (o app avisa sozinho).
- **Uma palavra por comando de música**: "Trilha, tocar", "pausar", "próxima", "anterior", "aumentar volume", "abaixar volume". Saíram as palavras que o vento confunde com outra ação ("troca"/"toca", "passa"/"pausa", "volta"/"toca"). "Voltar a tocar" agora toca.
- **Bipes**: dois agudos quando o app entendeu o comando, um grave quando não entendeu.
- **Diagnóstico da voz** (Telefone → Comandos de voz): as últimas 10 frases que o app ouviu e o que fez com cada uma. Se a voz falhar no capacete, mande um print dessa lista.
- **Dica**: os botões de música do intercomunicador do capacete funcionam direto no Android; quem usa só os botões pode desligar o assistente sempre ligado.

## O que mudou na 2.7.4

- **Mesma chave da 2.7.1 a 2.7.3**: atualiza por cima (o app avisa sozinho).
- **Comandos de voz só para a música**, a pedido do dono (a procura de cidades por voz não funcionou no celular): "Trilha, tocar", "pausar", "próxima música", "música anterior", "trocar música", "aumentar volume", "abaixar volume" (ou toque em **Voz** e fale). No aviso de queda, "cancelar" ou "estou bem" continua cancelando.
- **Saíram da voz**: "ir para", ligar/atender/recusar, ler mensagens, onde estou, quanto falta, repetir, velocidade, hora, clima, posto e lugares, marcar/apagar aviso, zoom, travar tela, gravar e ajuda. Tudo isso continua pela tela (Ir para, botões Atender/Recusar, Postos, Marcar radar, Abasteci…). A voz que **fala** (curvas, radares, quem liga) continua.
- Avisos de blitz, buraco e obra marcados por voz na 2.7.3 continuam valendo até vencer.

## O que mudou na 2.7.3

- **Mesma chave da 2.7.1/2.7.2**: atualiza por cima (o app avisa sozinho).
- **"Trilha, ir para Guidoval"**: as cidades a até 200 km de você entram no vocabulário do assistente de voz. As que o modelo de voz não conhece são escritas com sílabas que ele conhece ("guido val"): cobre uns 77% dos municípios de MG; nas outras o app pergunta "Para onde?". A rota sai da sua posição no GPS.
- **Radares e lombadas de MG de uma vez**: Ajustes → "Baixar radares e lombadas de MG" (uns 10 a 15 minutos). Lombada só avisa acima de 25 km/h (dá para desligar).
- **Blitz, buraco, obra**: não há base aberta com isso em tempo real; marque por voz ("Trilha, marcar blitz", "marcar buraco", "marcar obra") e o app avisa quando você passar de novo. A blitz some depois de 4 horas. "Trilha, apagar aviso" apaga o mais perto.
- **Postos e lugares sem internet**: pelo mapa de MG baixado: "posto", "hospital", "farmácia", "restaurante", "hotel", "polícia", "banco", "mercado"; "ir para o hospital" vai ao mais perto.

## O que mudou na 2.7.2

- **Mesma chave da 2.7.1**: quem já tem a 2.7.1 atualiza por cima (o app avisa sozinho). Quem ainda está na 2.6.3 precisa desinstalar uma vez.
- **Comandos de voz** (diga "Trilha" e o comando): o assistente sempre ligado não conhecia 30 palavras que o app entende, como "trocar" ("trocar música" virava "tocar"). Agora entende todas, e mais jeitos de falar ("mais volume", "baixa o som", "outra música", "liga a música", "não atender", "quero ir para…").
- **Comandos novos**: "onde estou" (rua e cidade pelo mapa offline), "quanto falta" (distância, tempo e hora de chegada), "repetir", "velocidade", "que horas são", "aproximar"/"afastar", "travar tela"/"destravar", "gravar trilha"/"parar gravação", "ajuda".
- **Com vento ou motor**: a frase fecha quando o que foi ouvido para de mudar (1,2 s) ou em até 8 s, e o app tenta a 2ª e a 3ª hipótese do reconhecimento quando a 1ª não é um comando.
- **Saiu o controle de guidão** (teclas configuráveis nos Ajustes), a pedido do dono.

## O que mudou na 2.7.1

- **Chave de assinatura fixa** (certificado SHA-256 `c7654768ee33ec4489240519181d6062ed8b5f6c2025aaea5b5606bed5da8dd1`): desta vez ainda é preciso desinstalar a versão anterior (exporte trilhas e faça backup dos ajustes antes); **da 2.7.1 em diante as atualizações instalam por cima**, sem apagar trilhas, notas e mapa. A chave fica só no Google Drive do dono.
- **Download do mapa de MG** não para mais com "Download interrompido: … the state had changed since it was read from disk" (`NotReadableError` do Android ao reler o arquivo logo depois de gravar): o SHA-256 é conferido nos bytes recebidos e a leitura do mapa é refeita com o arquivo novo.

## O que mudou na 2.7.0

- **Chave nova outra vez** (certificado `a78f3f98…b47740`): desinstale a versão anterior antes (exporte trilhas e faça backup dos ajustes). A chave fixa está pendente.
- **Saíram as funções de rali/off-road**: roadbook, odômetro TOTAL/PARCIAL, waypoints, zonas, voltar à trilha, altimetria, cronômetro, tela dividida e simulação. GPX continua para ver no mapa (Arquivos e gravações). Saiu o botão duplicado "Abrir o Spotify".
- **Sem internet, pelo mapa offline baixado no app**: busca de cidades do mapa inteiro e de ruas, povoados e lugares (posto, hospital…) a uns 6 km de você; **rota longa** (a cidade de destino pode estar a centenas de km: estradas detalhadas perto da partida e do destino + rodovias no meio).
- **Segurança e manutenção**: testes automáticos no GitHub a cada mudança, conferência das bibliotecas e do Gradle, teclas antigas do rali limpas.
- O site (versão no navegador) foi retirado: https://lubiell.github.io/trilhanav/ agora só leva ao APK.

## O que mudou na 2.6.3

- **Chave nova outra vez** (certificado `aa006695…ec72f2`): desinstale a 2.6.2 antes. Cada compilação no GitHub ainda gera chave nova; a chave fixa está pendente.
- **Funções de rali/trilha saíram da tela:** Roadbook, TOTAL/PARCIAL, waypoints, altimetria, cronômetro, tela dividida, voltar à trilha, zonas e simulação. O app abre no Mapa. Para religar: Ajustes › Aparência.
- **Janelas sem "Fechar":** toque fora fecha; tocar em outro botão da barra já troca de janela. O Voltar do Android fecha a janela (sem janela, o app vai para segundo plano sem fechar).
- **Atualização sempre automática:** procura ao abrir (no máximo 1 vez a cada 12 h).

## O que mudou na 2.6.2

- **Chave de assinatura nova:** a 2.6.1 foi assinada com uma chave que se perdeu. Para instalar a 2.6.2 é preciso **desinstalar a 2.6.1 antes** (apaga trilhas, notas, ajustes e o mapa offline: exporte/faça backup antes). Certificado da 2.6.2: `ea205c4c…f2df9b`.
- **Ir para sem Waze nem Google Maps:** saíram os botões. Com internet segue a rota de moto de antes; **sem internet** (ou se o serviço falhar) a rota sai pelas estradas do **mapa offline** baixado no app (até uns 30 km), com a mesma voz curva a curva. **Toque longo no mapa** escolhe o destino; recentes, favoritos e coordenadas funcionam sem internet. Sem estrada ligando: "Seguir em linha reta (bússola)".
- **Voz:** com o microfone do capacete ligado, a voz sai pelo fone (canal de ligação; o volume é o de ligação, suba durante a fala). A música abaixa antes de falar. "Testar voz" diz por que não sai som e abre a instalação da voz em português se faltar.
- **Música:** "Trilha, trocar música"; volume +/− nas teclas do guidão (Ajustes › Teclas).

## O que mudou na 2.6.1

- **Assistente de voz pelo fone/intercom Bluetooth do capacete:** com o fone conectado, o "Trilha" sempre ligado escuta pelo
  microfone do capacete (o botão Voz mostra "Ouvindo (fone)"). Enquanto ligado, o Android manda a música pelo mesmo canal,
  com **qualidade de ligação** (mono). Para ouvir música com qualidade normal, desmarque em Telefone → "Ouvir pelo microfone do
  fone/intercom Bluetooth" (aí ele volta a usar o microfone do celular). Em ligação, o microfone fica com a ligação.

## O que mudou na 2.6.0

- **Ligação pelo WhatsApp:** a tela de ligação mostra quem está ligando pelo WhatsApp (voz ou vídeo); diga "atender" ou
  "recusar" (ou use os botões). Funciona pelo mesmo "acesso a notificações" do WhatsApp (Telefone → Liberar acesso a notificações).
- **Aviso de queda (SOS):** em Telefone → Aviso de queda: ligue, ponha seu nome e até 3 contatos (ou o botão SOS na Agenda).
  Queda andando a 25 km/h ou mais + moto parada 15 s → contagem de 30 s com alarme → SMS com a localização e ligação para o
  1º contato. Cancela com "Estou bem", "Trilha, cancelar" ou qualquer tecla do guidão. Botão "Testar" manda um SMS de teste.
- **Autonomia:** Mais → Postos: tanque (L), consumo (km/l) e "Abasteci". Avisa na reserva com o posto mais perto.
  Voz: "Trilha, autonomia", "Trilha, abasteci".
- **Painel personalizável** (botão Personalizar): escolha os mostradores e o modo "grandes". Novos: Autonomia, Clima, Chegada.
- **Ícone novo** e tema dia com mais contraste ao sol.

## O que mudou na 2.5.0

- **Barra nova:** Roadbook, Mapa, Ir para, Painel, Telefone, Voz, Gravar e **Mais** (cabe no celular em pé sem rolar). Em "Mais",
  uma grade com o resto: Dividir, Altimetria, Arquivos, Waypoints, Cronômetro, Nota, Voltar à trilha, Zerar parcial, Postos,
  Música, Tema, Tela cheia e Ajustes. O cronômetro rodando aparece na barra de cima.
- **Sem repetições:** um só ajuste de girar o mapa (Ajustes: nunca / só durante o Ir para / sempre); "Abrir" ficou dentro de
  Arquivos; "Marcar radar" só nos Ajustes (e por voz: "Trilha, marcar radar"); o tema só pelo botão de "Mais".
- **Postos de combustível:** Mais → Postos (raio de 8 km, do OpenStreetMap) e por voz "Trilha, posto mais perto" (já faz a rota).
- **Limite da via:** placa com o limite de velocidade da rua onde você está (onde o OpenStreetMap tem o limite) e alerta ao
  passar do limite + 7 km/h. Ajustes → Limite da via.
- **Inclinação:** ângulo na curva e máximo de cada lado no Painel (calibra sozinho com a moto parada em pé).

## O que mudou na 2.4.0

- **Mapa gira sozinho durante o "Ir para"**, como no Waze (rumo para cima), e volta ao norte quando a rota termina.
  Dá para desligar em Ir para → "Mapa gira com a direção durante a rota".
- **"Trilha, ir para…"**: diga "Trilha, ir para a Praça da Estação" (ou "vamos para", "me leva para"). O app procura o lugar
  (primeiro nos recentes) e já começa a rota. Só "Trilha, ir para" → ele pergunta "Para onde?". "Trilha, encerrar rota" para.
- **Clima**: temperatura na barra de cima (vermelha quando há alerta; toque para ver as próximas 12 horas). Alertas por voz:
  chuva chegando, tempestade, rajadas de vento, calor forte, frio, neblina (cada um no máximo 1 vez por hora). No "Ir para",
  avisa se há chuva prevista no destino (e no meio do caminho em rotas longas). "Trilha, clima" fala a previsão.
  Dados do Open-Meteo, com o MET Norway de reserva; a posição vai arredondada (uns 1 km).

## O que mudou na 2.3.0

- **GPS:** se o serviço de localização demora a ligar, o app tenta de novo sozinho; mostra o motivo ("GPS desligado no celular",
  "GPS sem permissão"…) e, se em 25 s não chegar posição, usa o GPS do app como reserva (com a tela ligada).
- **Assistente de voz sempre ligado, sem internet** (Vosk, modelo de português dentro do APK): diga **"Trilha"** e o comando
  ("Trilha, atender", "Trilha, ligar para Maria", "Trilha, próxima música"). Com a ligação tocando, basta "atender"/"recusar".
  Para enquanto o app fala e durante a ligação. Liga/desliga em Telefone. Fica um ícone de microfone na barra do Android.
- **Agenda completa** em Telefone, com filtro e "Atualizar contatos"; os nomes entram no vocabulário do assistente.
- **WhatsApp:** leitura do estilo de conversa do WhatsApp e diagnóstico na tela Telefone (se o serviço de notificações está
  conectado, quantas notificações chegaram e por que alguma foi ignorada).
- O APK passou a 56 MB por causa do modelo de voz: baixe no Wi-Fi.

## O que mudou na 2.2.0

- **Telefone:** ligação chegando aparece em tela grande com Atender/Recusar, a voz diz quem liga e o app escuta "atender" ou
  "recusar". Fazer ligação por voz ("ligar para Maria": favoritos, depois a agenda) com 3 s para cancelar, ou pela tela.
- **WhatsApp:** quem mandou e o texto aparecem num cartão; a voz lê o nome (ou o texto, se você escolher). Nada é guardado.
- **Música:** a música que está tocando aparece em Spotify; volume +/−; "Tocar no Spotify" sem sair do TrilhaNav.
- **Comandos de voz:** botão Voz (ou tecla do guidão): atender, recusar, desligar, ligar para…, tocar, pausar, próxima,
  anterior, aumentar/abaixar volume, ler mensagens.
- **Atualização:** Ajustes → Atualização (e sozinho ao abrir, 1 vez a cada 12 h).
- Primeira vez: abra **Telefone** e toque em "Permitir telefone, agenda e microfone" e em "Liberar acesso a notificações".
  No Android 13+, se o TrilhaNav aparecer apagado nessa lista: Informações do app → ⋮ → "Permitir configurações restritas".

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
- Da 2.0.0 à 2.6.1 a chave de depuração é a mesma (certificado `16acb7ad…8029`); a 2.6.2 (`ea205c4c…`), a 2.6.3 (`aa006695…`) e a 2.7.0 (`a78f3f98…`) têm cada uma a sua, então para passar da 2.6.1 para a 2.6.2 é preciso desinstalar antes. Entre versões da mesma chave, então cada um atualiza por cima do anterior sem perder dados. Se o Android recusar ("app não instalado" / assinatura diferente), desinstale o anterior antes: isso apaga trilhas, notas e o mapa offline guardados no app.
- Ao abrir, permita a localização (escolha "o tempo todo" para a gravação seguir com a tela apagada) e as notificações.
- **Nunca rodou num aparelho de verdade**: foi conferido por dentro (manifest, permissões, assinatura, classes, assets), não em uso.
- Contém `leaflet-rotate` e `leaflet-elevation` (GPL-3.0): o código-fonte completo é o do repositório (ver `NOTICE.md`).
