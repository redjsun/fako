#!/usr/bin/env bash
# Baixa as bases brutas para pesquisa/data/raw/, fixadas em commits conhecidos.
# Uso: bash pesquisa/dados/baixar_dados.sh   (ou: make dados)
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$RAIZ/data/raw"
mkdir -p "$RAW"

# Fake.br-Corpus (NILC/USP) — 3.600 pares de notícias falsas e verdadeiras.
FAKEBR_REPO="https://github.com/roneysco/Fake.br-Corpus.git"
FAKEBR_COMMIT="780f5516c4ae070761632d98ac3368f3ded09d35"

# FakeRecogna (Recogna/UNESP) — 5.951 checagens de 6 agências e 5.951 notícias reais.
# O texto vem lematizado; usamos URL e rótulo e recoletamos o texto original.
FAKERECOGNA_COMMIT="143842ba71e824a028572a89c9a522cbca40726e"
FAKERECOGNA_URL="https://huggingface.co/datasets/recogna-nlp/FakeRecogna/resolve/$FAKERECOGNA_COMMIT/FakeRecogna.csv"
FAKERECOGNA_SHA256="282110d0390a6dff37fedf43a22b3e61b97e30381bf96dacaa668ed45d3c4407"

# Só a versão recomendada para treino (size_normalized_texts: em cada par, o texto mais
# longo é cortado no tamanho do mais curto) e os metadados, que só existem em full_texts/.
if [ -d "$RAW/Fake.br-Corpus/size_normalized_texts" ]; then
  echo "Fake.br-Corpus já existe em pesquisa/data/raw/, pulando."
else
  echo "Baixando Fake.br-Corpus (size_normalized_texts e metadados)..."
  git clone --quiet --filter=blob:none --no-checkout "$FAKEBR_REPO" "$RAW/Fake.br-Corpus"
  git -C "$RAW/Fake.br-Corpus" sparse-checkout set --no-cone \
    "/size_normalized_texts/" "/full_texts/*-meta-information/" "/README.md"
  git -C "$RAW/Fake.br-Corpus" checkout --quiet "$FAKEBR_COMMIT"
fi

CSV="$RAW/FakeRecogna.csv"
if [ -f "$CSV" ]; then
  echo "FakeRecogna.csv já existe em pesquisa/data/raw/, pulando."
else
  echo "Baixando FakeRecogna..."
  curl -fsSL "$FAKERECOGNA_URL" -o "$CSV"
fi

echo "$FAKERECOGNA_SHA256  $CSV" | sha256sum -c --quiet - \
  || { echo "Hash do FakeRecogna.csv não confere." >&2; exit 1; }

# FakenewsBR v6 (variante pública, com e-mails/CPFs/telefones mascarados). Usamos só
# parte das falsas; ver ler_fakenewsbr() em pesquisa/dados/preparar_dados.py.
FAKENEWSBR_COMMIT="44a55e5c0dee6d8d96824de66dbe462796915b53"
FAKENEWSBR_URL="https://media.githubusercontent.com/media/thiago-cg/fakenewsbr-v4/$FAKENEWSBR_COMMIT/data/FakenewsBR_v6_public.csv"
FAKENEWSBR_SHA256="75dc4b45649e6d2232cca5acee018cb70596cd824d2ccc5827f6e295a81e9a0b"

CSV="$RAW/FakenewsBR_v6_public.csv"
if [ -f "$CSV" ]; then
  echo "FakenewsBR_v6_public.csv já existe em pesquisa/data/raw/, pulando."
else
  echo "Baixando FakenewsBR (214 MB)..."
  curl -fsSL "$FAKENEWSBR_URL" -o "$CSV"
fi

echo "$FAKENEWSBR_SHA256  $CSV" | sha256sum -c --quiet - \
  || { echo "Hash do FakenewsBR_v6_public.csv não confere." >&2; exit 1; }

# FakeTrue.Br (ERBD 2023) — 1.791 pares de falsa (Boatos.org) e verdadeira
# (G1, Folha, UOL) do mesmo assunto. O texto vem em minúsculas da origem. Sem licença
# declarada no repositório.
FAKETRUE_REPO="https://github.com/jpchav98/FakeTrue.Br.git"
FAKETRUE_COMMIT="37cdd5f2ac697a7cd3d678373f29a9d731a13e02"

if [ -f "$RAW/FakeTrue.Br/FakeTrueBr_corpus.csv" ]; then
  echo "FakeTrue.Br já existe em pesquisa/data/raw/, pulando."
else
  echo "Baixando FakeTrue.Br..."
  git clone --quiet "$FAKETRUE_REPO" "$RAW/FakeTrue.Br"
  git -C "$RAW/FakeTrue.Br" checkout --quiet "$FAKETRUE_COMMIT"
fi

# ClaimPT (LIAAD/INESC TEC) — notícias da Lusa anotadas com afirmações e não-afirmações.
# Português europeu e sem rótulo de veracidade: serve para avaliar a extração de
# afirmações, não para treinar o classificador. O repositório traz só uma amostra de 20
# artigos; o dataset completo (1.308) exige um Data Use Agreement (ver README).
CLAIMPT_REPO="https://github.com/LIAAD/ClaimPT.git"
CLAIMPT_COMMIT="317a170356036a189408ae9b774a44be3e55ccad"

if [ -d "$RAW/ClaimPT/dataset_sample" ]; then
  echo "ClaimPT já existe em pesquisa/data/raw/, pulando."
else
  echo "Baixando ClaimPT (amostra)..."
  git clone --quiet "$CLAIMPT_REPO" "$RAW/ClaimPT"
  git -C "$RAW/ClaimPT" checkout --quiet "$CLAIMPT_COMMIT"
fi

echo "Dados brutos prontos em pesquisa/data/raw/."
