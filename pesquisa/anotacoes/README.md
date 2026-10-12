# Anotações da equipe

Rótulos de tipo de conteúdo, veracidade e sinais de manipulação feitos pela equipe (#5),
seguindo `doc/guia-classificacao.md` §7.

- `rodada-NN.csv`: uma linha por item e anotador (`id`, `anotador`, `tipo`,
  `tipo_secundario`, `veracidade`, os 4 sinais e `observacao`).
- `adjudicacao.csv`: decisão final nas discordâncias, com as mesmas colunas (o `anotador`
  pode ficar vazio).
- `consolidado.csv`: rótulo final por `id`, gerado por `consolidar_anotacoes.py` e lido por
  `pesquisa/dados/preparar_dados.py` (`origem_rotulo=equipe`) e `pesquisa/ml/dados.py`.

**Só `id` e rótulos vão para o Git, nunca o texto** (os textos são dos veículos). Nenhum
item de `split_produto=teste` é anotado para treino.

## Fluxo de uma rodada

1. Sortear os itens e gerar uma planilha por anotador, com o texto, em
   `pesquisa/data/anotacao/` (fora do Git). Os primeiros 20% (`--sobreposicao`) vão para
   todos, para medir a concordância:
   ```bash
   python pesquisa/dados/sortear_anotacao.py --rodada 1 --anotadores ana bruno --itens 600
   ```
2. Cada um preenche a sua planilha (Excel ou Google Sheets, salvando em CSV). O `tipo` vem
   pré-preenchido pelo veredito da agência, quando houver: confirmar ou corrigir. Sinais
   em branco contam como 0.
3. Importar as planilhas preenchidas. O script confere os valores, tira o texto e grava
   `rodada-NN.csv`:
   ```bash
   python pesquisa/dados/consolidar_anotacoes.py importar --rodada 1 pesquisa/data/anotacao/rodada-01-*.csv
   ```
4. Medir a concordância e gerar o consolidado:
   ```bash
   python pesquisa/dados/consolidar_anotacoes.py
   ```
   Imprime, por campo, a concordância simples, o kappa de Cohen de cada par e o alfa de
   Krippendorff. Concordância baixa: ajustar o guia antes de anotar o resto. Os itens sem
   maioria vão para `pesquisa/data/anotacao/pendentes.csv`; a decisão da reunião entra em
   `adjudicacao.csv` e o passo 4 roda de novo.
5. Registrar o kappa na issue e regerar o `dataset.jsonl` (`make dados`).
