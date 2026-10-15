# Avaliação nas notícias do jogo

> **Status:** coleta e medição prontas (`make coletar-avaliacao` e `make avaliar-jogo`). O
> conjunto cresce a cada coleta; os números abaixo são da primeira.

## Por quê

A validação do dataset mede o modelo em checagens e manchetes de anos atrás, com 2% de
verdadeiros. No jogo, as questões são notícias recentes da importação diária (Fact Check API,
GNews e Agência Brasil), metade verdadeiras, e o classificador recebe a afirmação extraída pela
LLM. Um modelo bom na validação pode errar quase todas as verdadeiras do jogo. Esta avaliação
mede o modelo no que o jogador responde.

O banco de 250 questões da branch `feat/expansao-banco-250-questoes` não serve para isso: são
afirmações de livro didático escritas por IA ("A tabela periódica organiza os elementos..."),
não notícias, e não passaram por auditoria (`doc/auditoria-factual-afirmacoes.md`, na branch
`feat/ml-treinamento-multiclasse-e-tema`, só confere as 11 que já existiam).

## Como roda

```bash
make coletar-avaliacao                                   # uma coleta (~250 notícias, ~30 min)
make avaliar-jogo MODELO="models/2026-11/referencia models/2026-11/bert"
```

- **Coleta** (`api/app/jobs/coletar_avaliacao.py`, no container da API): os mesmos provedores,
  normalização, descartes e extração de afirmação da importação
  (`services/noticias_service.py`), sem gravar no banco. Só entram notícias publicadas a partir
  de 07/10/2026 (`--desde`), o dia seguinte ao fim do dataset de treino, e checagens com lado no
  jogo (enganoso fica de fora). Cada coleta vira `pesquisa/data/avaliacao/jogo-AAAA-MM-DD-HHMM.jsonl`
  (fora do Git), com a manchete (`statement`), a primeira afirmação extraída (`claim_text`) e o
  gabarito (`is_true`), mais a `veracidade` em três níveis. As checagens enganosas, que a
  importação descarta (o jogo é binário, decisão 01 em aberto), entram como falsas ("não é
  verdade"), com o acerto à parte; as de veredito ambíguo ficam de fora. A extração usa `LLM_*`
  do `.env`; o alvo força `LLM_PROVIDER=openai` e `NOTICIAS_SEM_POLITICA=false` (política entra
  na avaliação, mesmo que o jogo a tire).
- **Cota:** o GNews gratuito aceita 100 pedidos por dia, e cada coleta usa 6 (até 60
  manchetes); a Fact Check API, 11 (um por agência); a Agência Brasil não tem cota.
- **Medição** (`pesquisa/ml/avaliar_jogo.py`): junta as coletas sem repetir URL nem manchete,
  tira o que já está no dataset (mesma URL, texto curto ou título, em qualquer split) e dá a
  cada modelo o texto que a API daria (manchete no modelo do texto original; afirmação extraída
  no padronizado e no híbrido), com a mesma `limpar()` e a mesma calibração da API.

## Medidas

O jogo é binário e o modelo é ordinal: a verdadeira é acerto quando a classe mais provável é
`verdadeiro`; a falsa, quando é `falso` ou `enganoso`.

| Medida | O que diz |
|---|---|
| Acerto | % de notícias acertadas, na proporção da coleta |
| Acerto balanceado | média do acerto nas verdadeiras e nas falsas; não depende da proporção |
| AUC da nota | se a nota de confiabilidade (100 × (P1 + P2) / 2, a barra do jogo) ordena verdadeiras acima de falsas, qualquer que seja o corte |
| Corte cruzado | acerto balanceado com o corte na nota escolhido numa metade (hash do `id`) e medido na outra: quanto o modelo acertaria com a régua ajustada ao jogo |

## Resultados

Coletas de 15/10/2026: 125 notícias (14 falsas do Fact Check, 35 verdadeiras do GNews e 76 da
Agência Brasil), nenhuma no dataset de treino. Com só 14 falsas, os números das falsas
oscilam muito; o Boatos.org entra nas próximas coletas.

| Modelo | Calibração | Acerto | Verdadeiras | Falsas | Balanceado | AUC nota | Corte cruzado |
|---|---|---|---|---|---|---|---|
| `atual` (referência, dataset de 07/10) | nenhuma | 22,4% | 12,6% | 100% | 56,3% | 0,901 | 78,6% |
| `referencia` (dataset de 15/10) | Platt + proporção do jogo | 65,6% | 61,3% | 100% | 80,6% | 0,948 | 85,5% |
| `bert` | Platt + proporção do jogo | 81,6% | 82,0% | 78,6% | 80,3% | 0,902 | 83,6% |

Sem ajuste, os modelos chamam de falso quase toda manchete verdadeira: aprenderam a proporção
da validação (~2,6% de verdadeiros), e no jogo elas são metade. A correção de proporção em
`calibrar.py --proporcao-verdadeiros 0.5` (ajustada só na validação; as notícias só medem)
leva o BERT a ~80% de acerto balanceado.

**Limiares de abstenção.** Com as metas antigas (no máximo 5% dos verdadeiros virando falso
no admin e 1% no jogador, na validação), quase tudo vira `incerto` no jogo: no BERT, 83% e 86%
das notícias, e as poucas que sobram (21 e 17) ficam 100% certas. Meio-termo adotado em
15/10/2026, ainda escolhido na validação: metas de **20% (admin) e 10% (jogador)**
(`--taxa-admin 0.2 --taxa-jogador 0.1`). A validação tem só ~57 verdadeiros, então cada passo
da meta anda ~1,75 ponto.

| Modelo | Uso | Limiar | Incerto no jogo | Acerto quando decide |
|---|---|---|---|---|
| `bert` | admin | 0,50 | 22% | 94% (97 notícias) |
| `bert` | jogador | 0,58 | 50% | 98% (63 notícias) |
| `referencia` | admin | 0,50 | 14% | 67% (108 notícias) |
| `referencia` | jogador | 0,59 | 70% | 79% (38 notícias) |

### Modelos no texto híbrido (15/10/2026)

Treinados com 4.232 dos 10.994 registros de treino sem texto curto já padronizados (a amostra
de `--limite 4000`), calibrados para o jogo como os anteriores (proporção 0,5; metas de 20% e
10%). Mesmas 125 notícias; nos híbridos, a entrada é a afirmação extraída.

| Modelo | Acerto | Verdadeiras | Falsas | Balanceado | AUC nota | Corte cruzado |
|---|---|---|---|---|---|---|
| `bert` (original, publicado) | 81,6% | 82,0% | 78,6% | 80,3% | 0,902 | 83,6% |
| `referencia-hibrido` | 60,0% | 56,8% | 85,7% | 71,2% | 0,765 | 67,4% |
| `bert-hibrido` | 80,0% | 78,4% | 92,9% | 85,6% | 0,896 | 82,8% |

| Modelo | Uso | Limiar | Incerto no jogo | Acerto quando decide |
|---|---|---|---|---|
| `bert` (publicado) | jogador | 0,58 | 50% | 98% (63 notícias) |
| `bert-hibrido` | admin | 0,45 | 4% | 82% (120 notícias) |
| `bert-hibrido` | jogador | 0,49 | 22% | 93% (97 notícias) |
| `referencia-hibrido` | jogador | 0,58 | 49% | 73% (64 notícias) |

O BERT híbrido decide em 78% das notícias para o jogador (contra 50% do publicado), com 93% de
acerto. Com 14 falsas, a diferença nas falsas (13 × 11 acertos) ainda não é conclusiva.

**Cuidado:** todas as falsas são alegações de checagem e todas as verdadeiras são manchetes.
Parte do AUC pode vir do formato (cara de boato × cara de manchete), e não da veracidade, o
atalho que a padronização quer tirar. A comparação com o modelo híbrido, em que as duas
passam pela mesma extração, vai dizer quanto.
