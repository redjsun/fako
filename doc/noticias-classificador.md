# Notícias externas e classificador no jogo

Como manchetes de uma API de notícias viram afirmações do jogo, e como a referência TF-IDF
(regressão logística ordinal, `pesquisa/ml/treinar_referencia.py`) entra na API.

## Fluxo

```
provedor de notícias ──► normalização ──► filtros ──► deduplicação ──► classificador ──► rascunho
(GNews, Fact Check     (igual ao treino)                               (limiar admin)    (draft)
 ou fake)
                                                                                           │
                                       jogo ◄── validated ◄── revisão humana ◄─────────────┘
                                         │
                                         └─ depois da resposta: palpite do modelo (limiar jogador)
```

1. `POST /admin/news/import` (`{"quantity": 5}`) busca os textos nos provedores
   (`integrations/noticias_client.py`), de todos os assuntos. Com mais de um provedor
   (`NOTICIAS_PROVIDER=factcheck,gnews`), a quantidade é dividida entre eles, para equilibrar
   as falsas das checagens com as verdadeiras das manchetes; um provedor fora do ar não derruba
   os outros, e o que ele não trouxe passa para os seguintes. O `category` é opcional
   (padrão `conhecimentos-gerais`): o jogo não separa por categoria, mas a questão exige uma.
2. Cada manchete é normalizada para o formato do `texto_curto` do treino
   (`ml/normalizacao.py`): entidades HTML, sufixo " - Veículo" do agregador e a mesma
   `limpar()` de `pesquisa/ml/dados.py` (URLs e créditos de veículo nas pontas; caixa e
   pontuação mantidas).
3. Saem as manchetes que não servem como afirmação verdadeira, com os mesmos filtros das
   matérias de portal no treino (`motivo_filtro_portal()` de `pesquisa/dados/preparar_dados.py`):
   opinião, vídeo, ao vivo, pergunta, fala relatada e aspas; e as fora da faixa de tamanho. As
   alegações checadas não passam pelos filtros de portal (pergunta e fala fazem parte do boato),
   mas saem as de veredito sem lado no jogo (enganoso, fora de contexto, exagerado, ambíguo) e
   as que não se sustentam sem revisão: fora da faixa de tamanho, que dependem de mídia ("foto
   mostra", "vídeo", "áudio"), que já trazem a conclusão ("é deepfake", "é falso"), falas em
   primeira pessoa e trechos com colchetes da agência. Com `NOTICIAS_SEM_POLITICA=true`, saem
   também as de política e eleição.
4. Saem as repetidas (mesma URL ou mesmo texto, no lote ou no banco).
5. O classificador analisa com o limiar do admin; categoria, nota, confiança e versão do modelo
   ficam na questão (`model_*`) para apoiar a revisão.
6. A questão entra como rascunho (`status=draft`, `origin=news`), com a URL como fonte. A
   manchete entra verdadeira; a alegação checada entra com o lado do veredito (`falso`,
   `montagem`... → falsa; `verdadeiro`, `comprovado`, `fato` → verdadeira), e a explicação cita
   a agência e o veredito. Com `NOTICIAS_PUBLICAR_DIRETO=true`, manchetes e checagens já
   entram validadas (vão direto ao jogo): o rótulo é o da agência ou o da publicação, nunca o
   do classificador.
7. A importação examina até 100 candidatos e para ao chegar na quantidade pedida: com os
   filtros, só uma parte pequena das checagens passa. Só chega ao jogador depois de aprovada em `PATCH /admin/questions/{id}/review`.

A resposta do import lista as importadas e as descartadas, com o motivo.

## Classificador na API

- Adaptador `ReferenciaTfidf` de `ClassificadorClient`
  (`ml/classificador.py`), ligado por `CLASSIFICADOR_PROVIDER=referencia`.
  Lê `MODELS_DIR/atual/referencia.joblib` e, se houver, o `limiares.json` do modelo.
- A frase passa pela `limpar()` do treino antes do TF-IDF. **`normalizacao.py` é cópia de
  `pesquisa/ml/dados.py` e `pesquisa/dados/preparar_dados.py`: mudou lá, muda aqui.**
- O `scikit-learn` da API tem a mesma versão da imagem `ml` (o joblib não carrega entre
  versões diferentes).
- Publicar um modelo: `make publicar [MODELO=models/2026-11/referencia]` copia a pasta para
  `models/atual`. Republicar troca o modelo sem reiniciar a API (recarrega pela data do arquivo).
- `POST /admin/classifier/analyze`: análise de uma frase para o admin, com o texto normalizado e
  os termos que mais pesaram.

## No jogo

Com `CLASSIFICADOR_NO_JOGO=true`, o feedback da resposta (`POST /matches/{id}/answers`) traz
`model_guess`: o palpite do modelo com o limiar do jogador. Abaixo do limiar a categoria é
`incerto`, sem nota. O front mostra o palpite depois da resposta, com o aviso de que é uma
estimativa pelo jeito do texto, não uma checagem.

O padrão é `false`: a referência é um piso reprodutível (F1 macro 0,43 na validação, ver
`doc/relatorio-tecnico.md`), não um modelo pronto para o jogador. Ligar só para teste ou depois
de um modelo melhor.

## Configuração (`.env`)

| Variável | Valores |
|---|---|
| `CLASSIFICADOR_PROVIDER` | `fake` (sem modelo) ou `referencia` |
| `CLASSIFICADOR_NO_JOGO` | `false` (padrão) ou `true` |
| `NOTICIAS_PROVIDER` | `fake` (manchetes inventadas, sem chave), `gnews`, `factcheck` ou vários separados por vírgula (`factcheck,gnews`) |
| `NOTICIAS_API_KEY` | chave gratuita do GNews (https://gnews.io, 100 pedidos por dia) |
| `FACTCHECK_API_KEY` | chave da Google Fact Check Tools API, a mesma da coleta da pesquisa |
| `NOTICIAS_PUBLICAR_DIRETO` | `false` (padrão, rascunho) ou `true` (já validadas) |
| `NOTICIAS_SEM_POLITICA` | `false` (padrão) ou `true` (descarta checagens de política) |

No GNews, as manchetes do dia do Brasil, em português, só dos tópicos `health`, `science` e
`technology` (um pedido por tópico, intercalados): o `general` é quase só futebol e TV, que o
jogador acerta sem pensar. Manchetes de serviço ("onde assistir", horário, sorteio, "confira")
e explicativas ("Por que...", "O que se sabe...", "...: entenda", com "?" no meio) também saem. Na Fact Check
API, as checagens mais recentes das agências brasileiras (a mesma lista de
`pesquisa/dados/coletar_factcheck.py`): um pedido por agência, juntando as mais recentes.

## Limites conhecidos

- O GNews só traz matérias publicadas (verdadeiras), e a Fact Check API traz quase só falsas
  (as agências checam o que circula): para ter os dois lados, use os dois provedores. Na
  publicação direta, a manchete entra verdadeira por ter sido publicada, a mesma suposição que
  o treino evita (`origem_rotulo=portal`); os filtros de portal tiram opinião e fala relatada.
- O texto da alegação às vezes só faz sentido com a imagem ou o vídeo que circulou. Na
  publicação direta, os filtros cuidam disso por palavras; o que escapar vai ao jogo. Em época
  de eleição, quase tudo que as agências checam é política: com `NOTICIAS_SEM_POLITICA=true`,
  sobram poucas (cerca de 6 em 100 checagens em outubro de 2026).
- Cada classe do treino tem uma "cara" própria (manchete, ponto final, minúsculas); o modelo
  pode puxar uma manchete para `confere` só pela forma (`pesquisa/ml/atalho.py`). A nota do
  modelo na curadoria é apoio à revisão, não um veredito.

## O que o jogador vê depois de responder

- **Onde circulou** (alegação checada): quem fez a alegação e quando, do `claimant` e do
  `claimDate` da Fact Check API, normalizados por `normalizar_autor()`
  (`ml/normalizacao.py`). Rótulos genéricos ("Boato de internet", "Várias fontes",
  "[site:name]", 83% dos casos) viram "redes sociais"; uma plataforma citada vira o nome dela
  (WhatsApp, Facebook, X...); nomes reais ficam ("Jair Bolsonaro"). A API não traz o link do
  post: raspar a matéria da agência achou link em 3 de 21 páginas, e às vezes era a prova da
  checagem, não o boato. Por isso o link mostrado é o da checagem, como apoio ("Checagem:
  aosfatos.org").
- **Onde foi publicada** (manchete): o veículo, a data e o link da matéria.
- A explicação segue a mesma ordem: "Circulou no WhatsApp em 30/09/2026. Aos Fatos checou e
  concluiu que é falsa."
- Campos em `questions`: `origin_author`, `origin_link` e `origin_date`; na resposta,
  `claim_origin` (`kind` `alegacao` ou `materia`). Questões humanas e as importadas antes
  ficam sem origem.

Se o modelo publicado foi treinado no texto padronizado (`"texto": "padronizado"` no
`config.json`), a manchete passa na importação pelo prompt de extração (#19/#20) e a primeira
afirmação vai para `questions.claim_text`, que é o que o classificador recebe na análise e no
palpite do jogo. A LLM roda uma vez, na importação, e o palpite continua levando
milissegundos.

## Rotina diária

O serviço `agendador-api` (mesma imagem da API, supercronic com os horários de
`api/crontab`, fuso de São Paulo) sobe com `make up` e roda todo dia:

| Horário | Comando | O que faz |
|---|---|---|
| 5h30 | `python -m app.jobs.limpar_noticias` | Notícias importadas há mais de `NOTICIAS_RETENCAO_DIAS` (30): apaga as que ninguém respondeu; **arquiva** (`status=archived`) as que algum jogador respondeu ou que estão em jogo numa partida, que saem do jogo e ficam para o histórico e a revisão |
| 6h | `python -m app.jobs.importar_noticias` | Até `NOTICIAS_POR_DIA` (50) notícias dos provedores de `NOTICIAS_PROVIDER` (`factcheck,gnews`: as duas APIs), **no máximo metade falsas e metade verdadeiras** (até 25 de cada; um lado curto não é completado com o outro), na categoria `NOTICIAS_CATEGORIA`. Mesmos filtros e deduplicação de `POST /admin/news/import`; notícias publicadas antes da janela de retenção ficam de fora, para não voltarem logo depois de apagadas |

As notícias entram como rascunho, ou já validadas com `NOTICIAS_PUBLICAR_DIRETO=true`. Se
os dois provedores estiverem fora, a importação do dia não grava nada e termina com erro no
log (`docker compose logs agendador-api`). Para rodar na hora: `make importar-noticias` e
`make limpar-noticias`.
