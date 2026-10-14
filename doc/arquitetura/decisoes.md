# Decisões de arquitetura

Registro das escolhas técnicas já tomadas no projeto: como construir o sistema, diferente
das [decisões de produto](../requisitos/decisoes-de-produto.md), que tratam do que o
produto faz. Cada decisão aqui já está implementada; não é uma proposta em aberto.

## AD01. Arquitetura em camadas, com o mesmo princípio no backend e no frontend

**Contexto.** O projeto tem um backend (API) e um frontend (jogo), e cada um precisa de
uma organização interna clara para não misturar regra de negócio com apresentação.

**Decisão.** Camadas MVC em ambos: no backend, `controller → service → repository →
model`; no frontend, `view → controller (hook) → service → API`. Cada camada só conhece a
camada imediatamente abaixo (ver [Visão geral](visao-geral.md)).

**Consequências.** Facilita testar a regra de negócio sem subir a API HTTP completa, e
trocar a camada de apresentação sem tocar nas regras. Em troca, cada funcionalidade nova
toca em várias pastas em vez de uma só.

## AD02. Autenticação por JWT, senha com hash bcrypt

**Contexto.** O jogo precisa de contas de jogador (RF02) com credenciais protegidas (RNF07,
RNF08).

**Decisão.** Login emite um JWT (`api/app/core/security.py`), enviado no header
`Authorization: Bearer`. Senhas nunca são gravadas em texto puro: só o hash bcrypt.
`core/deps.py` expõe `get_current_user` e `get_current_admin` para proteger as rotas.

**Consequências.** API sem estado de sessão no servidor (escalável sem sticky sessions),
mas exige que o cliente guarde e renove o token.

## AD03. PostgreSQL com SQLAlchemy 2 e Alembic

**Contexto.** O jogo precisa persistir contas, partidas, progresso e o banco de questões
com relações entre eles (ver [Esquema do banco](schema.md)).

**Decisão.** PostgreSQL como banco relacional (serviço `db` no compose), SQLAlchemy 2 como
ORM e Alembic para migrations geradas a partir dos models. `core/database.py` abre uma
sessão por requisição, com commit ao final e rollback em caso de erro.

**Consequências.** Migrations versionadas e reprodutíveis (`make migrate`,
`make makemigration`), ao custo de precisar rodar a migration em todo ambiente antes de
subir uma mudança de schema.

## AD04. Um container por serviço, com perfis para os opcionais

**Contexto.** O projeto reúne API, frontend, banco, pesquisa de dados, treino de ML,
agendador de coleta e, agora, a documentação, cada um com dependências diferentes (Python
com PyTorch no treino, Node no frontend, por exemplo).

**Decisão.** Cada parte roda em seu próprio serviço no `compose.yaml`, com imagem própria.
Serviços que não sobem toda hora (`pesquisa`, `ml`, `ml-legado`, `docs`) usam `profiles` do
Compose, para não pesar o `make up` do dia a dia.

**Consequências.** Nenhuma dependência de instalação local além do Docker; em troca, builds
e imagens a mais para manter.

## AD05. Classificador e LLM atrás de interfaces próprias, com provedor "fake" por padrão

**Contexto.** O jogo depende de um classificador de veracidade e, no futuro, de uma LLM
para gerar questões, mas nem todo ambiente de desenvolvimento ou de CI tem os modelos
publicados disponíveis.

**Decisão.** `integrations/classificador_client.py` (`ClassificadorClient`) e
`integrations/llm_client.py` (`LLMClient`) definem as interfaces, separadas porque classificar
e gerar texto têm dependências, falhas e versões diferentes. O provedor real é plugável
(`CLASSIFICADOR_PROVIDER`, `LLM_PROVIDER`), com um provedor `fake` como padrão. Sem modelo
publicado ou sem LLM configurada, o cliente lança `ClassificadorIndisponivel` ou
`LLMIndisponivel` e a API continua de pé.

**Consequências.** Desenvolvimento e testes não dependem de ter um modelo treinado em mãos;
em troca, o comportamento com o provedor fake pode divergir do real se a interface não for
fiel o bastante.

## AD06. Toda questão gerada automaticamente nasce como rascunho

**Contexto.** Questões podem vir de uma pessoa, de notícia externa ou de geração por IA
(`QuestionOrigin`), e o jogo não pode publicar direto algo que a equipe não revisou.

**Decisão.** `QuestionStatus` começa em `draft`; só uma revisão humana
(`PATCH /admin/questions/{id}/review`) muda para `validated` ou `rejected`. Nenhuma questão
`draft` chega ao jogador.

**Consequências.** Gargalo de revisão manual conforme o volume de geração automática
cresce, mas nenhuma pergunta sem checagem humana chega ao jogo (RF27, ainda planejado,
formaliza esse fluxo).

## AD07. Modelos publicados ficam fora do Git

**Contexto.** Modelos treinados (pesos do BERTimbau, artefatos da referência TF-IDF) são
grandes e não cabem num repositório Git sem LFS.

**Decisão.** `models/` fica fora do versionamento, montado na API só para leitura
(`MODELS_DIR`). A API lê sempre de `MODELS_DIR/atual`.

**Consequências.** Repositório leve e histórico de Git limpo; em troca, publicar um modelo
novo é uma operação fora do Git (`make publicar`), que precisa de disciplina própria de
versionamento (ver `doc/planejamento-retreino.md`).
