# Perguntas norteadoras

O FAKO usa a experiência de um jogo para desenvolver a capacidade do jogador de analisar e
identificar informações verdadeiras e falsas: ao coletar a maçã, ele recebe uma afirmação
para classificar como verdadeira ou falsa e, a partir da resposta, recebe um feedback que
ensina. Por trás dessa experiência, uma IA analisa fontes de informação e gera e atualiza as
questões armazenadas no banco que alimenta o jogo.

As dez perguntas abaixo orientam essa estrutura: como a IA analisa e classifica uma
informação, e como esse resultado se transforma em uma questão jogável com feedback que
ensina. Cada uma une um critério de classificação (o que a IA avalia) a uma decisão de
produto (como isso aparece para o jogador).

## 1. Quais padrões nos dados indicam que uma informação pode ser falsa?

E como a IA pode usá-los para alimentar o banco de questões do FAKO. Nenhum sinal isolado
basta para afirmar que algo é falso: a IA combina sinais de várias naturezas (linguagem,
fontes, similaridade com conteúdos já checados, metadados e evidências recuperadas) como
indícios que orientam a busca por evidências, não como veredito. Padrões linguísticos comuns
em desinformação, como sensacionalismo, apelo emocional, caixa alta e ausência de fonte,
também servem como pistas para ensinar o jogador a reconhecer sinais de alerta no feedback.

## 2. Qual é a afirmação principal da notícia e como transformá-la em uma questão jogável?

Uma notícia mistura fatos, opiniões e contexto. A IA extrai uma única afirmação verificável,
reescreve-a de forma curta e neutra e descarta os trechos opinativos, para que cada maçã
entregue uma afirmação julgável de forma objetiva e lida rapidamente durante a partida. A
fonte original e a evidência usada ficam guardadas junto da questão para embasar a
explicação.

## 3. A informação está fora de contexto? A data corresponde ao acontecimento descrito?

Muita desinformação usa fatos verdadeiros em contexto errado, como uma notícia antiga
apresentada como recente ou uma data alterada. A IA verifica se o contexto e a data de
publicação são coerentes com o acontecimento descrito, para o jogo não classificar como
falso algo verdadeiro que só foi tirado do lugar ou do momento em que aconteceu.

## 4. A afirmação é suportada, contradita, ou não há informação suficiente?

Ela é falsa ou apenas improvável? O jogo precisa de respostas objetivas: só entram no banco
como verdadeiras ou falsas as afirmações com evidência suficiente. Afirmações improváveis,
mas não comprovadamente falsas, e afirmações sem informação suficiente não recebem gabarito
definitivo: ficam de fora ou vão para revisão, para não punir o jogador injustamente nem
ensinar algo incorreto.

## 5. Existe intenção de manipular, informar, satirizar ou causar dano?

A intenção só pode ser inferida de forma indireta, a partir do tipo de conteúdo e do
contexto em que circula. Classificar o conteúdo como misinformation, disinformation,
malinformation ou sátira serve como etiqueta de apoio ao feedback, ajuda o jogador a
entender como aquela informação engana, não como acusação de má-fé. A sátira é identificada
à parte para não ser confundida com desinformação.

## 6. O conteúdo foi produzido por pessoa, automatizado ou gerado por IA?

Existem sinais de que diferentes conteúdos vêm de uma mesma origem ou modelo automatizado?
Descobrir se um texto foi escrito por IA é pouco confiável isoladamente. Sinais de origem
comum, como textos quase idênticos publicados juntos e em horários próximos, indicam possível
coordenação, mas não provam falsidade. Como o próprio FAKO usa IA para gerar questões, o
banco também registra quais itens foram gerados por modelo e quais foram revisados por
pessoas.

## 7. O acontecimento é plausível considerando a localização informada?

A IA verifica se o que a notícia descreve faz sentido no lugar em que ela diz que aconteceu,
considerando características geográficas, climáticas e sociais da região. Um fato que não
combina com o local informado é indício de que a afirmação pode ser falsa, e ajuda a compor
o gabarito e a explicação da questão.

## 8. Esse acontecimento já ocorreu anteriormente em outras regiões?

Verificar se algo parecido já aconteceu em outros lugares ajuda a distinguir um fato raro,
porém real, de um boato reciclado. Muitas notícias falsas reaproveitam eventos antigos ou de
outras regiões como se fossem atuais e locais; identificar esse precedente permite ao jogo
explicar de onde a informação realmente vem.

## 9. Existe algum padrão cultural ou regional que explique o acontecimento?

Alguns acontecimentos parecem estranhos para quem lê, mas são comuns em determinada cultura
ou região, como festas, costumes, práticas locais e fenômenos típicos de um lugar. A IA considera
esses padrões para não classificar como falso algo que apenas é incomum para o leitor,
evitando erros de gabarito e ensinando o jogador a não julgar uma informação só pelo
estranhamento.

## 10. Como transformar a análise da IA em aprendizado dentro do jogo?

O valor do FAKO está no ciclo em que o jogador joga, analisa a informação, toma uma decisão,
recebe feedback e aprende. O feedback após cada resposta deve ser imediato e curto,
explicar o porquê do gabarito, citar a fonte e apontar o sinal de alerta relevante. A
dificuldade pode crescer conforme o desempenho do jogador, e o banco de dados registra as
respostas para adaptar as próximas questões.

## Relação com o resto da documentação

As perguntas 1 a 9 descrevem critérios de classificação, hoje cobertos de formas distintas
pelo projeto: o classificador treinado (`doc/relatorio-tecnico.md`, `doc/guia-classificacao.md`)
decide com base em sinais de linguagem (pergunta 1) e evidência disponível (pergunta 4); a
extração de uma afirmação verificável a partir de uma notícia (pergunta 2) é o trabalho de
`doc/padronizacao.md`; contexto, localização e precedente regional (perguntas 3, 7, 8, 9) e a
distinção entre desinformação e sátira (pergunta 5) ainda não têm uma verificação automática
dedicada: ficam como lacuna de pesquisa para rodadas futuras, e por ora dependem da
curadoria humana das fontes (`doc/dataset-verdadeiras.md`, `doc/banco-perguntas.md`). A
pergunta 6 (origem humana, automatizada ou por IA) orienta o registro de proveniência das
questões geradas, ainda planejado (ver issue #26). A pergunta 10 é a proposta de valor do
produto, detalhada em [Visão do produto](visao-do-produto.md).
