import json
import math

import pytest

onnx = pytest.importorskip("onnx")
from onnx import TensorProto, helper  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402
from tokenizers.models import WordPiece  # noqa: E402
from tokenizers.pre_tokenizers import Whitespace  # noqa: E402
from tokenizers.processors import TemplateProcessing  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.ml.classificador import BertOnnx, get_classificador  # noqa: E402

PALAVRAS = ["vacina", "tem", "chip", "a", "o", "governo"]


def sigmoide(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def publicar_bert_de_teste(pasta, max_tokens: int = 16, calibracao: dict | None = None):
    """ONNX com logits = 0,1 × (nº de tokens) + (-0,5, -1,0): a saída depende da entrada."""
    pasta.mkdir(parents=True, exist_ok=True)
    grafo = helper.make_graph(
        [
            helper.make_node("Cast", ["attention_mask"], ["mascara"], to=TensorProto.FLOAT),
            helper.make_node("ReduceSum", ["mascara", "eixo"], ["tokens"], keepdims=1),
            helper.make_node("MatMul", ["tokens", "peso"], ["produto"]),
            helper.make_node("Add", ["produto", "vies"], ["logits"]),
        ],
        "bert_de_teste",
        [
            helper.make_tensor_value_info("input_ids", TensorProto.INT64, ["lote", "tokens"]),
            helper.make_tensor_value_info("attention_mask", TensorProto.INT64, ["lote", "tokens"]),
        ],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["lote", 2])],
        initializer=[
            helper.make_tensor("eixo", TensorProto.INT64, [1], [1]),
            helper.make_tensor("peso", TensorProto.FLOAT, [1, 2], [0.1, 0.1]),
            helper.make_tensor("vies", TensorProto.FLOAT, [2], [-0.5, -1.0]),
        ],
    )
    modelo = helper.make_model(grafo, opset_imports=[helper.make_opsetid("", 18)])
    modelo.ir_version = 9
    onnx.save(modelo, pasta / "modelo.onnx")

    vocabulario = {t: i for i, t in enumerate(["[PAD]", "[UNK]", "[CLS]", "[SEP]", *PALAVRAS])}
    tokenizador = Tokenizer(WordPiece(vocabulario, unk_token="[UNK]"))
    tokenizador.pre_tokenizer = Whitespace()
    tokenizador.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 2), ("[SEP]", 3)]
    )
    tokenizador.save(str(pasta / "tokenizer.json"))
    (pasta / "onnx.json").write_text(json.dumps({"max_tokens": max_tokens, "versao": "bert-teste"}))
    (pasta / "config.json").write_text(json.dumps({"texto": "hibrido"}))
    if calibracao:
        (pasta / "calibracao.json").write_text(json.dumps(calibracao))


def test_bert_onnx_tokeniza_roda_e_aplica_a_regra_de_decisao(tmp_path):
    publicar_bert_de_teste(tmp_path)
    classificador = BertOnnx(tmp_path)

    analise = classificador.analisar("a vacina tem chip", "admin")  # 4 palavras + CLS + SEP

    p1, p2 = sigmoide(0.1 * 6 - 0.5), sigmoide(0.1 * 6 - 1.0)
    assert analise.probabilidades == pytest.approx(
        {"falso": 1 - p1, "enganoso": p1 - p2, "verdadeiro": p2}
    )
    assert analise.versao_modelo == "bert-teste" and analise.contribuicoes == []
    assert classificador.texto_de_entrada == "hibrido"


def test_bert_onnx_corta_em_max_tokens_e_aplica_a_calibracao(tmp_path):
    calibracao = {"fronteira_1": {"a": 0.5, "b": 0.1}, "fronteira_2": {"a": 0.5, "b": -0.2}}
    publicar_bert_de_teste(tmp_path, max_tokens=4, calibracao=calibracao)
    classificador = BertOnnx(tmp_path)

    longa = classificador.fronteiras("a vacina tem chip o governo tem a vacina")
    curta = classificador.fronteiras("a vacina")  # já tem 4 tokens com CLS e SEP

    assert longa == pytest.approx(curta)

    def platt(p, parametros):
        return sigmoide(parametros["a"] * math.log(p / (1 - p)) + parametros["b"])

    p1 = platt(sigmoide(0.1 * 4 - 0.5), calibracao["fronteira_1"])
    p2 = platt(sigmoide(0.1 * 4 - 1.0), calibracao["fronteira_2"])
    assert curta == pytest.approx((p1, min(p1, p2)))


def test_provedor_bert_carrega_o_modelo_publicado(tmp_path, monkeypatch):
    publicar_bert_de_teste(tmp_path / "atual")
    monkeypatch.setenv("CLASSIFICADOR_PROVIDER", "bert")
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        assert isinstance(get_classificador(), BertOnnx)
    finally:
        get_settings.cache_clear()
