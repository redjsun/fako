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

Antes da primeira vez, crie o `.env` a partir do exemplo e gere o segredo dos tokens de login.
A API não sobe sem um `JWT_SECRET` próprio (32 bytes ou mais, diferente do exemplo):

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # cole em JWT_SECRET no .env
make up
```

- Frontend: `http://localhost:5173`
- Backend API (FastAPI, docs em `/docs`): `http://localhost:8000`

`make help` lista todos os comandos disponíveis.

### Classificador e LLM

O modelo não fica no Git: ele é publicado na
[Release do GitHub](https://github.com/redjsun/fako/releases) e baixado para `models/atual`.
É o classificador em **conjunto**: dois BERTimbau em ONNX (um treinado na manchete, outro na
afirmação extraída pela LLM), com a média das probabilidades.

```bash
make modelo        # baixa o modelo (~800 MB) para models/atual
```

No `.env`: `CLASSIFICADOR_PROVIDER=conjunto`, `CLASSIFICADOR_NO_JOGO=true` (o palpite aparece
depois da resposta) e a LLM, que extrai a afirmação e escreve o "Por quê?": `LLM_PROVIDER=openai`
com o Qwen pelo Ollama no host (`ollama pull qwen3:8b`; `LLM_BASE_URL` e `LLM_MODEL` como no
`.env.example`). Depois de trocar de modelo, `make reanalisar` refaz o palpite e o "Por quê?"
das questões do banco.

**Segurança do ambiente de desenvolvimento.** As portas publicadas (API, web, banco e
docs) escutam só em `127.0.0.1`, então nada fica exposto na rede local. As credenciais padrão do
banco (`fako`/`fako`) servem só para dev: troque `POSTGRES_USER` e `POSTGRES_PASSWORD` no `.env`
em qualquer outro ambiente. Se já houver um PostgreSQL na 5432 do host (comum no Windows), use
`POSTGRES_HOST_PORT=5433` no `.env`.
Administrador: `make admin u=usuario` (a senha é pedida no terminal). Senhas de jogador têm
de 8 caracteres a 72 bytes, e o login bloqueia por 15 minutos depois de 5 senhas erradas.

## Desenvolvimento

```bash
make test      # testes da API (pytest num banco fako_test separado)
make lint      # lint e formatação da API (ruff)
make format    # formata o código da API
make test-web  # tipos, lint e testes do frontend
```

O CI (`.github/workflows/ci.yml`) roda os mesmos comandos a cada push, com cobertura mínima
na API (80%), os testes do uso do modelo e da LLM (job "ML"), o build estrito dos docs
(`mkdocs build --strict`) e o build das imagens. A auditoria de dependências e a checagem de
links externos dos docs só avisam, sem bloquear.

## Dados do treino

O classificador foi treinado com as bases abaixo. O código de treino e os dados não ficam no
repositório: só o modelo pronto, na Release. Como os dados foram escolhidos, a divisão em
treino, validação e teste e os resultados estão no site de documentação.

| Base | Classe | Origem | O que entra |
|------|--------|--------|-------------|
| Fake.br-Corpus | fake e true | [roneysco/Fake.br-Corpus](https://github.com/roneysco/Fake.br-Corpus) (NILC/USP), commit `780f551` | 3.600 pares de 2016–2018 |
| FakeRecogna | fake e true | [recogna-nlp/FakeRecogna](https://huggingface.co/datasets/recogna-nlp/FakeRecogna) (commit `143842b`, MIT) | só URL e rótulo; o texto foi recoletado das páginas originais |
| FakeTrue.Br | fake e true | [jpchav98/FakeTrue.Br](https://github.com/jpchav98/FakeTrue.Br), commit `37cdd5f` | 1.791 pares Boatos.org × G1/Folha/UOL do mesmo assunto |
| Google Fact Check Tools API | fake, enganoso e true | 10 agências brasileiras | alegações com veredito "falso", de meia-verdade ou "verdadeiro"; a principal fonte de enganosos |
| FakenewsBR v6 | fake, enganoso e true | [thiago-cg/fakenewsbr-v4](https://github.com/thiago-cg/fakenewsbr-v4), commit `44a55e5`, variante pública | sub-bases de agência, mensagens de WhatsApp e de COVID |
| Verdadeiras (CSV próprio) | true | 9 portais | matérias de 2018 em diante |
| ClaimPT | sem veracidade | [LIAAD/ClaimPT](https://github.com/LIAAD/ClaimPT) (INESC TEC), commit `317a170` | notícias em português europeu, fora do dataset de treino |

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
