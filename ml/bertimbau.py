"""Modelo BERTimbau (neuralmind/bert-base-portuguese-cased) para o FAKO.

Consome o pipeline de dados oficial de ml/dados.py (Protocolo B, texto original),
utiliza tokenização cased do BERTimbau e realiza o fine-tuning de dois
classificadores independentes para Y1 e Y2 utilizando ponderação por sample_weight.
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from ml.dados import DadosML, carregar

logger = logging.getLogger("fako.ml.bertimbau")

# Hiperparâmetros e reprodutibilidade
MODEL_NAME = "neuralmind/bert-base-portuguese-cased"
RANDOM_STATE = 42
MAX_LENGTH = 256
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01


def fixar_seed(seed: int = RANDOM_STATE):
    """Garante reprodutibilidade em Python, NumPy e PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)


def obter_dispositivo() -> torch.device:
    """Seleciona MPS (Apple Silicon), CUDA ou CPU automaticamente."""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class NoticiasDataset(Dataset):
    """Dataset PyTorch para afirmações curtas com pesos amostrais."""

    def __init__(
        self,
        textos: list[str],
        labels: list[int],
        pesos: list[float],
        tokenizer: AutoTokenizer,
        max_length: int = MAX_LENGTH,
    ):
        self.labels = torch.tensor(labels, dtype=torch.long)
        self.pesos = torch.tensor(pesos, dtype=torch.float)
        self.encodings = tokenizer(
            textos,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "label": self.labels[idx],
            "peso": self.pesos[idx],
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


def avaliar_modelo(
    modelo: nn.Module,
    dataloader: DataLoader,
    dispositivo: torch.device,
) -> MetricasClassificacao:
    """Avalia o modelo em um DataLoader e retorna as métricas completas."""
    modelo.eval()
    todas_preds: list[int] = []
    todos_labels: list[int] = []

    with torch.no_grad():
        for lote in dataloader:
            input_ids = lote["input_ids"].to(dispositivo)
            attention_mask = lote["attention_mask"].to(dispositivo)
            labels = lote["label"].cpu().numpy()

            outputs = modelo(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=-1).cpu().numpy()

            todas_preds.extend(preds)
            todos_labels.extend(labels)

    cm = confusion_matrix(todos_labels, todas_preds, labels=[0, 1]).tolist()
    return MetricasClassificacao(
        accuracy=float(accuracy_score(todos_labels, todas_preds)),
        precision=float(precision_score(todos_labels, todas_preds, pos_label=1, zero_division=0)),
        recall=float(recall_score(todos_labels, todas_preds, pos_label=1, zero_division=0)),
        f1=float(f1_score(todos_labels, todas_preds, pos_label=1, zero_division=0)),
        macro_f1=float(f1_score(todos_labels, todas_preds, average="macro", zero_division=0)),
        balanced_accuracy=float(balanced_accuracy_score(todos_labels, todas_preds)),
        confusion_matrix=cm,
    )


def treinar_classificador(
    nome_alvo: str,
    textos_treino: list[str],
    labels_treino: list[int],
    pesos_treino: list[float],
    textos_val: list[str],
    labels_val: list[int],
    pesos_val: list[float],
    tokenizer: AutoTokenizer,
    dispositivo: torch.device,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
) -> tuple[nn.Module, MetricasClassificacao]:
    """Realiza o fine-tuning supervisionado de um modelo BERTimbau com sample_weight."""
    fixar_seed(RANDOM_STATE)

    # Inicializa modelo pré-treinado independente
    modelo = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
    ).to(dispositivo)

    ds_treino = NoticiasDataset(textos_treino, labels_treino, pesos_treino, tokenizer)
    ds_val = NoticiasDataset(textos_val, labels_val, pesos_val, tokenizer)

    dl_treino = DataLoader(ds_treino, batch_size=batch_size, shuffle=True)
    dl_val = DataLoader(ds_val, batch_size=batch_size, shuffle=False)

    otimizador = torch.optim.AdamW(
        modelo.parameters(),
        lr=learning_rate,
        weight_decay=WEIGHT_DECAY,
    )
    total_steps = len(dl_treino) * epochs
    warmup_steps = int(0.1 * total_steps)
    scheduler = get_linear_schedule_with_warmup(
        otimizador,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    criterio = nn.CrossEntropyLoss(reduction="none")

    melhor_macro_f1 = -1.0
    melhor_estado = None
    melhores_metricas_val = None

    print(f"\n--- Treinando BERTimbau {nome_alvo} ({epochs} épocas, batch={batch_size}, lr={learning_rate}) ---")

    for epoca in range(1, epochs + 1):
        modelo.train()
        loss_acumulada = 0.0
        total_exemplos = 0

        for lote in dl_treino:
            input_ids = lote["input_ids"].to(dispositivo)
            attention_mask = lote["attention_mask"].to(dispositivo)
            labels = lote["label"].to(dispositivo)
            pesos = lote["peso"].to(dispositivo)

            otimizador.zero_grad()
            outputs = modelo(input_ids=input_ids, attention_mask=attention_mask)

            # Aplicação de sample_weight na loss
            loss_unweighted = criterio(outputs.logits, labels)
            loss_ponderada = (loss_unweighted * pesos).sum() / (pesos.sum() + 1e-8)

            loss_ponderada.backward()
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), max_norm=1.0)
            otimizador.step()
            scheduler.step()

            loss_acumulada += loss_ponderada.item() * len(labels)
            total_exemplos += len(labels)

        loss_media_treino = loss_acumulada / total_exemplos
        metricas_val = avaliar_modelo(modelo, dl_val, dispositivo)

        print(
            f"  Época {epoca}/{epochs} | Loss Treino: {loss_media_treino:.4f} | "
            f"Val Acc: {metricas_val.accuracy*100:.2f}% | "
            f"Val Macro F1: {metricas_val.macro_f1*100:.2f}% | "
            f"Val Bal Acc: {metricas_val.balanced_accuracy*100:.2f}%"
        )

        if metricas_val.macro_f1 > melhor_macro_f1:
            melhor_macro_f1 = metricas_val.macro_f1
            melhor_estado = {k: v.cpu().clone() for k, v in modelo.state_dict().items()}
            melhores_metricas_val = metricas_val

    if melhor_estado:
        modelo.load_state_dict(melhor_estado)

    assert melhores_metricas_val is not None
    return modelo, melhores_metricas_val


def salvar_artefatos(
    modelo_y1: nn.Module,
    modelo_y2: nn.Module,
    tokenizer: AutoTokenizer,
    metadados: dict[str, Any],
    diretorio: Path | str = "models",
) -> dict[str, Path]:
    """Salva os modelos BERTimbau, o tokenizer e os metadados JSON."""
    dir_path = Path(diretorio)
    dir_path.mkdir(parents=True, exist_ok=True)

    dir_y1 = dir_path / "bertimbau_y1"
    dir_y2 = dir_path / "bertimbau_y2"
    caminho_meta = dir_path / "bertimbau_metadata.json"

    modelo_y1.save_pretrained(dir_y1)
    tokenizer.save_pretrained(dir_y1)

    modelo_y2.save_pretrained(dir_y2)
    tokenizer.save_pretrained(dir_y2)

    with open(caminho_meta, "w", encoding="utf-8") as f:
        json.dump(metadados, f, indent=2, ensure_ascii=False)

    return {
        "y1": dir_y1,
        "y2": dir_y2,
        "metadata": caminho_meta,
    }


def formatar_matriz(cm: list[list[int]]) -> str:
    """Formata a matriz de confusão binária de forma legível."""
    tn, fp = cm[0][0], cm[0][1]
    fn, tp = cm[1][0], cm[1][1]
    return f"[[TN={tn:4}, FP={fp:4}], [FN={fn:4}, TP={tp:4}]]"


def executar_experimento(
    dados: DadosML | None = None,
    diretorio_modelos: Path | str = "models",
    salvar: bool = True,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
) -> dict[str, Any]:
    """Executa o ciclo completo de fine-tuning e avaliação do BERTimbau."""
    fixar_seed(RANDOM_STATE)
    dispositivo = obter_dispositivo()

    if dados is None:
        dados = carregar(texto="original")

    # Extração rigorosa dos textos e alvos idênticos aos de TF-IDF
    X_treino = [r.texto for r in dados.treino]
    X_val = [r.texto for r in dados.validacao]
    X_teste = [r.texto for r in dados.teste]

    pesos_treino = [r.peso for r in dados.treino]
    pesos_val = [r.peso for r in dados.validacao]
    pesos_teste = [r.peso for r in dados.teste]

    y1_treino = [r.y1 for r in dados.treino]
    y1_val = [r.y1 for r in dados.validacao]
    y1_teste = [r.y1 for r in dados.teste]

    y2_treino = [r.y2 for r in dados.treino]
    y2_val = [r.y2 for r in dados.validacao]
    y2_teste = [r.y2 for r in dados.teste]

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    t_inicio = time.time()

    # 1. Treinamento BERTimbau Y1
    modelo_y1, metricas_val_y1 = treinar_classificador(
        nome_alvo="Y1 (É mais do que falso?)",
        textos_treino=X_treino,
        labels_treino=y1_treino,
        pesos_treino=pesos_treino,
        textos_val=X_val,
        labels_val=y1_val,
        pesos_val=pesos_val,
        tokenizer=tokenizer,
        dispositivo=dispositivo,
        epochs=epochs,
        batch_size=batch_size,
    )

    # 2. Treinamento BERTimbau Y2
    modelo_y2, metricas_val_y2 = treinar_classificador(
        nome_alvo="Y2 (É verdadeiro?)",
        textos_treino=X_treino,
        labels_treino=y2_treino,
        pesos_treino=pesos_treino,
        textos_val=X_val,
        labels_val=y2_val,
        pesos_val=pesos_val,
        tokenizer=tokenizer,
        dispositivo=dispositivo,
        epochs=epochs,
        batch_size=batch_size,
    )

    # 3. Avaliação no conjunto de teste (inédito)
    ds_teste_y1 = NoticiasDataset(X_teste, y1_teste, pesos_teste, tokenizer)
    ds_teste_y2 = NoticiasDataset(X_teste, y2_teste, pesos_teste, tokenizer)

    dl_teste_y1 = DataLoader(ds_teste_y1, batch_size=batch_size, shuffle=False)
    dl_teste_y2 = DataLoader(ds_teste_y2, batch_size=batch_size, shuffle=False)

    metricas_teste_y1 = avaliar_modelo(modelo_y1, dl_teste_y1, dispositivo)
    metricas_teste_y2 = avaliar_modelo(modelo_y2, dl_teste_y2, dispositivo)

    tempo_treinamento = time.time() - t_inicio

    # Metadados do experimento
    metadados = {
        "modelo": f"BERTimbau ({MODEL_NAME})",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dispositivo": str(dispositivo),
        "random_state": RANDOM_STATE,
        "tempo_treinamento_segundos": round(tempo_treinamento, 2),
        "dataset_hash": dados.dataset_hash,
        "total_exemplos": {
            "treino": len(dados.treino),
            "validacao": len(dados.validacao),
            "teste": len(dados.teste),
            "reserva": len(dados.reserva),
        },
        "hiperparametros": {
            "model_name": MODEL_NAME,
            "max_length": MAX_LENGTH,
            "batch_size": batch_size,
            "epochs": epochs,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
        },
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
            modelo_y1, modelo_y2, tokenizer, metadados, diretorio=diretorio_modelos
        )

    return {
        "modelo_y1": modelo_y1,
        "modelo_y2": modelo_y2,
        "tokenizer": tokenizer,
        "metadata": metadados,
        "metricas_val_y1": metricas_val_y1,
        "metricas_val_y2": metricas_val_y2,
        "metricas_teste_y1": metricas_teste_y1,
        "metricas_teste_y2": metricas_teste_y2,
        "artefatos": caminhos_artefatos,
    }


def main():
    print("=" * 68)
    print("      TREINAMENTO E AVALIAÇÃO DO BERTIMBAU (FAKO)")
    print("=" * 68)

    print("\n1. Carregando dados do pipeline oficial (ml.dados)...")
    dados = carregar(texto="original")
    print(f"   Dataset hash: {dados.dataset_hash}")
    print(f"   Exemplos: Treino={len(dados.treino)}, Validação={len(dados.validacao)}, Teste={len(dados.teste)}")
    print(f"   Dispositivo de aceleração: {obter_dispositivo()}")
    print(f"   max_length: {MAX_LENGTH}")

    print("\n2. Executando fine-tuning de BERTimbau Y1 e Y2...")
    resultado = executar_experimento(dados, diretorio_modelos="models", salvar=True)
    meta = resultado["metadata"]

    print(f"\n   Tempo total de treinamento: {meta.get('tempo_treinamento_segundos')}s")
    print("   Artefatos salvos em models/:")
    for k, p in resultado["artefatos"].items():
        print(f"     - {k}: {p}")

    val_y1 = resultado["metricas_val_y1"]
    val_y2 = resultado["metricas_val_y2"]
    te_y1 = resultado["metricas_teste_y1"]
    te_y2 = resultado["metricas_teste_y2"]

    print("\n" + "=" * 68)
    print("            RESULTADOS DE VALIDAÇÃO (BERTIMBAU)")
    print("=" * 68)
    print(f"{'Modelo':<15} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Macro F1':>10} {'Bal Acc':>10}")
    print("-" * 68)
    print(f"{'BERTimbau Y1':<15} {val_y1.accuracy*100:>7.2f}% {val_y1.precision*100:>7.2f}% {val_y1.recall*100:>7.2f}% {val_y1.f1*100:>7.2f}% {val_y1.macro_f1*100:>9.2f}% {val_y1.balanced_accuracy*100:>9.2f}%")
    print(f"{'BERTimbau Y2':<15} {val_y2.accuracy*100:>7.2f}% {val_y2.precision*100:>7.2f}% {val_y2.recall*100:>7.2f}% {val_y2.f1*100:>7.2f}% {val_y2.macro_f1*100:>9.2f}% {val_y2.balanced_accuracy*100:>9.2f}%")
    print("\nMatrizes de Confusão (Validação):")
    print(f"  Y1: {formatar_matriz(val_y1.confusion_matrix)}")
    print(f"  Y2: {formatar_matriz(val_y2.confusion_matrix)}")

    print("\n" + "=" * 68)
    print("              RESULTADOS DE TESTE (BERTIMBAU)")
    print("=" * 68)
    print(f"{'Modelo':<15} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Macro F1':>10} {'Bal Acc':>10}")
    print("-" * 68)
    print(f"{'BERTimbau Y1':<15} {te_y1.accuracy*100:>7.2f}% {te_y1.precision*100:>7.2f}% {te_y1.recall*100:>7.2f}% {te_y1.f1*100:>7.2f}% {te_y1.macro_f1*100:>9.2f}% {te_y1.balanced_accuracy*100:>9.2f}%")
    print(f"{'BERTimbau Y2':<15} {te_y2.accuracy*100:>7.2f}% {te_y2.precision*100:>7.2f}% {te_y2.recall*100:>7.2f}% {te_y2.f1*100:>7.2f}% {te_y2.macro_f1*100:>9.2f}% {te_y2.balanced_accuracy*100:>9.2f}%")
    print("\nMatrizes de Confusão (Teste):")
    print(f"  Y1: {formatar_matriz(te_y1.confusion_matrix)}")
    print(f"  Y2: {formatar_matriz(te_y2.confusion_matrix)}")
    print("=" * 68)


if __name__ == "__main__":
    main()
