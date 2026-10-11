# Notícias externas e classificador no jogo

Como manchetes de uma API de notícias viram afirmações do jogo, e como a referência TF-IDF
(regressão logística ordinal, `pesquisa/ml/treinar_referencia.py`) entra na API.

## Fluxo

```
provedor de notícias ──► normalização ──► filtros ──► deduplicação ──► classificador ──► rascunho
 (GNews ou fake)        (igual ao treino)                              (limiar admin)    (draft)
                                                                                           │
                                       jogo ◄── validated ◄── revisão humana ◄─────────────┘
                                         │
                                         └─ depois da resposta: palpite do modelo (limiar jogador)
```

1. `POST /admin/news/import` (`{"category": "saude", "quantity": 5}`) busca as manchetes no
   provedor (`integrations/noticias_client.py`).
2. Cada manchete é normalizada para o formato do `texto_curto` do treino
   (`integrations/normalizacao.py`): entidades HTML, sufixo " - Veículo" do agregador e a mesma
   `limpar()` de `pesquisa/ml/dados.py` (URLs e créditos de veículo nas pontas; caixa e
   pontuação mantidas).
3. Saem as que não servem como afirmação verdadeira, com os mesmos filtros das matérias de
   portal no treino (`motivo_filtro_portal()` de `pesquisa/dados/preparar_dados.py`): opinião,
   vídeo, ao vivo, pergunta, fala relatada e aspas; e as fora da faixa de tamanho.
4. Saem as repetidas (mesma URL ou mesmo texto, no lote ou no banco).
5. O classificador analisa com o limiar do admin; categoria, nota, confiança e versão do modelo
   ficam na questão (`model_*`) para apoiar a revisão.
6. A questão entra como rascunho (`status=draft`, `origin=news`), verdadeira, com a URL como
   fonte. Só chega ao jogador depois de aprovada em `PATCH /admin/questions/{id}/review`.

A resposta do import lista as importadas e as descartadas, com o motivo.

## Classificador na API

- Adaptador `ReferenciaTfidf` de `ClassificadorClient`
  (`integrations/classificador_client.py`), ligado por `CLASSIFICADOR_PROVIDER=referencia`.
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
| `NOTICIAS_PROVIDER` | `fake` (manchetes inventadas, sem chave) ou `gnews` |
| `NOTICIAS_API_KEY` | chave gratuita do GNews (https://gnews.io, 100 pedidos por dia) |

No GNews, as categorias do jogo viram tópicos: `saude` → `health`, `tecnologia` →
`technology`, `conhecimentos-gerais` → `science`; manchetes do Brasil, em português.

## Limites conhecidos

- Toda notícia importada entra como verdadeira: a API de notícias só traz matérias publicadas.
  As falsas do jogo continuam vindo da curadoria humana.
- Cada classe do treino tem uma "cara" própria (manchete, ponto final, minúsculas); o modelo
  pode puxar uma manchete para `confere` só pela forma (`pesquisa/ml/atalho.py`). A nota do
  modelo na curadoria é apoio à revisão, não um veredito.
