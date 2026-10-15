import json

import numpy as np

from avaliar_jogo import (
    corte_cruzado,
    ler_coletas,
    medir,
    sem_o_que_o_treino_viu,
    texto_de_entrada,
    vistos_no_treino,
)


def linha(identificador, manchete, is_true, afirmacao=None, provedor="gnews"):
    return {
        "id": identificador,
        "provedor": provedor,
        "url": f"https://exemplo.teste/{identificador}",
        "manchete": manchete,
        "afirmacao": afirmacao,
        "is_true": is_true,
    }


def gravar(caminho, linhas):
    caminho.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in linhas))


def test_coletas_juntas_sem_repetir_id_nem_manchete(tmp_path):
    gravar(tmp_path / "jogo-2026-10-15.jsonl", [linha("a", "Chuva forte atinge a capital", True)])
    gravar(
        tmp_path / "jogo-2026-10-16.jsonl",
        [
            linha("a", "Outra manchete com o mesmo id", True),
            linha("b", "chuva forte atinge a capital!", True),
            linha("c", "Vacina contém chip de rastreamento", False, provedor="factcheck"),
        ],
    )
    assert [x["id"] for x in ler_coletas(tmp_path)] == ["a", "c"]


def test_sai_o_que_ja_esta_no_dataset_de_treino(tmp_path):
    dataset = tmp_path / "dataset.jsonl"
    gravar(
        dataset,
        [
            {"texto_curto": "Vacina contém chip de rastreamento.", "titulo": None, "url": None},
            {"texto_curto": None, "titulo": None, "url": "https://exemplo.teste/d"},
        ],
    )
    linhas = [
        linha("c", "Vacina contém chip de rastreamento", False),
        linha("d", "Texto novo com URL já usada no treino", True),
        linha("e", "Chuva forte atinge a capital", True),
    ]
    assert [x["id"] for x in sem_o_que_o_treino_viu(linhas, vistos_no_treino(dataset))] == ["e"]


def test_texto_de_entrada_igual_ao_da_api():
    com_afirmacao = linha(
        "a", "Prefeitura diz que obra acaba em maio", True, "A obra acaba em maio"
    )
    sem_afirmacao = linha("b", "Prefeitura diz que obra acaba em maio", True)
    assert texto_de_entrada(com_afirmacao, "original").startswith("Prefeitura")
    assert texto_de_entrada(com_afirmacao, "hibrido").startswith("A obra")
    assert texto_de_entrada(sem_afirmacao, "padronizado").startswith("Prefeitura")


def test_jogo_binario_sobre_o_modelo_ordinal():
    linhas = [
        linha("v1", "x", True),
        linha("v2", "x", True),
        linha("f1", "x", False),
        linha("f2", "x", False),
    ]
    # verdadeiro, falso, enganoso (conta como falsa no jogo), verdadeiro
    p1 = np.array([0.9, 0.1, 0.8, 0.9])
    p2 = np.array([0.8, 0.05, 0.1, 0.7])
    medidas = medir(linhas, p1, p2)
    assert medidas["acerto_verdadeiras"] == 0.5 and medidas["acerto_falsas"] == 0.5
    assert medidas["acerto"] == medidas["acerto_balanceado"] == 0.5
    assert medidas["por_provedor"] == {"gnews": 0.5}
    assert medidas["por_veracidade"] == {"falso": 0.5, "verdadeiro": 0.5}


def test_enganosa_conta_como_falsa_com_acerto_a_parte():
    linhas = [linha("v", "x", True), {**linha("e", "x", False), "veracidade": "enganoso"}]
    medidas = medir(linhas, np.array([0.9, 0.9]), np.array([0.8, 0.2]))
    assert medidas["acerto"] == 1.0
    assert medidas["por_veracidade"] == {"enganoso": 1.0, "verdadeiro": 1.0}


def test_corte_escolhido_numa_metade_e_medido_na_outra():
    y = np.array([True, False] * 20)
    pontuacao = np.where(y, 70.0, 30.0)
    metades = np.arange(40) // 20
    resultado = corte_cruzado(pontuacao, y, metades)
    assert resultado["acerto_balanceado"] == 1.0
    assert all(30 < corte <= 70 for corte in resultado["cortes"])
    assert corte_cruzado(pontuacao, np.ones(40, bool), metades) is None
