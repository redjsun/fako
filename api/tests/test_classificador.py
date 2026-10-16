import json

import joblib
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from app.core.config import get_settings
from app.ml.classificador import (
    ClassificadorAusente,
    ClassificadorIndisponivel,
    FakeClassificador,
    ReferenciaTfidf,
    analise_das_fronteiras,
    get_classificador,
)


@pytest.mark.parametrize(
    "p1, p2, categoria, nota",
    [
        (0.05, 0.0, "falso", 2.5),
        (0.95, 0.05, "enganoso", 50.0),
        (1.0, 0.9, "confere", 95.0),
    ],
)
def test_regra_de_decisao_pela_classe_mais_provavel(p1, p2, categoria, nota):
    analise = analise_das_fronteiras("afirmação", p1, p2, limiar=0.5, versao_modelo="v")
    assert analise.categoria == categoria
    assert analise.nota == pytest.approx(nota)
    assert sum(analise.probabilidades.values()) == pytest.approx(1)


def test_abaixo_do_limiar_e_incerto_sem_nota():
    analise = analise_das_fronteiras("afirmação", 0.6, 0.3, limiar=0.7, versao_modelo="v")
    assert analise.categoria == "incerto" and analise.nota is None
    assert analise.confianca == pytest.approx(0.4)


def test_p2_maior_que_p1_e_cortado():
    analise = analise_das_fronteiras("afirmação", 0.4, 0.6, limiar=0.0, versao_modelo="v")
    assert analise.probabilidades["enganoso"] == 0
    assert analise.probabilidades["verdadeiro"] == pytest.approx(0.4)


def test_fake_e_deterministico():
    classificador = FakeClassificador()
    assert classificador.analisar("x", "admin") == classificador.analisar("x", "admin")


def test_sem_modelo_publicado_falha_de_forma_controlada(tmp_path, monkeypatch):
    monkeypatch.setenv("CLASSIFICADOR_PROVIDER", "referencia")
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        classificador = get_classificador()
        assert isinstance(classificador, ClassificadorAusente)
        with pytest.raises(ClassificadorIndisponivel, match="Nenhum modelo publicado"):
            classificador.analisar("x", "jogador")
    finally:
        get_settings.cache_clear()


def publicar_modelo_minimo(pasta):
    """Um referencia.joblib no formato do modelo publicado, com frases inventadas."""
    textos = [
        "vacina tem chip para controlar a população",
        "remédio caseiro cura doença grave em um dia",
        "governo esconde cura milagrosa da população",
        "prefeitura abre vagas em creches municipais",
        "ministério amplia vacinação contra a gripe",
        "instituto divulga estimativa da população",
    ]
    vetor = FeatureUnion([("palavras", TfidfVectorizer())])
    matriz = vetor.fit_transform(textos)
    modelo = {
        "vetorizador": vetor,
        "fronteira_1": LogisticRegression().fit(matriz, [0, 0, 1, 1, 1, 1]),
        "fronteira_2": LogisticRegression().fit(matriz, [0, 0, 0, 1, 1, 1]),
        "versao": "referencia-teste",
    }
    pasta.mkdir(parents=True)
    joblib.dump(modelo, pasta / "referencia.joblib")


def test_referencia_tfidf_limpa_classifica_e_explica_so_para_o_admin(tmp_path):
    publicar_modelo_minimo(tmp_path / "atual")
    classificador = ReferenciaTfidf(tmp_path / "atual")

    admin = classificador.analisar("Vacina tem chip para controlar a população | G1", "admin")
    jogador = classificador.analisar("Vacina tem chip para controlar a população", "jogador")

    assert admin.versao_modelo == "referencia-teste"
    assert admin.probabilidades == pytest.approx(jogador.probabilidades)  # crédito limpo
    assert sum(admin.probabilidades.values()) == pytest.approx(1)
    assert admin.contribuicoes and not jogador.contribuicoes


def test_limiares_do_modelo_substituem_o_padrao(tmp_path):
    publicar_modelo_minimo(tmp_path / "atual")
    (tmp_path / "atual" / "limiares.json").write_text(json.dumps({"jogador": 0.99}))
    analise = ReferenciaTfidf(tmp_path / "atual").analisar("vacina tem chip", "jogador")
    assert analise.categoria == "incerto"


def test_get_classificador_carrega_o_modelo_publicado_uma_vez(tmp_path, monkeypatch):
    publicar_modelo_minimo(tmp_path / "atual")
    monkeypatch.setenv("CLASSIFICADOR_PROVIDER", "referencia")
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        classificador = get_classificador()
        assert isinstance(classificador, ReferenciaTfidf)
        assert get_classificador() is classificador
    finally:
        get_settings.cache_clear()


def test_calibracao_do_modelo_e_aplicada_nas_fronteiras(tmp_path):
    publicar_modelo_minimo(tmp_path / "atual")
    bruto = ReferenciaTfidf(tmp_path / "atual").fronteiras("vacina tem chip")
    # a = 0 e b = 0 levam qualquer fronteira a 0,5: a saída passa a ser a calibrada.
    neutra = {"a": 0.0, "b": 0.0}
    calibracao = {"fronteira_1": neutra, "fronteira_2": neutra}
    (tmp_path / "atual" / "calibracao.json").write_text(json.dumps(calibracao))
    calibrado = ReferenciaTfidf(tmp_path / "atual").fronteiras("vacina tem chip")
    assert bruto != pytest.approx((0.5, 0.5))
    assert calibrado == pytest.approx((0.5, 0.5))


def test_texto_de_entrada_vem_do_config_do_modelo(tmp_path):
    publicar_modelo_minimo(tmp_path / "atual")
    assert ReferenciaTfidf(tmp_path / "atual").texto_de_entrada == "original"
    (tmp_path / "atual" / "config.json").write_text(json.dumps({"texto": "padronizado"}))
    assert ReferenciaTfidf(tmp_path / "atual").texto_de_entrada == "padronizado"
