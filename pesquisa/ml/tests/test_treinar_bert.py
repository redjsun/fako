import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from dados import Exemplo  # noqa: E402
from treinar_bert import fronteiras_de_logits, pesos_por_classe  # noqa: E402


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
