import pytest

from app.jobs.amostra_questoes import medir, wilson


def linha(gabarito="1", reescrita="1", fato_novo=""):
    return {
        "gabarito_correto": gabarito,
        "reescrita_fiel": reescrita,
        "explicacao_com_fato_novo": fato_novo,
    }


def test_mede_a_taxa_de_erro_so_nas_linhas_preenchidas():
    linhas = [
        linha(),
        linha(gabarito="0"),
        linha(reescrita="0", fato_novo="1"),
        linha(),
        linha("", ""),
    ]
    resultado = medir(linhas)
    assert resultado["questoes"] == 4 and resultado["com_erro"] == 2
    assert resultado["taxa_erro"] == pytest.approx(0.5)
    assert resultado["explicacoes"] == 1 and resultado["taxa_fato_novo"] == 1


def test_intervalo_de_wilson():
    minimo, maximo = wilson(10, 200)
    assert minimo < 0.05 < maximo
    assert wilson(0, 0) == (0.0, 1.0)
