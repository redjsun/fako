# Arquitetura

O projeto segue **arquitetura em camadas + MVC**, com a mesma ideia aplicada no
backend e no frontend: cada camada só conhece a camada imediatamente abaixo.

## Backend (`api/`)

```
app/
├── main.py           # composição da aplicação (monta app e rotas)
├── core/             # configuração e infraestrutura
├── controllers/      # Controller — rotas HTTP, validação de entrada
├── services/         # regras de negócio, sem conhecer HTTP
├── repositories/     # acesso a dados
├── models/           # Model — entidades de domínio (SQLAlchemy)
├── schemas/          # DTOs de entrada e saída da API
└── seeds/            # dados iniciais (categorias, níveis, questões)
migrations/           # migrations do Alembic, geradas a partir dos models
```

Persistência: PostgreSQL (serviço `db` no compose), SQLAlchemy 2 e Alembic.
`core/database.py` abre uma sessão por requisição (`get_db`), com commit ao
final e rollback em caso de erro. Comandos: `make migrate`, `make makemigration m="..."`
e `make seed`.

Segurança: senhas com hash bcrypt (`core/security.py`) e autenticação por JWT (HS256) no
header `Authorization: Bearer`. `core/deps.py` expõe `get_current_user` e
`get_current_admin` para proteger as rotas. Variáveis de ambiente em `.env.example`.

- **Segredo do JWT:** a API não sobe sem um `JWT_SECRET` de 32 bytes ou mais, diferente do
  valor de exemplo (`core/config.py`).
- **Senha:** 8 caracteres no mínimo e 72 bytes no máximo (o limite do bcrypt) no cadastro.
- **Limite de login:** 5 senhas erradas para o mesmo usuário, ou 20 vindas da mesma origem, em
  15 minutos, e o login responde 429 (`core/rate_limit.py`). O contador fica em memória e vale
  por processo; com vários workers ou atrás de um proxy, o limite precisa ir para o proxy.
- **Regras do jogo no servidor:** a API mede o tempo de cada pergunta (o tempo do nível mais
  30 s de folga, `game_rules.py`); resposta atrasada conta como erro e volta com
  `timed_out=true`. Cada jogador tem uma partida aberta: começar outra marca a anterior como
  `abandoned`, que não soma pontos. A partida fica travada no banco (`SELECT ... FOR UPDATE`)
  enquanto uma pergunta é servida, respondida ou a partida é encerrada, e uma questão só pode
  ser respondida uma vez por partida. Encerrar uma partida já encerrada responde 409.

Fluxo: `controller → service → repository → model`.
Os `schemas` trafegam entre controller e service; os `models` não vazam para fora
da camada de negócio.

## Frontend (`web/src/`)

```
src/
├── models/        # Model — tipos do domínio
├── services/      # acesso à API (httpClient + serviços por recurso)
├── controllers/   # Controller — hooks que orquestram estado e serviços
└── views/         # View — páginas e componentes de apresentação
    ├── pages/
    └── components/
```

Fluxo: `view → controller (hook) → service → API`.
As views não chamam `fetch` diretamente; toda chamada HTTP passa pelo
`services/httpClient.ts`.

## Rotas da API

| Módulo | Rotas | Acesso |
|---|---|---|
| health | `GET /health` | público |
| auth | `POST /auth/register`, `POST /auth/login` | público |
| users | `GET /users/me` | jogador |
| levels | `GET /levels` | público |
| matches | `POST /matches`, `GET /matches/{id}`, `GET /matches/{id}/next-question`, `POST /matches/{id}/answers`, `POST /matches/{id}/finish` | jogador |
| progress | `GET /progress/me` | jogador |
| admin | `GET/POST /admin/questions`, `PATCH /admin/questions/{id}/review`, `POST /admin/ai/generate`, `POST /admin/ai/classify`, `POST /admin/news/import`, `POST /admin/classifier/analyze` | administrador |
| ai | `POST /ai/analyze` (BERTimbau Y1/Y2 do `ml/` legado; 503 sem os artefatos) | administrador |

A documentação interativa fica em `http://localhost:8000/docs`. Os services levantam
exceções de `core/exceptions.py`, convertidas em respostas HTTP pelo handler de `main.py`.
A IA fica atrás da interface `integrations/ai_client.py` (`AI_PROVIDER=fake` por padrão).
O classificador de veracidade fica atrás de `integrations/classificador_client.py`
(`CLASSIFICADOR_PROVIDER=fake` por padrão): cada modelo treinado é um adaptador que devolve as
duas fronteiras ordinais, e `analise_das_fronteiras()` aplica a mesma regra de decisão a todos.
Os modelos publicados são lidos de `MODELS_DIR/atual` (a pasta `models/`, montada só para
leitura); sem modelo, o cliente lança `ClassificadorIndisponivel` e a API continua de pé.
Tudo o que a IA gera entra como rascunho, publicado só depois da revisão em
`/admin/questions/{id}/review`. Para criar um administrador: `make admin u=usuario` (a senha é
pedida no terminal).

## Qualidade e CI

O GitHub Actions (`.github/workflows/ci.yml`) roda a cada push e em todo pull request
para a `main`, só com permissão de leitura e com as actions fixadas por commit (SHA):

- **API**: `ruff check`, `ruff format --check`, `alembic upgrade head` e `pytest` (cobertura
  mínima de 80%) com um PostgreSQL temporário; `pip-audit` informativo;
- **ML**: `ruff check` e `ruff format --check` em `pesquisa/ml/`, `pesquisa/dados/` e no `ml/`
  legado (configuração de `pesquisa/ml/pyproject.toml`), `pytest` de `pesquisa/ml/` (cobertura
  mínima de 75%) e os testes do `ml/` legado que não precisam de PyTorch; `pip-audit` informativo;
- **Web**: `npm ci`, verificação de tipos, ESLint, Vitest e build do Vite; `npm audit` informativo;
- **Docs**: `mkdocs build --strict` (versões de `requirements-docs.txt`) e checagem de links
  externos;
- **Docker**: build das imagens `api`, `web`, `agendador` e `ml` (`docker/bake-action` sobre o
  `compose.yaml`, com cache), depois que os jobs da API e do web passam.

O `.github/dependabot.yml` abre PRs semanais para a `develop` com as atualizações das actions,
do npm e do pip. O deploy da documentação no GitHub Pages fica em `.github/workflows/docs.yml`.

Localmente: `make lint`, `make format` e `make test` (usa o banco `fako_test`,
separado do de desenvolvimento), `make test-ml` e `make test-web`.
