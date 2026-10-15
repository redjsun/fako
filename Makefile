COMPOSE := docker compose

.PHONY: help build up down restart logs ps shell-api shell-web shell-db migrate makemigration seed admin test lint format dados padronizar atalho contagens referencia bert avaliar coletar-avaliacao avaliar-jogo calibrar exportar-onnx classificar publicar reanalisar importar-noticias limpar-noticias amostra-questoes medir-amostra pre-anotar avaliar-extracao test-web test-ml shell-ml build-ml gpu eda docs clean

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
# GPU=1 usa a GPU NVIDIA (compose.gpu.yaml, PyTorch CUDA); exige o NVIDIA Container Toolkit.
COMPOSE_ML := $(COMPOSE)$(if $(GPU), -f compose.yaml -f compose.gpu.yaml) --profile ml
ML := $(COMPOSE_ML) run --rm --no-deps ml

build-ml: ## Constrói a imagem de treino (uso: make build-ml [GPU=1])
	$(COMPOSE_ML) build ml

gpu: ## Confere se o container de treino enxerga a GPU NVIDIA
	$(COMPOSE) -f compose.yaml -f compose.gpu.yaml --profile ml run --rm --no-deps ml python -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"

dados: ## Baixa as bases para pesquisa/data/raw/ e gera dataset.jsonl e claimpt.jsonl em pesquisa/data/processed/
	bash pesquisa/dados/baixar_dados.sh
	$(PESQUISA) python pesquisa/dados/preparar_dados.py
	$(PESQUISA) python pesquisa/dados/preparar_claimpt.py

PROMPT ?= api/app/ml/prompts/extrair_afirmacoes_v1.txt

padronizar: ## Padroniza o texto curto com a LLM (uso: make padronizar [PROMPT=api/app/ml/prompts/extrair_afirmacoes_vN.txt] [ARGS="--limite 50"])
	$(PESQUISA) python pesquisa/ml/padronizar.py --prompt $(PROMPT) $(ARGS)

atalho: ## Teste de atalho: AUC só pela forma do texto (uso: make atalho [ARGS="--prompt api/app/ml/prompts/extrair_afirmacoes_v1.txt"])
	$(ML) python pesquisa/ml/atalho.py $(ARGS)

contagens: ## Contagens por split e classe do conjunto de treino (pesquisa/ml/dados.py)
	$(ML) python pesquisa/ml/dados.py

CONFIG ?= pesquisa/ml/configs/referencia.toml

referencia: ## Treina a referência TF-IDF ordinal (uso: make referencia [CONFIG=pesquisa/ml/configs/referencia-padronizado.toml])
	$(ML) python pesquisa/ml/treinar_referencia.py --config $(CONFIG)

CONFIG_BERT ?= pesquisa/ml/configs/bert.toml

bert: ## Treina o BERTimbau ordinal CORAL (uso: make bert [GPU=1] [ARGS="--sementes 42 --max-epocas 3"])
	$(ML) python pesquisa/ml/treinar_bert.py --config $(CONFIG_BERT) $(ARGS)

MODELO ?= models/2026-11/referencia

classificar: ## Teste manual do modelo (uso: make classificar [ARGS='"uma frase"' | ARGS="--amostra 10 --erros" | ARGS=--exportar])
	$(ML) python pesquisa/ml/classificar.py --modelo $(MODELO) $(ARGS)

avaliar: ## Avalia modelo(s) na validação (uso: make avaliar [MODELO="models/2026-11/referencia models/2026-11/bert"] [ARGS=--teste])
	$(ML) python pesquisa/ml/avaliar.py --modelo $(MODELO) $(ARGS)

coletar-avaliacao: ## Notícias recentes no formato do jogo, para o avaliar-jogo (uso: make coletar-avaliacao [ARGS="--quantidade 50"])
	@mkdir -p pesquisa/data/avaliacao
	$(COMPOSE) run --rm --no-deps -T -e LLM_PROVIDER=openai -e NOTICIAS_SEM_POLITICA=false api python -m app.jobs.coletar_avaliacao $(ARGS) > pesquisa/data/avaliacao/jogo-$$(date +%F-%H%M).jsonl

avaliar-jogo: ## Acertos dos modelos nas notícias do jogo (uso: make avaliar-jogo [MODELO="models/2026-11/referencia models/2026-11/bert"])
	$(ML) python pesquisa/ml/avaliar_jogo.py --modelo $(MODELO) $(ARGS)

exportar-onnx: ## Exporta o BERTimbau para ONNX, para a API (uso: make exportar-onnx [MODELO=models/2026-11/bert])
	$(ML) python pesquisa/ml/exportar_onnx.py --modelo $(MODELO)

calibrar: ## Calibra as fronteiras e grava limiares.json na validação (uso: make calibrar [MODELO=models/2026-11/referencia] [ARGS="--proporcao-verdadeiros 0.5"])
	$(ML) python pesquisa/ml/calibrar.py --modelo $(MODELO) $(ARGS)

publicar: ## Publica um modelo para a API em models/atual (uso: make publicar [MODELO=models/2026-11/referencia])
	rm -rf models/atual && cp -r $(MODELO) models/atual

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

pre-anotar: ## Sugestões da LLM nas planilhas de anotação (uso: make pre-anotar r=2 [ACAO=comparar])
	$(PESQUISA) python pesquisa/dados/pre_anotar.py $(or $(ACAO),sugerir) --rodada $(r)

avaliar-extracao: ## Extração de afirmações nos textos BR rotulados (uso: make avaliar-extracao [ACAO=medir])
	$(PESQUISA) python pesquisa/ml/avaliar_extracao.py $(or $(ACAO),rodar) --prompt $(PROMPT)

shell-ml: ## Abre um shell no container de treino
	$(ML) bash

test-web: ## Roda tipos, lint e testes do frontend
	$(COMPOSE) run --rm --no-deps web sh -c "npm install --no-audit --no-fund && npm run typecheck && npm run lint && npm run test"

test-ml: ## Roda lint e testes de pesquisa/ml/
	$(COMPOSE) --profile pesquisa run --rm --no-deps -w /work/pesquisa/ml pesquisa sh -c "pip install -q -r requirements-dev.txt && ruff check . && ruff format --check . && pytest -v"

eda: ## Sobe o Jupyter Lab da EDA em http://localhost:8888
	$(COMPOSE) --profile pesquisa up -d pesquisa

docs: ## Sobe a documentação (MkDocs) em http://localhost:8001
	$(COMPOSE) --profile docs up docs

clean: ## Remove containers, volumes e imagens do projeto
	$(COMPOSE) down -v --rmi local
