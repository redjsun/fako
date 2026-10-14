"""Exporta o BERTimbau treinado (treinar_bert.py) para ONNX, para a API rodar sem PyTorch (#10).

Uso:
    python pesquisa/ml/exportar_onnx.py --modelo models/2026-11/bert

Grava na pasta do modelo, ao lado do que o treino e o calibrar.py já deixaram:
- `modelo.onnx`: entradas `input_ids` e `attention_mask` (lote × tokens, int64), saída
  `logits` (lote × 2), os logits das duas fronteiras CORAL antes da sigmoide;
- `tokenizer.json`: o tokenizador do BERTimbau no formato da biblioteca `tokenizers`;
- `onnx.json`: `max_tokens` e `versao`.

A API (api/app/ml/classificador.py, adaptador `BertOnnx`) lê esses três arquivos com
`onnxruntime` e `tokenizers` e aplica a mesma calibração (`calibracao.json`) e os mesmos
limiares (`limiares.json`). Antes de gravar, confere que as fronteiras do ONNX batem com as do
PyTorch em frases da validação.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

from treinar_bert import carregar_modelo, fronteiras

ARQUIVO_ONNX = "modelo.onnx"
ARQUIVO_TOKENIZADOR = "tokenizer.json"
ARQUIVO_META = "onnx.json"
TOLERANCIA = 1e-4
FRASES_CONFERENCIA = (
    "Vacina contra a covid tem chip para rastrear a população",
    "Ministério da Saúde amplia vacinação contra a gripe para todas as idades",
    "O governo vai confiscar a poupança de todos os brasileiros a partir de segunda-feira",
)


def exportar(pasta: Path, frases: tuple[str, ...] = FRASES_CONFERENCIA) -> float:
    """Grava modelo.onnx, tokenizer.json e onnx.json; devolve a maior diferença conferida."""
    import onnxruntime

    modelo = carregar_modelo(pasta)
    rede, tokenizador = modelo["rede"], modelo["tokenizador"]
    exemplo = tokenizador(list(frases), padding=True, return_tensors="pt")
    lote, tokens = torch.export.Dim("lote"), torch.export.Dim("tokens", max=512)
    torch.onnx.export(
        rede,
        (exemplo["input_ids"], exemplo["attention_mask"]),
        pasta / ARQUIVO_ONNX,
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_shapes=({0: lote, 1: tokens}, {0: lote, 1: tokens}),
        dynamo=True,
        external_data=False,  # um arquivo só, para publicar copiando a pasta
    )
    tokenizador.backend_tokenizer.save(str(pasta / ARQUIVO_TOKENIZADOR))
    (pasta / ARQUIVO_META).write_text(
        json.dumps({"max_tokens": modelo["max_tokens"], "versao": modelo["versao"]}, indent=2),
        encoding="utf-8",
    )

    p1_torch, p2_torch = fronteiras(list(frases), modelo)
    sessao = onnxruntime.InferenceSession(
        str(pasta / ARQUIVO_ONNX), providers=["CPUExecutionProvider"]
    )
    entrada = tokenizador(
        list(frases), truncation=True, max_length=modelo["max_tokens"], padding=True
    )
    logits = sessao.run(
        ["logits"],
        {
            "input_ids": np.array(entrada["input_ids"], dtype=np.int64),
            "attention_mask": np.array(entrada["attention_mask"], dtype=np.int64),
        },
    )[0]
    probabilidades = 1 / (1 + np.exp(-logits))
    p1_onnx = probabilidades[:, 0]
    p2_onnx = np.minimum(probabilidades[:, 1], p1_onnx)
    return float(max(np.abs(p1_onnx - p1_torch).max(), np.abs(p2_onnx - p2_torch).max()))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--modelo", type=Path, required=True)
    args = parser.parse_args()
    diferenca = exportar(args.modelo)
    print(f"Gravados {ARQUIVO_ONNX}, {ARQUIVO_TOKENIZADOR} e {ARQUIVO_META} em {args.modelo}")
    print(f"Maior diferença ONNX x PyTorch nas fronteiras: {diferenca:.2e}")
    if diferenca > TOLERANCIA:
        sys.exit(f"Diferença acima de {TOLERANCIA}: o ONNX não reproduz o modelo treinado")


if __name__ == "__main__":
    main()
