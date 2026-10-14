# Matriz de rastreabilidade

Liga cada requisito ao que já existe no repositório: a issue do GitHub que o acompanha
(quando há uma), o artefato que implementa (código ou documento) e o status real, levantado
lendo o código, não só os planos. Serve para auditar se o catálogo de
[requisitos funcionais](requisitos-funcionais.md) e de
[requisitos não funcionais](requisitos-nao-funcionais.md) ainda corresponde ao sistema.

## Requisitos funcionais

| RF | Issue | Artefato | Status |
|---|---|---|---|
| RF01 | | `web/src/components/LoginScreen.tsx` | Implementado |
| RF02 | | `LoginScreen.tsx`, `services/authService.ts`, `api/app/controllers/auth_controller.py` (`POST /auth/register`) | Implementado |
| RF03 | #30 | `api/app/models/progress.py` (`UserProgress`), `controllers/progress_controller.py` | Implementado |
| RF04 | | `LoginScreen.tsx`, `HomeScreen.tsx`, `authService.ts`, `auth_controller.py` (`POST /auth/login`) | Implementado |
| RF05 | | `web/src/components/TutorialScreen.tsx` | Implementado |
| RF06 | | `HomeScreen.tsx`, `services/matchService.ts`, `match_controller.py` (`POST /matches`) | Implementado |
| RF07 | | `components/QuestionModal.tsx`, `match_controller.py` (`GET /matches/{id}/next-question`) | Implementado |
| RF08 | | `QuestionModal.tsx`, `components/ReliabilityBar.tsx` | Implementado, contrato sob revisão ([Decisão 01](decisoes-de-produto.md#01-mecanica-binaria-ou-em-tres-niveis)) |
| RF09 | | `match_controller.py` (`POST /matches/{id}/answers`), `api/app/services/game_rules.py` | Implementado |
| RF10 | | `components/MatchDialogs.tsx`, `QuestionModal.tsx` | Implementado |
| RF11 | | `components/GameBoard.tsx`, `game_rules.py` | Implementado |
| RF12 | | `GameBoard.tsx` | Implementado |
| RF14 | | `GameBoard.tsx` | Implementado |
| RF15 | | `api/app/models/level.py`, `controllers/level_controller.py`, `components/JourneyScreen.tsx` | Implementado |
| RF16 | | `Level.board_size` (model e seeds) | Implementado |
| RF17 | | `Level.tick_ms` (model e seeds) | Implementado |
| RF18 | | `Match.score` (model), `game_rules.py` | Implementado |
| RF19 | | `models/progress.py` (`UserProgress`), `progress_controller.py` | Implementado |
| RF20 | | `components/MatchSummary.tsx`, `POST /matches/{id}/finish` | Implementado |
| RF21 | | `Question.explanation` (model), `MatchSummary.tsx` | Implementado |
| RF22 | | `pesquisa/ml/padronizar.py`, `pesquisa/dados/preparar_dados.py` | Implementado |
| RF23 | | `Question.model_category`/`model_score`/`model_confidence` (model), `api/app/ml/classificador.py` | Implementado |
| RF24 | | `pesquisa/ml/treinar_referencia.py`, `doc/relatorio-tecnico.md` | Implementado na referência TF-IDF; pendente no BERTimbau |
| RF25 | #30 | `authService.ts`, `matchService.ts`, `progressService.ts`, `auth_controller.py`, `match_controller.py`, `progress_controller.py` | Implementado, com banco local em `matchService.ts` como fallback quando a API está fora do ar |
| RF26 | #23 | | Planejado |
| RF27 | #27 | | Planejado |
| RF28 | #28 | | Planejado |
| RF29 | perguntas norteadoras, questão 6 | `api/app/models/question.py` (`QuestionOrigin`: `human`, `ai`, `news`) | Parcial: o campo já existe, falta o fluxo de revisão do RF27 para explorá-lo |
| RF30 | [Decisão 04](decisoes-de-produto.md#04-api-de-noticias-e-noticias-nao-checadas) | `doc/noticias-classificador.md`, `QuestionOrigin.NEWS` | Em implementação |

## Requisitos não funcionais

| RNF | Issue | Artefato | Status |
|---|---|---|---|
| RNF01 | | interface do jogo (`web/src/components`) | A validar com jogadores |
| RNF02 | | | A validar |
| RNF03 | | `web/src/index.css` | A validar |
| RNF04 | | | A medir |
| RNF05 | | build do Vite | A medir |
| RNF06 | | `compose.yaml` (`restart: unless-stopped`) | Implementado na infraestrutura local |
| RNF07 | | `api/app/core/security.py`, `core/deps.py` | Implementado |
| RNF08 | | `core/security.py` (hash bcrypt) | Implementado |
| RNF09 | | `core/deps.py` (`get_current_user`) | Implementado |
| RNF10 | | PostgreSQL, migrations do Alembic | Implementado |
| RNF11 | | JWT, `UserProgress`, cache local em `authService.ts` | Implementado |
| RNF13 | | `.github/workflows/ci.yml` (build do `web`) | Verificado em CI |
| RNF14 | | organização em camadas (`doc/arquitetura/visao-geral.md`) | Implementado como princípio de design |
| RNF15 | | `controllers/`, `services/`, `repositories/` | Implementado |
| RNF16 | | `categories`, `levels` (tabelas extensíveis via seed) | Implementado |
| RNF19 | | | A detalhar |
| RNF20 | | `QuestionModal.tsx`, `MatchDialogs.tsx` | A validar |
| RNF21 | | `core/exceptions.py`, lint no CI | Parcial |
| RNF22 | | | Não implementado |
| RNF23 | | RF24, `pesquisa/ml/treinar_referencia.py` | Parcial: só a referência TF-IDF expõe pesos |
| RNF24 | #14 | `doc/planejamento-retreino.md` | Planejado |
| RNF25 | | `pesquisa/ml/atalho.py` | Implementado |
| RNF26 | | | A medir |
| RNF27 | | `pesquisa/ml/configs/`, `configuracao.py` | Implementado |

## Como manter atualizada

Esta matriz reflete o estado do código no momento em que foi escrita; ela desatualiza
sozinha conforme o projeto avança. Ao fechar uma issue listada aqui ou ao implementar um
requisito marcado como planejado, atualizar a linha correspondente faz parte do fechamento
do trabalho, não uma tarefa de documentação à parte.
