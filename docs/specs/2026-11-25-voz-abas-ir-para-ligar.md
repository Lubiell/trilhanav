# Spec — voz no bolso, abas, "ir para", "ligar para", nome do assistente e extras (2.7.12)
Data: 2026-11-25 · Estado: **aprovada pelo dono em 25/11 ("Ok")**

## Problema
- Com o celular no bolso, o microfone dele fica abafado (roupa e vento): o "Trilha" quase não é ouvido.
- Pela voz só dá para mexer na música e atender ou recusar ligação.
- O dono pediu também, por voz:
  - mudar de aba;
  - "ir para" e "de … para …";
  - "ligar para" um favorito (ex.: "ligar para Emiliane");
  - escolher outro nome no lugar de "Trilha";
  - os extras que escolheu: posto mais perto, mandar localização, onde estou / quanto falta.

## Solução escolhida (com as escolhas do dono)
1. **Recepção com o celular no bolso**
   - No bolso, só o **microfone do capacete** ouve bem.
     - Ele já vem ligado (`voiceBt`).
     - O app passa a avisar na tela e por voz quando o capacete não está conectado: "o microfone do capacete não está ligado; no bolso o celular quase não ouve".
     - O Diagnóstico da voz mostra qual microfone está ouvindo (capacete ou celular).
   - Na sensibilidade **alta**, o nativo liga também o **supressor de ruído** do Android (`NoiseSuppressor`, se o aparelho tiver), junto com o ganho que já existe.
   - Dica fora do app: uma **espuma no microfone do capacete** corta mais vento do que qualquer ajuste de software.
2. **Mudar de aba**:
   - "Trilha, mapa" e "Trilha, painel" trocam a aba;
   - "Trilha, telefone" abre o Telefone.
3. **Ir para** (o dono escolheu: o Google escuta o nome):
   - "Trilha, ir para" → bipe e "Para onde?";
   - a escuta do Google ouve por 7 s;
   - vale "Guidoval" ou "de Ubá para Guidoval" (preenche o De e o Para da aba Ir para);
   - a busca é a mesma da tela (Photon com internet, mapa offline sem);
   - o app pega o resultado mais perto de você, calcula a rota e fala "Rota para Guidoval, 32 quilômetros".
   - Sem internet, a escuta do Google só funciona se o pacote de voz offline em português estiver instalado no celular [Provável]. Sem ele, o app fala "Não consegui ouvir o nome sem internet; use a tela".
4. **Ligar para um favorito**:
   - "Trilha, ligar para" → "Para quem?" → o Google escuta o nome;
   - o nome é comparado **só com os favoritos do Telefone** (`tn_phFav`, até 30), sem acento e sem maiúscula, aceitando só o primeiro nome;
   - achou um: usa o `dial()` que já existe ("Ligando para Emiliane", 3,5 s para cancelar);
     - nesses 3,5 s, "cancelar" vale **sem "Trilha"**, como o atender/recusar;
   - achou dois: fala os dois nomes e não liga;
   - não achou: "Emiliane não está nos favoritos".
5. **Nome do assistente** (o dono escolheu uma lista de nomes testados):
   - Ajuste "Chamar o assistente de": **Trilha** (padrão) ou um de até 4 nomes da lista.
   - Candidatos: Piloto, Garupa, Parceiro, Comandante.
   - Um nome só entra na lista se:
     - estiver no vocabulário do modelo de voz (conferido no `Gr.fst`);
     - não soar como um comando.
   - O nome escolhido entra na gramática no lugar de "trilha".
   - "Trilho"/"trilhas" da sensibilidade alta valem só para Trilha.
6. **Extras**:
   - "Trilha, posto": procura o posto mais perto (mapa offline primeiro, internet se não achar), calcula a rota e fala o nome e a distância. Volta o `fuelGo` da 2.7.3.
   - "Trilha, onde estou": fala a rua e a cidade pelo mapa offline (`whereSay`).
   - "Trilha, quanto falta": fala a distância e a hora de chegada da rota (`etaSay`).
   - "Trilha, mandar localização":
     - "Para quem?" → o Google escuta o nome → o nome é comparado com os favoritos;
     - "Mandando sua localização para Emiliane", com **5 s para dizer "cancelar"**;
     - **SMS** com o link do mapa, pelo `sendSms` do SOS: funciona com sinal fraco e sem internet; pede a permissão de SMS na 1ª vez.

### Palavras novas na gramática do Vosk
- ir, para, ligar, mapa, painel, telefone, posto, onde, quanto, falta, mandar, localização e os nomes da lista.
- São comandos de 2 palavras sempre que dá ("ir para", "ligar para", "onde estou", "quanto falta"), que o vento confunde menos.
- O `t26` confere que cada palavra está no `VBASE`.
- Toda palavra nova é conferida no vocabulário do modelo antes de entrar.

### Alternativas descartadas
- (a) **Nomes de cidades e contatos na gramática do Vosk**: funciona sem internet, mas na 2.7.3/2.7.4 as cidades falharam no celular. O dono escolheu o Google.
- (b) **Localização pelo WhatsApp**: precisa de internet, e o Android não deixa mandar sem tocar em "enviar".

## Fora de escopo
- Ligar para quem não está nos favoritos.
- Ler ou responder mensagem por voz.
- Encerrar a rota por voz.
- Paradas no caminho.
- Mandar localização pelo WhatsApp.
- Voz durante a ligação (o microfone é da ligação).

## Arquivos afetados
- `index.html`:
  - `parseCmd`, `VBASE`, `runCmd`, `onHeard`;
  - escuta do Google em duas etapas (`voiceAsk`);
  - casamento com favoritos;
  - `fuelGo`/`whereSay`/`etaSay` (voltam da 2.7.3);
  - mandar localização;
  - ajuste do nome;
  - aviso de capacete desconectado.
- `android-app/native/TrilhaVoiceService.java`: `NoiseSuppressor` no modo alta; informar qual microfone está ouvindo.
- Testes:
  - `t33` novo;
  - `t26` ajustado (as palavras novas deixam de ser "sem efeito");
  - `t18` e `t16` se precisar.

## Como saber que deu certo
- Testes (nativo simulado):
  - "trilha mapa"/"painel"/"telefone" trocam a aba;
  - "trilha ir para" + escuta "de Ubá para Guidoval" preenche De/Para e calcula a rota;
    - sem resultado, fala que não achou;
  - "trilha ligar para" + "Emiliane" com favorito Emiliane chama `placeCall` depois de 3,5 s;
    - "cancelar" sem Trilha nesse tempo não liga;
    - com nome fora dos favoritos não liga;
    - com dois parecidos não liga;
  - "mandar localização" chama `sendSms` só para o favorito, com o link, depois de 5 s;
    - "cancelar" não manda;
  - "posto", "onde estou" e "quanto falta" falam a resposta (com mapa de teste);
  - nome "Piloto" escolhido: "piloto próxima" vale e "trilha próxima" não;
  - nenhuma chamada de rede nova além das que a tela já faz (Photon/Valhalla/Overpass).
- No celular: o dono testa com o celular no bolso e o Helmet V10, e manda um print do Diagnóstico da voz se falhar.

## Risco e volta atrás
- **Ligação ou SMS sem querer**: só para favoritos; 3,5 s (ligar) e 5 s (localização) com "cancelar"; o app fala o nome antes.
- **Mais palavras → mais comando sem querer** (foi o motivo de enxugar na 2.7.5):
  - os comandos novos são de 2 palavras;
  - o Diagnóstico mostra o que foi ouvido;
  - dá para tirar uma palavra que dê problema na versão seguinte.
- **Escuta do Google sem internet** pode falhar: o app fala o motivo e a tela continua valendo.
- **SMS** pode custar no plano do dono [Provável: a maioria dos planos no Brasil inclui SMS].
- **Código**: reverter o commit no `main` e publicar com número maior (2.7.13).

Estimativa: um dia de trabalho (cerca de 6 h) com testes, PR, APK e publicação.
