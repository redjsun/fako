# Requisitos funcionais

Catálogo oficial do Documento de Requisitos do grupo (v1), levantado por workshop interno
da equipe (brainstorming em quadro no Miro) e entrevista com jogadores em potencial, e
priorizado com MoSCoW. Cada requisito carrega a técnica de origem, para rastreabilidade; ver
[Técnicas de elicitação](tecnicas-elicitacao.md).

RF31 a RF38 detalham a progressão de dificuldade e o fim da partida previstos no workshop
(redução do espaço de jogo, colisão com a borda, aumento gradual da dificuldade e checagem de
nível) e entraram na revisão dos níveis; as regras de cada nível estão em
[Níveis da jornada](../jogo/niveis.md).

Ao todo foram levantados 49 requisitos; os classificados como **Won't have** (fora do
escopo atual) não entram nesta tabela, só os que seguem para o MVP (Must, Should e Could
have).

| ID | Requisito | Descrição | Prioridade (MoSCoW) | Origem |
|----|---|---|---|---|
| RF01 | Tela inicial | O sistema deve apresentar uma tela inicial com as opções de realizar login ou cadastro. | Must have | Workshop |
| RF02 | Cadastro de jogador | O sistema deve permitir que o jogador crie uma conta utilizando nome de usuário e senha. | Must have | Workshop |
| RF03 | Persistência da jornada | O sistema deve associar o progresso do jogador à sua conta e permitir que ele seja recuperado em sessões futuras. | Must have | Workshop |
| RF04 | Login | Após realizar o login, o sistema deve apresentar ao jogador as opções de iniciar o jogo ou acessar o tutorial. | Must have | Workshop |
| RF05 | Tutorial | O sistema deve disponibilizar um tutorial com as instruções necessárias para compreender o funcionamento do jogo, seus objetivos e suas mecânicas. | Should have | Entrevista |
| RF06 | Início da partida | O sistema deve permitir que o jogador inicie uma nova partida por meio da opção de Start. | Must have | Workshop |
| RF07 | Apresentação das afirmações | O sistema deve apresentar afirmações ao jogador durante a partida para que sejam classificadas de acordo com a proposta do jogo. | Must have | Workshop e Entrevista |
| RF08 | Classificação da afirmação | O sistema deve permitir que o jogador indique se a afirmação apresentada é verdadeira ou falsa. | Must have | Workshop e Entrevista |
| RF09 | Validação da resposta | O sistema deve verificar a resposta fornecida pelo jogador e compará-la com a resposta correta cadastrada. | Must have | Workshop e Entrevista |
| RF10 | Feedback da resposta | O sistema deve informar ao jogador se a resposta escolhida está correta ou incorreta. | Must have | Entrevista |
| RF11 | Progressão da cobra | O sistema deve aumentar o tamanho da cobra de acordo com as regras definidas para a partida, incluindo o crescimento decorrente de respostas incorretas. | Must have | Workshop |
| RF12 | Movimentação da cobra | O sistema deve permitir a movimentação da cobra pelo espaço disponível da partida, atualizando a posição de sua cabeça e de seu corpo a cada passo. | Must have | Workshop |
| RF14 | Controle do espaço de jogo | O sistema deve utilizar uma área em formato de grade para a movimentação da cobra. | Must have | Workshop |
| RF15 | Progressão de níveis | O sistema deve permitir a progressão do jogador por diferentes níveis de dificuldade conforme seu desempenho na partida. | Should have | Workshop e Entrevista |
| RF16 | Redução da área por nível | O sistema deve reduzir progressivamente o espaço disponível para movimentação conforme o avanço dos níveis, utilizando uma grade de 16×16 nos níveis 1 e 2, 14×14 nos níveis 3 e 4 e 12×12 nos níveis 5 e 6. | Should have | Workshop |
| RF17 | Aumento da dificuldade | O sistema deve aumentar gradualmente a dificuldade da partida conforme o jogador avança nos níveis, combinando a velocidade da cobra com os modificadores de RF31 a RF36. | Should have | Workshop e Entrevista |
| RF18 | Controle da pontuação | O sistema deve registrar e atualizar a pontuação do jogador de acordo com seu desempenho durante a partida. | Must have | Workshop e Entrevista |
| RF19 | Controle do progresso do jogador | O sistema deve registrar o nível alcançado e o desempenho obtido pelo jogador durante sua jornada. | Must have | Workshop |
| RF20 | Encerramento da partida | O sistema deve identificar as condições definidas para encerramento da partida e apresentar ao jogador o resultado obtido. | Must have | Workshop e Entrevista |
| RF21 | Explicação educativa | O sistema deve apresentar uma explicação relacionada à afirmação após a resposta do jogador, indicando o motivo pelo qual ela é verdadeira ou falsa e contribuindo para o aprendizado sobre o conteúdo apresentado. | Must have | Entrevista |
| RF22 | Pré-processamento dos textos | O sistema deve padronizar os textos, convertendo para minúsculas e removendo links, números, pontuação e stopwords em português, com redução das palavras ao radical. | Must have | Workshop |
| RF23 | Classificação prévia das afirmações | O sistema deve classificar previamente as afirmações do jogo e armazenar no banco de dados a previsão e o grau de confiança de cada uma. | Must have | Workshop |
| RF24 | Palavras de maior influência | O sistema deve exibir as palavras que mais influenciaram a classificação do modelo. | Should have | Workshop |
| RF25 | Integração real do jogo com a API | O sistema deve autenticar o jogador, criar partidas e persistir seu progresso pela API, não só pela interface. | Must have | Workshop e Entrevista |
| RF26 | Geração automática de questões | O sistema deve gerar e publicar novas questões diariamente a partir das checagens e notícias coletadas. | Must have | Workshop e Entrevista |
| RF27 | Fila de revisão do admin | O sistema deve colocar toda questão gerada automaticamente em fila de revisão antes de publicá-la, com limite de segurança. | Should have | Workshop e Entrevista |
| RF28 | Contestação de questão | O sistema deve permitir que o jogador conteste uma questão, para revisão posterior. | Could have | Workshop e Entrevista |
| RF29 | Registro de proveniência da questão | O sistema deve registrar se uma questão foi gerada por IA ou revisada por pessoa. | Should have | Workshop e Entrevista |
| RF30 | Notícia recente como contexto | O sistema deve poder exibir uma notícia recente sem checagem como contexto informativo, nunca como questão com gabarito. | Could have | Workshop e Entrevista |
| RF31 | Tempo por nível | O sistema deve definir, para cada nível, a duração da partida e o tempo para responder cada afirmação, reduzindo-os nos níveis mais avançados. | Should have | Workshop |
| RF32 | Tolerância de acerto por nível | O sistema deve definir, para cada nível, a distância máxima entre a confiabilidade marcada e a de referência para a resposta contar como acerto, reduzindo-a nos níveis mais avançados. | Should have | Workshop |
| RF33 | Penalidade do erro por nível | O sistema deve definir, para cada nível, quantos blocos a cobra cresce e quantos pontos o jogador perde a cada resposta incorreta, sem que a pontuação fique negativa. | Should have | Workshop |
| RF34 | Paredes sólidas | O sistema deve encerrar a partida quando a cobra colidir com a borda do tabuleiro nos níveis com paredes sólidas; nos demais, a cobra atravessa a borda e reaparece no lado oposto. | Should have | Workshop |
| RF35 | Maçã com prazo | O sistema deve mudar a maçã de lugar quando ela não for coletada dentro do prazo definido para o nível, sinalizando ao jogador que o prazo está acabando. | Could have | Workshop |
| RF36 | Maçãs podres | O sistema deve exibir, nos níveis definidos, a quantidade de maçãs podres definida para o nível; comer uma delas faz a cobra crescer sem apresentar afirmação, e o jogador deve evitá-las. | Could have | Workshop |
| RF37 | Encerramento ao atingir a meta | O sistema deve encerrar a partida quando o jogador atingir a pontuação mínima do seu nível atual, depois de apresentar o resultado da última resposta. | Should have | Workshop |
| RF38 | Ações ao fim da partida | O sistema deve oferecer, ao fim da partida, as opções de jogar o mesmo nível novamente, jogar o próximo nível (quando liberado) e voltar à tela inicial. | Should have | Workshop |

## Leitura em relação ao que já está implementado

Esta tabela é o requisito como levantado; o estado real de cada um está em
`doc/relatorio-tecnico.md` (classificador), `doc/banco-perguntas.md` (geração e validação de
afirmações) e no restante da documentação de produto. Em particular:

- RF07 a RF11, RF18 e RF20 correspondem às mecânicas do jogo já descritas no `README.md`.
- RF15 a RF17 e RF31 a RF36 são parâmetros de cada nível, guardados na tabela `levels` da
  API; a tabela completa está em [Níveis da jornada](../jogo/niveis.md).
- RF22 a RF24 correspondem ao pré-processamento e à classificação do modelo de referência
  (`doc/relatorio-tecnico.md`), não a um pipeline isolado por requisito.
- RF08 (classificação binária verdadeiro/falso) está sob revisão: ver
  [Decisão 01](decisoes-de-produto.md#01-mecanica-binaria-ou-em-tres-niveis).
