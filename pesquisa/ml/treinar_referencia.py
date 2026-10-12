"""Experimento 1: referência TF-IDF + regressão logística ordinal (issue #9).

Uso:
    python pesquisa/ml/treinar_referencia.py                                    # configs/referencia.toml
    python pesquisa/ml/treinar_referencia.py --config pesquisa/ml/configs/referencia-padronizado.toml
    python pesquisa/ml/avaliar.py --modelo models/2026-11/referencia            # o relatório

Modelo ordinal pelo método de Frank e Hall: duas regressões logísticas sobre o mesmo TF-IDF
(palavras e, se configurado, n-gramas de caracteres), ajustado só no treino.
- fronteira 1: y1 = veracidade > falso    → P1
- fronteira 2: y2 = veracidade > enganoso → P2, cortada em P1 se passar dela por ruído
`class_weight="balanced"` e o peso por `origem_rotulo` de dados.py. O `C` é escolhido na
grade da configuração pelo F1 macro das três classes na validação; o teste não é olhado.

Saídas na pasta `saida` da configuração:
- `referencia.joblib`: dicionário só com objetos do scikit-learn (vetorizador e as duas
  fronteiras), para a API carregar sem importar código da pesquisa;
- `previsoes.jsonl` e `config.json` (contrato do avaliar.py), com o `C` escolhido, a grade,
  o tempo de treino e a latência por frase.

`contribuicoes()` devolve as palavras que mais pesaram numa frase (valor TF-IDF × peso, exato
num modelo linear), para o admin auditar o modelo. Nunca vai para o jogador.
"""

import argparse
import time
from datetime import date
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from avaliar import gravar_previsoes, metricas
from configuracao import CONFIGS, Configuracao, carregar_configuracao
from dados import ORDEM, Exemplo, carregar

ARQUIVO_MODELO = "referencia.joblib"
FRONTEIRAS = (">falso", ">enganoso")
FRASES_LATENCIA = 200


def vetorizador(treino: dict) -> FeatureUnion:
    partes = [
        (
            "palavras",
            TfidfVectorizer(
                ngram_range=tuple(treino.get("ngram_palavras", (1, 2))),
                min_df=treino.get("min_df", 3),
                max_df=treino.get("max_df", 0.9),
                sublinear_tf=treino.get("sublinear_tf", True),
            ),
        )
    ]
    if treino.get("ngram_caracteres"):
        partes.append(
            (
                "caracteres",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=tuple(treino["ngram_caracteres"]),
                    min_df=treino.get("min_df", 3),
                    max_df=treino.get("max_df", 0.9),
                    sublinear_tf=treino.get("sublinear_tf", True),
                ),
            )
        )
    return FeatureUnion(partes)


def fronteiras(textos, modelo: dict) -> tuple[np.ndarray, np.ndarray]:
    """P1 e P2 de um modelo salvo (o dicionário do referencia.joblib)."""
    matriz = modelo["vetorizador"].transform(textos)
    p1 = modelo["fronteira_1"].predict_proba(matriz)[:, 1]
    p2 = modelo["fronteira_2"].predict_proba(matriz)[:, 1]
    return p1, np.minimum(p2, p1)


def contribuicoes(texto: str, modelo: dict, n: int = 10) -> dict[str, list[tuple[str, float]]]:
    """As `n` variáveis de maior |valor × peso| em cada fronteira (negativo puxa para falso)."""
    linha = modelo["vetorizador"].transform([texto]).tocsr()
    nomes = modelo["vetorizador"].get_feature_names_out()
    resultado = {}
    for nome, chave in zip(FRONTEIRAS, ("fronteira_1", "fronteira_2"), strict=True):
        pesos = modelo[chave].coef_[0]
        valores = linha.data * pesos[linha.indices]
        ordem = np.argsort(-np.abs(valores))[:n]
        resultado[nome] = [(legivel(nomes[linha.indices[i]]), float(valores[i])) for i in ordem]
    return resultado


def legivel(variavel: str) -> str:
    """ "palavras__lula disse" -> "lula disse"; "caracteres__ vac" -> "[ vac]" (trecho de palavra)."""
    tipo, _, termo = variavel.partition("__")
    return f"[{termo}]" if tipo == "caracteres" else termo


def treinar_fronteiras(matriz, exemplos: list[Exemplo], c: float, max_iter: int) -> dict:
    pesos = [e.peso for e in exemplos]
    return {
        f"fronteira_{i}": LogisticRegression(C=c, class_weight="balanced", max_iter=max_iter).fit(
            matriz, [getattr(e, alvo) for e in exemplos], sample_weight=pesos
        )
        for i, alvo in ((1, "y1"), (2, "y2"))
    }


def latencia_ms(modelo: dict, textos: list[str]) -> float:
    """Tempo médio para classificar uma frase de cada vez, como na API."""
    inicio = time.perf_counter()
    for texto in textos:
        fronteiras([texto], modelo)
    return 1000 * (time.perf_counter() - inicio) / max(len(textos), 1)


def treinar(config: Configuracao, saida: Path | None = None) -> dict:
    """Treina, escolhe o C na validação e grava modelo, previsões e configuração."""
    saida = saida or config.saida
    inicio = time.perf_counter()
    conjunto = carregar(**config.argumentos_dados())
    treino, validacao = conjunto.splits["treino"], conjunto.splits["validacao"]
    if len({e.veracidade for e in treino}) < 3 or not validacao:
        raise ValueError("O treino precisa das três classes e a validação não pode estar vazia")

    vetor = vetorizador(config.treino)
    matriz_treino = vetor.fit_transform([e.texto for e in treino])
    matriz_validacao = vetor.transform([e.texto for e in validacao])
    y_validacao = np.array([ORDEM[e.veracidade] for e in validacao])
    max_iter = config.treino.get("max_iter", 2000)

    grade, melhor = {}, None
    for c in config.treino.get("grade_c", [1.0]):
        candidato = treinar_fronteiras(matriz_treino, treino, c, max_iter)
        p1 = candidato["fronteira_1"].predict_proba(matriz_validacao)[:, 1]
        p2 = np.minimum(candidato["fronteira_2"].predict_proba(matriz_validacao)[:, 1], p1)
        f1 = metricas(y_validacao, p1, p2)["f1_macro"]
        grade[str(c)] = f1
        print(f"C = {c:<5}  F1 macro na validação {f1:.3f}")
        if melhor is None or f1 > melhor[1]:
            melhor = (c, f1, candidato)

    c, f1, escolhido = melhor
    versao = f"{config.nome}-{date.today().isoformat()}"
    modelo = {"vetorizador": vetor, **escolhido, "versao": versao, "fronteiras": FRONTEIRAS}
    saida.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, saida / ARQUIVO_MODELO, compress=3)

    previsoes = {}
    for split in ("validacao", "teste"):
        exemplos = conjunto.splits[split]
        if exemplos:
            previsoes[split] = (exemplos, *fronteiras([e.texto for e in exemplos], modelo))
    resultado = {
        "versao": versao,
        "c_escolhido": c,
        "f1_macro_validacao": f1,
        "grade_f1_macro_validacao": grade,
        "variaveis": len(vetor.get_feature_names_out()),
        "exemplos_treino": len(treino),
        "segundos_treino": round(time.perf_counter() - inicio, 1),
        "latencia_ms_por_frase": round(
            latencia_ms(modelo, [e.texto for e in validacao[:FRASES_LATENCIA]]), 3
        ),
    }
    gravar_previsoes(saida, previsoes, {**config.registro(conjunto.dataset_sha256), **resultado})
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--config", type=Path, default=CONFIGS / "referencia.toml")
    parser.add_argument("--saida", type=Path, help="sobrescreve a pasta de saída da configuração")
    args = parser.parse_args()
    config = carregar_configuracao(args.config)
    resultado = treinar(config, args.saida)
    saida = args.saida or config.saida
    print(
        f"\nC escolhido {resultado['c_escolhido']} (F1 macro {resultado['f1_macro_validacao']:.3f}), "
        f"{resultado['variaveis']} variáveis, {resultado['segundos_treino']} s de treino, "
        f"{resultado['latencia_ms_por_frase']} ms por frase"
    )
    print(
        f"Gravado {saida / ARQUIVO_MODELO}; avalie com: python pesquisa/ml/avaliar.py --modelo {saida}"
    )


if __name__ == "__main__":
    main()
