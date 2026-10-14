import json

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
pytest.importorskip("onnx")
pytest.importorskip("onnxscript")
pytest.importorskip("onnxruntime")

from exportar_onnx import ARQUIVO_META, ARQUIVO_ONNX, ARQUIVO_TOKENIZADOR, exportar  # noqa: E402
from treinar_bert import Coral, salvar_modelo  # noqa: E402

PALAVRAS = ["vacina", "tem", "chip", "governo", "confisca", "poupança", "a", "o", "de"]


def bert_minusculo(pasta):
    """Um BERT de 1 camada, com vocabulário próprio: sem baixar nada."""
    vocabulario = pasta / "vocab.txt"
    vocabulario.write_text(
        "\n".join(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *PALAVRAS]), encoding="utf-8"
    )
    tokenizador = transformers.BertTokenizerFast(vocab_file=str(vocabulario), do_lower_case=False)
    config = transformers.BertConfig(
        vocab_size=5 + len(PALAVRAS),
        hidden_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=32,
    )
    torch.manual_seed(0)
    rede = Coral(transformers.BertModel(config))
    torch.nn.init.normal_(rede.vieses, std=1.0)
    salvar_modelo(rede, tokenizador, pasta, {"max_tokens": 16, "versao": "bert-teste"})


def test_onnx_reproduz_as_fronteiras_do_pytorch(tmp_path):
    bert_minusculo(tmp_path)
    diferenca = exportar(tmp_path, ("a vacina tem chip", "o governo confisca a poupança", "chip"))
    assert diferenca < 1e-4
    assert (tmp_path / ARQUIVO_ONNX).exists() and (tmp_path / ARQUIVO_TOKENIZADOR).exists()
    assert json.loads((tmp_path / ARQUIVO_META).read_text()) == {
        "max_tokens": 16,
        "versao": "bert-teste",
    }
