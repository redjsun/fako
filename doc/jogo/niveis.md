# Níveis da jornada

A jornada tem 6 níveis. A dificuldade cresce pela mecânica do jogo, não pelas afirmações: em
todos os níveis as perguntas vêm do mesmo banco. Cada nível é uma linha da tabela `levels`
da API (`api/app/models/level.py`, valores em `api/app/seeds/data.py`), exposta em
`GET /levels` e dentro de cada partida (`POST /matches`). O front lê as regras do nível da
partida e só usa a cópia local (`web/src/services/levelService.ts`) quando a API está fora do ar.

Requisitos: RF15 a RF17 e RF31 a RF38 ([Requisitos funcionais](../requisitos/requisitos-funcionais.md)).

## Regras por nível

| Nível | Tabuleiro | Passo da cobra | Partida | Pergunta | Tolerância | Erro: pontos | Erro: cresce | Paredes | Maçã muda de lugar | Maçãs podres | Meta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 16×16 | 160 ms | 120 s | 45 s | ±15 | 0 | 1 bloco | atravessáveis | não | 0 | 30 pts |
| 2 | 16×16 | 145 ms | 120 s | 40 s | ±15 | 0 | 1 bloco | atravessáveis | não | 0 | 40 pts |
| 3 | 14×14 | 130 ms | 110 s | 35 s | ±12 | 0 | 2 blocos | atravessáveis | não | 0 | 50 pts |
| 4 | 14×14 | 125 ms | 100 s | 30 s | ±10 | −5 | 2 blocos | sólidas | a cada 12 s | 0 | 50 pts |
| 5 | 12×12 | 115 ms | 90 s | 25 s | ±10 | −5 | 2 blocos | sólidas | a cada 10 s | 2 | 60 pts |
| 6 | 12×12 | 105 ms | 90 s | 20 s | ±8 | −10 | 3 blocos | sólidas | a cada 8 s | 4 | 70 pts |

Os valores são o ponto de partida e devem ser calibrados jogando. Para mudar um nível, altere
o seed e crie uma migration que atualize os bancos já populados: o seed só insere os níveis
que faltam.

## Como cada modificador funciona

- **Tabuleiro e passo da cobra:** o tabuleiro encolhe e a cobra anda mais rápido (menos ms
  entre um passo e outro).
- **Partida e pergunta:** a partida tem menos tempo de cobra andando, e o jogador tem menos
  tempo para marcar a confiabilidade. No fim do tempo da pergunta vale o valor marcado na barra.
- **Tolerância:** a resposta acerta quando fica a até essa distância da confiabilidade de
  referência. A API corrige com a tolerância do nível da partida.
- **Erro:** cada resposta errada faz a cobra crescer e, a partir do nível 4, tira pontos. O
  placar nunca fica negativo. O acerto vale sempre +10.
- **Paredes:** atravessáveis, a cobra sai de um lado e volta pelo outro; sólidas, bater na
  borda encerra a partida. A borda do tabuleiro fica mais grossa nos níveis com paredes sólidas.
- **Maçã que muda de lugar:** se a cobra não comer a maçã no prazo, ela reaparece em outra
  célula, sem abrir pergunta. Nos últimos 2 s a maçã fica apagada, como aviso. O prazo só
  corre com a cobra andando.
- **Maçãs podres:** marrons, com manchas e sem folha: 2 no nível 5 e 4 no nível 6, junto da
  maçã normal. Comer uma podre faz a cobra crescer 2 blocos e não abre pergunta; ela reaparece
  em outro lugar.

## Fim da partida e avanço

- Ao bater a meta do nível atual, a partida termina depois do resultado da pergunta. Rejogar
  um nível já vencido segue até o fim do tempo.
- O jogador avança quando a partida é do nível atual, o placar alcança a meta e existe um
  nível acima (`match_service.finish`).
- O tempo da pergunta também vale no servidor: a API aceita a resposta até o tempo do nível
  mais 30 s de folga (rede e animação). Depois disso a resposta conta como erro, e o resultado
  avisa o jogador.
- Cada jogador tem uma partida aberta por vez. Começar outra abandona a anterior, que não
  soma pontos nem conta como partida jogada.
- No fim da partida há três opções: jogar o mesmo nível de novo, jogar o próximo nível (só
  quando ele já está liberado) e voltar ao início.
