# Spec — "Trilha" mais sensível, atender/recusar por voz e WhatsApp de pessoas escolhidas (2.7.11)
Data: 2026-11-25 · Estado: **proposta, esperando o ok do dono**

## Problema
Com a moto andando, o "Trilha" às vezes não é reconhecido. Quando o telefone toca, só dá para atender ou recusar pela tela ou pelo botão do capacete (o atender/recusar por voz saiu na 2.7.4). E o WhatsApp é lido do mesmo jeito para todo mundo (`cfg.waRead`: não / só quem mandou / quem mandou e o texto).

## Solução escolhida (recomendada)
1. **Sensibilidade do "Trilha"**
   - Sempre:
     - procurar "trilha" também nas outras 2 hipóteses do Vosk (hoje só na 1ª: `onHeard`);
     - a espera pelo comando depois de "Trilha" sozinho (bipe, "Fale o comando…") passa de 6 para 8 s.
   - Ajuste novo **"Sensibilidade do Trilha: normal / alta"**, padrão **normal**.
     - Alta aceita algumas palavras que o Vosk escreve no lugar de "trilha" com vento (lista curta, ajustada pelo Diagnóstico da voz).
     - Alta também liga o ganho automático do Android e reforça o som (×2) antes do Vosk (`TrilhaVoiceService`).
   - Alternativas descartadas:
     - (a) só a parte "sempre": menor risco de comando sem querer, mas ganho pequeno;
     - (b) "alta" como padrão: mais resposta, porém mais comandos sem querer com música ou conversa.
2. **Ligações**
   - Ao tocar, o app fala "Ligação de Fulano" (sem nome na agenda: o número, dígito por dígito) e depois "Diga atender ou recusar".
   - Enquanto toca, **sem precisar do "Trilha"**:
     - "atender"/"atende" atende;
     - "recusar"/"recusa"/"desligar" recusa.
   - Para evitar engano, só vale a hipótese principal do Vosk e só enquanto toca; um bipe confirma.
   - Usa o que já existe: `answerCall`/`endCall` no telefone e `waCallAction` no WhatsApp (o Android 14 pode barrar este, como já acontece pelos botões da tela).
   - Ajuste **"Atender/recusar por voz"** (padrão ligado) para desligar se der engano.
3. **WhatsApp de pessoas escolhidas**
   - Em Telefone → WhatsApp, lista **"Ler o texto de:"**, escolhendo entre as últimas pessoas que mandaram mensagem ou digitando o nome.
   - Dos escolhidos: lê quem mandou e o texto (até 200 caracteres, como hoje).
   - Dos outros: segue o ajuste atual (não / só quem mandou).
   - Grupos: vale se o nome escolhido aparece no título da notificação.
   - A lista fica **só no aparelho** (`localStorage` `tn_waSel`, só nomes); nada sai do celular.

## Fora de escopo
- Ler ou responder mensagem por comando de voz.
- **Desligar por voz durante a ligação**: o microfone é da ligação e o Android não divide. Durante a ligação, desliga-se pelo botão do capacete ou pela tela.
- Ligar para alguém por voz (saiu na 2.7.4).
- Telegram e SMS.
- Trocar a palavra "Trilha".

## Arquivos afetados
- `index.html`:
  - `onHeard`, `parseCmd`, `VBASE`, `onCall`, `onWa`;
  - Ajustes (sensibilidade, atender por voz);
  - Telefone → WhatsApp (lista).
- `android-app/native/TrilhaVoiceService.java`: ganho/AGC no modo alta.
- Testes: `t18` e `t26` ajustados; `t32` novo; emulador sem mudança (o Vosk não roda nele).

## Como saber que deu certo
- Testes:
  - "trilha" só na 2ª hipótese arma o comando;
  - com "alta", uma palavra da lista vale; com "normal", não;
  - telefone tocando + "atender" chama `answerCall`, e "recusar" chama `endCall`, sem "Trilha";
  - sem ligação, "atender" não faz nada;
  - com o ajuste desligado, também não faz nada;
  - mensagem de um escolhido lê o texto; de outro, só o nome (ou nada);
  - nenhuma chamada de rede nova.
- No celular: o dono confirma andando, com o Helmet V10, e manda um print do Diagnóstico da voz se o "Trilha" falhar.

## Risco e volta atrás
- **Atender sem querer** (vento, conversa): só vale enquanto toca e na hipótese principal, e há o ajuste "Atender/recusar por voz" para desligar.
- **Comando de música sem querer** no modo alta: voltar para "normal".
- **Código**: reverter o commit no `main` e publicar uma 2.7.12. O Android não instala versão menor por cima, então "voltar para a 2.7.10" é publicar o código antigo com número maior.

Estimativa: uma tarde (cerca de 4 h) com testes, PR, APK e publicação.
