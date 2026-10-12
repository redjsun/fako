# FAKO

Jogo educativo (Snake) em que o jogador avalia a confiabilidade de afirmações reais, mais
um classificador de veracidade treinado com bases brasileiras de fake news. Ao comer a
maçã, o jogador recebe uma afirmação e marca de 0% a 100% o quanto confia nela; a cobrinha
só cresce quando ele erra.

## Documentação

A documentação completa (requisitos, arquitetura, pesquisa e dados, relatório do
classificador) está no site gerado com MkDocs:

```bash
make docs
```

Acesse em `http://localhost:8001`.

## Como executar

### Só o frontend

```bash
cd web
npm install
npm run dev
```

Acesse em `http://localhost:5173`.

### Projeto completo (Docker Compose)

```bash
make up
```

- Frontend: `http://localhost:5173`
- Backend API (FastAPI, docs em `/docs`): `http://localhost:8000`

`make help` lista todos os comandos disponíveis.

## Dados

As bases não ficam no Git: `pesquisa/data/` está no `.gitignore`. Para baixá-las e gerar a
versão unificada:

```bash
bash pesquisa/dados/baixar_dados.sh                     # Fake.br, FakeRecogna, FakeTrue.Br, FakenewsBR e ClaimPT
python pesquisa/dados/coletar_noticias.py               # texto das verdadeiras do FakeRecogna
python pesquisa/dados/coletar_boatos.py                 # texto das falsas do FakeRecogna
python pesquisa/dados/coletar_verdadeiras.py            # notícias verdadeiras dos portais (~1 h)
python pesquisa/dados/coletar_factcheck.py              # precisa de FACTCHECK_API_KEY no .env
python pesquisa/dados/preparar_dados.py                 # pesquisa/data/processed/dataset.jsonl
python pesquisa/dados/preparar_claimpt.py               # pesquisa/data/processed/claimpt.jsonl
make eda                                                # Jupyter Lab em http://localhost:8888
```

Os coletores usam `requests` e `beautifulsoup4` (`pesquisa/requirements.txt`), esperam 1 s
entre requisições ao mesmo site e guardam as páginas em cache em `pesquisa/data/raw/`, então
rodar de novo só baixa o que falta. O preparo usa só a biblioteca padrão.

**Coleta diária.** O serviço `agendador` do compose (sobe com `make up`) roda
`pesquisa/crontab` com o [supercronic](https://github.com/aptible/supercronic): às 3h,
`coletar_factcheck.py --incremental` e depois `preparar_dados.py`. Logs em
`docker compose logs agendador`.

**Anotação da equipe** (`doc/guia-classificacao.md` §7, `pesquisa/anotacoes/README.md`):

```bash
python pesquisa/dados/sortear_anotacao.py --rodada 1 --anotadores ana bruno --itens 600
python pesquisa/dados/consolidar_anotacoes.py importar --rodada 1 pesquisa/data/anotacao/rodada-01-*.csv
python pesquisa/dados/consolidar_anotacoes.py          # concordância e anotacoes/consolidado.csv
```

| Base | Classe | Origem | O que entra |
|------|--------|--------|-------------|
| Fake.br-Corpus | fake e true | [roneysco/Fake.br-Corpus](https://github.com/roneysco/Fake.br-Corpus) (NILC/USP), commit `780f551` | 3.600 pares de 2016–2018 |
| FakeRecogna | fake e true | [recogna-nlp/FakeRecogna](https://huggingface.co/datasets/recogna-nlp/FakeRecogna) (commit `143842b`, MIT) | só URL e rótulo; o texto é recoletado: as falsas do Boatos.org por `coletar_boatos.py` e as verdadeiras por `coletar_noticias.py` |
| FakeTrue.Br | fake e true | [jpchav98/FakeTrue.Br](https://github.com/jpchav98/FakeTrue.Br), commit `37cdd5f` | 1.791 pares Boatos.org × G1/Folha/UOL do mesmo assunto |
| Google Fact Check Tools API | fake, enganoso e true | 10 agências brasileiras, por `coletar_factcheck.py` | alegações com veredito "falso", de meia-verdade ou "verdadeiro"; a principal fonte de enganosos |
| FakenewsBR v6 | fake, enganoso e true | [thiago-cg/fakenewsbr-v4](https://github.com/thiago-cg/fakenewsbr-v4), commit `44a55e5`, variante pública | sub-bases de agência, mensagens de WhatsApp e de COVID |
| Verdadeiras (CSV próprio) | true | 9 portais, por `coletar_verdadeiras.py` | matérias de 2018 em diante |
| ClaimPT | sem veracidade | [LIAAD/ClaimPT](https://github.com/LIAAD/ClaimPT) (INESC TEC), commit `317a170` | notícias em português europeu, fora do `dataset.jsonl` (vai para `claimpt.jsonl`) |

**Licenças.** O Fake.br e o FakeTrue.Br não declaram licença. FakeRecogna e a compilação da
FakenewsBR são MIT, mas o conteúdo de terceiros na FakenewsBR segue os termos das fontes
originais (a sub-base `FakeWhatsApp.BR_2018` é GPL-3.0). O ClaimPT é CC BY-NC-ND 4.0: só uso
não comercial, sem redistribuir versões derivadas. Os textos dos checadores e dos portais
têm direitos dos veículos. O uso aqui é acadêmico, os dados não são redistribuídos e os
trabalhos são citados:

- Monteiro R.A. et al. (2018). *Contributions to the Study of Fake News in Portuguese:
  New Corpus and Automatic Detection Results*. PROPOR 2018, LNCS 11122.
- Garcia G.L., Afonso L.C.S., Papa J.P. (2022). *FakeRecogna: A New Brazilian Corpus for
  Fake News Detection*. PROPOR 2022, LNCS 13208.
- FakenewsBR, de thiago-cg (ver `CITATION.cff` no repositório).
- *FakeTrueBr: Um corpus brasileiro de notícias falsas*. XVIII Escola Regional de Banco de
  Dados (ERBD 2023), [SBC OpenLib](https://sol.sbc.org.br/index.php/erbd/article/view/24352).
- *ClaimPT: A Portuguese Dataset of Annotated Claims in News Articles* (LIAAD/INESC TEC),
  [arXiv:2601.19490](https://arxiv.org/abs/2601.19490).

Divisão em treino/validação/teste, critérios de rótulo, equilíbrio entre classes e a EDA
completa estão em `doc/dataset-verdadeiras.md`, `doc/eda.md` e `doc/relatorio-tecnico.md`,
no site de documentação.
