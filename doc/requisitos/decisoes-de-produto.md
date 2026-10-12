# Decisões de produto

Registro das decisões do épico `[E1] Decisões de produto` (issue #36) que mudam o contrato
entre jogo, API e modelo. Diferente de uma decisão de arquitetura (como implementar), são
decisões de **o que o produto faz**, por isso bloqueiam issues de implementação até
fechadas. Cada seção espelha a issue correspondente: problema, opções consideradas e,
quando já decidido, a escolha e o motivo.

## 01. Mecânica binária ou em três níveis

**Status:** em aberto (issue #31).

**Problema.** O projeto hoje tem três versões da mesma ideia ao mesmo tempo: a API é
binária (`Question.is_true: bool`), o frontend usa uma barra de 0% a 100%
(`reliability_reference`, acerto com distância ≤ 15 pontos) e o modelo classifica em três
níveis (falso, enganoso, verdadeiro). Sem decidir, a integração do front com a API e a
geração automática de questões não têm contrato estável, e os enganosos das checagens não
podem virar questão.

**Opções.**

- **A. Binário.** Simples, sem migração, mas deixa os enganosos fora do jogo e a escala só
  aparece na análise pós-resposta.
- **B. Três níveis.** Usa os enganosos como questões e casa com a saída do modelo, mas exige
  migração (`Question` ganha campo de veracidade, `AnswerRequest`/`AnswerResultResponse`
  trocam de tipo) e é mais difícil de calibrar para o jogador.

## 02. O que o jogador vê: nota, confiança ou as duas

**Status:** em aberto (issue #32).

**Problema.** Depois da resposta, a API devolve uma nota de veracidade (0 a 100) e uma
confiança do modelo (0 a 1), coisas diferentes e fáceis de confundir ("nota 8" quer dizer
quase certamente falso; "confiança 0,84" quer dizer 84% de certeza na categoria). Mostrar as
duas sem explicação confunde; mostrar a errada passa a impressão de que o jogo "sabe" mais do
que sabe.

**Opções.** Só a nota; só a confiança; as duas; ou a nota com a confiança decidindo se ela
aparece (categoria `incerto` abaixo do limiar do jogador, calibrado para poucos verdadeiros
marcados como falsos), sendo esta última a recomendação do planejamento.

**Regras já fechadas, em qualquer opção:** a análise só aparece depois da resposta; o
gabarito do jogo é sempre o veredito da checagem, nunca a predição do modelo; a explicação
vem das evidências.

## 03. De onde vêm as questões verdadeiras

**Status:** em aberto (issue #33).

**Problema.** As questões vêm de checagens de agência, e agências checam sobretudo o que é
suspeito: há muito mais falsos checados que verdadeiros checados. Sem corrigir isso, quase
toda questão seria "falso" e o jogador acertaria respondendo sempre a mesma coisa; o jogo
precisa de verdadeiros no mesmo formato das falsas, senão o estilo do texto entrega a
resposta.

**Opções.** Coletar mais verdadeiros checados em agências como G1 "É FATO", Lupa, Aos Fatos,
Comprova e e-farsas; ou usar o dataset de portais confiáveis com curadoria e auditoria
(`doc/dataset-verdadeiras.md`), que tem mais volume mas não é checagem de agência.

## 04. API de notícias e notícias não checadas

**Status:** decisão da Parte 1 implementada; Parte 2 em aberto (issue #34).

**Problema.** Duas decisões ligadas: qual fonte usar na coleta diária de matérias recentes
para análise (sem rótulo, fora do treino, já que "verdadeiro" de matéria recém-coletada é
suposição); e como mostrar ao jogador uma notícia recente que nenhuma agência checou, já que
a nota do classificador sobre ela é só uma estimativa, sem gabarito.

**Decidido (Parte 1).** Importação de manchetes via GNews, normalizadas como no treino,
com a referência TF-IDF (`doc/noticias-classificador.md`), em vez de estender a API de
portais do `coletar_verdadeiras.py`.

**Em aberto (Parte 2).** Como exibir ao jogador uma notícia sem checagem. A regra já
fechada é que ela nunca vira questão com gabarito, só entra como contexto ou rascunho para
revisão.
