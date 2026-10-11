"""Modelo Baseline TF-IDF + Regressão Logística para o projeto FAKO.

Consome o pipeline de dados em ml/dados.py (Protocolo B, texto original),
ajusta o vocabulário e IDF exclusivamente no conjunto de treino e treina
dois classificadores independentes para Y1 e Y2 utilizando ponderação
por sample_weight.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from ml.dados import DadosML, carregar

# Configuração e reprodutibilidade
RANDOM_STATE = 42

DEFAULT_TFIDF_PARAMS = {
    "ngram_range": (1, 2),
    "min_df": 2,
    "sublinear_tf": True,
    "lowercase": False,  # Preserva maiúsculas conforme regras de ml/dados.py
}

DEFAULT_LOGISTIC_PARAMS = {
    "max_iter": 2000,
    "random_state": RANDOM_STATE,
}


@dataclass
class MetricasClassificacao:
    accuracy: float
    precision: float
    recall: float
    f1: float
    macro_f1: float
    balanced_accuracy: float
    confusion_matrix: list[list[int]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preparar_vetorizador(params: dict[str, Any] | None = None) -> TfidfVectorizer:
    """Cria o vetorizador TF-IDF com os hiperparâmetros configurados."""
    config = dict(DEFAULT_TFIDF_PARAMS)
    if params:
        config.update(params)
    return TfidfVectorizer(**config)


def treinar_vetorizador(
    textos_treino: list[str],
    params: dict[str, Any] | None = None,
) -> tuple[TfidfVectorizer, Any]:
    """Ajusta (fit) o vocabulário e IDF estritamente sobre os textos de treino."""
    vec = preparar_vetorizador(params)
    X_treino_vec = vec.fit_transform(textos_treino)
    return vec, X_treino_vec


def treinar_classificador(
    X_vec: Any,
    y: list[int],
    sample_weight: list[float] | None = None,
    params: dict[str, Any] | None = None,
) -> LogisticRegression:
    """Treina um classificador LogisticRegression sobre a matriz esparsa."""
    config = dict(DEFAULT_LOGISTIC_PARAMS)
    if params:
        config.update(params)
    clf = LogisticRegression(**config)
    clf.fit(X_vec, y, sample_weight=sample_weight)
    return clf


def avaliar_modelo(
    clf: LogisticRegression,
    X_vec: Any,
    y_true: list[int],
) -> MetricasClassificacao:
    """Calcula métricas completas de classificação para o split especificado."""
    y_pred = clf.predict(X_vec)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    return MetricasClassificacao(
        accuracy=float(accuracy_score(y_true, y_pred)),
        precision=float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        f1=float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        macro_f1=float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, y_pred)),
        confusion_matrix=cm,
    )


def salvar_artefatos(
    vectorizer: TfidfVectorizer,
    clf_y1: LogisticRegression,
    clf_y2: LogisticRegression,
    metadata: dict[str, Any],
    diretorio: Path | str = "models",
) -> dict[str, Path]:
    """Salva os modelos e metadados no diretório especificado."""
    dir_path = Path(diretorio)
    dir_path.mkdir(parents=True, exist_ok=True)

    caminho_vec = dir_path / "tfidf_vectorizer.joblib"
    caminho_y1 = dir_path / "tfidf_y1.joblib"
    caminho_y2 = dir_path / "tfidf_y2.joblib"
    caminho_meta = dir_path / "tfidf_metadata.json"

    joblib.dump(vectorizer, caminho_vec)
    joblib.dump(clf_y1, caminho_y1)
    joblib.dump(clf_y2, caminho_y2)

    with open(caminho_meta, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return {
        "vectorizer": caminho_vec,
        "y1": caminho_y1,
        "y2": caminho_y2,
        "metadata": caminho_meta,
    }


def carregar_artefatos(
    diretorio: Path | str = "models",
) -> tuple[TfidfVectorizer, LogisticRegression, LogisticRegression, dict[str, Any]]:
    """Carrega os modelos e metadados salvos."""
    dir_path = Path(diretorio)
    vec = joblib.load(dir_path / "tfidf_vectorizer.joblib")
    clf_y1 = joblib.load(dir_path / "tfidf_y1.joblib")
    clf_y2 = joblib.load(dir_path / "tfidf_y2.joblib")
    with open(dir_path / "tfidf_metadata.json", encoding="utf-8") as f:
        metadata = json.load(f)
    return vec, clf_y1, clf_y2, metadata


def formatar_matriz(cm: list[list[int]]) -> str:
    """Formata a matriz de confusão binária de forma legível."""
    tn, fp = cm[0][0], cm[0][1]
    fn, tp = cm[1][0], cm[1][1]
    return f"[[TN={tn:4}, FP={fp:4}], [FN={fn:4}, TP={tp:4}]]"


def executar_experimento(
    dados: DadosML | None = None,
    diretorio_modelos: Path | str = "models",
    salvar: bool = True,
) -> dict[str, Any]:
    """Executa o ciclo completo de treinamento, avaliação e persistência."""
    if dados is None:
        dados = carregar(texto="original")

    # Extração de textos e alvos
    X_treino = [r.texto for r in dados.treino]
    X_val = [r.texto for r in dados.validacao]
    X_teste = [r.texto for r in dados.teste]

    pesos_treino = [r.peso for r in dados.treino]

    y1_treino = [r.y1 for r in dados.treino]
    y1_val = [r.y1 for r in dados.validacao]
    y1_teste = [r.y1 for r in dados.teste]

    y2_treino = [r.y2 for r in dados.treino]
    y2_val = [r.y2 for r in dados.validacao]
    y2_teste = [r.y2 for r in dados.teste]

    # 1. Ajuste do TF-IDF SOMENTE no treino
    vectorizer, X_treino_vec = treinar_vetorizador(X_treino)

    # 2. Transformação estrita nos splits de validação e teste
    X_val_vec = vectorizer.transform(X_val)
    X_teste_vec = vectorizer.transform(X_teste)

    # 3. Treinamento dos classificadores Y1 e Y2
    clf_y1 = treinar_classificador(X_treino_vec, y1_treino, sample_weight=pesos_treino)
    clf_y2 = treinar_classificador(X_treino_vec, y2_treino, sample_weight=pesos_treino)

    # 4. Avaliação na validação
    metricas_val_y1 = avaliar_modelo(clf_y1, X_val_vec, y1_val)
    metricas_val_y2 = avaliar_modelo(clf_y2, X_val_vec, y2_val)

    # 5. Avaliação no teste
    metricas_teste_y1 = avaliar_modelo(clf_y1, X_teste_vec, y1_teste)
    metricas_teste_y2 = avaliar_modelo(clf_y2, X_teste_vec, y2_teste)

    # Preparação de metadados
    metadata = {
        "modelo": "TF-IDF + LogisticRegression",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "random_state": RANDOM_STATE,
        "dataset_hash": dados.dataset_hash,
        "total_exemplos": {
            "treino": len(dados.treino),
            "validacao": len(dados.validacao),
            "teste": len(dados.teste),
            "reserva": len(dados.reserva),
        },
        "vocabulario_tamanho": int(X_treino_vec.shape[1]),
        "tfidf_params": {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in DEFAULT_TFIDF_PARAMS.items()
        },
        "logistic_params": DEFAULT_LOGISTIC_PARAMS,
        "metricas_validacao": {
            "y1": metricas_val_y1.to_dict(),
            "y2": metricas_val_y2.to_dict(),
        },
        "metricas_teste": {
            "y1": metricas_teste_y1.to_dict(),
            "y2": metricas_teste_y2.to_dict(),
        },
    }

    caminhos_artefatos = {}
    if salvar:
        caminhos_artefatos = salvar_artefatos(
            vectorizer, clf_y1, clf_y2, metadata, diretorio=diretorio_modelos
        )

    return {
        "vectorizer": vectorizer,
        "clf_y1": clf_y1,
        "clf_y2": clf_y2,
        "metadata": metadata,
        "metricas_val_y1": metricas_val_y1,
        "metricas_val_y2": metricas_val_y2,
        "metricas_teste_y1": metricas_teste_y1,
        "metricas_teste_y2": metricas_teste_y2,
        "artefatos": caminhos_artefatos,
    }


def main():
    print("=" * 68)
    print("   TREINAMENTO E AVALIAÇÃO DO BASELINE TF-IDF (FAKO)")
    print("=" * 68)

    print("\n1. Carregando dados do pipeline oficial (ml.dados)...")
    dados = carregar(texto="original")
    print(f"   Dataset hash: {dados.dataset_hash}")
    print(f"   Exemplos: Treino={len(dados.treino)}, Validação={len(dados.validacao)}, Teste={len(dados.teste)}")

    print("\n2. Executando treinamento e avaliação...")
    resultado = executar_experimento(dados, diretorio_modelos="models", salvar=True)
    meta = resultado["metadata"]

    print(f"   Vocabulário TF-IDF gerado no treino: {meta['vocabulario_tamanho']} termos")
    print("   Artefatos salvos em models/:")
    for k, p in resultado["artefatos"].items():
        print(f"     - {k}: {p}")

    val_y1 = resultado["metricas_val_y1"]
    val_y2 = resultado["metricas_val_y2"]
    te_y1 = resultado["metricas_teste_y1"]
    te_y2 = resultado["metricas_teste_y2"]

    print("\n" + "=" * 68)
    print("                 RESULTADOS DE VALIDAÇÃO")
    print("=" * 68)
    print(f"{'Modelo':<10} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Macro F1':>10} {'Bal Acc':>10}")
    print("-" * 68)
    print(f"{'TF-IDF Y1':<10} {val_y1.accuracy*100:>7.2f}% {val_y1.precision*100:>7.2f}% {val_y1.recall*100:>7.2f}% {val_y1.f1*100:>7.2f}% {val_y1.macro_f1*100:>9.2f}% {val_y1.balanced_accuracy*100:>9.2f}%")
    print(f"{'TF-IDF Y2':<10} {val_y2.accuracy*100:>7.2f}% {val_y2.precision*100:>7.2f}% {val_y2.recall*100:>7.2f}% {val_y2.f1*100:>7.2f}% {val_y2.macro_f1*100:>9.2f}% {val_y2.balanced_accuracy*100:>9.2f}%")
    print("\nMatrizes de Confusão (Validação):")
    print(f"  Y1: {formatar_matriz(val_y1.confusion_matrix)}")
    print(f"  Y2: {formatar_matriz(val_y2.confusion_matrix)}")

    print("\n" + "=" * 68)
    print("                   RESULTADOS DE TESTE")
    print("=" * 68)
    print(f"{'Modelo':<10} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Macro F1':>10} {'Bal Acc':>10}")
    print("-" * 68)
    print(f"{'TF-IDF Y1':<10} {te_y1.accuracy*100:>7.2f}% {te_y1.precision*100:>7.2f}% {te_y1.recall*100:>7.2f}% {te_y1.f1*100:>7.2f}% {te_y1.macro_f1*100:>9.2f}% {te_y1.balanced_accuracy*100:>9.2f}%")
    print(f"{'TF-IDF Y2':<10} {te_y2.accuracy*100:>7.2f}% {te_y2.precision*100:>7.2f}% {te_y2.recall*100:>7.2f}% {te_y2.f1*100:>7.2f}% {te_y2.macro_f1*100:>9.2f}% {te_y2.balanced_accuracy*100:>9.2f}%")
    print("\nMatrizes de Confusão (Teste):")
    print(f"  Y1: {formatar_matriz(te_y1.confusion_matrix)}")
    print(f"  Y2: {formatar_matriz(te_y2.confusion_matrix)}")
    print("=" * 68)


if __name__ == "__main__":
    main()
