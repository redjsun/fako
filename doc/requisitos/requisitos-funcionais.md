# Requisitos funcionais

Catálogo oficial do Documento de Requisitos do grupo (v1), levantado por brainstorming
(quadro da equipe no Miro) e entrevista com jogadores em potencial, e priorizado com
MoSCoW. Cada requisito carrega a técnica de origem, para rastreabilidade; ver
[Técnicas de elicitação](tecnicas-elicitacao.md).

Ao todo foram levantados 49 requisitos; os classificados como **Won't have** (fora do
escopo atual) não entram nesta tabela, só os que seguem para o MVP (Must, Should e Could
have).

| ID | Requisito | Descrição | Prioridade (MoSCoW) | Origem |
|----|---|---|---|---|
| RF01 | Tela inicial | O sistema deve apresentar uma tela inicial com as opções de realizar login ou cadastro. | Must have | Brainstorming |
| RF02 | Cadastro de jogador | O sistema deve permitir que o jogador crie uma conta utilizando nome de usuário e senha. | Must have | Brainstorming |
| RF03 | Persistência da jornada | O sistema deve associar o progresso do jogador à sua conta e permitir que ele seja recuperado em sessões futuras. | Must have | Brainstorming |
| RF04 | Login | Após realizar o login, o sistema deve apresentar ao jogador as opções de iniciar o jogo ou acessar o tutorial. | Must have | Brainstorming |
| RF05 | Tutorial | O sistema deve disponibilizar um tutorial com as instruções necessárias para compreender o funcionamento do jogo, seus objetivos e suas mecânicas. | Should have | Entrevista |
| RF06 | Início da partida | O sistema deve permitir que o jogador inicie uma nova partida por meio da opção de Start. | Must have | Brainstorming |
| RF07 | Apresentação das afirmações | O sistema deve apresentar afirmações ao jogador durante a partida para que sejam classificadas de acordo com a proposta do jogo. | Must have | Brainstorming e Entrevista |
| RF08 | Classificação da afirmação | O sistema deve permitir que o jogador indique se a afirmação apresentada é verdadeira ou falsa. | Must have | Brainstorming e Entrevista |
| RF09 | Validação da resposta | O sistema deve verificar a resposta fornecida pelo jogador e compará-la com a resposta correta cadastrada. | Must have | Brainstorming e Entrevista |
| RF10 | Feedback da resposta | O sistema deve informar ao jogador se a resposta escolhida está correta ou incorreta. | Must have | Entrevista |
| RF11 | Progressão da cobra | O sistema deve aumentar o tamanho da cobra de acordo com as regras definidas para a partida, incluindo o crescimento decorrente de respostas incorretas. | Must have | Brainstorming |
| RF12 | Movimentação da cobra | O sistema deve permitir a movimentação da cobra pelo espaço disponível da partida, atualizando a posição de sua cabeça e de seu corpo a cada passo. | Must have | Brainstorming |
| RF14 | Controle do espaço de jogo | O sistema deve utilizar uma área em formato de grade para a movimentação da cobra. | Must have | Brainstorming |
| RF15 | Progressão de níveis | O sistema deve permitir a progressão do jogador por diferentes níveis de dificuldade conforme seu desempenho na partida. | Should have | Brainstorming e Entrevista |
| RF16 | Redução da área por nível | O sistema deve reduzir progressivamente o espaço disponível para movimentação conforme o avanço dos níveis, utilizando, inicialmente, uma grade de 7×7 nos níveis 1, 2 e 3 e uma grade de 6×6 nos níveis 4, 5 e 6, seguindo a progressão definida para os níveis posteriores. | Should have | Brainstorming |
| RF17 | Aumento da dificuldade | O sistema deve aumentar gradualmente a dificuldade da partida conforme o jogador avança nos níveis. | Should have | Brainstorming e Entrevista |
| RF18 | Controle da pontuação | O sistema deve registrar e atualizar a pontuação do jogador de acordo com seu desempenho durante a partida. | Must have | Brainstorming e Entrevista |
| RF19 | Controle do progresso do jogador | O sistema deve registrar o nível alcançado e o desempenho obtido pelo jogador durante sua jornada. | Must have | Brainstorming |
| RF20 | Encerramento da partida | O sistema deve identificar as condições definidas para encerramento da partida e apresentar ao jogador o resultado obtido. | Must have | Brainstorming e Entrevista |
| RF21 | Explicação educativa | O sistema deve apresentar uma explicação relacionada à afirmação após a resposta do jogador, indicando o motivo pelo qual ela é verdadeira ou falsa e contribuindo para o aprendizado sobre o conteúdo apresentado. | Must have | Entrevista |
| RF22 | Pré-processamento dos textos | O sistema deve padronizar os textos, convertendo para minúsculas e removendo links, números, pontuação e stopwords em português, com redução das palavras ao radical. | Must have | Brainstorming |
| RF23 | Classificação prévia das afirmações | O sistema deve classificar previamente as afirmações do jogo e armazenar no banco de dados a previsão e o grau de confiança de cada uma. | Must have | Brainstorming |
| RF24 | Palavras de maior influência | O sistema deve exibir as palavras que mais influenciaram a classificação do modelo. | Should have | Brainstorming |

## Leitura em relação ao que já está implementado

Esta tabela é o requisito como levantado; o estado real de cada um está em
`doc/relatorio-tecnico.md` (classificador), `doc/banco-perguntas.md` (geração e validação de
afirmações) e no restante da documentação de produto. Em particular:

- RF07 a RF11, RF18 e RF20 correspondem às mecânicas do jogo já descritas no `README.md`.
- RF22 a RF24 correspondem ao pré-processamento e à classificação do modelo de referência
  (`doc/relatorio-tecnico.md`), não a um pipeline isolado por requisito.
- RF08 (classificação binária verdadeiro/falso) está sob revisão: ver
  [Decisão 01](decisoes-de-produto.md#01-mecanica-binaria-ou-em-tres-niveis).

## Revisão v1 → v2

### Duplicatas removidas

O RF13 original ("Controle das posições da cobra": atualizar a posição da cabeça e do
corpo conforme a movimentação) descrevia a mesma mecânica do RF12 ("Movimentação da
cobra"), só invertendo causa e efeito. Foi fundido no RF12, que agora cobre as duas pontas:
permitir o movimento e atualizar a posição resultante.

### Lacunas candidatas (v2)

O catálogo v1 foi levantado antes de o classificador, a importação de notícias e os
fluxos de admin existirem no sistema. Comparando com o que está implementado e planejado
(epics `[E6]` a `[E8]`, `doc/banco-perguntas.md`, `doc/noticias-classificador.md`), faltam
requisitos para:

| ID proposto | Requisito | Descrição | Origem |
|---|---|---|---|
| RF25 | Integração real do jogo com a API | O sistema deve autenticar o jogador, criar partidas e persistir seu progresso pela API, não só pela interface. | Sistema (issue #30) |
| RF26 | Geração automática de questões | O sistema deve gerar e publicar novas questões diariamente a partir das checagens e notícias coletadas. | Sistema (issue #23) |
| RF27 | Fila de revisão do admin | O sistema deve colocar toda questão gerada automaticamente em fila de revisão antes de publicá-la, com limite de segurança. | Sistema (issue #27) |
| RF28 | Contestação de questão | O sistema deve permitir que o jogador conteste uma questão, para revisão posterior. | Sistema (issue #28) |
| RF29 | Registro de proveniência da questão | O sistema deve registrar se uma questão foi gerada por IA ou revisada por pessoa. | Sistema (perguntas norteadoras, questão 6) |
| RF30 | Notícia recente como contexto | O sistema deve poder exibir uma notícia recente sem checagem como contexto informativo, nunca como questão com gabarito. | Sistema ([Decisão 04](decisoes-de-produto.md#04-api-de-noticias-e-noticias-nao-checadas)) |

Essas propostas ficam como insumo para a próxima revisão do Documento de Requisitos (v2).
