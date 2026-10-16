COMPOSE := docker compose

.PHONY: help build up down restart logs ps shell-api shell-web shell-db migrate makemigration seed admin test lint format modelo reanalisar importar-noticias limpar-noticias amostra-questoes medir-amostra test-web docs clean

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

build: ## Constrói as imagens do projeto
	$(COMPOSE) build

up: ## Sobe os containers em background
	$(COMPOSE) up -d

down: ## Derruba os containers
	$(COMPOSE) down

restart: down up ## Reinicia os containers

logs: ## Acompanha os logs dos serviços
	$(COMPOSE) logs -f

ps: ## Mostra o status dos containers
	$(COMPOSE) ps

shell-api: ## Abre um shell no container da API
	$(COMPOSE) exec api bash

shell-web: ## Abre um shell no container do frontend
	$(COMPOSE) exec web sh

shell-db: ## Abre o psql no container do banco
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

migrate: ## Aplica as migrations pendentes no banco
	$(COMPOSE) exec api alembic upgrade head

makemigration: ## Gera uma migration a partir dos models (uso: make makemigration m="descricao")
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

seed: ## Popula o banco com categorias, níveis e questões iniciais
	$(COMPOSE) exec api python -m app.seeds.run

# Sem p=, o script pede a senha no terminal (não fica no histórico do shell nem na lista de processos).
admin: ## Cria um administrador de conteúdo (uso: make admin u=usuario; a senha é pedida no terminal)
	$(COMPOSE) exec api python -m app.seeds.create_admin "$(u)" $(if $(p),"$(p)",)

# As credenciais vêm do .env do container (env_file), com os padrões de dev do compose.yaml.
TEST_DB_URL := postgresql+psycopg://\$${POSTGRES_USER:-fako}:\$${POSTGRES_PASSWORD:-fako}@db:5432/fako_test
# Segredo só de teste: a API recusa subir sem um JWT_SECRET de 32+ bytes.
TEST_JWT_SECRET := teste-local-somente-nao-usar-em-producao-0123456789

test: ## Roda os testes da API num banco separado (fako_test)
	-$(COMPOSE) exec db sh -c 'createdb -U "$$POSTGRES_USER" fako_test'
	$(COMPOSE) run --rm --no-deps -v ./api:/app -e JWT_SECRET=$(TEST_JWT_SECRET) api sh -c "pip install -q -r requirements-dev.txt && DATABASE_URL=$(TEST_DB_URL) pytest -v"

lint: ## Verifica lint e formatação da API
	$(COMPOSE) run --rm --no-deps -v ./api:/app -e JWT_SECRET=$(TEST_JWT_SECRET) api sh -c "pip install -q -r requirements-dev.txt && ruff check . && ruff format --check ."

format: ## Formata o código da API
	$(COMPOSE) run --rm --no-deps -v ./api:/app -e JWT_SECRET=$(TEST_JWT_SECRET) api sh -c "pip install -q -r requirements-dev.txt && ruff format . && ruff check --fix ."

# Modelo publicado (fora do Git): o classificador em conjunto (os dois BERTimbau em ONNX), num
# arquivo da Release do GitHub. A API o lê de models/atual (MODELS_DIR).
MODELO_VERSAO ?= conjunto-2026-10-15
MODELO_URL ?= https://github.com/redjsun/fako/releases/download/modelo-$(MODELO_VERSAO)/modelo-$(MODELO_VERSAO).tar.gz

modelo: ## Baixa o modelo publicado da Release para models/atual (uso: make modelo [MODELO_VERSAO=...])
	mkdir -p models
	curl -fL --progress-bar -o models/modelo.tar.gz $(MODELO_URL)
	rm -rf models/atual && mkdir -p models/atual && tar -xzf models/modelo.tar.gz -C models/atual
	rm models/modelo.tar.gz
	@echo "Modelo em models/atual. Use CLASSIFICADOR_PROVIDER=conjunto no .env e recrie a API."

reanalisar: ## Refaz a análise guardada nas questões com o modelo publicado (uso: make reanalisar [ARGS=--todas])
	$(COMPOSE) exec api python -m app.jobs.reanalisar_questoes $(ARGS)

importar-noticias: ## Importa as notícias do dia agora, como o agendador-api (uso: make importar-noticias [ARGS="--quantidade 5"])
	$(COMPOSE) exec api python -m app.jobs.importar_noticias $(ARGS)

limpar-noticias: ## Apaga as notícias vencidas agora, como o agendador-api (uso: make limpar-noticias [ARGS="--dias 30"])
	$(COMPOSE) exec api python -m app.jobs.limpar_noticias $(ARGS)

amostra-questoes: ## Planilha de avaliação das questões da LLM para o admin (uso: make amostra-questoes [ARGS="--itens 50"] > amostra.csv)
	@$(COMPOSE) exec -T api python -m app.jobs.amostra_questoes sortear $(ARGS)

medir-amostra: ## % de questões com erro na planilha preenchida (uso: make medir-amostra < amostra.csv)
	@$(COMPOSE) exec -T api python -m app.jobs.amostra_questoes medir

test-web: ## Roda tipos, lint e testes do frontend
	$(COMPOSE) run --rm --no-deps web sh -c "npm ci --no-audit --no-fund && npm run typecheck && npm run lint && npm run test"

docs: ## Sobe a documentação (MkDocs) em http://localhost:8001
	$(COMPOSE) --profile docs up docs

clean: ## Remove containers, volumes e imagens do projeto
	$(COMPOSE) down -v --rmi local
