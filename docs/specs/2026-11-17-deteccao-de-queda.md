# Spec — Detecção de queda com aviso ao contato de emergência
Data: 2026-11-17 · Estado: **aprovada (opção A) e implementada na v2.6.0**

## Problema
Numa queda sozinho na estrada ou na trilha, ninguém fica sabendo onde você está. Apps de moto como Detecht, EatSleepRIDE
(CRASHLIGHT), calimoto/Bosch e Triumph SOS avisam um contato quando detectam a queda; nenhum deles tem código aberto.

## Solução proposta (só no APK)
1. **Detecção no nativo** (serviço que já roda em primeiro plano, então funciona com a tela apagada): acelerômetro + GPS.
   Considera queda quando, **andando a ≥ 25 km/h**, há um **impacto ≥ 4 g** e em seguida a moto fica **parada (< 5 km/h) por 15 s**.
   Tombo parado ou a menos de 25 km/h (como no EatSleepRIDE) e celular caindo do suporte com a moto andando não disparam.
2. **Contagem de 30 s** na tela: alarme alto, vibração e a voz "Queda detectada. Diga cancelar ou toque em Estou bem".
   Cancela por toque, pelo "Trilha, cancelar" ou por qualquer tecla do guidão.
3. Sem cancelar: **SMS automático** para até 3 contatos de emergência (escolhidos na agenda, em Telefone), com
   "TrilhaNav: possível queda de Jefferson às HH:MM. Localização: https://maps.google.com/?q=LAT,LON" (o nome é configurável),
   e depois **ligação** para o 1º contato. Se o GPS mexer de novo (você levantou e saiu andando), não liga.
4. Ajustes: liga/desliga (padrão **desligado** até você configurar os contatos), sensibilidade (normal/alta), botão "Testar"
   (faz a contagem e manda um SMS dizendo que é teste).

## Opções consideradas
- **A. Detecção nativa + SMS direto (recomendada)**: funciona com a tela apagada e manda sem você tocar em nada.
  Precisa da permissão de **enviar SMS**; o SMS sai do seu plano (custo da operadora, normalmente incluso).
- B. Detecção no app (JavaScript): só com a tela ligada e o app na frente. Mais simples, mas falha justo quando o celular apaga.
- C. Abrir o app de SMS pronto para enviar: não manda nada se você estiver desacordado; não resolve o problema.

## Fora de escopo
- Ligar para 190/192/193 automaticamente.
- Enviar a localização continuamente (rastreamento ao vivo) ou para qualquer servidor.
- Detecção pelo som ou por relógio/fone.

## Dado pessoal
Contatos de emergência (nome + número) e o nome do piloto ficam só no aparelho (`localStorage`). A localização só sai por
SMS, na hora da queda não cancelada ou no teste que você mesmo pede.

## Arquivos afetados
`android-app/native/` (sensor no serviço, `sendSms`), `patch-android.py` (permissão `SEND_SMS`), `index.html` (contagem,
ajustes, contatos), `dev/t21.py` (novo, sensores e SMS simulados), `NOTICE.md`/`CLAUDE.md`.

## Como saber que deu certo
- Aqui: teste com sensores simulados: impacto a 40 km/h + parado 15 s → contagem → SMS para os 3 contatos com o link certo e
  ligação para o 1º; cancelar nos 30 s não manda nada; impacto parado, a 15 km/h ou seguido de movimento não dispara.
- No seu celular: botão "Testar" manda o SMS de teste para você mesmo. A queda real não dá para testar sem cair.

## Risco e volta atrás
- **Falso alarme** (buraco muito forte e parada logo depois): a contagem de 30 s e o "cancelar" por voz existem para isso.
- **Não detectar** uma queda real: celular solto no bolso ou suporte que absorve o impacto. Não é um equipamento certificado.
- Volta atrás: desligar em Ajustes; ou instalar a versão anterior por cima.
