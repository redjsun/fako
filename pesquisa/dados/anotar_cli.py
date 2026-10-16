"""Anotação pelo terminal, item a item, numa planilha de trabalho (#5).

Uso:
    python pesquisa/dados/anotar_cli.py ana               # rodada 1: pesquisa/data/anotacao/rodada-01-ana.csv
    python pesquisa/dados/anotar_cli.py ana --rodada 2

A planilha vem de sortear_anotacao.py (ou da pré-anotação pela LLM, com anotador
"pre_anotacao_llm") e fica fora do Git, porque tem o texto das matérias. Pendentes são os itens
pré-anotados pela LLM ou ainda sem veracidade. Cada resposta é gravada na hora; dá para sair
(q) e continuar depois. No fim, a planilha entra no repositório, sem o texto, por
`consolidar_anotacoes.py importar`.
"""

import argparse
import os
import textwrap
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PLANILHAS = RAIZ / "data" / "anotacao"
TIPOS = {
    "o": "opiniao",
    "f": "fabricado",
    "m": "manipulado",
    "i": "impostor",
    "c": "falso_contexto",
    "e": "enganoso",
    "l": "falsa_conexao",
    "n": "nenhum",
    "x": "fora_escopo",
}
VERAC = {"v": "verdadeiro", "e": "enganoso", "f": "falso"}
SINAIS = ["pede_compartilhamento", "urgencia", "apelo_emocional", "ataque"]
SEM_VERACIDADE = ("opiniao", "fora_escopo")

parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("anotador")
parser.add_argument("--rodada", type=int, default=1)
args = parser.parse_args()
EU = args.anotador
ARQ = PLANILHAS / f"rodada-{args.rodada:02d}-{EU}.csv"

df = pd.read_csv(ARQ, dtype=str, keep_default_na=False, encoding="utf-8-sig")
pend = df.index[
    (df["anotador"] == "pre_anotacao_llm")
    | ((df["veracidade"] == "") & ~df["tipo"].isin(SEM_VERACIDADE))
].tolist()
print(f"{ARQ.name}: {len(pend)} pendentes. Comandos: Enter=aceita, e=edita, s=pula, q=sai\n")


def salvar():
    temporario = ARQ.with_suffix(".tmp")
    df.to_csv(temporario, index=False, encoding="utf-8-sig")
    os.replace(temporario, ARQ)


def pergunta(msg, opcoes, atual):
    while True:
        r = input(f"{msg} {opcoes} [{atual}]: ").strip().lower()
        if r == "":
            return atual
        if r in opcoes:
            return opcoes[r] if isinstance(opcoes, dict) else r
        if r == "-":
            return ""
        print("  inválido")


for n, i in enumerate(pend, 1):
    r = df.loc[i]
    print("=" * 80)
    print(f"[{n}/{len(pend)}] {r['id']}")
    print(textwrap.fill(r["texto_curto"].replace("\n", " ")[:700], 100))
    if r["veredito_original"]:
        print(f"\nVEREDITO ORIGINAL: {r['veredito_original']}")
    print(
        f"\nPRÉ: tipo={r['tipo'] or '?'} | veracidade={r['veracidade'] or '-'} | "
        + " ".join(f"{s}={r[s]}" for s in SINAIS)
    )
    cmd = input("[Enter=aceita | e=edita | s=pula | q=sai]: ").strip().lower()
    if cmd == "q":
        break
    if cmd == "s":
        continue
    if cmd == "e" or not r["tipo"]:
        df.at[i, "tipo"] = pergunta("tipo", TIPOS, r["tipo"])
        if df.at[i, "tipo"] in SEM_VERACIDADE:
            df.at[i, "veracidade"] = ""
        else:
            df.at[i, "veracidade"] = pergunta("veracidade (- p/ vazio)", VERAC, r["veracidade"])
        for s in SINAIS:
            df.at[i, s] = pergunta(s, {"0": "0", "1": "1"}, r[s] or "0")
        obs = input("observacao (URL/dúvida, Enter p/ manter): ").strip()
        if obs:
            df.at[i, "observacao"] = obs
    df.at[i, "anotador"] = EU
    salvar()

print("Salvo.")
