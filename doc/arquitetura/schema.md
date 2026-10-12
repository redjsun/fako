# Esquema do banco

Tabelas do PostgreSQL, uma por model em `api/app/models/`, geradas pelas migrations do
Alembic. Todas herdam de `Entity` (`id` autoincremento e `created_at`); só as colunas
próprias de cada tabela aparecem abaixo.

## `users`

Jogador do FAKO (`user.py`).

| Coluna | Tipo | Notas |
|---|---|---|
| `username` | `String(50)` | único, indexado |
| `password_hash` | `String(255)` | hash bcrypt; a senha em texto puro nunca é persistida |
| `is_admin` | `bool` | responsável pelo conteúdo: pode cadastrar e validar questões |

## `categories`

Categoria das questões: Saúde, Tecnologia, Conhecimentos Gerais (`category.py`).

| Coluna | Tipo | Notas |
|---|---|---|
| `name` | `String(80)` | único |
| `slug` | `String(80)` | único, indexado |

## `levels`

Nível de dificuldade da partida (`level.py`).

| Coluna | Tipo | Notas |
|---|---|---|
| `number` | `int` | único, indexado |
| `board_size` | `int` | 7×7 nos níveis 1 a 3, 6×6 nos níveis 4 a 6 |
| `tick_ms` | `int` | intervalo entre movimentos da cobra; menor é mais difícil |
| `min_score_to_advance` | `int` | pontuação mínima na partida para liberar o próximo nível |

## `questions`

Questão do banco de conteúdo, com a confiabilidade de referência da afirmação
(`question.py`).

| Coluna | Tipo | Notas |
|---|---|---|
| `statement` | `Text` | o texto da afirmação |
| `is_true` | `bool` | gabarito binário (ver [Decisão 01](../requisitos/decisoes-de-produto.md#01-mecanica-binaria-ou-em-tres-niveis)) |
| `reliability_reference` | `int` | confiabilidade de referência (0 a 100) usada na barra do jogo |
| `explanation` | `Text` | explicação exibida após a resposta (RF21) |
| `source` | `String(500)` | origem da informação usada na validação |
| `category_id` | `FK → categories.id` | indexado |
| `status` | `enum` (`QuestionStatus`) | `draft`, `validated` ou `rejected`; só `validated` chega ao jogador |
| `origin` | `enum` (`QuestionOrigin`) | `human`, `ai` ou `news` (manchete externa); suporta o registro de proveniência (RF29) |
| `validated_at` | `DateTime`, opcional | quando a revisão humana mudou o status |
| `model_category`, `model_score`, `model_confidence`, `model_version` | `String`/`Float`, opcionais | análise do classificador na curadoria, para apoiar a revisão humana (RF23) |

## `levels` e `categories` alimentam `questions`

`questions.category_id` referencia `categories.id`; o nível não tem relação direta com a
questão (ele define o tabuleiro e a velocidade, não qual questão aparece).

## `matches`

Partida do jogador (`match.py`).

| Coluna | Tipo | Notas |
|---|---|---|
| `user_id` | `FK → users.id` | indexado |
| `level_id` | `FK → levels.id` | |
| `score` | `int` | pontuação acumulada na partida (RF18) |
| `duration_seconds` | `int` | duração máxima de 120 segundos |
| `status` | `enum` (`MatchStatus`) | `in_progress` ou `finished` |
| `started_at` | `DateTime` | |
| `ended_at` | `DateTime`, opcional | |
| `current_question_id` | `FK → questions.id`, opcional | pergunta servida e ainda sem resposta: a única que a partida aceita responder, e a que `next-question` devolve até ser respondida |

## `match_answers`

Confiabilidade (0 a 100) dada pelo jogador a uma questão durante a partida.

| Coluna | Tipo | Notas |
|---|---|---|
| `match_id` | `FK → matches.id` | indexado |
| `question_id` | `FK → questions.id` | |
| `answer` | `bool` | leitura binária da resposta (`reliability >= 50`), mantida para relatórios |
| `reliability` | `int`, opcional | valor de 0 a 100 marcado na barra |
| `is_correct` | `bool` | distância até `reliability_reference` dentro da tolerância (`game_rules.py`) |

## `user_progress`

Progresso consolidado do jogador na jornada (`progress.py`), um registro por jogador.

| Coluna | Tipo | Notas |
|---|---|---|
| `user_id` | `FK → users.id`, único | uma linha por jogador |
| `current_level` | `int` | |
| `highest_level` | `int` | maior nível já alcançado |
| `total_score` | `int` | soma histórica de pontos |
| `matches_played` | `int` | |
| `updated_at` | `DateTime` | atualizado a cada mudança |

## Relações entre tabelas

- `questions.category_id → categories.id` (N para 1)
- `matches.user_id → users.id` (N para 1)
- `matches.level_id → levels.id` (N para 1)
- `matches.current_question_id → questions.id` (N para 1, opcional)
- `match_answers.match_id → matches.id` (N para 1)
- `match_answers.question_id → questions.id` (N para 1)
- `user_progress.user_id → users.id` (1 para 1)

Nenhuma tabela liga diretamente `questions` a `levels`: a dificuldade do tabuleiro (nível)
e o conteúdo da pergunta (categoria) variam de forma independente.
