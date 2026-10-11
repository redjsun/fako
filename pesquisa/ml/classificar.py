"""Teste manual de um modelo treinado: classificar frases e conferir os dados.

Uso:
    python pesquisa/ml/classificar.py "Vacina contém chip para rastrear a população"
    python pesquisa/ml/classificar.py                        # modo interativo (linha vazia sai)
    python pesquisa/ml/classificar.py --amostra 10           # 10 exemplos da validação: rótulo × previsão
    python pesquisa/ml/classificar.py --amostra 10 --erros   # só os que o modelo errou
    python pesquisa/ml/classificar.py --exportar             # CSV da validação para abrir no Excel

O modelo padrão é models/2026-11/referencia (--modelo para outro). O CSV vai para
pesquisa/data/conferencia/, fora do Git (tem o texto das checagens). A categoria segue a regra
de decisão da API, com o limiar do jogador (--limiar para mudar).
"""

import argparse
import csv
import random
from pathlib import Path

import joblib
import numpy as np

from avaliar import ler_previsoes, nota, probabilidades
from dados import CLASSES, carregar
from treinar_referencia import ARQUIVO_MODELO, contribuicoes, fronteiras

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
MODELO = RAIZ_REPOSITORIO / "models" / "2026-11" / "referencia"
CONFERENCIA = RAIZ_REPOSITORIO / "pesquisa" / "data" / "conferencia"
CATEGORIA = {"falso": "falso", "enganoso": "enganoso", "verdadeiro": "confere"}


def categoria(proba: np.ndarray, limiar: float) -> str:
    return "incerto" if proba.max() < limiar else CATEGORIA[CLASSES[int(proba.argmax())]]


def barra(valor: float, largura: int = 20) -> str:
    return "█" * round(valor * largura)


def mostrar(texto: str, modelo: dict, limiar: float, n_palavras: int = 6):
    p1, p2 = fronteiras([texto], modelo)
    proba = probabilidades(p1, p2)[0]
    print(f"\n{texto}")
    for classe, valor in zip(CLASSES, proba, strict=True):
        print(f"  {classe:10} {valor:6.1%} {barra(valor)}")
    print(f"  nota {nota(p1, p2)[0]:.0f}/100  →  {categoria(proba, limiar)} (limiar {limiar:.0%})")
    for fronteira, termos in contribuicoes(texto, modelo, n_palavras).items():
        lista = ", ".join(f"{termo!r} {valor:+.2f}" for termo, valor in termos)
        print(f"  {fronteira:10} {lista}")


def exemplos_validacao(pasta: Path):
    conjunto = carregar()
    previsoes = ler_previsoes(pasta)
    for exemplo in conjunto.splits["validacao"]:
        if exemplo.id in previsoes:
            p1, p2 = previsoes[exemplo.id]
            yield exemplo, probabilidades([p1], [p2])[0], nota([p1], [p2])[0]


def amostra(pasta: Path, n: int, so_erros: bool, limiar: float, semente: int):
    linhas = list(exemplos_validacao(pasta))
    if so_erros:
        linhas = [x for x in linhas if CLASSES[int(x[1].argmax())] != x[0].veracidade]
    for exemplo, proba, valor in random.Random(semente).sample(linhas, min(n, len(linhas))):
        previsto = categoria(proba, limiar)
        marca = "ok  " if CATEGORIA[exemplo.veracidade] == previsto else "ERRO"
        print(
            f"{marca} rótulo {exemplo.veracidade:10} previsto {previsto:9} nota {valor:3.0f}  "
            f"{exemplo.fonte} {exemplo.ano}\n     {exemplo.texto[:150]}"
        )


def exportar(pasta: Path, limiar: float) -> Path:
    CONFERENCIA.mkdir(parents=True, exist_ok=True)
    destino = CONFERENCIA / f"validacao-{pasta.name}.csv"
    with open(destino, "w", encoding="utf-8-sig", newline="") as saida:
        escritor = csv.writer(saida)
        escritor.writerow(
            ["id", "texto", "rotulo", "previsto", "acertou", "nota", *(f"p_{c}" for c in CLASSES)]
            + ["fonte", "base", "ano", "origem_rotulo", "tipo_sugerido"]
        )
        for exemplo, proba, valor in exemplos_validacao(pasta):
            previsto = categoria(proba, limiar)
            escritor.writerow(
                [exemplo.id, exemplo.texto, exemplo.veracidade, previsto]
                + [int(CATEGORIA[exemplo.veracidade] == previsto), round(float(valor), 1)]
                + [round(float(p), 3) for p in proba]
                + [exemplo.fonte, exemplo.base, exemplo.ano, exemplo.origem_rotulo]
                + [exemplo.tipo_sugerido]
            )
    return destino


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("frases", nargs="*")
    parser.add_argument("--modelo", type=Path, default=MODELO)
    parser.add_argument(
        "--limiar", type=float, default=0.5, help="confiança mínima (senão incerto)"
    )
    parser.add_argument("--amostra", type=int, help="exemplos sorteados da validação")
    parser.add_argument("--erros", action="store_true", help="na amostra, só os erros")
    parser.add_argument("--semente", type=int, default=1)
    parser.add_argument("--exportar", action="store_true", help="CSV da validação com as previsões")
    args = parser.parse_args()

    if args.amostra:
        amostra(args.modelo, args.amostra, args.erros, args.limiar, args.semente)
        return
    if args.exportar:
        print(f"Gravado {exportar(args.modelo, args.limiar)}")
        return

    modelo = joblib.load(args.modelo / ARQUIVO_MODELO)
    print(f"Modelo {modelo['versao']}")
    for frase in args.frases:
        mostrar(frase, modelo, args.limiar)
    if not args.frases:
        while frase := input("\nFrase (vazia para sair): ").strip():
            mostrar(frase, modelo, args.limiar)


if __name__ == "__main__":
    main()
