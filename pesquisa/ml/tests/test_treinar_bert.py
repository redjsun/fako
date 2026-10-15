import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from dados import Exemplo  # noqa: E402
from treinar_bert import (  # noqa: E402
    escolher_dispositivo,
    fronteiras_de_logits,
    pesos_por_classe,
)


def exemplo(veracidade: str) -> Exemplo:
    ordem = ("falso", "enganoso", "verdadeiro").index(veracidade)
    return Exemplo(
        id=veracidade,
        texto="frase",
        veracidade=veracidade,
        y1=int(ordem > 0),
        y2=int(ordem > 1),
        tipo=None,
        tipo_sugerido=None,
        ano=None,
        fonte=None,
        base="teste",
        origem_rotulo="agencia",
        peso=1.0,
        checado=True,
    )


def test_fronteiras_respeitam_a_ordem_mesmo_com_vies_invertido():
    logits = torch.tensor([[0.0, 2.0], [3.0, -1.0], [-2.0, -4.0]])
    p1, p2 = fronteiras_de_logits(logits)
    assert np.all(p2 <= p1)
    probabilidades = np.column_stack([1 - p1, p1 - p2, p2])
    np.testing.assert_allclose(probabilidades.sum(axis=1), 1)
    assert np.all(probabilidades >= 0)


def test_classe_rara_pesa_mais():
    exemplos = [exemplo("falso")] * 6 + [exemplo("enganoso")] * 3 + [exemplo("verdadeiro")]
    pesos = pesos_por_classe(exemplos)
    assert pesos["verdadeiro"] > pesos["enganoso"] > pesos["falso"]
    total = sum(pesos[e.veracidade] for e in exemplos)
    assert total == pytest.approx(len(exemplos))


def test_dispositivo_prefere_cuda_depois_mps_depois_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert escolher_dispositivo().type == "cuda"
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert escolher_dispositivo().type == "mps"
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    assert escolher_dispositivo().type == "cpu"


def test_dispositivo_pedido_precisa_existir(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert escolher_dispositivo("cpu").type == "cpu"
    with pytest.raises(ValueError, match="indisponível"):
        escolher_dispositivo("cuda")
    with pytest.raises(ValueError, match="desconhecido"):
        escolher_dispositivo("tpu")


PALAVRAS = ["vacina", "tem", "chip", "governo", "confisca", "poupança", "a", "o", "de"]


@pytest.fixture
def bert_minusculo(tmp_path, monkeypatch):
    """Troca o BERTimbau por um BERT de 1 camada, sem baixar nada."""
    import transformers

    import treinar_bert

    vocabulario = tmp_path / "vocab.txt"
    vocabulario.write_text(
        "\n".join(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *PALAVRAS]), encoding="utf-8"
    )
    config = transformers.BertConfig(
        vocab_size=5 + len(PALAVRAS),
        hidden_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=32,
    )
    monkeypatch.setattr(
        treinar_bert.AutoTokenizer,
        "from_pretrained",
        lambda *_: transformers.BertTokenizerFast(vocab_file=str(vocabulario)),
    )
    monkeypatch.setattr(
        treinar_bert.AutoModel, "from_pretrained", lambda *_: transformers.BertModel(config)
    )
    return treinar_bert


def exemplos_de_treino():
    frases = {
        "falso": "a vacina tem chip",
        "enganoso": "o governo confisca a poupança",
        "verdadeiro": "vacina de governo",
    }
    return [
        Exemplo(**{**exemplo(v).__dict__, "id": f"{v}{i}", "texto": frases[v]})
        for v in frases
        for i in range(4)
    ]


def test_retomada_continua_da_epoca_salva_e_da_o_mesmo_resultado(bert_minusculo, tmp_path):
    from configuracao import Configuracao

    config = Configuracao(
        nome="bert",
        modelo="bert",
        saida=tmp_path,
        dataset=tmp_path / "x.jsonl",
        treino={"modelo_base": "x", "max_epocas": 2, "paciencia": 5, "lote": 4},
    )
    treino = validacao = exemplos_de_treino()
    assinatura = {"configuracao_sha1": "c", "dataset_sha256": "d"}

    f1_direto, _, rede_direta, historico_direto = bert_minusculo.treinar_semente(
        7, treino, validacao, config
    )

    # Uma rodada que "pausa" depois da época 1: a avaliação da época 2 é interrompida.
    retomada = bert_minusculo.caminho_retomada(tmp_path, 7)
    original = bert_minusculo.fronteiras
    chamadas = []

    def pausa_na_segunda(*args, **kwargs):
        chamadas.append(1)
        if len(chamadas) == 2:
            raise KeyboardInterrupt
        return original(*args, **kwargs)

    bert_minusculo.fronteiras = pausa_na_segunda
    try:
        with pytest.raises(KeyboardInterrupt):
            bert_minusculo.treinar_semente(7, treino, validacao, config, retomada, assinatura)
    finally:
        bert_minusculo.fronteiras = original
    assert torch.load(retomada, weights_only=False)["epoca"] == 1

    f1, _, rede, historico = bert_minusculo.treinar_semente(
        7, treino, validacao, config, retomada, assinatura
    )
    assert historico == pytest.approx(historico_direto) and f1 == pytest.approx(f1_direto)
    for chave, valor in rede_direta.state_dict().items():
        torch.testing.assert_close(rede.state_dict()[chave], valor)

    # Com outra assinatura, o ponto salvo não vale.
    assert bert_minusculo.ler_retomada(retomada, {"configuracao_sha1": "outra"}) is None
