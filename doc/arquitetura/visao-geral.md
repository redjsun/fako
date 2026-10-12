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

Segurança: senhas com hash bcrypt (`core/security.py`) e autenticação por JWT no
header `Authorization: Bearer`. `core/deps.py` expõe `get_current_user` e
`get_current_admin` para proteger as rotas. Variáveis de ambiente em `.env.example`.

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
| admin | `GET/POST /admin/questions`, `PATCH /admin/questions/{id}/review`, `POST /admin/ai/generate`, `POST /admin/ai/classify` | administrador |

A documentação interativa fica em `http://localhost:8000/docs`. Os services levantam
exceções de `core/exceptions.py`, convertidas em respostas HTTP pelo handler de `main.py`.
A IA fica atrás da interface `integrations/ai_client.py` (`AI_PROVIDER=fake` por padrão).
O classificador de veracidade fica atrás de `integrations/classificador_client.py`
(`CLASSIFICADOR_PROVIDER=fake` por padrão): cada modelo treinado é um adaptador que devolve as
duas fronteiras ordinais, e `analise_das_fronteiras()` aplica a mesma regra de decisão a todos.
Os modelos publicados são lidos de `MODELS_DIR/atual` (a pasta `models/`, montada só para
leitura); sem modelo, o cliente lança `ClassificadorIndisponivel` e a API continua de pé.
Tudo o que a IA gera entra como rascunho, publicado só depois da revisão em
`/admin/questions/{id}/review`. Para criar um administrador: `make admin u=usuario p=senha`.

## Qualidade e CI

O GitHub Actions (`.github/workflows/ci.yml`) roda a cada push e em todo pull request
para a `main`:

- **API**: `ruff check`, `ruff format --check` e `pytest` com um PostgreSQL temporário;
- **Web**: `npm run build` (checagem de tipos do TypeScript + build do Vite);
- **Docker**: `docker compose build`, depois que os dois jobs anteriores passam.

Localmente: `make lint`, `make format` e `make test` (usa o banco `fako_test`,
separado do de desenvolvimento).
