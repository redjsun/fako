import pytest

from app.core.config import get_settings
from app.integrations.classificador_client import (
    ClassificadorAusente,
    ClassificadorIndisponivel,
    FakeClassificador,
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
