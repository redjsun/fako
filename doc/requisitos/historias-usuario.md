# Histórias de usuário

Reescrita dos [requisitos funcionais](requisitos-funcionais.md) no formato "Como
[ator], quero [ação], para [benefício]", na ordem do catálogo. Cada história mantém o
vínculo com o RF de origem, para rastreabilidade; ver também a
[matriz de rastreabilidade](matriz-rastreabilidade.md).

| ID | Ator | História | RF |
|----|---|---|---|
| HU01 | Jogador novo | Como jogador novo, quero ver uma tela inicial com as opções de entrar ou criar conta, para começar a usar o FAKO sem me perder. | RF01 |
| HU02 | Jogador novo | Como jogador novo, quero criar uma conta com usuário e senha, para ter meu progresso guardado. | RF02 |
| HU03 | Jogador | Como jogador, quero que meu progresso fique salvo na minha conta, para continuar de onde parei em outra sessão. | RF03 |
| HU04 | Jogador | Como jogador, quero fazer login e ver as opções de jogar ou ver o tutorial, para decidir por onde começar. | RF04 |
| HU05 | Jogador novo | Como jogador novo, quero um tutorial explicando as regras, para entender o jogo antes da primeira partida. | RF05 |
| HU06 | Jogador | Como jogador, quero iniciar uma partida pelo botão Start, para começar a jogar quando eu quiser. | RF06 |
| HU07 | Jogador | Como jogador, quero receber afirmações durante a partida, para poder avaliar a confiabilidade delas. | RF07 |
| HU08 | Jogador | Como jogador, quero indicar se considero uma afirmação verdadeira ou falsa, para participar da checagem. | RF08 |
| HU09 | Jogador | Como jogador, quero que minha resposta seja comparada com o gabarito, para saber se acertei. | RF09 |
| HU10 | Jogador | Como jogador, quero receber um feedback dizendo se acertei ou errei, para aprender com a resposta. | RF10 |
| HU11 | Jogador | Como jogador, quero que a cobrinha cresça quando eu erro, para sentir a consequência do erro na mecânica do jogo. | RF11 |
| HU12 | Jogador | Como jogador, quero mover a cobrinha pelo tabuleiro, para jogar a parte de Snake do FAKO. | RF12 |
| HU13 | Jogador | Como jogador, quero jogar numa grade bem definida, para ter um espaço de jogo claro e previsível. | RF14 |
| HU14 | Jogador | Como jogador, quero avançar de nível conforme meu desempenho, para sentir progressão na minha jornada. | RF15 |
| HU15 | Jogador | Como jogador, quero que o tabuleiro diminua nos níveis mais avançados, para sentir o jogo ficando mais difícil. | RF16 |
| HU16 | Jogador | Como jogador, quero que a dificuldade aumente aos poucos, para o jogo continuar desafiador sem ficar impossível de repente. | RF17 |
| HU17 | Jogador | Como jogador, quero acumular pontos pelo meu desempenho, para acompanhar o quanto estou indo bem. | RF18 |
| HU18 | Jogador | Como jogador, quero ver meu nível e desempenho registrados, para acompanhar minha evolução na jornada. | RF19 |
| HU19 | Jogador | Como jogador, quero ver o resultado ao final da partida, para saber como me saí. | RF20 |
| HU20 | Jogador | Como jogador, quero uma explicação depois de cada resposta, para entender por que a afirmação é verdadeira ou falsa. | RF21 |
| HU21 | Equipe de dados | Como responsável pelos dados, quero que os textos sejam padronizados automaticamente, para que o classificador receba entradas consistentes. | RF22 |
| HU22 | Administrador | Como administrador, quero que as afirmações já cheguem classificadas pelo modelo, com a previsão e a confiança registradas, para apoiar a curadoria. | RF23 |
| HU23 | Administrador | Como administrador, quero ver quais palavras mais pesaram na classificação, para entender a decisão do modelo antes de aprovar uma questão. | RF24 |
| HU24 | Jogador | Como jogador, quero que minhas partidas e meu progresso sejam de fato salvos no servidor, para não perder nada se trocar de dispositivo. | RF25 |
| HU25 | Administrador | Como administrador, quero que novas questões sejam geradas automaticamente todo dia, para não depender só de cadastro manual de conteúdo. | RF26 |
| HU26 | Administrador | Como administrador, quero revisar toda questão gerada automaticamente antes dela valer para os jogadores, para garantir a qualidade do conteúdo. | RF27 |
| HU27 | Jogador | Como jogador, quero poder contestar uma questão que considero errada, para que o time revise o conteúdo. | RF28 |
| HU28 | Administrador | Como administrador, quero saber se uma questão foi gerada por IA ou revisada por uma pessoa, para avaliar o nível de confiança no conteúdo. | RF29 |
| HU29 | Jogador | Como jogador, quero ver notícias recentes ainda não checadas como contexto, sem que elas virem pergunta com gabarito, para não ser enganado por uma resposta que ninguém confirmou. | RF30 |
| HU30 | Jogador | Como jogador, quero ter menos tempo para jogar e responder nos níveis avançados, para sentir a pressão crescer conforme avanço. | RF31 |
| HU31 | Jogador | Como jogador, quero precisar de mais precisão na barra de confiabilidade nos níveis avançados, para que acertar exija uma análise mais cuidadosa. | RF32 |
| HU32 | Jogador | Como jogador, quero que errar custe mais nos níveis avançados, para que cada resposta pese na partida. | RF33 |
| HU33 | Jogador | Como jogador, quero que bater na borda do tabuleiro encerre a partida a partir do nível 4, para precisar planejar melhor o caminho da cobra. | RF34 |
| HU34 | Jogador | Como jogador, quero que a maçã mude de lugar se eu demorar, para ter um motivo a mais para agir rápido. | RF35 |
| HU35 | Jogador | Como jogador, quero ver maçãs podres que devo evitar, em maior número nos níveis finais, para ter mais decisões a tomar durante a partida. | RF36 |
| HU36 | Jogador | Como jogador, quero que a partida termine assim que eu bater a meta do nível, para seguir logo para o próximo desafio. | RF37 |
| HU37 | Jogador | Como jogador, quero escolher ao fim da partida entre jogar de novo, ir ao próximo nível ou voltar ao início, para decidir como continuar. | RF38 |
