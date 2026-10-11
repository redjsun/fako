# FAKO — Jogo Educativo de Checagem de Fatos (Snake)

O **FAKO** transforma a clássica mecânica do Snake (jogo da cobrinha) em uma ferramenta educativa para treinar a análise crítica e o combate à desinformação. O jogador guia a cobrinha pelo tabuleiro, coleta maçãs e avalia a confiabilidade de afirmações reais sobre Saúde, Tecnologia e Conhecimentos Gerais.

---

## 🎯 Mecânicas do Jogo

- **Tabuleiro em Grade 16x16:** Renderizado em `<canvas>` com suporte a displays Retina/High-DPI e design em tons de verde xadrez.
- **Bordas Conectadas (Torus):** A cobrinha atravessa as paredes e reaparece no lado oposto do tabuleiro.
- **Olhos Direcionais:** Os olhos da cobrinha acompanham ativamente a direção do movimento.
- **A Maçã Pausa o Jogo:** Ao comer a maçã, o jogo pausa e abre um balão de pergunta/afirmação sobre o tabuleiro.
- **Crescimento Apenas no Erro:** A cobrinha **não** cresce ao comer a maçã! Ela só cresce 1 segmento quando o jogador erra a avaliação da pergunta (> 15 pontos de distância da referência).
- **Fim de Jogo:** Quando a cobrinha colide com o próprio corpo.
- **Progressão em 6 Níveis:** A cada 10 maçãs coletadas e respondidas, o jogador avança de nível. A subida de nível é silenciosa (apenas atualiza o placar no cabeçalho). Completar o nível 6 é a condição de vitória.

---

## ⚖️ Sistema de Perguntas e Avaliação

1. **Afirmação e Categoria:** Cada maçã traz uma afirmação categorizada (*Saúde*, *Tecnologia* ou *Conhecimentos Gerais*).
2. **Tempo Limite de 15 Segundos:** Cronômetro regressivo com alerta visual e sonoro nos últimos 5 segundos. Caso o tempo se esgote, o palpite atual é confirmado automaticamente.
3. **Barra Deslizante (0% a 100%):** Passo de 5%, começando em 50% ("Nada confiável" a "Totalmente confiável").
4. **Revelação e Comparação:** Ao confirmar, a barra revela dois marcadores visuais:
   - **Você:** O palpite selecionado pelo jogador.
   - **Referência:** A taxa oficial calculada por especialistas/ciência.
5. **Critério de Pontuação:**
   - **Distância ≤ 15 pontos (Acerto):** Pontuação cheia (+100 pontos, com bônus de 120 para acerto exato). A cobrinha **não** cresce.
   - **Distância > 15 pontos (Erro):** 0 pontos. A cobrinha cresce 1 quadrado no próximo passo.
6. **Explicação e Fontes:** Apresenta justificativa pedagógica e fontes de órgãos oficiais (OMS, Fiocruz, Cochrane, EFF, NIST, NASA, etc.).

---

## 🎮 Controles

- **Teclado:** Setas direcionais ou teclas `W`, `A`, `S`, `D`.
- **Atalhos de Ação:** Tecla `Enter` confirma o palpite e avança as telas; barra de `Espaço` também retoma o jogo.
- **Celular / Toque:**
  - Botões virtuais na tela (D-pad direcional).
  - Gestos de deslize (*swipe*) diretamente sobre o tabuleiro.
- **Tema:** Alternância automática (claro/escuro) conforme o sistema operacional ou manual via botão `☀️ / 🌙 / 🌓`.
- **Efeitos Sonoros:** Sintetizados diretamente via Web Audio API (sem dependências externas de áudio ou rede), com botão para mutar/desmutar (`🔊 / 🔇`).

---

## 🏗️ Arquitetura e Modelo de Dados

### Modelo de Cada Pergunta
```typescript
interface Question {
  categoria: "Saúde" | "Tecnologia" | "Conhecimentos Gerais";
  afirmacao: string;
  confiabilidade_referencia: number; // 0 a 100
  explicacao: string;
  fonte?: string;
}
```

### Isolamento da Função `nextQuestion()`
A busca pela próxima pergunta está isolada em `src/services/questionService.ts`. No futuro, essa função pode ser substituída diretamente por uma chamada a uma API REST (`GET /api/questions/next`) ou banco de dados, sem alterar nenhuma lógica do jogo.

---

## 🚀 Como Executar

### Opção 1: Projeto React + Vite
Na pasta `web`:

```bash
cd web
npm install
npm run dev
```

Acesse em: `http://localhost:5173/`

### Opção 2: Docker Compose
```bash
docker compose up
# ou
make up
```

- Frontend: `http://localhost:5173`
- Backend API (FastAPI): `http://localhost:8000`

---

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

Os coletores usam `requests` e `beautifulsoup4` (`pesquisa/requirements.txt`), esperam
1 s entre requisições ao mesmo site e guardam as páginas em cache em `pesquisa/data/raw/`, então
rodar de novo só baixa o que falta. O preparo usa só a biblioteca padrão.

**Coleta diária.** O serviço `agendador` do compose (sobe com `make up`) roda
`pesquisa/crontab` com o [supercronic](https://github.com/aptible/supercronic): às 3h,
`coletar_factcheck.py --incremental` (só as páginas com checagens novas, uma requisição por
agência quando não há nada novo) e depois `preparar_dados.py`. Cada coleta acrescenta uma linha
em `pesquisa/data/raw/factcheck/execucoes.jsonl`, com as checagens novas e as requisições por
agência. Os logs ficam em `docker compose logs agendador`.

**Anotação da equipe** (`doc/guia-classificacao.md` §7, `pesquisa/anotacoes/README.md`):

```bash
python pesquisa/dados/sortear_anotacao.py --rodada 1 --anotadores ana bruno --itens 600
python pesquisa/dados/consolidar_anotacoes.py importar --rodada 1 pesquisa/data/anotacao/rodada-01-*.csv
python pesquisa/dados/consolidar_anotacoes.py          # concordância e anotacoes/consolidado.csv
```

| Base | Classe | Origem | O que entra |
|------|--------|--------|-------------|
| Fake.br-Corpus | fake e true | [roneysco/Fake.br-Corpus](https://github.com/roneysco/Fake.br-Corpus) (NILC/USP), commit `780f551` | 3.600 pares de 2016–2018 |
| FakeRecogna | fake e true | [recogna-nlp/FakeRecogna](https://huggingface.co/datasets/recogna-nlp/FakeRecogna) (commit `143842b`, MIT) | só URL e rótulo; o texto é recoletado: as falsas do Boatos.org por `coletar_boatos.py` (o boato que circulou, nunca o texto da checagem) e as verdadeiras por `coletar_noticias.py` |
| FakeTrue.Br | fake e true | [jpchav98/FakeTrue.Br](https://github.com/jpchav98/FakeTrue.Br), commit `37cdd5f` | 1.791 pares Boatos.org × G1/Folha/UOL do mesmo assunto; texto em minúsculas na origem |
| Google Fact Check Tools API | fake, enganoso e true | 10 agências brasileiras, por `pesquisa/dados/coletar_factcheck.py` | alegações com veredito "falso", de meia-verdade ou "verdadeiro"; a principal fonte de enganosos |
| FakenewsBR v6 | fake, enganoso e true | [thiago-cg/fakenewsbr-v4](https://github.com/thiago-cg/fakenewsbr-v4), commit `44a55e5`, variante pública | sub-bases de agência (enganosos, verdadeiros com veredito e uma amostra dos falsos) e as mensagens de WhatsApp e de COVID, com as duas classes (ver `FAKENEWSBR_INCLUIR` em `preparar_dados.py`) |
| Verdadeiras (CSV próprio) | true | 9 portais de linhas editoriais variadas, por `pesquisa/dados/coletar_verdadeiras.py` | matérias de 2018 em diante; completam os verdadeiros recentes |
| ClaimPT | sem veracidade | [LIAAD/ClaimPT](https://github.com/LIAAD/ClaimPT) (INESC TEC), commit `317a170` | notícias da Lusa (português europeu) com afirmações, não-afirmações e quem disse. Fica fora do `dataset.jsonl`: vai para `claimpt.jsonl`, para avaliar a extração de afirmações. O Git traz uma amostra de 20 artigos; o completo (1.308) exige um Data Use Agreement ([doi:10.25747/JY10-E413](https://doi.org/10.25747/JY10-E413)) e, quando obtido, vai em `pesquisa/data/raw/ClaimPT-completo/`, com a mesma estrutura da amostra |

**Critérios.** A veracidade tem três níveis: os vereditos "falso" (e equivalentes) viram
`falso`, as meias-verdades ("enganoso", "fora de contexto", "distorcido"...) viram
`enganoso` e os "verdadeiro" e "comprovado" viram `verdadeiro`. Sátira e vereditos
ambíguos ficam de fora. Nas verdadeiras, só entram portais cujo `robots.txt` não bloqueia
robôs de treino de IA.

**Divisão e equilíbrio** (`split_produto`, ver `definir_split_produto` e `equilibrar` em
`preparar_dados.py`). As bases pareadas (Fake.br, FakeRecogna, FakeTrue.Br) são sorteadas
por par em 80/10/10; as checagens e os portais vão por data (treino de 2016 a 2023,
validação em 2024, teste de 2025 em diante); as mensagens ficam no treino. Depois, as
classes são equilibradas, e o que sobra vira `reserva`:

| Split | Verdadeiro | Enganoso | Falso |
|---|---:|---:|---:|
| `treino` | 12.512 | 1.541 | 12.512 |
| `validacao` | 1.446 | 964 | 1.446 |
| `teste` | 1.638 | 1.092 | 1.638 |

Cada registro tem um `origem_rotulo` (`agencia`, `curadoria`, `portal`, `mensagem` ou
`equipe`) para pesar os exemplos no treino: portal e mensagem valem menos, porque o rótulo
"verdadeiro" deles é suposição ou só quer dizer "não é desinformação". Os itens anotados pela
equipe (`pesquisa/anotacoes/consolidado.csv`) ganham `tipo`, `sinais` e `origem_rotulo=equipe`.

**Licenças.** O Fake.br e o FakeTrue.Br não declaram licença. FakeRecogna e a compilação da FakenewsBR
são MIT, mas o conteúdo de terceiros na FakenewsBR segue os termos das fontes
originais (ver o `SOURCES_AND_LICENSES.md` dela; a sub-base `FakeWhatsApp.BR_2018` é
GPL-3.0). O ClaimPT é CC BY-NC-ND 4.0: só uso não comercial, e versões derivadas (como
o `claimpt.jsonl`) não podem ser redistribuídas. Os textos dos checadores e dos portais têm direitos dos veículos. O uso aqui é
acadêmico, os dados não são redistribuídos e os trabalhos são citados:

- Monteiro R.A. et al. (2018). *Contributions to the Study of Fake News in Portuguese:
  New Corpus and Automatic Detection Results*. PROPOR 2018, LNCS 11122.
- Garcia G.L., Afonso L.C.S., Papa J.P. (2022). *FakeRecogna: A New Brazilian Corpus for
  Fake News Detection*. PROPOR 2022, LNCS 13208.
- FakenewsBR, de thiago-cg (ver `CITATION.cff` no repositório).
- *FakeTrueBr: Um corpus brasileiro de notícias falsas*. XVIII Escola Regional de Banco de
  Dados (ERBD 2023), [SBC OpenLib](https://sol.sbc.org.br/index.php/erbd/article/view/24352).
- *ClaimPT: A Portuguese Dataset of Annotated Claims in News Articles* (LIAAD/INESC TEC),
  [arXiv:2601.19490](https://arxiv.org/abs/2601.19490).

**Análises.** A EDA da base atual está em dois notebooks: `pesquisa/notebooks/eda_1_datasets.ipynb`
explora cada dataset (linhas, classes, período, formato, fontes e uso no modelo) e
`pesquisa/notebooks/eda_2_conjunto.ipynb` analisa todos juntos (equilíbrio por split, origem do
rótulo, período, formato e teste de atalho). [doc/eda.md](doc/eda.md) registra a primeira
análise, que levou ao descarte do Fakepedia.
