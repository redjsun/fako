"""Teste de atalho: quanto a forma do texto, sem o conteúdo, já separa as classes (issue #8).

Uso:
    python pesquisa/ml/atalho.py
    python pesquisa/ml/atalho.py --prompt api/app/prompts/extrair_afirmacoes_v1.txt   # + padronizado
    python pesquisa/ml/atalho.py --com-portal    # inclui os portais, como o notebook eda_2 (seção 7)

Uma regressão logística que só vê tamanho, pontuação, caixa alta e a primeira palavra. A AUC
dela é o piso: um classificador que não passa dela com folga aprendeu o formato, não a
veracidade. É só diagnóstico e nunca vai para a API.

Versões do texto:
    original                       `texto_curto`
    padronizado                    a afirmação extraída pela LLM (#20), com --prompt e --modelo
    original_mesmos_registros      as duas versões só nos registros que têm as duas, para
    padronizado_mesmos_registros   comparar na mesma população
Com a padronização igualando o formato, a AUC do padronizado deve ficar abaixo da do
original nos mesmos registros.

A saída vai para pesquisa/ml/saidas/atalho.json, que o avaliar.py (#13) lê para comparar cada modelo
com o piso.

Os dados vêm de `dados.carregar()` (#7): mesmos splits, limpeza e filtros dos modelos.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from dados import DATASET, Exemplo, carregar

SAIDA = Path(__file__).resolve().parent / "saidas" / "atalho.json"

CLASSES = ("falso", "enganoso", "verdadeiro")
SPLITS = ("treino", "validacao", "teste")
N_PRIMEIRAS = 30  # primeiras palavras mais comuns no treino que viram coluna
N_PESOS = 12

EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿]")
PALAVRA = re.compile(r"\w+")


def variaveis_de_forma(texto: str) -> dict[str, float]:
    """Variáveis que descrevem a forma do texto, sem o conteúdo."""
    palavras = PALAVRA.findall(texto)
    caixa_alta = sum(p.isupper() and len(p) > 1 for p in palavras)
    return {
        "palavras": len(palavras),
        "% caixa alta": 100 * caixa_alta / max(len(palavras), 1),
        "!": "!" in texto,
        "?": "?" in texto,
        "aspas": bool(re.search('["“”]', texto)),
        "dois-pontos": ":" in texto,
        "número": bool(re.search(r"\d", texto)),
        "emoji": bool(EMOJI.search(texto)),
        "termina com ponto": texto.rstrip().endswith("."),
        "começa com maiúscula": texto[:1].isupper(),
        "tudo minúsculo": texto == texto.lower(),
    }


def primeira_palavra(texto: str) -> str | None:
    m = PALAVRA.search(texto)
    return m[0].lower() if m else None


class ModeloAtalho:
    """Variáveis de forma padronizadas + regressão logística com classes balanceadas."""

    def fit(self, textos: list[str], y: list[str]) -> "ModeloAtalho":
        contagem = Counter(primeira_palavra(t) for t in textos)
        contagem.pop(None, None)
        self.primeiras = [p for p, _ in contagem.most_common(N_PRIMEIRAS)]
        self.nomes = [*variaveis_de_forma(""), *(f"1a_{p}" for p in self.primeiras), "1a_outra"]
        X = self._matriz(textos)
        self.escala = StandardScaler().fit(X)
        self.regressao = LogisticRegression(max_iter=2000, class_weight="balanced")
        self.regressao.fit(self.escala.transform(X), y)
        return self

    def _matriz(self, textos: list[str]) -> np.ndarray:
        indice = {p: i for i, p in enumerate(self.primeiras)}
        linhas = []
        for texto in textos:
            uma_quente = [0.0] * (len(self.primeiras) + 1)
            uma_quente[indice.get(primeira_palavra(texto), len(self.primeiras))] = 1.0
            linhas.append([float(v) for v in variaveis_de_forma(texto).values()] + uma_quente)
        return np.array(linhas)

    @property
    def classes(self) -> list[str]:
        return list(self.regressao.classes_)

    def predict_proba(self, textos: list[str]) -> np.ndarray:
        return self.regressao.predict_proba(self.escala.transform(self._matriz(textos)))

    def pesos(self, n: int = N_PESOS) -> list[dict]:
        """As n variáveis de maior peso (em módulo, em qualquer classe), com o peso por classe."""
        coef = self.regressao.coef_
        if coef.shape[0] == 1:  # com duas classes, o sklearn guarda um vetor só
            coef = np.vstack([-coef[0], coef[0]])
        ordem = np.argsort(-np.abs(coef).max(axis=0))[:n]
        return [
            {
                "variavel": self.nomes[j],
                **{c: round(float(coef[i, j]), 3) for i, c in enumerate(self.classes)},
            }
            for j in ordem
        ]


def auc(modelo: ModeloAtalho, textos: list[str], y: list[str]) -> dict:
    """AUC de cada classe contra o resto e a média delas (AUC macro, como o `ovr` do sklearn).

    Classes sem exemplo no split, ou que são o split inteiro, ficam de fora da média.
    """
    proba = modelo.predict_proba(textos)
    y = np.array(y)
    por_classe = {}
    for i, classe in enumerate(modelo.classes):
        alvo = y == classe
        if 0 < alvo.sum() < len(y):
            por_classe[classe] = round(float(roc_auc_score(alvo, proba[:, i])), 3)
    macro = round(float(np.mean(list(por_classe.values()))), 3) if por_classe else None
    return {"registros": len(y), "auc_macro": macro, "auc_por_classe": por_classe}


def rodar(splits: dict[str, list[Exemplo]]) -> dict:
    """Treina no treino e mede a AUC em cada split."""
    dados = {s: ([e.texto for e in ex], [e.veracidade for e in ex]) for s, ex in splits.items()}
    textos, y = dados.get("treino", ([], []))
    if len(set(y)) < 2:
        raise ValueError("Treino sem pelo menos duas classes.")
    modelo = ModeloAtalho().fit(textos, y)
    return {
        "splits": {s: auc(modelo, *dados[s]) for s in SPLITS if dados.get(s, ([],))[0]},
        "pesos": modelo.pesos(),
    }


def mesmos_registros(splits: dict[str, list[Exemplo]], ids: set[str]) -> dict[str, list[Exemplo]]:
    return {s: [e for e in ex if e.id in ids] for s, ex in splits.items()}


def imprimir(resultado: dict) -> None:
    for versao, saida in resultado["versoes"].items():
        print(f"\n{versao}   0,5 = acaso; 1,0 = separa tudo só pela forma")
        print(
            f"  {'split':10} {'registros':>9} {'macro':>6}  "
            + "  ".join(f"{c:>10}" for c in CLASSES)
        )
        for split, m in saida["splits"].items():
            classes = "  ".join(
                f"{m['auc_por_classe'].get(c, float('nan')):10.3f}" for c in CLASSES
            )
            print(f"  {split:10} {m['registros']:9} {m['auc_macro']:6.3f}  {classes}")
        print(f"  {N_PESOS} variáveis de maior peso:")
        for p in saida["pesos"]:
            pesos = "  ".join(f"{c} {p[c]:+.2f}" for c in CLASSES if c in p)
            print(f"    {p['variavel']:22} {pesos}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--prompt", type=Path, help="prompt da padronização (#20), para comparar")
    parser.add_argument(
        "--modelo",
        default=os.environ.get("LLM_MODEL"),
        help="modelo que gerou o cache da padronização (padrão: LLM_MODEL)",
    )
    parser.add_argument("--com-portal", action="store_true", help="inclui os portais (notebook)")
    parser.add_argument("--saida", type=Path, default=SAIDA)
    args = parser.parse_args()

    if not args.dataset.exists():
        sys.exit(f"{args.dataset} não encontrado. Rode antes: make dados")
    original = carregar(dataset=args.dataset, incluir_portal=args.com_portal)
    resultado = {
        "dataset_sha256": original.dataset_sha256,
        "com_portal": args.com_portal,
        "versoes": {"original": rodar(original.splits)},
    }

    if args.prompt:
        if not args.modelo:
            sys.exit("Informe o modelo da padronização: --modelo ou LLM_MODEL no .env.")
        padronizado = carregar(
            "padronizado", args.dataset, args.prompt, args.modelo, incluir_portal=args.com_portal
        )
        if not any(padronizado.splits.values()):
            sys.exit("Cache da padronização vazio para esse prompt e modelo. Rode: make padronizar")
        resultado["prompt"] = padronizado.prompt
        ids_p = {e.id for ex in padronizado.splits.values() for e in ex}
        ids_o = {e.id for ex in original.splits.values() for e in ex}
        versoes = resultado["versoes"]
        versoes["padronizado"] = rodar(padronizado.splits)
        versoes["original_mesmos_registros"] = rodar(mesmos_registros(original.splits, ids_p))
        versoes["padronizado_mesmos_registros"] = rodar(mesmos_registros(padronizado.splits, ids_o))

    imprimir(resultado)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGravado {args.saida}")


if __name__ == "__main__":
    main()
