# Planejamento: coleta contínua e retreino do classificador

> **Status:** a coleta diária está implementada (serviço `agendador` e `pesquisa/crontab`,
> issue #4). O treino e a avaliação já existem, mas rodam à mão: `pesquisa/ml/treinar_referencia.py`
> (`make referencia`), `pesquisa/ml/treinar_bert.py` (`make bert`) e `pesquisa/ml/avaliar.py`
> (`make avaliar`). A publicação ainda é uma cópia sem portão de qualidade (`make publicar`, issue
> #14), e por isso o retreino mensal automático não está agendado.
>
> - Se a coleta falhar (por exemplo, sem `FACTCHECK_API_KEY`), o `crontab` registra `[ERRO]` no
>   log e o `preparar_dados` roda mesmo assim. O dataset é gravado num arquivo temporário e
>   trocado de uma vez, então um treino rodando às 3h não lê um arquivo pela metade.
> - O `avaliar.py` confere o `dataset_sha256` do modelo com o dataset atual e aborta se forem
>   diferentes; `--aceitar-dataset-diferente` segue mesmo assim e avisa no relatório.
> - O conjunto de teste só é olhado sob pedido: `--teste` nos scripts legados (`ml/tfidf.py`,
>   `ml/bertimbau.py`) e `INCLUIR_TESTE = True` no notebook `avaliacao_modelos.ipynb`.
> - Os scripts de treino gravam o SHA-256 dos artefatos no `config.json`, e quem carrega um
>   modelo confere o hash antes do `joblib.load`. Modelos antigos, sem hash, carregam com aviso.

## Por que retreinar

As fake news acompanham o noticiário: cada época tem seus personagens, golpes e
assuntos. Um modelo treinado até certa data não conhece o vocabulário que aparece
depois, e a precisão cai aos poucos (*drift*). O split temporal da base (treino de 2016 a
2023, validação em 2024 e teste de 2025 em diante, ver `pesquisa/dados/preparar_dados.py`)
mede essa queda. É ele que define a frequência:

- queda pequena no teste temporal: retreinar a cada 3–6 meses;
- queda grande: retreinar todo mês, com as checagens novas.

Classificar é diferente de retreinar. A classificação das notícias novas é leve e pode
ser diária ou a cada requisição da API. O retreino é periódico.

## Decisão: supercronic no compose

Um container de agendamento no `compose.yaml` com o [supercronic](https://github.com/aptible/supercronic),
um cron feito para containers (binário de poucos MB, ~10–30 MB de RAM, sem banco nem
interface). Ele roda os scripts que já existem, nos horários de um arquivo `crontab`.

Alternativas consideradas:

| Opção | Por que não, por enquanto |
|---|---|
| Airflow | 4+ containers e centenas de MB a GB de RAM para um fluxo de poucas etapas |
| Prefect / Dagster | mais leves que o Airflow, mas ainda são um serviço a mais para manter |
| cron do host / Agendador de Tarefas do Windows | a configuração fica presa a uma máquina |
| GitHub Actions agendado | o cache de `pesquisa/data/` não persiste entre execuções |

Se o projeto crescer, a migração para um orquestrador é direta: cada linha do
`crontab` vira uma tarefa de DAG.

## Desenho

```
diário   coletar_factcheck --incremental ─> preparar_dados      (implementado)

mensal   preparar_dados ─> treinar ─> avaliar ─┬─> publicar em models/ (se melhor)
                                               └─> manter o modelo atual (se pior)
```

O `pesquisa/crontab` hoje:

```cron
0 3 * * * python pesquisa/dados/coletar_factcheck.py --incremental && python pesquisa/dados/preparar_dados.py
```

Quando a publicação com portão existir (#14), entra uma linha mensal, por exemplo
`0 5 1 * * python pesquisa/dados/preparar_dados.py && python pesquisa/ml/treinar_referencia.py --config pesquisa/ml/configs/referencia.toml && python pesquisa/ml/publicar.py`
(`publicar.py` é o script previsto em #14, que roda o `avaliar.py` e só publica se o modelo novo for melhor).
O treino precisa do PyTorch da imagem `pesquisa/ml/`: nesse momento o agendador passa a usar
essa imagem ou ganha um segundo serviço.

O serviço no `compose.yaml` usa a imagem de `pesquisa/` (o `Dockerfile` instala o binário do
supercronic, conferido por SHA-1). Ele fica no profile `agendador` e sobe só na máquina que faz
a coleta, com `make agendador` (um `make up` comum não regenera o `dataset.jsonl` de madrugada):

```yaml
  agendador:
    build: ./pesquisa
    profiles: ["agendador"]
    restart: unless-stopped
    env_file: .env                     # FACTCHECK_API_KEY
    environment:
      TZ: America/Sao_Paulo            # horário do crontab
    command: supercronic /work/pesquisa/crontab
    volumes:
      - ./pesquisa:/work/pesquisa
```

Quando o retreino entrar, o serviço que treina passa a montar `./models` para gravar o modelo
publicado, que a API lê.

Para testar um horário próximo sem mexer no `crontab`:
`docker compose --profile agendador run --rm agendador supercronic -test /work/pesquisa/crontab` confere a sintaxe,
e um `crontab` temporário com `* * * * *` roda a tarefa no minuto seguinte.

### Fontes da coleta diária

- **Fact Check API**: modo `--incremental`. A API devolve as checagens da mais recente para
  a mais antiga, e a paginação de cada agência para na primeira página sem checagem nova.
  Medido em 07/10/2026: com o arquivo de 06/10 (11.910 checagens), a primeira execução trouxe
  601 checagens novas em 65 requisições; a segunda, logo depois, 0 novas em 15 requisições
  (uma por agência). O modo completo percorria até 500 páginas por agência.
- **Boatos.org**: decisão (a), entra só se vier pela Fact Check API. O `--descobrir` de
  07/10/2026 não achou o Boatos.org entre os publicadores em português, e o filtro
  `boatos.org` devolve 0 checagens. Falsos recentes já vêm das outras agências; o
  `coletar_boatos.py` continua só para recoletar o FakeRecogna (2019–2021).
- **Notícias recentes** (fonte em decisão na #34): só como afirmações para analisar, sem
  rótulo e fora do `dataset.jsonl`.
- **Portais (`coletar_verdadeiras.py`)**: fora da coleta diária. O "verdadeiro" deles é
  suposição; os verdadeiros do treino vêm do dataset confiável (#6).

## Requisitos para implementar

1. **Portão de qualidade.** O modelo novo só substitui o atual se não for pior num
   conjunto recente que nenhum dos dois viu no treino. Sem isso, um retreino com dados
   ruins piora o produto sem ninguém notar.
2. **Versionamento.** Cada modelo em `models/AAAA-MM/`, com `metricas.json` (dados
   usados, métricas por split e por fonte), para poder comparar e voltar atrás. A API
   lê o modelo publicado (por exemplo `models/atual`).
3. **Monitoramento.** Registrar a proporção de previsões *fake* por dia. Uma mudança
   brusca indica *drift* ou que alguma fonte mudou de formato.
4. **Coleta incremental.** Feita no `coletar_factcheck.py --incremental` (ver acima).
5. **Mesmo formato no treino e no uso.** Se o modelo for treinado com `texto_curto`
   (título ou alegação), a classificação diária também usa o título.

## Ordem

1. Fechar a EDA (`pesquisa/notebooks/eda_1_datasets.ipynb` e `pesquisa/notebooks/eda_2_conjunto.ipynb`).
2. Treinar e avaliar o primeiro modelo (`pesquisa/ml/`), medindo a queda no teste temporal.
3. Com essa medida, definir a frequência e acrescentar o retreino ao `pesquisa/crontab`.
