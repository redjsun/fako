# Guia de classificação e anotação

> **Status:** os dados e a divisão em treino, validação e teste (seções 3 e 5) estão
> implementados em `pesquisa/dados/preparar_dados.py`. O classificador (seção 4) e a anotação
> (seções 7 e 8) são planejados: `pesquisa/ml/` ainda não existe e `/admin/ai/classify` usa o
> `FakeAIClient`. Revisão de 05/10/2026 do guia original (PDF), alinhada ao que o projeto
> tem hoje.

Baseado no framework de desordem informacional de Wardle e Derakhshan (2017, relatório
*Information Disorder*, Conselho da Europa).

## 1. Objetivo e escopo

Este guia reúne as decisões de modelagem do classificador de confiabilidade do FAKO: como
o framework vira rótulos, o que os dados atuais permitem treinar, como o modelo é avaliado
e como a equipe anota um conjunto próprio.

**Entrada:** uma afirmação curta, no formato das questões do jogo. No dataset é o campo
`texto_curto` (a alegação checada ou o título da matéria). Treinar e usar no mesmo formato
evita que o modelo dependa de tamanho e gênero de texto (ver `doc/eda.md`).

**Saída:** uma categoria (`confere`, `enganoso`, `falso`, `opiniao` ou `incerto`), uma
nota de veracidade de 0 a 100 (onde a afirmação fica entre falso e verdadeiro), a
confiança calibrada e, à parte, os sinais de manipulação encontrados no texto (seção 4).
Textos com várias afirmações recebem uma análise por afirmação. Ela aparece em dois lugares:

- **para o admin**, como sugestão ao revisar questões (`/admin/ai/classify`). O revisor
  decide; nada é publicado sem revisão;
- **para o jogador**, depois que ele responde (antes, entregaria a resposta). Aqui o erro
  custa mais (ensina errado), então o limiar para mostrar `falso` ou `confere` é mais alto
  e, abaixo dele, o jogador vê `incerto`.

**Fora do escopo:** sátira e paródia (nenhuma base tem exemplos; o FakeRecogna é binário e
só traz checagens de sátiras tomadas como fato), malinformação e conteúdo manipulado em
imagem, vídeo ou áudio.

## 2. O framework

O relatório cruza dois eixos, se a informação é falsa e se há intenção de causar dano:

| Categoria | A informação é falsa? | Há intenção de causar dano? |
|---|---|---|
| Misinformação | sim | não (quem compartilha acredita) |
| Desinformação | sim | sim |
| Malinformação | não (é verdadeira) | sim (vazamento, assédio, exposição) |

**A intenção é de quem cria ou compartilha, não do texto.** A mesma mensagem é
desinformação quando quem a inventou quer enganar e misinformação quando alguém a repassa
acreditando nela. Por isso o FAKO **não classifica** um texto como mis ou desinformação:
ele classifica a veracidade e aponta sinais de manipulação. Os três conceitos entram no
conteúdo educativo do jogo, não como rótulo do modelo.

O framework descreve 7 tipos de conteúdo problemático:

| Tipo (rótulo) | Definição |
|---|---|
| Sátira ou paródia (`satira`) | Humor sem intenção de dano, mas que engana quem não percebe a piada. Fora do escopo do FAKO. |
| Falsa conexão (`falsa_conexao`) | Título, imagem ou legenda não condizem com o conteúdo. |
| Conteúdo enganoso (`enganoso`) | Uso enganoso de informação para enquadrar um assunto ou uma pessoa. |
| Falso contexto (`falso_contexto`) | Conteúdo genuíno compartilhado com informação contextual falsa. |
| Conteúdo impostor (`impostor`) | Fontes genuínas são imitadas (nome, logo, domínio). |
| Conteúdo manipulado (`manipulado`) | Informação ou mídia genuína adulterada para enganar. |
| Conteúdo fabricado (`fabricado`) | Totalmente falso, criado para enganar. |

Além desses, o guia usa `opiniao` (sem afirmação factual checável) e `nenhum` (conteúdo
que confere com as fontes, sem problema de forma).

## 3. Os dados que temos

As bases e os critérios de coleta estão no `README.md`. O que importa para os rótulos:

| Base (`base`) | Rótulo | Formato do `texto_curto` | Período |
|---|---|---|---|
| `fakebr` | falso e verdadeiro, pareados por assunto | não tem (só texto completo) | 2016–2018 |
| `fakerecogna` | falso (Boatos.org) e verdadeiro (G1, UOL, Extra) | alegação do boato / título | 2019–2021 |
| `boatos` | falso | alegação do boato | 2024 em diante |
| `factcheck` | falso, enganoso e verdadeiro (Google Fact Check API, 10 agências) | alegação checada | 2018 em diante |
| `fakenewsbr` | falso, enganoso e verdadeiro (sub-bases brasileiras de agência) | alegação, quando é de agência | 2010 em diante |
| `verdadeiras` | verdadeiro (9 portais) | título da matéria | 2018 em diante |

Cada registro do `dataset.jsonl` tem:

- `veracidade`: `falso`, `enganoso` ou `verdadeiro`. Nas bases com veredito de agência,
  vem dele: "falso", "fake", "montagem" e "predominantemente falso" viram `falso`;
  "enganoso", "distorcido", "fora de contexto", "sem contexto", "exagerado", "impreciso",
  "não é bem assim" e afins viram `enganoso`; "verdadeiro", "comprovado" e "fato" viram
  `verdadeiro`. Sátira e vereditos ambíguos ("insustentável", "sem provas") ficam de fora;
- `rotulo`: a versão binária (`fake` ou `true`), vazia nos enganosos;
- `veredito_original`: o veredito da agência, normalizado;
- `tipo_sugerido`: o tipo de conteúdo que o veredito indica (tabela abaixo).

Nenhuma base traz tipo de conteúdo confirmado nem sinais de manipulação: esses precisam
ser anotados pela equipe (seção 7).

**Os enganosos se concentram nos anos recentes.** Quase todos vêm da Fact Check API, que
devolve sobretudo checagens de 2023 em diante. Por isso o treino vai até 2023 e a Fact
Check API segue a mesma regra de data das outras bases (seção 5): assim há 844 enganosos
no treino e 750 na validação. Com o corte anterior (treino até 2022, Fact Check API só no
teste), eram 243 e 47. As alegações checadas como verdadeiras são poucas (cerca de 700); a
classe verdadeira continua vindo, na maior parte, de títulos de portais, que são um gênero
de texto diferente das alegações (atalho medido em `eda_2_conjunto.ipynb`).

**Rótulos fracos de tipo.** O `tipo_sugerido` pré-preenche a planilha de anotação e é
sempre conferido por um anotador:

| Veredito da agência | Tipo sugerido |
|---|---|
| falso, fake, predominantemente falso | `fabricado` (ou outro, se o anotador vir motivo) |
| montagem | `manipulado` |
| fora de contexto, sem contexto, falta contexto | `falso_contexto` |
| enganoso, distorcido, exagerado, impreciso, não é bem assim | `enganoso` |
| verdadeiro, comprovado, fato | `nenhum` |

## 4. Arquitetura do classificador (planejada)

Opinião, forma do conteúdo e falsidade são eixos diferentes. Um único rótulo fake/real mistura tudo
e erra nos casos de fronteira. Por isso o modelo é multitarefa, com uma etapa de decisão
no fim.

**Entrada do encoder: só o texto.** A fonte (veículo, domínio, autor) **não entra** no
modelo. Nas nossas bases cada classe vem de um conjunto diferente de sites, e o modelo
aprenderia o site em vez da veracidade (`doc/eda.md`, seção "Atalhos"). URLs, nomes de
portal e assinaturas são removidos do texto antes do treino.

- **Encoder compartilhado:** BERTimbau (`neuralmind/bert-base-portuguese-cased`), lendo o
  `texto_curto` uma vez e alimentando as cabeças.
- **Cabeça de veracidade, ordinal:** `falso` < `enganoso` < `verdadeiro` (campo
  `veracidade`), tratados como uma **escala**, não como três classes soltas. O modelo
  aprende duas fronteiras ("é mais que falso?" e "é mais que enganoso?"), então os
  milhares de falsos e verdadeiros também ensinam onde fica o meio, mesmo com poucos
  enganosos. A saída é uma **nota de veracidade de 0 a 100** (0 = falso, 50 = enganoso,
  100 = verdadeiro) e as três probabilidades.
- **Cabeça de tipo:** `opiniao`, `fabricado`, `enganoso` e `nenhum` no começo, depois os
  demais (seção 8). Treina com os tipos confirmados pela equipe; o `tipo_sugerido` serve
  como rótulo fraco, com peso menor.
- **Sinais de manipulação** (no lugar da cabeça de intenção do guia original): detectores
  independentes de *pede para compartilhar*, *urgência artificial*, *apelo emocional
  extremo* e *ataque a pessoa ou grupo*. São mostrados ao jogador como itens, não viram
  categoria. Cuidado: esses sinais também separam mensagem de rede social de matéria
  jornalística, e a EDA do Fake.br não mostrou diferença de emotividade entre as classes.
  Eles descrevem o texto, não provam falsidade.
- **Cabeça de evidência:** compara a afirmação com checagens já publicadas (embeddings das
  alegações de `factcheck`, `boatos` e das sub-bases de agência da `fakenewsbr`). A
  similaridade e o veredito da checagem mais próxima entram como sinal. **O índice só pode
  ter checagens anteriores à data do item e do período de treino**, sem o próprio item e
  sem as quase-duplicatas dele (`grupos_quase_duplicatas` em `preparar_dados.py`). Sem
  isso, o item acha a própria checagem e a avaliação fica perfeita e falsa.
- **Conteúdo impostor:** regra separada sobre o domínio ou o nome da fonte (lista de
  domínios parecidos com os de veículos reais), fora do encoder.
- **Meta-classificador (stacking):** regressão logística que combina as cabeças, treinada
  com previsões que o classificador fez sem ter visto aqueles exemplos (seção 5).
- **Calibração:** temperature scaling (BERT) ou Platt scaling (modelos clássicos), ajustada
  na validação de 2024, para a confiança refletir o acerto real.
- **Textos longos:** quando a entrada tem várias afirmações, cada uma é classificada à
  parte (a extração é feita por uma LLM, ver `pipeline-fako/03-llm.md`). O resultado é
  por afirmação ("2 conferem, 1 enganosa, 1 falsa"), não uma nota única para o texto.

### Regra de decisão

A categoria depende só do tipo, da veracidade e da confiança. Os sinais de manipulação
aparecem à parte e não mudam a categoria.

| Condição | Categoria exibida |
|---|---|
| tipo = `opiniao` | `opiniao`: não há o que checar, sem nota |
| maior probabilidade abaixo do limiar | `incerto`, sem nota firme (no admin, vai para revisão humana) |
| classe mais provável = falso | `falso` |
| classe mais provável = enganoso | `enganoso` |
| classe mais provável = verdadeiro | `confere` |

Fora de `opiniao` e `incerto`, a nota de 0 a 100 aparece junto da categoria. Ela mostra
**onde na escala** a afirmação fica (uma afirmação `enganoso` com nota 35 está mais perto
do falso). A nota é diferente da confiança: a confiança diz o quanto o modelo tem certeza
da categoria.

Os limiares de confiança são escolhidos na validação de 2024, um para cada lugar onde a
saída aparece. Um critério possível é fixar a taxa de verdadeiros marcados como falsos,
que é o erro mais caro para um jogo educativo: por exemplo, 5% no admin (o revisor
corrige) e 1% para o jogador.

## 5. Divisão dos dados e avaliação

A divisão implementada (`split_produto`, protocolo B) combina sorteio e data, e depois
equilibra as classes:

| Split | Regra | falso | enganoso | verdadeiro |
|---|---|---|---|---|
| `treino` | pareadas 80%; checagens e portais de 2016 a 2023; mensagens | 12.512 | 1.541 | 12.512 |
| `validacao` | pareadas 10%; checagens e portais de 2024 | 1.446 | 964 | 1.446 |
| `teste` | pareadas 10%; checagens e portais de 2025 em diante | 1.638 | 1.092 | 1.638 |
| `reserva` | sobra do equilíbrio (portais e falsos da FakenewsBR, quase todos) | 15.288 | 0 | 16.876 |
| `fora` | sem data, anterior a 2016 ou quase-duplicata de treino/validação | 1.840 | 83 | 207 |

Contagem de 05/10/2026. As bases pareadas (Fake.br, FakeRecogna, FakeTrue.Br) são sorteadas
por par, para validação e teste também terem verdadeiros, que as checagens recentes quase
não têm. A Fact Check API e a FakenewsBR seguem a data: as checagens até 2023 ensinam o
enganoso, e as de 2024 em diante, que o modelo não vê, são a validação e o teste. No
treino, verdadeiros e falsos ficam iguais; na validação e no teste entram todos os
enganosos, e falsos e verdadeiros a 1,5 vez o número deles (~38/25/38). O protocolo A
(`split`: treina em Fake.br + FakeRecogna e testa em todo o resto) fica como referência de
quanto as bases públicas generalizam.

**Com stacking**, o meta-classificador precisa de previsões que o classificador fez sem ter
visto aqueles exemplos. Elas vêm de **dobras por ano** dentro do treino: as previsões de
cada ano saem de um classificador treinado nos outros anos. Separar um ano inteiro para o
meta-classificador não funciona aqui: 2023 tem 491 dos 842 enganosos do treino. A
calibração e os limiares saem da validação de 2024.

**Métricas**, sempre por split, por fonte e por ano, e não só a média:

- F1 por classe e AUC;
- por ser uma escala, o erro médio da nota (MAE) e o kappa ponderado quadrático: errar
  `falso` por `verdadeiro` pesa mais que errar `falso` por `enganoso`;
- recall de falsas com 5% de verdadeiros marcados como falsos;
- calibração (ECE e diagrama de confiabilidade);
- o teste de atalho: um modelo só com estilo e tamanho, sem conteúdo
  (`eda_2_conjunto.ipynb`, seção 7). Se ele já acerta muito, o problema está nos dados.

Escolhas de modelo, hiperparâmetros e limiares usam só a validação. Os testes são olhados
uma vez, no fim.

## 6. O que um classificador de afirmações curtas consegue cobrir

| Tipo | Sinal disponível | Viabilidade no MVP |
|---|---|---|
| Opinião | ausência de afirmação checável | viável |
| Sátira ou paródia | estilo, exagero absurdo | fora do escopo (sem dados) |
| Conteúdo fabricado | veracidade + evidência de checagens | viável |
| Conteúdo enganoso | veracidade em escala de 3 níveis + evidência | viável; 844 exemplos no treino (seção 3) |
| Falso contexto | precisa achar o original e comparar data e contexto | difícil; rótulo fraco nos vereditos |
| Falsa conexão | título contra corpo | fora do escopo: a entrada é só a afirmação |
| Conteúdo impostor | domínio e nome da fonte, não o texto | só por regra sobre a fonte |
| Conteúdo manipulado | análise de imagem, vídeo ou áudio | fora do MVP |

## 7. Guia de anotação

O tipo e a veracidade são **campos separados**. O anotador preenche os dois.

**Tipo.** Responda em ordem e pare na primeira que se aplicar:

| Passo | Pergunta | Tipo |
|---|---|---|
| 1 | É sátira ou paródia? Fora do escopo: marque `fora_escopo` e passe ao próximo item. | `fora_escopo` |
| 2 | O texto não afirma nada que dê para checar (só opinião ou análise)? | `opiniao` |
| 3 | O conteúdo é inteiramente inventado? | `fabricado` |
| 4 | Mídia genuína foi adulterada (imagem, vídeo, áudio, documento)? | `manipulado` |
| 5 | O texto imita uma fonte real (nome, logo ou domínio parecido)? | `impostor` |
| 6 | Fato real, mas fora do contexto (data, lugar ou pessoa errada)? | `falso_contexto` |
| 7 | Fato real com distorção, omissão ou enquadramento enganoso? | `enganoso` |
| 8 | O título promete algo que o corpo não sustenta (só se houver corpo)? | `falsa_conexao` |
| 9 | Nenhuma das anteriores. | `nenhum` |

A ordem vai do mais grave ao mais leve: uma matéria inventada com título caça-clique é
`fabricado`, não `falsa_conexao`. Se um segundo tipo também couber, registre-o em
`tipo_secundario`. Uma checagem de sátira que circulou como fato (por exemplo, "é uma
sátira o artigo sobre chip na vacina") não é sátira: é a alegação que circulou, anotada
como qualquer outra.

**Veracidade:** `verdadeiro`, `enganoso` ou `falso`. Confira em pelo menos uma fonte
externa e cite a URL. Para `opiniao`, deixe em branco.

**Sinais de manipulação:** marque cada um que aparecer no texto, independentemente da
veracidade: `pede_compartilhamento`, `urgencia`, `apelo_emocional`, `ataque`.

**De onde vêm os textos:** do `dataset.jsonl`, sorteados por `base`, `fonte` e ano, para
cada classe ter fontes variadas. Itens da Fact Check API chegam com o tipo pré-preenchido
pelo veredito (tabela da seção 3), que o anotador confirma ou corrige. Itens dos splits de
teste não devem ser anotados para treino.

### Colunas da planilha

| Coluna | Conteúdo |
|---|---|
| `id` | o `id` do `dataset.jsonl` (para cruzar com base, fonte, data e split) |
| `texto_curto` | o texto anotado, sem edição |
| `veredito_original` | o veredito da agência, quando houver |
| `tipo` | um dos rótulos da seção 7 |
| `tipo_secundario` | opcional |
| `veracidade` | `verdadeiro`, `enganoso`, `falso` ou vazio |
| `pede_compartilhamento`, `urgencia`, `apelo_emocional`, `ataque` | 0 ou 1 |
| `anotador` | quem anotou (para a concordância) |
| `observacao` | URLs de checagem, dúvidas, justificativa de casos de fronteira |

## 8. Regras de processo

- **Mais de um anotador.** Coloque 2 ou 3 pessoas nos mesmos 10 a 20% dos textos. Com 2
  anotadores, use o kappa de Cohen; com 3 ou mais, o kappa de Fleiss ou o alfa de
  Krippendorff. Concordância baixa indica definição ruim no guia: ajuste antes de anotar
  mais.
- **Adjudicação.** Reúnam-se para decidir as discordâncias e incluam esses casos como
  exemplos no guia.
- **Exemplos no guia.** Pelo menos 3 exemplos reais por tipo, incluindo um caso de
  fronteira.
- **Fontes variadas.** Misture fontes diferentes em cada classe e cada tipo. Respeite os
  termos de uso dos portais.
- **Teste separado por fonte e por tempo.** Use a divisão da seção 5; os anotados herdam o
  split do registro de origem.
- **Comece pequeno.** `opiniao`, `fabricado`, `enganoso` e `nenhum`; abra os demais
  quando houver exemplos suficientes.
- **Métricas por classe e análise de erros** a cada rodada: os 50 piores casos, o padrão
  do erro, mais dados desse tipo.
- **Feedback dos jogadores e do admin.** As questões aprovadas ou rejeitadas em
  `/admin/questions/{id}/review` e as contestações dos jogadores entram numa fila de
  revisão; só viram dado de treino depois que um humano confirma. As questões aprovadas
  formam o conjunto de referência final, com a distribuição real do jogo.

## 9. Limites e cuidados

- **Os sinais de manipulação não provam falsidade nem intenção.** Mostram o que o texto
  faz, não o que o autor quis. Use `incerto` na dúvida.
- **A classe verdadeira tem outro gênero de texto.** Títulos de portal contra alegações e
  mensagens de rede social. Parte do que o modelo aprende é gênero, não veracidade; o teste
  de atalho e as métricas por fonte e por dataset medem isso
  (`pesquisa/notebooks/eda_2_conjunto.ipynb`).
- **As épocas não se sobrepõem entre as bases** (Fake.br até 2018, FakeRecogna em
  2019–2021). Cada época tem seus assuntos, e a queda das checagens de 2025 em diante, no
  `teste`, mede o drift (ver `doc/planejamento-retreino.md`).
- **Malinformação** fica fora do MVP ou entra como exemplos curados para fins educativos.
- **Fronteiras são subjetivas.** Opinião, enganoso e polêmica se confundem. Se os
  anotadores não concordam, o modelo também não vai concordar.
- **Sem promessa de acurácia.** Os números dependem dos dados reais e são medidos em fontes
  e períodos que o modelo não viu.

## 10. Decisões

Tomadas:

- **A saída aparece para o admin e para o jogador**, com limiares diferentes (seções 1 e 4).
- **Sátira fica fora do escopo**: não há exemplos nas bases.
- **As meias-verdades entram** no `preparar_dados.py` como veracidade `enganoso`, com o
  veredito original e o tipo sugerido.
- **A veracidade é uma escala de três níveis**, com nota de 0 a 100, e não um rótulo
  binário: nem toda notícia é inteiramente verdadeira ou falsa.
- **Divisão por data com treino até 2023**, validação em 2024 e teste de 2025 em diante,
  com a Fact Check API seguindo a mesma regra: 844 enganosos no treino (eram 243).
- **Textos longos são classificados por afirmação.**
- **As anotações da equipe** ficam em `anotacoes/` no repositório, só com `id` e rótulos
  (ver `pipeline-fako.md`, etapa 4).

Em aberto:

- **A mecânica do jogo.** Hoje a questão é verdadeira ou falsa (`is_true`). O jogador pode
  passar a responder em três níveis, ou continuar binário e ver a escala só na análise
  depois de responder.
- **Se o jogador puder enviar notícias completas**, os tipos que dependem do corpo
  (`falsa_conexao`) voltam ao escopo.
