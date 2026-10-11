COMPOSE := docker compose

.PHONY: help build up down restart logs ps shell-api shell-web shell-db migrate makemigration seed admin test lint format dados padronizar atalho contagens referencia bert avaliar classificar test-ml shell-ml eda ml-legado clean

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
	$(COMPOSE) exec db psql -U fako -d fako

migrate: ## Aplica as migrations pendentes no banco
	$(COMPOSE) exec api alembic upgrade head

makemigration: ## Gera uma migration a partir dos models (uso: make makemigration m="descricao")
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

seed: ## Popula o banco com categorias, níveis e questões iniciais
	$(COMPOSE) exec api python -m app.seeds.run

admin: ## Cria um administrador de conteúdo (uso: make admin u=usuario p=senha)
	$(COMPOSE) exec api python -m app.seeds.create_admin "$(u)" "$(p)"

TEST_DB_URL := postgresql+psycopg://fako:fako@db:5432/fako_test

test: ## Roda os testes da API num banco separado (fako_test)
	-$(COMPOSE) exec db createdb -U fako fako_test
	$(COMPOSE) run --rm --no-deps -v ./api:/app -e DATABASE_URL=$(TEST_DB_URL) api sh -c "pip install -q -r requirements-dev.txt && pytest -v"

lint: ## Verifica lint e formatação da API
	$(COMPOSE) run --rm --no-deps -v ./api:/app api sh -c "pip install -q -r requirements-dev.txt && ruff check . && ruff format --check ."

format: ## Formata o código da API
	$(COMPOSE) run --rm --no-deps -v ./api:/app api sh -c "pip install -q -r requirements-dev.txt && ruff format . && ruff check --fix ."

PESQUISA := $(COMPOSE) --profile pesquisa run --rm --no-deps pesquisa
ML := $(COMPOSE) --profile ml run --rm --no-deps ml

dados: ## Baixa as bases para pesquisa/data/raw/ e gera dataset.jsonl e claimpt.jsonl em pesquisa/data/processed/
	bash pesquisa/dados/baixar_dados.sh
	$(PESQUISA) python pesquisa/dados/preparar_dados.py
	$(PESQUISA) python pesquisa/dados/preparar_claimpt.py

PROMPT ?= api/app/prompts/extrair_afirmacoes_v1.txt

padronizar: ## Padroniza o texto curto com a LLM (uso: make padronizar [PROMPT=api/app/prompts/extrair_afirmacoes_vN.txt] [ARGS="--limite 50"])
	$(PESQUISA) python pesquisa/ml/padronizar.py --prompt $(PROMPT) $(ARGS)

atalho: ## Teste de atalho: AUC só pela forma do texto (uso: make atalho [ARGS="--prompt api/app/prompts/extrair_afirmacoes_v1.txt"])
	$(ML) python pesquisa/ml/atalho.py $(ARGS)

contagens: ## Contagens por split e classe do conjunto de treino (pesquisa/ml/dados.py)
	$(ML) python pesquisa/ml/dados.py

CONFIG ?= pesquisa/ml/configs/referencia.toml

referencia: ## Treina a referência TF-IDF ordinal (uso: make referencia [CONFIG=pesquisa/ml/configs/referencia-padronizado.toml])
	$(ML) python pesquisa/ml/treinar_referencia.py --config $(CONFIG)

CONFIG_BERT ?= pesquisa/ml/configs/bert.toml

bert: ## Treina o BERTimbau ordinal CORAL (uso: make bert [ARGS="--sementes 42 --max-epocas 3"])
	$(ML) python pesquisa/ml/treinar_bert.py --config $(CONFIG_BERT) $(ARGS)

MODELO ?= models/2026-11/referencia

classificar: ## Teste manual do modelo (uso: make classificar [ARGS='"uma frase"' | ARGS="--amostra 10 --erros" | ARGS=--exportar])
	$(ML) python pesquisa/ml/classificar.py --modelo $(MODELO) $(ARGS)

avaliar: ## Avalia modelo(s) na validação (uso: make avaliar [MODELO="models/2026-11/referencia models/2026-11/bert"] [ARGS=--teste])
	$(ML) python pesquisa/ml/avaliar.py --modelo $(MODELO) $(ARGS)

shell-ml: ## Abre um shell no container de treino
	$(ML) bash

test-ml: ## Roda lint e testes de pesquisa/ml/
	$(COMPOSE) --profile pesquisa run --rm --no-deps -w /work/pesquisa/ml pesquisa sh -c "pip install -q -r requirements-dev.txt && ruff check . && ruff format --check . && pytest -v"

eda: ## Sobe o Jupyter Lab da EDA em http://localhost:8888
	$(COMPOSE) --profile pesquisa up -d pesquisa

ml-legado: ## Ambiente do ml/ antigo (BERTimbau Y1/Y2 da API): carregamento e verificação dos dados
	$(COMPOSE) --profile ml-legado run --rm ml-legado python -m ml.dados

clean: ## Remove containers, volumes e imagens do projeto
	$(COMPOSE) down -v --rmi local
