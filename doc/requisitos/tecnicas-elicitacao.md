# Técnicas de elicitação

Elicitação é a primeira das quatro fases da engenharia de requisitos (elicitação, análise,
especificação, validação): descobrir o que stakeholders e usuários precisam, antes de
analisar, documentar e validar esse conhecimento. O grupo combinou duas técnicas
complementares, brainstorming e benchmark, e usou a priorização MoSCoW para decidir o que
entra no MVP. O resultado está em
[Requisitos funcionais](requisitos-funcionais.md) e
[Requisitos não funcionais](requisitos-nao-funcionais.md), cada requisito com a sua origem.

## Brainstorming

Sessão da equipe, registrada em quadro no Miro, para levantar o problema, o público-alvo e
as primeiras ideias de software antes de qualquer decisão técnica.

**Problemas identificados:** identificação de fake news e de notícias maldosas,
desenvolvimento do letramento midiático, engajamento e aprendizado mais interativo (indo
além de perguntas simples de verdadeiro ou falso) e regras que o jogador compreenda
rapidamente.

**Público-alvo:** adolescentes e jovens adultos, estudantes e pessoas que consomem
informação diariamente pelas redes; qualquer pessoa que queira desenvolver habilidades de
análise de informação de forma interativa.

**Ideias que viraram requisito:** cenário quadriculado com a cobra como mecânica principal,
pergunta binária (verdadeiro ou falso) ao comer a maçã, cobra que cresce só no erro, 3 vidas,
colisão com borda ou corpo, temporizador de 120 segundos, progressão de níveis com redução
do espaço de jogo, telas de login/cadastro e tutorial. O brainstorming também definiu o fluxo
do jogador (página inicial → perfil/login → partida → afirmação → acerto ou erro → feedback
→ pontuação → checagem de nível → resultado) e a stack inicial cogitada (React, Node.js,
PostgreSQL, um classificador que recebe uma frase e devolve verdadeiro ou falso).

A maior parte dos requisitos funcionais e quase todos os não funcionais vêm desta técnica,
pois ela cobre o que o produto faz e como ele deve se comportar por dentro (dados, sessão,
segurança), questões que um benchmark de produtos prontos não revela sozinho.

## Benchmark

Teste direto de jogos e ferramentas de educação midiática e combate à desinformação, para
identificar mecânicas e funcionalidades recorrentes antes de desenhar as próprias.

| Ferramenta | Endereço | O que trouxe para o FAKO |
|---|---|---|
| Bad News (versão júnior) | getbadnews.com | Táticas de criação de desinformação; existência de uma versão para público mais novo reforçou a necessidade de tutorial (RF05) |
| Harmony Square | harmonysquare.game/en | Técnicas de manipulação usadas para dividir uma comunidade |
| Troll Factory | trollfactory.yle.fi | Produção de conteúdo manipulador por trolls, da emissora pública finlandesa Yle |
| Debunkbot | debunkbot.com | Contra-argumentos e evidências para questionar uma crença, o que reforça a explicação pós-resposta (RF21) |
| Spot the Troll | spotthetroll.org | Julgamento de contas reais (legítimas vs. trolls): o formato treina discriminação, não desconfiança geral |
| Fakey | fakey.osome.iu.edu | Feed simulado da Universidade de Indiana que mistura fontes confiáveis e de baixa credibilidade, promovendo o que é bom e não só marcando o ruim |

Requisitos como feedback imediato da resposta (RF10), explicação educativa (RF21),
usabilidade (RNF01) e clareza das mensagens (RNF20) vêm do benchmark: são padrões que
apareceram de forma consistente nas ferramentas testadas, não ocorrências da equipe.

## Priorização: MoSCoW

Com o levantamento feito, cada requisito foi classificado em um de quatro níveis, para
gerenciar o escopo de um MVP com prazo curto e recursos limitados:

- **Must have:** essencial; sem ele o MVP é inviável (núcleo do jogo, pré-processamento e
  classificação prévia das afirmações, conta do jogador e segurança das credenciais).
- **Should have:** importante para a eficácia do jogo, mas não inviabiliza a primeira
  versão (tutorial, progressão de níveis, acessibilidade, responsividade, modularidade,
  privacidade).
- **Could have:** agrega valor perceptível, mas só entra se houver folga no cronograma
  (auditabilidade).
- **Won't have:** fora do escopo atual, explicitamente postergado para depois do MVP; não
  aparece nas tabelas de requisitos.

## Técnicas não usadas nesta rodada

Entrevista, grupo focal, observação, questionário e análise de documentos também são
técnicas de elicitação reconhecidas, cada uma mais indicada a um tipo de contexto. Por
exemplo, entrevista e grupo focal valem mais quando já existe uma base de usuários reais
para ouvir, o que ainda não é o caso do FAKO. Ficam como opção para rodadas futuras de
levantamento, quando houver jogadores usando o produto para entrevistar ou observar.
