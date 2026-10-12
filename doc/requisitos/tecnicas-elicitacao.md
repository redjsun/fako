# Técnicas de elicitação

Elicitação é a primeira das quatro fases da engenharia de requisitos (elicitação, análise,
especificação, validação): descobrir o que stakeholders e usuários precisam, antes de
analisar, documentar e validar esse conhecimento. O grupo combinou duas técnicas
complementares, brainstorming e entrevista, e usou a priorização MoSCoW para decidir o que
entra no MVP. O resultado está em
[Requisitos funcionais](requisitos-funcionais.md) e
[Requisitos não funcionais](requisitos-nao-funcionais.md), cada requisito com a sua origem.

O benchmark de jogos e ferramentas de educação midiática também fez parte do processo, mas
não como elicitação: ele serviu para definir o produto (que mecânicas e padrões de mercado
adotar), não para descobrir necessidades de stakeholders. Fica descrito à parte, em
[Benchmark](#benchmark-apoio-a-definicao-do-produto).

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
segurança).

## Entrevista

**Objetivo.** Validar, na perspectiva de potenciais jogadores externos à equipe, hipóteses
do brainstorming sobre hábito de uso e permanência em aplicativos de aprendizagem
gamificados, antes de consolidar as mecânicas de progresso e recompensa do FAKO.

**Método.** Entrevistas individuais semiestruturadas, conduzidas por videochamada (Google
Meet), com roteiro voltado ao hábito de uso de aplicativos de aprendizagem gamificados
(Duolingo e similares): o que sustenta o uso contínuo desses aplicativos e o que leva ao
abandono.

**Participantes.**

| Participante | Perfil | Relação com apps de aprendizagem gamificada |
|---|---|---|
| Entrevistada 1 | 21 anos, estudante de Engenharia de Software | Uso pouco frequente; relata dificuldade em manter o uso diário exigido por esse tipo de aplicativo |
| Entrevistado 2 | 24 anos, trabalha em um aeroporto | Usuário frequente e assíduo do Duolingo |

**Achados.**

- A entrevistada 1 não sustenta o uso regular desse tipo de aplicativo por não conseguir
  manter a constância diária exigida por eles. Avaliou que a proposta do FAKO se adequaria
  melhor à sua rotina por não depender de uma sequência consecutiva de dias jogados para a
  manutenção do progresso.
- O entrevistado 2 destacou, como fator determinante de sua permanência no Duolingo, a
  abordagem de aprendizagem por reforço do aplicativo: o acerto é recompensado
  imediatamente, e o item errado é reapresentado posteriormente.

**Impacto nos requisitos.** O achado da entrevistada 1 fundamenta o controle de progresso
por nível e por partida avulsa, em vez de por sequência de dias consecutivos. O achado do
entrevistado 2 fundamenta a pontuação imediata por acerto e o feedback apresentado logo após
a resposta.

**Limitações.** As duas entrevistas relatadas fazem parte de uma rodada mais ampla; as
notas dos demais participantes ainda não foram consolidadas neste documento. Os requisitos
que carregam a origem Entrevista nas tabelas de [requisitos funcionais](requisitos-funcionais.md)
e de [requisitos não funcionais](requisitos-nao-funcionais.md) refletem tanto os achados já
registrados acima quanto os que ainda serão detalhados conforme a consolidação avança.

## Benchmark (apoio à definição do produto)

Teste direto de jogos e ferramentas de educação midiática e combate à desinformação, para
identificar mecânicas e funcionalidades recorrentes antes de desenhar as próprias. Não é uma
técnica de elicitação (não descobre necessidades de stakeholders), mas de definição de
produto: compara o que já existe no mercado para situar o FAKO.

| Ferramenta | Endereço | O que trouxe para o FAKO |
|---|---|---|
| Bad News (versão júnior) | getbadnews.com | Táticas de criação de desinformação; existência de uma versão para público mais novo reforçou a necessidade de tutorial (RF05) |
| Harmony Square | harmonysquare.game/en | Técnicas de manipulação usadas para dividir uma comunidade |
| Troll Factory | trollfactory.yle.fi | Produção de conteúdo manipulador por trolls, da emissora pública finlandesa Yle |
| Debunkbot | debunkbot.com | Contra-argumentos e evidências para questionar uma crença, o que reforça a explicação pós-resposta (RF21) |
| Spot the Troll | spotthetroll.org | Julgamento de contas reais (legítimas vs. trolls): o formato treina discriminação, não desconfiança geral |
| Fakey | fakey.osome.iu.edu | Feed simulado da Universidade de Indiana que mistura fontes confiáveis e de baixa credibilidade, promovendo o que é bom e não só marcando o ruim |

O benchmark ajudou a desenhar mecânicas como o feedback imediato da resposta (RF10) e a
explicação educativa (RF21), mas, por não ser elicitação, esses requisitos aparecem na
tabela com a origem Entrevista: foram as conversas com jogadores em potencial que
confirmaram essas necessidades como requisito, não o teste das ferramentas em si.

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

Grupo focal, observação, questionário e análise de documentos também são técnicas de
elicitação reconhecidas, cada uma mais indicada a um tipo de contexto. Por exemplo,
observação e questionário em escala valem mais quando já existe uma base de jogadores reais
usando o produto, o que ainda não é o caso do FAKO. Ficam como opção para rodadas futuras de
levantamento.
