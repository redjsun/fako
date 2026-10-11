import json

import numpy as np
import pytest

from avaliar import (
    avaliar,
    comparar,
    ece,
    gravar_previsoes,
    ler_previsoes,
    metricas,
    nota,
    probabilidades,
    recall_com_falso_alarme,
    relatorio,
)
from dados import carregar

# p1, p2 que dão certeza em cada classe: falso, enganoso, verdadeiro
CERTEZA = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (1.0, 1.0)}


def fronteiras(classes):
    p1, p2 = zip(*(CERTEZA[c] for c in classes), strict=True)
    return np.array(p1), np.array(p2)


def test_probabilidades_e_nota_a_partir_das_fronteiras():
    proba = probabilidades([0.0, 1.0, 1.0, 0.8], [0.0, 0.0, 1.0, 0.3])
    np.testing.assert_allclose(proba[:3], np.eye(3))
    np.testing.assert_allclose(proba[3], [0.2, 0.5, 0.3])
    np.testing.assert_allclose(proba.sum(axis=1), 1)
    np.testing.assert_allclose(nota([0, 1, 1, 0.8], [0, 0, 1, 0.3]), [0, 50, 100, 55])


def test_metricas_ordinais_perfeitas():
    y = [0, 0, 1, 1, 2, 2]
    m = metricas(np.array(y), *fronteiras(y))
    assert m["f1_macro"] == 1 and m["mae_nota"] == 0 and m["kappa_quadratico"] == 1
    assert m["auc_fronteira"] == {">falso": 1.0, ">enganoso": 1.0}
    assert m["ece"] == 0


def test_mae_da_nota_e_kappa_quadratico_casos_conhecidos():
    y = np.array([0, 1, 2])
    tudo_meio = metricas(y, np.ones(3), np.zeros(3))  # nota 50 para todos
    assert tudo_meio["mae_nota"] == pytest.approx(100 / 3)

    # Erros de duas posições com marginais trocadas: kappa quadrático = 1 - 1 / 0,5 = -1
    invertido = metricas(np.array([0, 2]), *fronteiras([2, 0]))
    assert invertido["kappa_quadratico"] == pytest.approx(-1)
    assert invertido["mae_nota"] == 100


def test_recall_de_falsos_com_taxa_de_falso_alarme():
    y = np.array([0, 0, 0] + [2] * 100)
    prob_falso = np.array([0.9, 0.8, 0.3, 0.85] + [0.1] * 99)
    # 1% de 100 verdadeiros: um pode passar (o 0,85); o limiar fica em 0,1
    assert recall_com_falso_alarme(prob_falso, y, 0.01) == 1.0
    # 0%: o limiar é o maior verdadeiro (0,85); só o 0,9 passa
    assert recall_com_falso_alarme(prob_falso, y, 0.0) == pytest.approx(1 / 3)
    assert recall_com_falso_alarme(prob_falso[:3], y[:3], 0.01) is None


def test_ece_confiante_e_errando_metade():
    proba = np.array([[0.9, 0.05, 0.05]] * 4)
    erro, diagrama = ece(proba, np.array([0, 0, 1, 1]))
    assert erro == pytest.approx(0.4)
    assert diagrama == [{"faixa": 9, "n": 4, "confianca": pytest.approx(0.9), "acerto": 0.5}]


def test_incerto_com_limiares():
    m = metricas(np.array([0, 2]), np.array([0.4, 1.0]), np.array([0.0, 1.0]), {"jogador": 0.8})
    assert m["incerto"] == {"jogador": 0.5}  # o primeiro tem confiança 0,6


def registro(item, veracidade, split="validacao", data="2024-03-01", **outros):
    return {
        "id": item,
        "base": "factcheck",
        "fonte": "aosfatos.org",
        "data": data,
        "veracidade": veracidade,
        "veredito_original": veracidade,
        "tipo_sugerido": None,
        "origem_rotulo": "agencia",
        "split_produto": split,
        "texto_curto": f"Alegação número {item}",
        **outros,
    }


@pytest.fixture
def dataset(tmp_path):
    registros = []
    for i, classe in enumerate(["falso", "enganoso", "verdadeiro"] * 10):
        registros.append(registro(f"v{i}", classe))
        registros.append(registro(f"t{i}", classe, split="teste", data="2025-06-01"))
    registros.append(registro("x0", "falso", split="treino", data="2020-01-01"))
    caminho = tmp_path / "dataset.jsonl"
    caminho.write_text("\n".join(json.dumps(r) for r in registros), encoding="utf-8")
    return caminho


def gravar_modelo(pasta, dataset, acerta_ate: int):
    """Modelo que acerta os `acerta_ate` primeiros de cada split e chuta falso no resto."""
    conjunto = carregar(dataset=dataset)
    previsoes = {}
    for split in ("validacao", "teste"):
        exemplos = conjunto.splits[split]
        classes = [
            {"falso": 0, "enganoso": 1, "verdadeiro": 2}[e.veracidade] if i < acerta_ate else 0
            for i, e in enumerate(exemplos)
        ]
        p1, p2 = fronteiras(classes)
        previsoes[split] = (exemplos, 0.05 + 0.9 * p1, 0.05 + 0.9 * p2)
    gravar_previsoes(pasta, previsoes, {"texto": "original"})


def test_avaliar_de_ponta_a_ponta_e_comparacao(tmp_path, dataset):
    gravar_modelo(tmp_path / "bom", dataset, acerta_ate=30)
    gravar_modelo(tmp_path / "ruim", dataset, acerta_ate=10)
    assert len(ler_previsoes(tmp_path / "bom")) == 60

    so_validacao = avaliar(tmp_path / "bom", dataset, atalho=tmp_path / "sem-atalho.json")
    assert list(so_validacao["splits"]) == ["validacao"]  # o teste só com --teste
    assert so_validacao["envelhecimento"] is None

    bom = avaliar(tmp_path / "bom", dataset, teste=True, atalho=tmp_path / "sem-atalho.json")
    ruim = avaliar(tmp_path / "ruim", dataset, teste=True, atalho=tmp_path / "sem-atalho.json")
    geral = bom["splits"]["validacao"]["geral"]
    assert geral["n"] == 30 and geral["f1_macro"] == 1 and bom["piores"]["validacao"] == []
    assert set(bom["splits"]["validacao"]["por_ano"]) == {"2024"}
    assert bom["splits"]["validacao"]["checados"]["n"] == 30
    assert bom["envelhecimento"]["queda_f1_macro"] == pytest.approx(0)

    piores = ruim["piores"]["validacao"]
    assert len(piores) == 14  # 20 chutes "falso", 6 deles acertam
    assert piores[0]["veracidade"] == "verdadeiro" and piores[0]["previsto"] == "falso"
    assert ruim["splits"]["validacao"]["geral"]["f1_macro"] < geral["f1_macro"]

    texto = relatorio(ruim)
    assert "## validacao" in texto and "piores erros" in texto and "Envelhecimento" in texto
    lado_a_lado = comparar([bom, ruim])
    assert str(tmp_path / "bom") in lado_a_lado and str(tmp_path / "ruim") in lado_a_lado


def test_margem_sobre_o_atalho(tmp_path, dataset):
    gravar_modelo(tmp_path / "bom", dataset, acerta_ate=30)
    atalho = tmp_path / "atalho.json"
    piso = {"versoes": {"original": {"splits": {"validacao": {"auc_macro": 0.7}}}}}
    atalho.write_text(json.dumps(piso), encoding="utf-8")
    resultado = avaliar(tmp_path / "bom", dataset, atalho=atalho)
    assert resultado["atalho"]["validacao"]["margem"] == pytest.approx(0.3)
