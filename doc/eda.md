# Análise exploratória dos dados

Resumo da primeira análise, que comparou o Fake.br e o Fakepedia e levou ao descarte do
Fakepedia. O notebook dela (`notebooks/eda.ipynb`) saiu do repositório porque o Fakepedia
não é mais baixado; ele continua no histórico do Git. A EDA da base atual está em
`pesquisa/notebooks/eda_1_datasets.ipynb` e `pesquisa/notebooks/eda_2_conjunto.ipynb`.

## As bases

| | Fake.br-Corpus | Fakepedia |
|---|---|---|
| Notícias | 3.600 fake + 3.600 true, pareadas por assunto | 5.201 boatos (só fake) |
| Campos úteis | texto, categoria, data, URL, 21 métricas linguísticas | título, texto do boato, categoria, entidades, link da checagem |
| Período | 2016–2018 (cauda até 2009) | sem data; entidades indicam até pelo menos 2020 (Covid-19) |
| Categorias | 58% política; economia, religião e ciência somam < 3% | política, brasil, saúde, mundo, tecnologia, entretenimento… |

`pesquisa/data/processed/dataset.jsonl` junta as duas bases num esquema único: `id`, `base`,
`rotulo`, `titulo`, `texto`, `categoria`, `data`, `autor`, `url`, `par_id` e `metricas`.

## Qualidade

- **Fakepedia tem 39% de linhas duplicadas** (8.517 linhas para 5.201 URLs). O preparo
  deduplica por URL. 12% dos boatos têm só título, sem texto.
- **As datas do Fake.br vêm em 19 formatos**. Foram normalizadas para ISO; só 3 com ano
  inválido (`0201`) ficaram nulas.
- **`n_links` no Fake.br é `None` em 1.393 verdadeiras e em nenhuma falsa.** A ausência
  do valor denuncia a classe, então a métrica não deve ser usada.

## Atalhos que um classificador aprenderia

1. **Tamanho.** A verdadeira é mais longa que a falsa em 98% dos pares (mediana de 918
   × 157 palavras). O próprio corpus oferece `size_normalized_texts/` para contornar isso,
   e é a versão que `preparar_dados.py` lê.
2. **Fonte.** 93% das falsas vêm de diariodobrasil.org; as verdadeiras, de G1 (64%) e
   Estadão (33%). Só as verdadeiras têm autor (98% × 2%). "G1", horários ("14h") e
   URLs no texto (3,2% × 0,1%) vazam a fonte.
3. **Tempo.** A mediana das verdadeiras fica ~10 meses depois da das falsas.
4. **Métricas dependentes de tamanho.** `diversidade` (types/palavras) e o tamanho médio
   de sentença têm os maiores efeitos, mas são consequência do comprimento do texto.

Descontado o tamanho, as diferenças de estilo são **moderadas** (d de Cohen ≈ 0,5):
mais CAIXA ALTA (1,6% × 1,0% das palavras) e mais verbos nas falsas, menos pausas.
**Emotividade, adjetivos, pronomes e erros de ortografia praticamente não diferem.**

## Recomendações

- Treinar com `size_normalized_texts` (ou truncar por par) e sem URL, domínio, autor ou
  data como features. Remover URLs e assinaturas e normalizar espaços.
- Dividir treino e teste por `par_id`, para que as duas notícias de um par fiquem no
  mesmo lado.
- Usar o Fakepedia como teste fora da distribuição: outra época (Covid-19, governo
  Bolsonaro) e outro formato (mensagens curtas de redes sociais). Como é só *fake*,
  acompanhar o recall.
- **Para o jogo:** os títulos do Fakepedia são afirmações curtas e autocontidas (mediana
  de 67 caracteres), com categoria e link de checagem do Boatos.org, o que os torna bons
  candidatos a questões. Para questões verdadeiras, falta uma fonte equivalente.
- Não ensinar "fake news são mais emotivas" como dica: a base não sustenta isso. CAIXA
  ALTA sim.
