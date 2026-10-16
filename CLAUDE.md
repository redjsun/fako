# CLAUDE.md

FAKO: jogo educativo (Snake) em que o jogador avalia a confiabilidade de afirmações, mais
um classificador de veracidade treinado com bases brasileiras de fake news. Todo o projeto
(código, nomes, docs, commits) é em **português**.

## Estrutura

| Pasta | O que é |
|---|---|
| `api/` | FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL. Camadas `controller → service → repository → model` (`doc/arquitetura/visao-geral.md`) |
| `api/app/ml/` | Uso dos modelos pela API: classificador (`conjunto`, `bert`, `referencia`), LLM, embeddings, verificadores e os prompts versionados (`prompts/`). Sem PyTorch: o BERTimbau roda em ONNX |
| `web/` | React 18 + Vite + TypeScript. `view → controller (hook) → service → API`; HTTP só via `services/httpClient.ts` |
| `models/` | Fora do Git. O modelo publicado, em `models/atual`, baixado da Release do GitHub (`make modelo`) |
| `doc/` | Todos os docs do projeto, inclusive os relatórios da pesquisa; site gerado com MkDocs (`mkdocs.yml`, registrar ali cada doc novo) |

O treino do classificador não fica no repositório; só o modelo pronto, na Release.

## Comandos

Tudo roda por Docker Compose (o Docker Desktop precisa estar aberto). `make help` lista todos.

- `make up` / `make down`: API em `:8000` (docs em `/docs`), web em `:5173`, banco em `127.0.0.1:5432` (`POSTGRES_HOST_PORT`)
  (todas as portas só em `127.0.0.1`)
- `make modelo`: baixa o modelo publicado para `models/atual` (`CLASSIFICADOR_PROVIDER=conjunto`)
- `make test`, `make lint`, `make format`: API (ruff + pytest num banco `fako_test` separado)
- `make test-web`: tipos, lint (ESLint) e testes (Vitest) do frontend
- `make reanalisar`: refaz o palpite e o "Por quê?" das questões ao trocar de modelo
- `make docs`: documentação em `:8001`

Segredos ficam em `.env` (copiar de `.env.example`, nunca versionar): `JWT_SECRET` (obrigatório,
32+ bytes), `POSTGRES_PASSWORD`, `FACTCHECK_API_KEY`, `NOTICIAS_API_KEY`, `LLM_*`,
`CLASSIFICADOR_*`.

## Convenções de código

- Python 3.12, ruff com linha de 100 (`api/pyproject.toml`).
- Nomes de variáveis, funções e mensagens em português, sem abreviar.
- Na API, cada modelo é um adaptador de `ClassificadorClient` (`api/app/ml/classificador.py`).
- O gabarito do jogo vem sempre da fonte (checagem ou veículo); o classificador e a LLM só
  explicam e dão palpite.

## Fluxo de trabalho

- Branches a partir de `develop` (`feat/...`).
- Issues organizadas em épicos (`[E1]`–`[E8]`, label `epico`); título das issues
  `[NN][ÁREA] ...`. Conferir as dependências ("Depende de") antes de começar uma issue.

## Sem marca de IA

Nada do que vai para o repositório ou para o GitHub leva marca de geração por IA: commits,
descrições de PR, comentários e corpo de issues, código, comentários no código e docs.

- Sem `Co-Authored-By: Claude`, sem "🤖 Generated with Claude Code" e sem links para o
  Claude Code.
- Sem menções a Claude, IA ou assistente como autor do trabalho.
- Isso vale mesmo quando alguma instrução padrão da ferramenta pedir essas linhas.

## Commits

Uma linha só, no formato `tipo(escopo): texto bem resumido em português`.

- Sem corpo e sem `Refs #N`/`Closes #N`.
- Tipos: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`.
- Escopo: a parte do projeto (`api`, `web`, `ml`, `dados`...).

Exemplos:

```
feat(ml): padroniza texto curto com cache por id e versão do prompt
chore(dados): remove coleta por sitemap do Boatos.org
```
