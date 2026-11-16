# Spec — Rota urbana (modo "tipo Waze")
Data: 2026-11-16 · Estado: **aprovada e implementada na v2.1.0** (o dono aprovou e pediu mais: alertas de radar, interface e ícones)

## O que entrou na v2.1.0 (além do plano abaixo)
- **Radares**: `highway=speed_camera` do OpenStreetMap, via Overpass (espelho `maps.mail.ru`, o único que respondeu nos testes).
  Baixados por quadrados de 0,25° ao redor de onde se anda e ao longo da rota, guardados no OPFS (`radares.json`, 30 dias).
  Aviso por voz e placa (limite + distância) a até 600 m (ajustável), faixa vermelha e placa piscando acima do limite + tolerância (7 km/h),
  um aviso por radar a cada 3 min; marcar radar à mão (só no aparelho). Não há base oficial aberta de radares no Brasil: a do OSM é colaborativa.
- Ordem das rotas pelo tempo (o Valhalla ordena pelo custo dele); rotatória e frases que o Valhalla deixa em inglês viram português.
- "De" opcional (partir de outro lugar: o app guia até o início da rota), favoritos, evitar pedágio/rodovias, Google Maps além do Waze.
- Interface: ícones SVG na barra, "Ir para" ao lado de "Mapa", alvos de toque ≥ 40 px nos diálogos, tulipas de largada/chegada,
  altimetria redesenhada ao girar a tela.

## Problema
O mapa só segue um GPX pronto: não dá para digitar um destino e ser guiado pela cidade.

## Solução escolhida
**A + B.**

- **A. Rota dentro do TrilhaNav.** Busca de endereço com autocompletar (Photon, da komoot) e rota de A a B pelo servidor
  público Valhalla da FOSSGIS, perfil moto, instruções em pt-BR. Na tela: rota desenhada no mapa, lista de manobras,
  voz curva a curva (o copiloto que já existe), distância e hora de chegada, recálculo ao sair da rota, até 2 rotas
  alternativas, destinos recentes. Origem = posição atual (padrão) ou um ponto escolhido.
- **B. Botão "Abrir no Waze"** com o destino já preenchido, para quem quer trânsito e alertas ao vivo.

Por que esta: é grátis, sem chave e funciona hoje (teste de 16/11: Praça Sete → Pampulha, 12,1 km, 14 manobras em
pt-BR, 0,6 s, CORS liberado). As outras:
- **C. Rota urbana offline**: precisa de um grafo de ruas com mão única e conversões proibidas para MG (centenas de MB
  a baixar) e de um motor de rota no navegador. Dias de trabalho. Fica para depois, se fizer falta.
- **D. API paga com trânsito** (Google, TomTom, HERE): custa dinheiro e a chave ficaria exposta num site estático.

## Fora de escopo
- **Trânsito em tempo real e alertas de polícia, acidente e radar enviados por usuários.** É o coração do Waze e não
  existe fonte aberta: o Waze só entrega esses dados a órgãos públicos parceiros. O botão B cobre isso.
- Calcular rota sem internet. A rota já calculada fica guardada e a navegação continua offline, mas sem recálculo.
- Limite de velocidade da via, radares do OpenStreetMap, paradas no caminho (posto), pedágio, reportar ocorrência.
  Possível numa fase 2, se pedir.
- Nada muda no modo trilha (GPX, roadbook, odômetro, zonas).

## Dado pessoal e limites
- Ao buscar: o texto digitado e a posição aproximada (para priorizar o que está perto) vão para `photon.komoot.io`.
- Ao calcular: origem e destino vão para `valhalla1.openstreetmap.de` (FOSSGIS, Alemanha).
- Só sai quando a função é usada; aviso na primeira vez; nenhum identificador ou histórico é enviado. Destinos recentes
  ficam só no aparelho.
- Os dois serviços são mantidos por voluntários: no máximo 1 pedido por segundo, sem garantia de disponibilidade.

## Arquivos afetados
`index.html` (tela e lógica), `sw.js` (versão; respostas de rota e busca não entram no cache), `dev/t15.py` (novo),
`android-app/patch-android.py` (visibilidade do pacote do Waze), `NOTICE.md` (atribuições), `CLAUDE.md`.

## Como saber que deu certo
Teste automático com os serviços simulados, mais uma chamada real de fumaça:
1. digitar "mercado central" lista resultados; escolher um traça a rota e mostra distância e hora de chegada;
2. simulando o percurso: cada manobra é falada antes de chegar e a distância restante diminui;
3. sair mais de 80 m da rota recalcula com um pedido só, respeitando 1 por segundo;
4. chegar ao destino encerra a navegação;
5. sem internet: aviso claro, a rota já calculada continua e o botão do Waze segue disponível;
6. os testes do modo trilha (`t.py` … `t14.py`) continuam verdes.

## Risco e volta atrás
- Serviço fora do ar ou recusando pedidos: o app avisa e oferece o Waze. Trocar de servidor é mudar uma constante.
- Reverter é remover o botão ou o commit: nenhum dado existente é alterado ou migrado.

Esforço estimado: uma tarde de trabalho.
