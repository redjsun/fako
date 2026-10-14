# LLM na API: geração, extração e explicação

A LLM escreve texto; ela **nunca decide o gabarito**. Fica atrás de `LLMClient`
(`api/app/ml/llm.py`), com o `FakeLLMClient` nos testes e, em uso, o Qwen pelo Ollama
(`LLM_PROVIDER=openai`, `LLM_BASE_URL`, `LLM_MODEL`; o nome `openai` é o formato da API de
chat, não uma biblioteca: a chamada é HTTP direto, sem dependência nova).

## Usos e prompts

| Uso | Método | Prompt | Saída validada |
|---|---|---|---|
| Reescrever uma checagem como questão (#21) | `gerar_questao` | `gerar_questao_v1.txt` | `{statement, category}` |
| Extrair afirmações com quem disse (#19) | `extrair_afirmacoes` | `extrair_afirmacoes_v1.txt` | `{e_opiniao, afirmacoes: [{texto, quem_disse}]}` |
| Explicar a análise ao jogador (#21) | `explicar` | `explicar_v1.txt` | `{explicacao}` |
| Pré-anotar tipo e sinais (#21) | `pesquisa/dados/pre_anotar.py` | `pre_anotar_v1.txt` | `{tipo, 4 sinais}` |

Os prompts ficam em `api/app/ml/prompts/`, com a versão no nome; a pesquisa lê os mesmos
arquivos (a padronização do treino usa o prompt de extração). Mudar um prompt é criar o
`_v2`, nunca editar o `_v1`. Temperatura 0,2.

Toda resposta passa por um esquema Pydantic. Fora dele, o pedido é refeito uma vez; se falhar
de novo, o item é descartado (`RespostaInvalida`). Sem LLM configurada, a API sobe e as rotas
que dependem dela respondem 503.

## Proteções automáticas (`api/app/ml/verificadores.py`)

- **Gabarito e fonte** da questão vêm da checagem; campos que a LLM inventar são ignorados.
- **Troca de assunto**: a reescrita precisa ter similaridade de embeddings (`bge-m3`, pelo
  Ollama) de pelo menos **0,6** com a alegação original (`SIMILARIDADE_MINIMA_REESCRITA`).
- **Inversão de sentido**: a reescrita que ganha ou perde uma negação ("não", "nunca"...) é
  descartada. Os embeddings não pegam isso ("não atirou" × "atirou": 0,84).
- **Fatos inventados na explicação**: todo nome próprio, sigla, número ou link citado precisa
  estar na análise que a LLM recebeu; e a explicação de `incerto` diz que o modelo não tem
  certeza. Recusada duas vezes, o jogador vê só a checagem e os sinais.

### Como o limiar de 0,6 foi escolhido

Em 14/10/2026, 40 alegações checadas (Fact Check API, `veracidade` falso ou verdadeiro, fora
do teste) foram reescritas pelo `qwen3:8b` e comparadas no `bge-m3`:

| Par | Mínimo | p5 | Mediana | Máximo |
|---|---:|---:|---:|---:|
| Original × a própria reescrita | 0,67 | 0,82 | 0,95 | |
| Original × reescrita de outra alegação (troca de assunto) | | | 0,30 | 0,49 |

O limiar fica no meio do intervalo entre os dois grupos. A checagem de negação recusou 2 das
40: uma inversão real ("Soldado Wesley não atirou..." virou "...atirou...") e uma pergunta
retórica ("Não acredita na nova cepa...?"), um falso positivo aceito para ficar do lado seguro.
Tempo médio por reescrita: 2,9 s; extração e explicação, 6 a 9 s (CPU/GPU do Mac, Ollama no
host).

## Avaliações

- **Extração (#19)**: rótulos da equipe em `pesquisa/anotacoes/extracao-br.csv` (`id`,
  `e_opiniao`, `quem_disse` e, se o texto for da equipe, `texto`); textos de terceiros em
  `pesquisa/data/avaliacao/extracao-textos.csv`, fora do Git. `make avaliar-extracao` roda a
  LLM e gera a planilha de revisão (`checavel`); `make avaliar-extracao ACAO=medir` mede o
  acerto de "é opinião?", o "quem disse" preservado e a proporção de afirmações checáveis.
- **Questões e explicações (#21)**: `make amostra-questoes > amostra.csv` sorteia questões
  geradas; o admin preenche `gabarito_correto`, `reescrita_fiel` e
  `explicacao_com_fato_novo`; `make medir-amostra < amostra.csv` mede a % com erro (meta
  **< 5%**; acima disso, a publicação automática para).
- **Pré-anotação (#21)**: `make pre-anotar r=N` sugere tipo e sinais nas planilhas da rodada,
  escondendo a sugestão nos itens de concordância; depois de importada a rodada,
  `make pre-anotar r=N ACAO=comparar` compara o kappa da LLM com os humanos e o dos humanos
  entre si. Campo em que a LLM fica abaixo sai das próximas planilhas.
