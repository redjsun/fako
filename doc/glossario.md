# Glossário

Termos que aparecem repetidamente nesta documentação, reunidos num só lugar em vez de
espalhados pelo texto corrido.

## Produto e jogo

**Afirmação.** O texto curto apresentado ao jogador ao coletar a maçã, para ser avaliado
como confiável ou não confiável (RF07).

**Confiabilidade.** Nota de 0% a 100% que o jogador atribui a uma afirmação na barra do
jogo. A referência oficial de uma questão é `reliability_reference` (0 a 100); o jogador
acerta quando sua nota fica a até 15 pontos de distância dela.

**Gabarito.** A resposta correta de uma questão. Vem sempre de uma checagem de agência ou
de uma fonte confiável auditada, nunca da predição do classificador; ver
[Visão do produto](requisitos/visao-do-produto.md).

**Rascunho (`draft`).** Status inicial de toda questão nova, gerada por pessoa, por IA ou a
partir de notícia externa. Só vira `validated` (visível ao jogador) depois de revisão
humana; ver [AD06](arquitetura/decisoes.md#ad06-toda-questao-gerada-automaticamente-nasce-como-rascunho).

## Dados e classificador

**Veracidade.** Escala ordinal usada pelo classificador: `falso` < `enganoso` <
`verdadeiro`. Diferente de confiabilidade, que é a nota do jogador, não a classe do modelo.

**Texto curto.** A entrada do classificador: a afirmação extraída e normalizada do texto
original, documentada em `pesquisa/dados/preparar_dados.py` e em
`doc/padronizacao.md`.

**Origem do rótulo (`origem_rotulo`).** De onde veio o rótulo de verdadeiro ou falso de um
registro do dataset (por exemplo, agência de checagem ou portal). Registros com
`origem_rotulo=portal` não entram nos splits de treino, validação e teste, porque o
"verdadeiro" de uma matéria de portal é suposição, não checagem; ver
`doc/dataset-verdadeiras.md`.

**Teste de atalho.** Mede se o modelo aprendeu a prever pela fonte, pelo autor ou pela data
em vez do conteúdo da afirmação (`pesquisa/ml/atalho.py`); é o piso que todo modelo novo
precisa superar.

**Referência TF-IDF.** O modelo de classificação de referência do projeto: regressão
logística ordinal sobre vetores TF-IDF (`pesquisa/ml/treinar_referencia.py`); ver
`doc/relatorio-tecnico.md`.

**Misinformation, disinformation, malinformation, sátira.** Classificação do tipo de
conteúdo, não só do seu veredito: `misinformation` é informação falsa sem intenção de
enganar; `disinformation`, com intenção de enganar; `malinformation`, informação verdadeira
usada para causar dano; sátira é identificada à parte para não ser confundida com
desinformação. Ver [Perguntas norteadoras](requisitos/perguntas-norteadoras.md), questão 5.

## Engenharia de requisitos

**RF / RNF.** Requisito funcional e requisito não funcional, respectivamente; ver
[Requisitos funcionais](requisitos/requisitos-funcionais.md) e
[Requisitos não funcionais](requisitos/requisitos-nao-funcionais.md).

**HU.** História de usuário, no formato "Como [ator], quero [ação], para [benefício]"; ver
[Histórias de usuário](requisitos/historias-usuario.md).

**MoSCoW.** Técnica de priorização em quatro níveis: **Must have** (essencial ao MVP),
**Should have** (importante, mas não bloqueia a primeira versão), **Could have** (desejável,
se houver folga) e **Won't have** (fora do escopo atual).

**Elicitação.** Primeira fase da engenharia de requisitos: descobrir o que stakeholders e
usuários precisam. No FAKO, feita por workshop interno (com brainstorming em quadro no
Miro) e por entrevista; ver [Técnicas de elicitação](requisitos/tecnicas-elicitacao.md).

**MVP.** Produto mínimo viável: o recorte de requisitos Must, Should e Could have que forma
a primeira versão entregável do FAKO.

## Arquitetura

**AD.** Decisão de arquitetura (de "architecture decision"): uma escolha técnica já
implementada sobre como construir o sistema, diferente de uma decisão de produto; ver
[Decisões de arquitetura](arquitetura/decisoes.md).

**JWT.** JSON Web Token, usado para autenticar o jogador depois do login, sem manter sessão
no servidor; ver [AD02](arquitetura/decisoes.md#ad02-autenticacao-por-jwt-senha-com-hash-bcrypt).

**Camada (MVC).** Divisão da aplicação em `controller`, `service`, `repository` e `model`
no backend, e `view`, `controller` e `service` no frontend, em que cada camada só conhece a
imediatamente abaixo; ver [Visão geral](arquitetura/visao-geral.md).
