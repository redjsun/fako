# Relatório técnico: classificador de veracidade do FAKO

Entrega de documentação e validação do modelo (desafio 1, grupo 11). Cobre a preparação dos
dados e o treino, o critério de escolha da abordagem, as métricas e a análise dos
resultados, os desafios e os aprendizados. O código para carregar, executar e avaliar o
modelo está em `pesquisa/notebooks/avaliacao_modelos.ipynb`.

## Resumo

- **Tarefa:** dada uma afirmação curta em português, dizer se ela é `falso`, `enganoso` ou
  `verdadeiro`, tratados como **escala ordinal**, com uma nota de 0 a 100 e a confiança.
  O resultado alimenta o jogo FAKO (o jogador avalia afirmações) e o painel do admin.
- **Modelo:** TF-IDF de palavras e de caracteres + regressão logística **ordinal**
  (método de Frank e Hall), com o hiperparâmetro `C` escolhido na validação. Arquivo:
  `models/2026-11/referencia/referencia.joblib`.
- **Resultado no teste (checagens de 2025 em diante, nunca vistas):** F1 macro **0,411** (validação 0,426), AUC macro
  0,630 e MAE da nota 25 pontos. O resultado mais importante é negativo: **no teste, o
  modelo fica abaixo do teste de atalho** (AUC macro 0,630 × 0,664). Ou seja, ainda não
  aprendeu conteúdo que generalize além da forma do texto (seção 3).

## 1. Preparação dos dados

### 1.1 Bases

| Base | Rótulos | Formato do texto curto | Período |
|---|---|---|---|
| Fake.br-Corpus | falso e verdadeiro, pareados por assunto | texto completo (sem texto curto) | 2016–2018 |
| FakeRecogna | falso (Boatos.org) e verdadeiro (G1, UOL, Extra) | alegação do boato / título | 2019–2021 |
| FakeTrue.Br | falso e verdadeiro, pareados | alegação / título | 2019–2021 |
| Google Fact Check Tools API | falso, enganoso e verdadeiro (10 agências) | alegação checada | 2018 em diante |
| FakenewsBR | falso, enganoso e verdadeiro (sub-bases de agência) | alegação | 2010 em diante |
| Portais (9 veículos) | verdadeiro **por suposição** | título da matéria | 2018 em diante |

`pesquisa/dados/baixar_dados.sh` baixa as bases públicas; os coletores
(`coletar_factcheck.py`, `coletar_verdadeiras.py`) rodam à parte, com cache e ~1
requisição/s. `pesquisa/dados/preparar_dados.py` junta tudo em `dataset.jsonl`, com um
esquema único (`id`, `base`, `veracidade`, `texto_curto`, `data`, `fonte`, `origem_rotulo`,
`veredito_original`, `tipo_sugerido`, splits).

### 1.2 Rótulos

- O veredito de cada agência é normalizado para a escala de três níveis: "falso",
  "montagem", "predominantemente falso" → `falso`; "enganoso", "distorcido", "fora de
  contexto", "exagerado", "impreciso" → `enganoso`; "verdadeiro", "comprovado", "fato" →
  `verdadeiro`. Sátira e vereditos ambíguos ("sem provas", "insustentável") ficam fora.
- **Verdadeiros confiáveis** (`doc/dataset-verdadeiras.md`): matérias de portal não são
  usadas como verdadeiro, porque ninguém as checou e uma manchete pode relatar uma
  afirmação falsa. Os portais vão para o split `reserva`.
- **Anotação da equipe** (`pesquisa/anotacoes/`): uma amostra sorteada foi rotulada à mão
  (veracidade e tipo de conteúdo); quando existe, o rótulo da equipe substitui o da base.
  `dados.py` dá a cada exemplo um peso por `origem_rotulo` (agência, equipe, base pública).

### 1.3 Limpeza e atalhos

A EDA (`doc/eda.md`, `pesquisa/notebooks/eda_1_datasets.ipynb` e `eda_2_conjunto.ipynb`)
mostrou que **cada classe vem de fontes com "cara" própria**: no Fake.br, a notícia
verdadeira é mais longa em 98% dos pares, 93% das falsas vêm de um só site, e nomes de
veículo, horários e URLs vazam a fonte. Por isso:

- só o texto entra no modelo; fonte, autor e data **nunca** são variáveis;
- `dados.limpar()` tira URLs, créditos de veículo no início e no fim do texto ("G1 -",
  "(Estadão)") e normaliza espaços;
- o Fake.br é usado na versão de tamanho normalizado;
- o **teste de atalho** (`pesquisa/ml/atalho.py`) treina um modelo só com a forma do texto
  (pontuação, maiúsculas, tamanho) e dá o piso que qualquer modelo precisa superar. Ele
  chega a AUC macro ≈ 0,66 na validação: a forma sozinha já separa bastante as classes.

### 1.4 Divisão (protocolo B, `split_produto`)

| Split | Regra |
|---|---|
| `treino` | bases pareadas (80%, por par); checagens de 2016 a 2023 |
| `validacao` | pareadas (10%); checagens de 2024 |
| `teste` | pareadas (10%); checagens de 2025 em diante |
| `reserva` / `fora` | portais, sobras do balanceamento, itens sem data e quase-duplicatas |

A divisão por data imita o uso real (o modelo classifica notícias depois do treino) e mede
o envelhecimento. As quase-duplicatas de itens do treino saem da validação e do teste.
Hiperparâmetros e escolha de modelo usam **só a validação**; o teste foi olhado uma vez por
modelo, no notebook.

Contagens efetivas após a limpeza (dataset `8dc32332…`):

| Split | falso | enganoso | verdadeiro | total |
|---|---:|---:|---:|---:|
| treino | 7.221 | 1.539 | 1.458 | 10.218 |
| validacao | 1.187 | 964 | 57 | 2.208 |
| teste | 1.474 | 1.092 | 96 | 2.662 |

A validação e o teste são quase só checagens de agência, com pouquíssimos verdadeiros
(2,6% e 3,6%).

### 1.5 Padronização do texto pela LLM (preparada, não usada nesta entrega)

No uso real, o classificador recebe afirmações extraídas por uma LLM do texto do usuário,
enquanto no treino os verdadeiros são manchetes e os falsos são alegações de checador.
`pesquisa/ml/padronizar.py` passa o treino pelo mesmo prompt (`extrair_afirmacoes_v1.txt`)
com o **Qwen3 8B pelo Ollama**, local, com cache por `id` e versão do prompt
(`doc/padronizacao.md`). A configuração está pronta (`.env`: `LLM_MODEL=qwen3:8b`), mas a
rodada completa em CPU leva horas; o modelo desta entrega usa o texto original, e a
comparação original × padronizado fica como próximo passo (`configs/referencia-padronizado.toml`).

## 2. Treino e critério de escolha da abordagem

### 2.1 Por que ordinal

Nem toda notícia é inteiramente verdadeira ou falsa, e o erro "falso → verdadeiro" é muito
pior que "falso → enganoso". Em vez de três classes soltas, o modelo aprende **duas
fronteiras**: P1 = P(veracidade > falso) e P2 = P(veracidade > enganoso). Daí saem
P(falso) = 1 − P1, P(enganoso) = P1 − P2, P(verdadeiro) = P2 e a nota = 100 × (P1 + P2) / 2.
Com poucos enganosos, os milhares de falsos e verdadeiros também ensinam onde fica o meio.

### 2.2 O modelo: TF-IDF + regressão logística ordinal

`pesquisa/ml/treinar_referencia.py`, configuração `pesquisa/ml/configs/referencia.toml`.

1. **Representação:** TF-IDF de palavras (unigramas e bigramas) somado ao TF-IDF de
   n-gramas de caracteres (3 a 5, dentro das palavras), com `min_df = 3`, `max_df = 0,9` e
   TF sublinear. Os n-gramas de caracteres pegam variações de grafia e flexões do português.
   O vocabulário é ajustado **só no treino** (94.598 variáveis).
2. **Fronteiras:** duas regressões logísticas sobre a mesma matriz, uma para cada fronteira
   (método de Frank e Hall). P2 é cortada em P1 para as probabilidades nunca ficarem negativas.
3. **Desbalanceamento:** `class_weight="balanced"` em cada fronteira, multiplicado pelo
   peso por origem do rótulo de `dados.py` (rótulo de agência e da equipe valem mais que o
   de base pública).
4. **Hiperparâmetro:** a regularização `C` é escolhida numa grade (0,25; 0,5; 1; 2; 4; 8; 16)
   pelo F1 macro das três classes na validação. Venceu **C = 4**.
5. **Saídas:** `referencia.joblib` (só objetos do scikit-learn: vetorizador e as duas
   fronteiras, para a API carregar sem o código da pesquisa), `previsoes.jsonl` e
   `config.json`, com o hash do dataset e da configuração para reproduzir o resultado.

Treino em 65 s numa CPU comum, com 10.218 exemplos; inferência de ~2 ms por frase.

### 2.3 Critérios de seleção da abordagem

- **Piso honesto antes de modelos maiores.** Com o atalho de forma tão forte nos dados
  (seção 1.3), era preciso primeiro um modelo simples e reproduzível para saber quanto o
  *conteúdo* acrescenta. Sem ele, não dá para dizer se um modelo maior ganhou por entender
  o texto ou por reconhecer melhor a fonte.
- **Viável na infraestrutura que temos.** Treina em um minuto em CPU, sem GPU, e cabe na
  API (2 MB compactado, milissegundos por frase). O ajuste fino do BERTimbau em CPU não
  terminou nem uma época em uma hora nesta máquina.
- **Explicável.** Num modelo linear, a contribuição de cada palavra é exata
  (`contribuicoes()` em `treinar_referencia.py`), o que permite ao admin auditar por que uma
  afirmação recebeu a nota, coisa importante num jogo educativo.
- **Ordinal em vez de binário ou multiclasse**, pela natureza do problema (seção 2.1).
- **Escolhas só na validação.** `C` e configuração foram decididos pelo F1 macro da
  validação (2024). F1 macro porque as classes são desbalanceadas e `verdadeiro` é rara;
  o teste (2025+) foi olhado uma única vez, no notebook. O critério de aceite para uso no
  produto é ter **margem positiva sobre o teste de atalho**.

## 3. Métricas e análise dos resultados

Métricas (todas em `pesquisa/ml/avaliar.py`, por split, base, fonte e ano):

| Métrica | O que mede |
|---|---|
| F1 por classe e F1 macro | acerto equilibrado entre as três classes |
| AUC por fronteira e AUC macro | separação, sem depender de limiar |
| MAE da nota (0–100) e kappa quadrático | se o erro respeita a ordem da escala |
| Recall de falsos com 1% e 5% de alarme falso | falsos pegos sem marcar verdadeiros como falsos (o erro mais caro no jogo) |
| ECE e diagrama de confiabilidade | se a confiança corresponde ao acerto |
| Margem sobre o atalho | quanto o modelo supera um modelo só de forma |

### 3.1 Referência TF-IDF: validação e teste

| Split | n | F1 macro | F1 falso | F1 enganoso | F1 verdadeiro | AUC >falso | AUC >enganoso | AUC macro | MAE nota | kappa quad. | recall falsos @5% | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| validação (2024) | 2.208 | 0,426 | 0,689 | 0,361 | 0,229 | 0,638 | 0,727 | 0,667 | 23,7 | 0,155 | 0,198 | 0,132 |
| teste (2025+) | 2.662 | 0,411 | 0,679 | 0,346 | 0,208 | 0,580 | 0,729 | 0,630 | 25,2 | 0,131 | 0,096 | 0,138 |

Escolha do `C` na validação (F1 macro): 0,25 → 0,300; 0,5 → 0,346; 1 → 0,388; 2 → 0,422;
**4 → 0,426**; 8 → 0,420; 16 → 0,419.

### 3.2 Margem sobre o teste de atalho

| Split | AUC macro do modelo | AUC macro do atalho | Margem |
|---|---:|---:|---:|
| validação | 0,667 | 0,663 | +0,004 |
| teste | 0,630 | 0,664 | **−0,034** |

### 3.3 Por base (teste)

| Base | n | F1 macro | AUC macro | MAE nota |
|---|---:|---:|---:|---:|
| factcheck | 2.285 | 0,356 | 0,556 | 24,8 |
| fakenewsbr | 197 | 0,411 | 0,683 | 41,2 |
| fakerecogna | 138 | 0,989 | — | 12,1 |
| faketrue | 42 | 0,937 | — | 17,0 |

### 3.4 Análise

- **O modelo está no nível do atalho.** Na validação, a margem é praticamente zero, e no
  teste é negativa. Com o texto original, o TF-IDF aprende sobretudo o *gênero* do texto
  (alegação de checador × manchete × mensagem), não a veracidade. É o que a EDA previa e o
  motivo da padronização pela LLM (seção 1.5).
- **Os números altos são enganosos.** FakeRecogna e FakeTrue.Br passam de 0,93 de F1, mas
  só têm uma classe no recorte e o modelo reconhece o estilo da base. Nas checagens
  (`factcheck`), que são o caso real do jogo, o F1 macro é 0,356 e a AUC, 0,556.
- **`falso` é a única classe razoável** (F1 ≈ 0,68). `enganoso` (0,35) se confunde com
  `falso`, porque as duas são alegações de checador com o mesmo estilo, e `verdadeiro`
  (0,21) tem só 57 e 96 exemplos na validação e no teste.
- **A ordem é pouco respeitada:** kappa quadrático de 0,13 e erro médio de 25 pontos na
  nota (meia classe).
- **Recall de falsos com 5% de alarme falso cai de 0,20 para 0,10 no teste:** para não
  marcar verdadeiros como falsos, o modelo deixa passar quase todos os falsos. Não serve
  para afirmar "falso" sozinho ao jogador.
- **Calibração moderada** (ECE ≈ 0,13–0,14): a confiança erra em média 13 pontos
  percentuais. Os limiares de `incerto` precisam levar isso em conta.
- **Envelhecimento pequeno:** nas checagens, o F1 macro passa de 0,411 (2024) para 0,401
  (2025+). O problema principal é o atalho, não o tempo.
- **Em frases novas, o modelo hesita entre falso e enganoso** e quase nunca diz
  `verdadeiro`, mesmo em frases neutras de serviço (notebook, seção 8). É o reflexo da
  pouca presença de verdadeiros checados.

**Conclusão:** a referência cumpre o papel de piso reprodutível e de pipeline de ponta a
ponta (dados → treino → previsões → avaliação comum), mas **não está pronta para dar
veredito ao jogador**: não passa no critério de aceite (margem sobre o atalho). No produto,
deve entrar com limiar alto de `incerto` e passar pela revisão do admin. Para melhorar de
verdade, os próximos passos (seção 6) atacam a causa, os dados, antes da arquitetura.

## 4. Principais desafios

- **Atalhos nos dados.** Cada classe vem de fontes e gêneros de texto diferentes (manchete ×
  alegação de checador × mensagem de rede social). O modelo de forma, sem conteúdo, já chega
  a AUC ≈ 0,66. Boa parte do trabalho foi medir isso (teste de atalho, métricas por fonte) e
  limpar o que vaza a fonte.
- **Poucos verdadeiros confiáveis.** Agências checam o que é suspeito: na Fact Check API,
  só 103 de 12.511 checagens são "verdadeiro", e só 9 de 2024 em diante. A validação tem
  57 verdadeiros; o F1 dessa classe é instável e puxa o F1 macro para baixo.
- **Rótulo por suposição.** Matérias de portal não são verdade checada e foram tiradas do
  treino, o que agravou a falta de verdadeiros.
- **Mudança de distribuição no tempo.** Treino até 2023, validação em 2024 e teste em 2025:
  assuntos, personagens e o mix de agências mudam (só a Fact Check API traz enganosos
  recentes).
- **Bases muito diferentes entre si.** Fake.br (textos longos, 2016–2018), FakeRecogna,
  checagens: foi preciso um esquema único, normalização de veredito e de datas (19 formatos
  no Fake.br) e deduplicação.
- **Infraestrutura.** Sem GPU, modelos de linguagem maiores (ajuste fino do BERTimbau) e a
  padronização pela LLM (Qwen3 8B local) ficaram lentos demais para esta entrega. Duas
  linhas de código paralelas (`ml/` e `pesquisa/ml/`) também precisaram ser integradas.

## 5. Aprendizados

- **Medir o piso antes de comemorar.** Sem o teste de atalho, um F1 alto nas bases públicas
  (FakeRecogna, FakeTrue.Br passam de 0,95) pareceria sucesso; é o modelo reconhecendo a
  fonte.
- **O rótulo importa mais que o modelo.** A maior parte do ganho possível está em mais
  verdadeiros checados e em rótulos da equipe, não em trocar a arquitetura.
- **Dividir por tempo dá números honestos.** A divisão aleatória misturaria as mesmas
  checagens e assuntos entre treino e teste.
- **Uma porta única para os dados e um avaliador comum** (`dados.py`, `avaliar.py`,
  configurações TOML com hash do dataset) permitem comparar modelos futuros de forma justa e
  reproduzir cada resultado.
- **Ordinal em vez de binário** reflete melhor o problema (meias-verdades) e dá ao jogo uma
  nota, não só um rótulo.
- **Calibração e incerteza fazem parte do produto:** um jogo educativo não deve afirmar
  "falso" com 90% de confiança quando acerta 60%; daí o ECE e os limiares de `incerto`.

## 6. Próximos passos

- Treinar e avaliar no texto padronizado pelo Qwen3 (mesmo formato no treino e no uso).
- Ajuste fino do BERTimbau (`neuralmind/bert-base-portuguese-cased`) com cabeça ordinal
  CORAL, já implementado em `pesquisa/ml/treinar_bert.py`, treinado em GPU e comparado com
  esta referência pelo mesmo notebook e pelo mesmo atalho.
- Calibração (Platt) na validação, para a confiança refletir o acerto.
- Limiares de `incerto` para admin e jogador (`limiares.json`).
- Ampliar os verdadeiros checados (anotação da equipe, outras agências).

## Artefatos

| Artefato | Onde |
|---|---|
| Notebook de carregamento, execução e avaliação | `pesquisa/notebooks/avaliacao_modelos.ipynb` |
| Modelo treinado | `models/2026-11/referencia/referencia.joblib` (+ `config.json`, `previsoes.jsonl`) |
| Métricas | `models/2026-11/referencia/metricas.json`, `relatorio.md`, `confiabilidade.png` |
| Treino | `pesquisa/ml/treinar_referencia.py`, `pesquisa/ml/configs/referencia.toml` |
| Avaliação | `pesquisa/ml/avaliar.py` (relatório por modelo em `relatorio.md`) |

O modelo fica fora do Git (`models/` no `.gitignore`) e é entregue à parte.
