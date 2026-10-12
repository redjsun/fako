# Padronização do texto curto pela LLM (issue #20)

> **Status:** o lote e o cache estão em `pesquisa/ml/padronizar.py`, e `pesquisa/ml/dados.py` já lê
> o cache. Para rodar o lote faltam o prompt de extração (#19) e a escolha do modelo
> (`LLM_MODEL`); depois, a comparação pelo teste de atalho (#8).

## Por quê

Em uso, o classificador recebe afirmações extraídas pela LLM do texto do usuário. No
treino, o `texto_curto` é uma manchete nos verdadeiros e uma alegação de checador nos
falsos. Treinado num formato e usado em outro, o modelo erra sem aviso, e a forma do
texto já separa as classes (AUC macro de ~0,64 no teste de atalho na validação e no teste).
Passar o treino pelo **mesmo prompt** do uso põe as duas classes no mesmo formato.

A afirmação padronizada é também a pergunta do jogo, sem outra reescrita: ver
`doc/banco-perguntas.md`.

## Como roda

```bash
make padronizar ARGS="--limite 50"   # amostra, com api/app/prompts/extrair_afirmacoes_v1.txt
make padronizar ARGS="--paralelo 8"  # lote todo; outra versão: PROMPT=api/app/prompts/..._v2.txt
```

- **Entrada:** os registros de `pesquisa/data/processed/dataset.jsonl` com `split_produto` em
  `treino`, `validacao` ou `teste` (~28 mil), com ou sem `texto_curto`, para as classes ficarem
  no mesmo formato. `reserva` e `fora` (~42 mil) não entram no modelo do jogo e ficam de fora
  (`--splits todos` inclui). Usa o `texto_curto`; sem ele (Fake.br, verdadeiras do
  FakeTrue.Br, a maior parte das mensagens), usa o `texto`.
- **Prompt:** o arquivo `api/app/prompts/extrair_afirmacoes_vN.txt` da #19, o mesmo do
  uso. O texto do registro entra no marcador `{texto}` (ou no fim, se o prompt não tiver o
  marcador). A resposta segue o esquema da #19, `{"e_opiniao": ..., "afirmacoes":
  [{"texto": ..., "quem_disse": ...}]}`; lista vazia quer dizer opinião. O cache guarda o
  `quem_disse`, mas o treino usa só o `texto`, como o classificador em uso.
- **LLM:** o **Qwen pelo Ollama** (local, `qwen3:8b`), o mesmo da coleta diária de notícias:
  treino e uso precisam do mesmo prompt **e** do mesmo modelo, senão o formato volta a
  divergir. O Ollama roda no host, e os containers chegam nele por
  `LLM_BASE_URL=http://host.docker.internal:11434/v1` (endpoint compatível com a API de chat
  da OpenAI), com `LLM_MODEL` no `.env`. A tag do Ollama pode mudar num novo `ollama pull`:
  anotar o id do modelo (`ollama list`; `qwen3:8b` = `500a1f067a9f`) junto do cache.
  No Ollama, `LLM_EXTRA_BODY={"reasoning_effort": "none"}` desliga o raciocínio do Qwen3
  (`{"think": false}` é ignorado no endpoint `/v1`); sem isso, cada texto leva 30–60 s.
  O contexto padrão do Ollama é de 4.096 tokens: textos maiores perdem o começo do prompt,
  então manter `--max-caracteres` em uns 4 mil ou subir `OLLAMA_CONTEXT_LENGTH`.
  Temperatura 0; o pedido leva o JSON Schema da #19 em `response_format` (`--sem-esquema`
  se o provedor não aceitar) e o texto truncado em `--max-caracteres` (padrão 16 mil, ~4 mil
  tokens). `LLM_EXTRA_BODY` passa opções do provedor, como desligar o raciocínio do Qwen3.
  Erros 429 e 5xx e falhas de rede ganham até 4 tentativas, com espera de 2, 4 e 8 s.
- **Escolha do modelo:** 2 a 3 tamanhos de Qwen comparados nos 100 textos BR da #19
  (opinião, checabilidade, `quem_disse`, % de JSON válido, tempo e custo por texto), antes do
  lote. Com o Ollama, os textos não saem da máquina.
- **Teste no Fake.br (prompts provisórios, `qwen3:8b`, os mesmos 100 registros do treino,
  10–13 s por texto no Mac M4):**

  | Rodada | Pedido ao modelo | Palavras (falso × verdadeiro) | Acima de 25 | Opinião |
  |---|---|---|---|---|
  | v1 | frase curta, sem pontuação final | 9 × 10 | 0 | 2 × 5 |
  | v2 | quem, o quê e detalhes, 20–40 palavras | 16 × 17 | – | 2 × 3 |
  | v3 | o mesmo, numa frase de 12–25 palavras | 14 × 14 | 0 | 1 × 1 |

  A pontuação final é tirada depois da LLM: na primeira rodada, 17% dos falsos × 59% dos
  verdadeiros terminavam em ponto, um atalho. A v3 é a base para o prompt da #19. Ainda
  falha em: fidelidade em textos com várias pessoas (fakebr-fake-290 trocou a tese sobre
  Dilma Rousseff por outro fato do texto), nomes incompletos ("Kim", "o dono da JBS") e
  agendas de eventos, que deviam sair como opinião.
- **Cache:** `pesquisa/data/processed/padronizado_<versao>.jsonl` (fora do Git), uma linha por `id`
  com as afirmações, a versão, o hash do prompt e o modelo. Trocar o modelo também refaz as
  linhas. A versão vem do nome do arquivo. Rodar
  de novo só processa os ids que faltam (nos retreinos, só as frases novas). Se o texto
  do prompt mudar sem trocar a versão, o hash não bate e as linhas antigas são refeitas.
  Cada linha é gravada ao ficar pronta: dá para interromper e retomar. Falhas da LLM
  (rede, timeout, resposta fora do formato) não entram no cache e são refeitas na próxima
  rodada.
- **Custo:** cada rodada acrescenta o tempo, o número de chamadas e os tokens (quando o
  endpoint informa) em `padronizado_<versao>.rodadas.jsonl`.

## Regra para várias afirmações ou nenhuma

Decisão: **o cache guarda todas as afirmações**, e `aplicar()` (que `pesquisa/ml/dados.py` vai
chamar) gera dois campos:

| Caso | `texto_padronizado` | `n_afirmacoes` | No treino de frases curtas |
|---|---|---|---|
| uma afirmação | a afirmação | 1 | entra |
| várias | a primeira | quantas vieram | entra, com a primeira |
| nenhuma (opinião) | `None` | 0 | sai |
| não processado | `None` | `None` | sai |

A primeira afirmação tende a ser a principal (é a da manchete ou do início do texto).
Descartar as opiniões evita ensinar `falso` ou `verdadeiro` a quem não afirma nada; elas
podem servir depois à cabeça de tipo (`opiniao`). Como o cache guarda a lista inteira,
mudar a regra (usar todas as afirmações, por exemplo) não exige chamar a LLM de novo.

## Como validar (depende de #7 e #8)

1. Treinar os modelos de referência nas duas versões, `texto_curto` original e
   `texto_padronizado`, com os mesmos splits.
2. Comparar F1 macro na validação, no conjunto todo e na fatia "só checados".
3. Rodar o teste de atalho nas duas versões (`make atalho ARGS="--prompt ..."`): o AUC
   deve **cair** na padronizada, comparada ao original nos mesmos registros.
4. Registrar aqui as duas tabelas e o tempo e custo do lote (de `*.rodadas.jsonl`).

| Versão | F1 validação | F1 só checados | AUC atalho validação | AUC atalho teste |
|---|---|---|---|---|
| original | – | – | ~0,64 | ~0,64 |
| padronizado | – | – | – | – |

| Lote | Modelo | Itens | Tempo | Tokens | Custo |
|---|---|---|---|---|---|
| – | – | – | – | – | – |
