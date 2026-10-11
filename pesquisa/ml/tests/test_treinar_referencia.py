import json

import joblib
import numpy as np

from configuracao import CONFIGS, carregar_configuracao
from treinar_referencia import ARQUIVO_MODELO, contribuicoes, fronteiras, treinar


def treinar_smoke(tmp_path, **treino):
    config = carregar_configuracao(CONFIGS / "smoke.toml")
    config.treino = {**config.treino, **treino}
    return config, treinar(config, tmp_path), tmp_path


def test_escolhe_c_na_validacao_e_registra_a_grade(tmp_path):
    _, resultado, pasta = treinar_smoke(tmp_path, grade_c=[0.01, 1, 10])
    assert set(resultado["grade_f1_macro_validacao"]) == {"0.01", "1", "10"}
    melhor = max(resultado["grade_f1_macro_validacao"].values())
    assert resultado["f1_macro_validacao"] == melhor
    config = json.loads((pasta / "config.json").read_text(encoding="utf-8"))
    assert config["c_escolhido"] == resultado["c_escolhido"]
    assert config["latencia_ms_por_frase"] > 0 and config["dataset_sha256"]


def test_modelo_salvo_carrega_sem_codigo_da_pesquisa_e_respeita_a_ordem(tmp_path):
    _, _, pasta = treinar_smoke(tmp_path)
    modelo = joblib.load(pasta / ARQUIVO_MODELO)
    assert set(modelo) >= {"vetorizador", "fronteira_1", "fronteira_2", "versao"}
    p1, p2 = fronteiras(["Vacina contém chip", "Prefeitura publica calendário oficial"], modelo)
    assert np.all(p2 <= p1)
    probabilidades = np.column_stack([1 - p1, p1 - p2, p2])
    np.testing.assert_allclose(probabilidades.sum(axis=1), 1)

    previsoes = [json.loads(linha) for linha in open(pasta / "previsoes.jsonl", encoding="utf-8")]
    assert {p["split"] for p in previsoes} == {"validacao", "teste"}
    assert all(p["p2"] <= p["p1"] for p in previsoes)


def test_contribuicoes_explicam_a_frase(tmp_path):
    _, _, pasta = treinar_smoke(tmp_path, ngram_caracteres=[3, 4])
    modelo = joblib.load(pasta / ARQUIVO_MODELO)
    explicacao = contribuicoes("Vacina contém chip para rastrear moradores", modelo, n=5)
    assert set(explicacao) == {">falso", ">enganoso"}
    termos = [termo for termo, _ in explicacao[">falso"]]
    assert len(termos) == 5 and any("chip" in termo for termo in termos)
    valores = [abs(v) for _, v in explicacao[">falso"]]
    assert valores == sorted(valores, reverse=True)
