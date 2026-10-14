"""Calibração das fronteiras e limiares de abstenção (issue #12, parte da referência).

Uso:
    python pesquisa/ml/calibrar.py --modelo models/2026-11/referencia

Um modelo pode dizer "90% falso" e acertar 70% das vezes: a porcentagem mostrada ao jogador
precisa ser honesta. Na `validacao`:

1. **Platt scaling** por fronteira: uma regressão logística de uma variável sobre o logit de
   P1 (alvo veracidade > falso) e outra sobre o de P2 (veracidade > enganoso). Grava
   `calibracao.json` (`{"fronteira_1": {"a", "b"}, "fronteira_2": {"a", "b"}}`); a API aplica
   `sigmoide(a · logit(p) + b)` (api/app/ml/classificador.py).
2. Regrava `previsoes.jsonl` com as fronteiras calibradas (o contrato do avaliar.py) e guarda
   as brutas em `previsoes_brutas.jsonl`. Rodar de novo parte sempre das brutas.
3. **Limiares** sobre a confiança calibrada (a maior das três probabilidades), gravados em
   `limiares.json`: o menor limiar em que no máximo 5% (admin) e 1% (jogador) dos verdadeiros
   viram `falso`. Abaixo do limiar, a saída é `incerto`.

Imprime o ECE da validação antes e depois e a % de `incerto` em cada limiar. O teste não é
usado aqui.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from avaliar import ece, probabilidades
from dados import CLASSES, carregar

TAXAS = {"admin": 0.05, "jogador": 0.01}
GRADE = np.round(np.arange(0.34, 1.0001, 0.01), 2)  # abaixo de 1/3 a confiança não decide
EPSILON = 1e-6
# Nenhum limiar da grade respeita a taxa: acima de 1, toda saída vira `incerto`.
SEM_DECISAO = 1.01


def ler_brutas(caminho: Path) -> dict[str, tuple[float, float]]:
    with open(caminho, encoding="utf-8") as entrada:
        return {(linha := json.loads(texto))["id"]: (linha["p1"], linha["p2"]) for texto in entrada}


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, float), EPSILON, 1 - EPSILON)
    return np.log(p / (1 - p))


def ajustar_platt(p: np.ndarray, alvo: np.ndarray) -> dict[str, float]:
    """`a` e `b` de sigmoide(a · logit(p) + b), ajustados por máxima verossimilhança."""
    regressao = LogisticRegression(C=1e6, max_iter=1000)  # praticamente sem regularização
    regressao.fit(logit(p).reshape(-1, 1), np.asarray(alvo, int))
    return {"a": float(regressao.coef_[0, 0]), "b": float(regressao.intercept_[0])}


def aplicar_platt(p: np.ndarray, parametros: dict[str, float]) -> np.ndarray:
    return 1 / (1 + np.exp(-(parametros["a"] * logit(p) + parametros["b"])))


def calibrar(p1: np.ndarray, p2: np.ndarray, y: np.ndarray) -> dict[str, dict[str, float]]:
    """Platt por fronteira; `y` em índices de CLASSES (0 falso, 1 enganoso, 2 verdadeiro)."""
    return {
        "fronteira_1": ajustar_platt(p1, y > 0),
        "fronteira_2": ajustar_platt(np.minimum(p2, p1), y > 1),
    }


def aplicar(p1: np.ndarray, p2: np.ndarray, calibracao: dict) -> tuple[np.ndarray, np.ndarray]:
    c1 = aplicar_platt(p1, calibracao["fronteira_1"])
    c2 = aplicar_platt(np.minimum(p2, p1), calibracao["fronteira_2"])
    return c1, np.minimum(c2, c1)  # P1 >= P2 continua valendo


def taxa_verdadeiro_vira_falso(proba: np.ndarray, y: np.ndarray, limiar: float) -> float:
    verdadeiros = proba[y == 2]
    if not len(verdadeiros):
        return 0.0
    viram_falso = (verdadeiros.argmax(axis=1) == 0) & (verdadeiros.max(axis=1) >= limiar)
    return float(viram_falso.mean())


def limiares(proba: np.ndarray, y: np.ndarray, taxas: dict[str, float] = TAXAS) -> dict:
    """Para cada uso, o menor limiar da grade que respeita a taxa de verdadeiros → falso."""
    resultado = {}
    for uso, taxa in taxas.items():
        resultado[uso] = next(
            (float(t) for t in GRADE if taxa_verdadeiro_vira_falso(proba, y, t) <= taxa),
            SEM_DECISAO,
        )
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--modelo", type=Path, required=True)
    args = parser.parse_args()
    pasta = args.modelo
    brutas = pasta / "previsoes_brutas.jsonl"
    if not brutas.exists():
        if not (pasta / "previsoes.jsonl").exists():
            sys.exit(f"{pasta}/previsoes.jsonl não encontrado: treine o modelo antes")
        shutil.copy(pasta / "previsoes.jsonl", brutas)

    config = json.loads((pasta / "config.json").read_text(encoding="utf-8"))
    conjunto = carregar(
        texto=config.get("texto", "original"),
        prompt=Path(config["prompt"]) if config.get("prompt") else None,
        modelo=config.get("modelo_llm"),
    )
    previsoes = ler_brutas(brutas)
    validacao = [e for e in conjunto.splits["validacao"] if e.id in previsoes]
    y = np.array([CLASSES.index(e.veracidade) for e in validacao])
    p1 = np.array([previsoes[e.id][0] for e in validacao])
    p2 = np.array([previsoes[e.id][1] for e in validacao])

    calibracao = calibrar(p1, p2, y)
    c1, c2 = aplicar(p1, p2, calibracao)
    antes, depois = ece(probabilidades(p1, p2), y)[0], ece(probabilidades(c1, c2), y)[0]
    escolhidos = limiares(probabilidades(c1, c2), y)

    (pasta / "calibracao.json").write_text(json.dumps(calibracao, indent=2), encoding="utf-8")
    (pasta / "limiares.json").write_text(json.dumps(escolhidos, indent=2), encoding="utf-8")
    with (
        open(brutas, encoding="utf-8") as entrada,
        open(pasta / "previsoes.jsonl", "w", encoding="utf-8", newline="\n") as saida,
    ):
        for texto in entrada:
            linha = json.loads(texto)
            a, b = aplicar(np.array([linha["p1"]]), np.array([linha["p2"]]), calibracao)
            saida.write(json.dumps({**linha, "p1": float(a[0]), "p2": float(b[0])}) + "\n")

    confianca = probabilidades(c1, c2).max(axis=1)
    print(f"validação: {len(y)} exemplos, ECE {antes:.3f} -> {depois:.3f}")
    for uso, limiar in escolhidos.items():
        taxa = taxa_verdadeiro_vira_falso(probabilidades(c1, c2), y, limiar)
        print(
            f"limiar {uso}: {limiar:.2f} ({np.mean(confianca < limiar):.0%} incerto, "
            f"{taxa:.1%} dos verdadeiros viram falso; meta {TAXAS[uso]:.0%})"
        )
    print(f"Gravados {pasta}/calibracao.json, limiares.json e previsoes.jsonl calibradas")


if __name__ == "__main__":
    main()
