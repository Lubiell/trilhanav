# Spec — Telefone, WhatsApp, Spotify, comandos de voz e atualização (v2.2)
Data: 2026-11-16 · Estado: **aprovada (opção A: APK novo) e implementada na v2.2.0**

Na implementação: ao chegar uma ligação o app fecha qualquer diálogo aberto (o diálogo modal ficava por cima e bloqueava Atender/Recusar); "cancelar" nos 3 s antes de ligar também cancela; com a tela apagada o anúncio por voz funciona, mas o Android não deixa usar o microfone em segundo plano (o serviço é de localização), então "atender/recusar" por voz só com o app na tela.

## Problema
Pilotando, não dá para tirar a mão do guidão para atender ligação, ver mensagem ou trocar música, e cada versão nova do APK
exige baixar e instalar à mão.

## Solução proposta (só no APK; no navegador nada disto existe)

1. **Telefone** (botão novo "Telefone")
   - Ligação chegando: tela grande no TrilhaNav com o nome do contato, botões **Atender** e **Recusar**, e a voz diz
     "Ligação de Maria. Diga atender ou recusar". Funciona com a tela apagada (o app já tem serviço em primeiro plano).
   - Atender/recusar/desligar: `TelecomManager.acceptRingingCall()` / `endCall()` (Android 9+).
   - Fazer ligação: lista de **contatos favoritos** escolhidos por você no app (nome + número), mais busca na agenda.
   - Permissões: telefone (estado, atender, ligar), registro de chamadas (número de quem liga) e contatos.
2. **WhatsApp**: cartão no topo com quem mandou e o texto (WhatsApp e WhatsApp Business), opção de ler em voz alta.
   Usa o "acesso a notificações" do Android, que você liga uma vez nas configurações.
3. **Spotify**: o Spotify continua tocando em segundo plano. No TrilhaNav aparecem a música atual e os botões
   tocar/pausar/próxima/anterior/volume. A música atual vem do mesmo acesso a notificações.
4. **Comandos de voz** (reconhecimento de fala do próprio Android, pt-BR):
   - Para falar: botão de microfone na tela ou uma tecla do controle de guidão. Quando chega uma ligação, o app escuta
     sozinho por uns 8 s.
   - Frases: "atender", "recusar", "desligar", "ligar para Maria", "tocar", "pausar", "próxima", "anterior",
     "aumentar/abaixar volume", "ler mensagens", "silêncio".
5. **Atualização**: botão "Procurar atualização" e um aviso ao abrir quando houver versão nova (ver a decisão abaixo).

Não entra biblioteca nova: tudo usa APIs do próprio Android e o que o Capacitor já traz.

### Decisão em aberto: o que a atualização baixa
- **A. O APK novo (recomendado)**: o app lê um `versao.json` no branch `apk` (versão, link, SHA-256), baixa o APK, confere
  o SHA-256 e abre o instalador do Android. Você confirma "Atualizar" e pronto. Atualiza tudo, inclusive a parte nativa
  (telefone, voz). Custo: um toque de confirmação por atualização, que o Android exige.
- **B. Um zip só com a parte web** (`index.html`, `lib/`): o app baixa o zip, confere o SHA-256, descompacta e passa a
  usar os arquivos novos, sem reinstalar. Não atualiza nada nativo (telefone, voz, permissões), então metade das
  mudanças futuras ainda precisaria de APK novo. E qualquer código no zip roda com as permissões de ligação e de
  mensagens do app: o risco de um zip adulterado é maior.
- Nas duas, a origem confiável é o seu repositório no GitHub (a mesma de onde você já baixa o APK).

## Fora de escopo
- Responder mensagem do WhatsApp (só mostrar e ler).
- Ficar escutando o tempo todo com palavra de ativação ("Ok TrilhaNav"): gasta bateria, falha com o vento no capacete e
  exige biblioteca paga.
- Virar o app de telefone padrão do Android, ou gravar ligações.
- Tocar uma playlist específica por voz, ou login na conta do Spotify.
- Guardar o texto das mensagens em disco ou mandar para a internet: ficam só na memória (as últimas 20) e somem ao fechar.

## Arquivos afetados
`index.html` (botão Telefone, tela de ligação, cartões de WhatsApp e Spotify, microfone, parser de comandos,
atualização), `android-app/native/TrilhaNativePlugin.java` + classes novas (escuta de ligação, `NotificationListenerService`,
reconhecimento de voz, instalador), `android-app/patch-android.py` (permissões, serviço, FileProvider),
`android-app/package.json` (2.2.0), `dev/t16.py` (novo), `NOTICE.md`, `CLAUDE.md`; branch `apk`: `versao.json`.

## Como saber que deu certo
- **Aqui (antes de te passar o APK):** `t16` com o lado nativo simulado: ligação chega → tela, voz e escuta abrem;
  "atender"/"recusar"/"ligar para Maria" chamam o método nativo certo; mensagem do WhatsApp vira cartão (texto escapado,
  nada gravado em disco); cartão do Spotify; atualização com SHA-256 errado é recusada. Regressão t…t15 verde. APK compila;
  manifest com as permissões e o serviço; mesma chave (atualiza por cima da 2.1.0).
- **Só no seu celular** (não há emulador neste ambiente): ligação real, WhatsApp real, microfone com capacete e o
  instalador. No Android 13+ um APK instalado fora da loja precisa de "Permitir configurações restritas" (nas informações
  do app) antes de liberar o acesso a notificações. O app vai te guiar nisso.

## Risco e volta atrás
- `endCall`/`acceptRingingCall` são obsoletos no Android 10+ e alguns fabricantes podem bloquear. Se não funcionar no seu
  aparelho, a tela da ligação continua avisando, e você atende pelo fone ou intercomunicador.
- Reconhecimento de voz sem internet só funciona com o pacote pt-BR offline do Google instalado.
- Volta atrás: instalar o APK 2.1.0 do branch `apk` por cima (mesma chave, não perde dados).
- Estimativa: uma tarde de trabalho aqui.
