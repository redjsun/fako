# Dataset de verdadeiros confiáveis

Issue #6 (épico E2). As matérias de portais coletadas por `coletar_verdadeiras.py` não
entram no dataset selecionado como estão: o rótulo "verdadeiro" delas é **suposição**. Foram
publicadas, mas ninguém as checou. Uma manchete pode ter erro factual, ser exagerada ou
**relatar** uma afirmação falsa ("Deputado diz que vacina causa infertilidade": a matéria
está certa, a afirmação é falsa). Este documento define quando um verdadeiro é confiável.

## Prioridade 1: verdadeiros checados

Veredito "verdadeiro", "comprovado" ou "fato" de agência (`origem_rotulo=agencia`). É o
melhor rótulo, mas há poucos: as agências checam o que é suspeito.

Fact Check API, coleta de 07/10/2026 (12.511 checagens), por agência:

| Agência | Verdadeiro | Enganoso | Falso |
|---|---:|---:|---:|
| eleicoes.apublica.org | 42 | 26 | 46 |
| checamos.afp.com | 16 | 1.065 | 3.070 |
| noticias.uol.com.br | 14 | 302 | 1.295 |
| aosfatos.org | 12 | 128 | 1.315 |
| projetocomprova.com.br | 5 | 167 | 157 |
| bol.uol.com.br | 4 | 84 | 547 |
| estadao.com.br | 4 | 1.433 | 1.346 |
| www1.folha.uol.com.br | 3 | 103 | 107 |
| outras (Tatu, O Globo, Pública) | 3 | 0 | 89 |
| **total** | **103** | | |

Quase metade é de 2018 (47); de 2024 em diante são 9. Lupa, G1 e e-farsas não aparecem na
API (`coletar_factcheck.py --descobrir`). Somam-se os ~600 verdadeiros checados da FakenewsBR,
quase todos do e-farsas (`pesquisa/notebooks/eda_1_datasets.ipynb`). Não bastam para
equilibrar as classes, e menos ainda nos anos de validação e teste.

## Prioridade 2: matérias de portal verificadas

Matérias dos 9 portais de `coletar_verdadeiras.py` (API WordPress aberta e `robots.txt` sem
opt-out de IA, conferidos em 01/10/2026) que passam nos filtros e cujo veículo é aprovado na
auditoria manual. Recebem `origem_rotulo=portal_verificado` (peso 1,0 em
`ORIGEM_ROTULO_PESO`, até a validação dizer outra coisa).

### Filtros automáticos

`motivo_filtro_portal` em `pesquisa/dados/preparar_dados.py`, sobre o título (`texto_curto`)
e a URL:

| Filtro | Regra | Fora (de 21.295) |
|---|---|---:|
| Relata fala | verbo de declaração no título (diz, afirma, nega, critica, acusa...), "Segundo X" ou aspas | 5.050 |
| Opinião, vídeo, ao vivo ou publicidade | seção da URL (`/opiniao/`, `/coluna/`, `/blog/`, `/video/`, `/ao-vivo/`, `/artigos/`, `/entrevista/`, `/publieditorial/`...) ou título começando com "Ao vivo", "Opinião", "Análise"... | 560 |
| Pergunta | título terminado em "?" | 298 |

Passam 15.313 matérias (72%), de 1.400 a 1.900 por veículo. O filtro de aspas é
conservador: também tira títulos com aspas de destaque ("saidinha"), que não são fala.

Ainda não implementado: tirar matérias muito parecidas com uma checagem falsa ou enganosa,
pelo índice de evidências (#15), e usar a extração com `quem_disse` (#19) no lugar da lista
de verbos.

**Política editorial.** Antes de aprovar um veículo na auditoria, conferir se ele publica
política editorial e de correções. Registrar a URL na issue #6.

### Auditoria manual

`pesquisa/dados/auditar_verdadeiras.py`:

1. `sortear --itens 200 --revisores A B`: 200 matérias que passam nos filtros, fora do
   teste, alternando os veículos (~22 por veículo), em sorteio reproduzível (hash do `id` com
   prefixo `auditoria-`). Cada revisor recebe todos os itens numa planilha em
   `pesquisa/data/auditoria/`, com título e URL.
2. Cada revisor marca `problema`: `nenhum`, `erro_factual`, `exagero`, `relata_fala_falsa`
   ou `opiniao`, com a justificativa em `observacao`.
3. `importar pesquisa/data/auditoria/auditoria-*.csv`: grava
   `pesquisa/anotacoes/auditoria-verdadeiras.csv`, só com `id`, `fonte`, `revisor`,
   `problema` e `observacao`. O título não vai para o Git.
4. `medir`: imprime o ruído (proporção de itens com problema) no total e por veículo, com
   intervalo de confiança de Wilson de 95% (com n = 200 e ruído de 5%, ±3 p.p.), e o kappa
   de Cohen entre os revisores. Grava `pesquisa/anotacoes/veiculos-verificados.csv`.

### Critério de aceite

- Um item tem problema se **algum** revisor marcou (conservador).
- Veículo com ruído acima de **10%** (o dobro do limite) sai.
- O dataset é aceito se o ruído dos veículos que ficam é de no máximo **5%**
  (`LIMITE_RUIDO`). Se não for, nenhum veículo é aprovado.
- Itens marcados com problema na auditoria nunca viram `portal_verificado`.

## No `dataset.jsonl`

`verificar_portais` (em `preparar_dados.py`) lê `veiculos-verificados.csv`. Sem esse
arquivo, nada muda: as matérias continuam `portal` e vão para `reserva`. As verificadas
seguem a divisão por data dos portais (treino até 2023, validação em 2024, teste de 2025 em
diante). Em `equilibrar`, elas completam os verdadeiros de cada split até o número de
falsos; o que passa disso vira `reserva`.

Simulação com os 9 veículos aprovados (07/10/2026):

| Split | Falso | Enganoso | Verdadeiro | dos quais portal verificado |
|---|---:|---:|---:|---:|
| treino | 12.512 | 1.541 | 12.512 | 5.349 (2018–2023) |
| validação | 1.446 | 964 | 1.446 | 1.014 (2024) |
| teste | 1.638 | 1.092 | 1.638 | 1.197 (2025–2026) |

Hoje, sem os portais, são 7.163, 432 e 441 verdadeiros, e os de validação e teste são quase
todos do Fake.br (2016–2018).

## Limites

- **Gênero de texto.** Título de portal não tem a mesma cara de uma alegação checada. O
  teste de atalho (`pesquisa/ml/atalho.py`) e as métricas por `origem_rotulo` medem quanto o
  modelo aprende "é manchete" em vez de "é verdade".
- **Questões do jogo.** A #33 decide se `portal_verificado` pode virar questão com gabarito.
  Se puder, a validação de #23 precisa de uma exceção explícita para essa origem.
