# FAKO

Jogo educativo (Snake) em que o jogador avalia a confiabilidade de afirmações, mais um
classificador de veracidade treinado com bases brasileiras de fake news.

Esta documentação cobre o produto (arquitetura, banco de perguntas, notícias externas),
a pesquisa e preparo dos dados, e o relatório técnico do classificador. Use as abas no
topo para navegar, ou veja o índice completo abaixo.

## Produto

| Documento | Conteúdo |
|---|---|
| [Arquitetura](arquitetura.md) | Organização em camadas + MVC no backend e no frontend |
| [Banco de perguntas do jogo](banco-perguntas.md) | Afirmação, contexto, notícias de API externa rotuladas, checagens e revisão humana |
| [Notícias externas e classificador](noticias-classificador.md) | Importação de manchetes (GNews), referência TF-IDF e rascunhos para revisão |

## Pesquisa e dados

| Documento | Conteúdo |
|---|---|
| [Análise exploratória dos dados](eda.md) | Qualidade, vieses e recomendações sobre as bases Fake.br e Fakepedia |
| [Dataset de verdadeiros confiáveis](dataset-verdadeiras.md) | Critérios de verdadeiro confiável, filtros e auditoria manual |
| [Guia de classificação e anotação](guia-classificacao.md) | Rótulos do framework de desordem informacional, divisão dos dados e guia de anotação |
| [Padronização pela LLM](padronizacao.md) | Lote e cache da extração de afirmações no treino |
| [Planejamento de coleta e retreino](planejamento-retreino.md) | Coleta diária e plano de retreino, com portão de qualidade e versionamento |

## Modelo

| Documento | Conteúdo |
|---|---|
| [Relatório técnico do classificador](relatorio-tecnico.md) | Preparação dos dados, treino, métricas, desafios e aprendizados |
