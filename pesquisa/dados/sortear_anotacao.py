"""Sorteia os itens de uma rodada de anotação da equipe e monta uma planilha por anotador.

Uso:
    python pesquisa/dados/sortear_anotacao.py --rodada 1 --anotadores ana bruno --itens 600
    python pesquisa/dados/sortear_anotacao.py --rodada 2 --anotadores ana bruno carla \\
        --itens 900 --sobreposicao 0.15

Só biblioteca padrão. Lê pesquisa/data/processed/dataset.jsonl e grava as planilhas de
trabalho em pesquisa/data/anotacao/rodada-NN-<anotador>.csv, fora do Git: elas têm o
`texto_curto` e o `veredito_original` para o anotador ler. Depois de preenchidas, entram no
repositório por `consolidar_anotacoes.py importar`, que tira o texto.

Regras (doc/guia-classificacao.md §7 e §8, issue #5):
- Só `split_produto` em `treino` e `validacao`, nunca `teste`; sem `origem_rotulo=portal`;
  só registros com `texto_curto`; ids já anotados em rodadas anteriores ficam de fora.
- Estratificado: alterna as classes de veracidade e, dentro de cada classe, os estratos de
  `base`, `fonte` e ano, para cada classe ter fontes variadas.
- Sorteio determinístico (hash do id com o número da rodada): rodar de novo gera as mesmas
  planilhas.
- Os primeiros `--sobreposicao` dos itens vão para todos os anotadores (concordância); o
  resto é dividido entre eles.
- `tipo` vem pré-preenchido com o `tipo_sugerido` (rótulo fraco do veredito da agência),
  para o anotador confirmar ou corrigir. A veracidade fica em branco.
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from itertools import zip_longest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "processed" / "dataset.jsonl"
ANOTACOES = RAIZ / "anotacoes"
PLANILHAS = RAIZ / "data" / "anotacao"

SPLITS_ANOTAVEIS = ("treino", "validacao")
SINAIS = ("pede_compartilhamento", "urgencia", "apelo_emocional", "ataque")
# Colunas da planilha de trabalho (doc/guia-classificacao.md §7).
COLUNAS = (
    "id",
    "texto_curto",
    "veredito_original",
    "tipo",
    "tipo_secundario",
    "veracidade",
    *SINAIS,
    "anotador",
    "observacao",
)


def ordem(rodada: int, chave: str) -> str:
    return hashlib.sha1(f"anotacao-{rodada}-{chave}".encode()).hexdigest()


def intercalar(listas: list[list]) -> list:
    """Um de cada lista por vez: [[a1, a2], [b1]] -> [a1, b1, a2]."""
    return [item for grupo in zip_longest(*listas) for item in grupo if item is not None]


def ja_anotados() -> set[str]:
    ids = set()
    for arquivo in sorted(ANOTACOES.glob("rodada-*.csv")):
        with open(arquivo, encoding="utf-8", newline="") as entrada:
            ids.update(linha["id"] for linha in csv.DictReader(entrada))
    return ids


def candidatos(registros, excluir: set[str]) -> list[dict]:
    return [
        r
        for r in registros
        if r["split_produto"] in SPLITS_ANOTAVEIS
        and r["origem_rotulo"] != "portal"
        and (r.get("texto_curto") or "").strip()
        and r["id"] not in excluir
    ]


def sortear(registros: list[dict], itens: int, rodada: int) -> list[dict]:
    """Amostra estratificada por classe e, dentro dela, por base, fonte e ano."""
    estratos: dict[str, dict[tuple, list]] = defaultdict(lambda: defaultdict(list))
    for r in registros:
        estratos[r["veracidade"]][(r["base"], r["fonte"], (r.get("data") or "")[:4])].append(r)
    por_classe = []
    for classe in sorted(estratos):
        grupos = sorted(estratos[classe].items(), key=lambda par: ordem(rodada, repr(par[0])))
        por_classe.append(
            intercalar([sorted(g, key=lambda r: ordem(rodada, r["id"])) for _, g in grupos])
        )
    return intercalar(por_classe)[:itens]


def distribuir(amostra: list[dict], anotadores: list[str], sobreposicao: float, rodada: int):
    """Itens comuns a todos (concordância) e o resto dividido entre os anotadores."""
    comuns = math.ceil(sobreposicao * len(amostra)) if len(anotadores) > 1 else 0
    por_anotador = {a: list(amostra[:comuns]) for a in anotadores}
    for i, registro in enumerate(amostra[comuns:]):
        por_anotador[anotadores[i % len(anotadores)]].append(registro)
    for anotador, itens in por_anotador.items():
        # Embaralha para os itens comuns não ficarem todos no começo da planilha.
        itens.sort(key=lambda r: ordem(rodada, f"{anotador}-{r['id']}"))
    return por_anotador, comuns


def linha_planilha(registro: dict, anotador: str) -> dict:
    return {
        "id": registro["id"],
        "texto_curto": registro["texto_curto"],
        "veredito_original": registro.get("veredito_original") or "",
        "tipo": registro.get("tipo_sugerido") or "",
        "tipo_secundario": "",
        "veracidade": "",
        **dict.fromkeys(SINAIS, ""),
        "anotador": anotador,
        "observacao": "",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--rodada", type=int, required=True)
    parser.add_argument("--anotadores", nargs="+", required=True)
    parser.add_argument("--itens", type=int, required=True, help="itens distintos na rodada")
    parser.add_argument(
        "--sobreposicao", type=float, default=0.2, help="fração anotada por todos (0,1 a 0,2)"
    )
    args = parser.parse_args()
    if not DATASET.exists():
        sys.exit(f"{DATASET.relative_to(RAIZ)} não encontrado; rode antes: make dados")

    with open(DATASET, encoding="utf-8") as entrada:
        registros = candidatos((json.loads(linha) for linha in entrada), ja_anotados())
    amostra = sortear(registros, args.itens, args.rodada)
    por_anotador, comuns = distribuir(amostra, args.anotadores, args.sobreposicao, args.rodada)

    PLANILHAS.mkdir(parents=True, exist_ok=True)
    for anotador, itens in por_anotador.items():
        destino = PLANILHAS / f"rodada-{args.rodada:02d}-{anotador}.csv"
        # utf-8-sig: o Excel abre com os acentos certos.
        with open(destino, "w", encoding="utf-8-sig", newline="") as saida:
            escritor = csv.DictWriter(saida, fieldnames=COLUNAS)
            escritor.writeheader()
            escritor.writerows(linha_planilha(r, anotador) for r in itens)
        print(f"{destino.relative_to(RAIZ)}: {len(itens)} itens")

    classes = defaultdict(int)
    for r in amostra:
        classes[r["veracidade"]] += 1
    print(f"{len(amostra)} itens sorteados de {len(registros)} candidatos, {comuns} comuns a todos")
    print("por veracidade original:", dict(sorted(classes.items())))


if __name__ == "__main__":
    main()
