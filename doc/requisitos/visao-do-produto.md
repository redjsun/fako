# Visão do produto

## Problema

Desinformação e notícias enganosas circulam no mesmo formato das verdadeiras, e boa parte
do público não tem o hábito de parar para avaliar a confiabilidade de uma afirmação antes
de aceitá-la. Ensinar essa pausa crítica funciona melhor quando vem embutida numa atividade
que a pessoa já quer repetir, em vez de um aviso ou um curso.

## Proposta

O FAKO é um jogo educativo que usa a mecânica do Snake para treinar a avaliação de
confiabilidade de afirmações reais. A cada maçã, o jogo pausa e pede uma nota de 0% a 100%
para uma afirmação; o acerto (±15 pontos da referência) não altera o tamanho da cobrinha, e
o erro faz a cobrinha crescer: a consequência do jogo é proporcional ao desempenho na
checagem, não ao ato de jogar.

Depois de cada resposta, o jogador vê a nota que deu, a referência oficial, a explicação e a
fonte. O aprendizado vem da comparação repetida entre a intuição do jogador e o veredito
checado, não de uma aula sobre como identificar fake news.

## Princípio de linguagem

A saída do classificador (`doc/relatorio-tecnico.md`) é probabilística, não um veredito
absoluto. Por isso a linguagem voltada ao jogador usa "confiável" / "não confiável" em vez
de apresentar a nota como verdade estabelecida, resultado de uma decisão de produto já
fechada (issue #46). Essa regra vale tanto para o gabarito das questões (sempre o veredito de
uma checagem, nunca a opinião do modelo) quanto para qualquer análise que o classificador
devolva ao jogador (`doc/noticias-classificador.md`).

## Para quem

O público é quem já joga esse tipo de jogo casual (navegador, sessões curtas, sem
cadastro obrigatório para a primeira partida) e não necessariamente tem prática em checar
notícias. O jogo não pressupõe conhecimento prévio de jornalismo ou de ciência de dados: a
dificuldade cresce pela progressão de níveis (velocidade da cobrinha), não pela
complexidade das afirmações.

## Fora de escopo

- **Checar texto livre do jogador.** As afirmações vêm de um banco curado
  (`doc/banco-perguntas.md`), nunca de conteúdo que o jogador cole ou digite: o gabarito
  sempre precisa de uma checagem de agência ou de uma fonte confiável por trás.
- **Apresentar o modelo como fonte da verdade.** O classificador apoia a geração de questões
  e a análise pós-resposta; o gabarito do jogo nunca é a predição do modelo.
- **Cobrir qualquer idioma além do português do Brasil.** Dados, prompts e interface são só
  em pt-BR.

## Decisões em aberto

As decisões de produto que ainda mudam o contrato entre jogo, API e modelo estão registradas
em [Decisões de produto](decisoes-de-produto.md).
