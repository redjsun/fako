"""De ponta a ponta no dataset de fixture: configuração → dados → atalho → modelo → avaliação."""

import pytest

from atalho import rodar
from avaliar import avaliar, relatorio
from configuracao import CONFIGS, ErroConfiguracao, carregar_configuracao
from dados import carregar
from treinar_referencia import treinar

SMOKE = CONFIGS / "smoke.toml"


@pytest.mark.parametrize("arquivo", sorted(CONFIGS.glob("*.toml")), ids=lambda p: p.stem)
def test_todas_as_configuracoes_versionadas_carregam(arquivo, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "modelo-de-teste")  # a variante padronizada lê do .env
    config = carregar_configuracao(arquivo)
    assert config.nome and config.sementes and config.saida.is_absolute()


def test_configuracao_invalida(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    arquivo = tmp_path / "x.toml"
    arquivo.write_text('nome = "x"\nmodelo = "svm"\nsaida = "s"\n', encoding="utf-8")
    with pytest.raises(ErroConfiguracao, match="modelo"):
        carregar_configuracao(arquivo)
    arquivo.write_text(
        'nome = "x"\nmodelo = "bert"\nsaida = "s"\n[dados]\ntexto = "padronizado"\n',
        encoding="utf-8",
    )
    with pytest.raises(ErroConfiguracao, match="padronizado"):
        carregar_configuracao(arquivo)


def test_smoke_de_ponta_a_ponta(tmp_path):
    config = carregar_configuracao(SMOKE)
    conjunto = carregar(**config.argumentos_dados())
    assert {s: len(e) for s, e in conjunto.splits.items()} == {
        "treino": 60,
        "validacao": 15,
        "teste": 15,
    }

    piso = rodar(conjunto.splits)
    assert piso["splits"]["validacao"]["registros"] == 15

    pasta = tmp_path / config.nome
    treinar(config, pasta)

    resultado = avaliar(pasta, config.dataset, teste=True, atalho=tmp_path / "sem-atalho.json")
    assert resultado["config"]["configuracao_sha1"] == config.sha1
    assert resultado["config"]["dataset_sha256"] == conjunto.dataset_sha256
    geral = resultado["splits"]["validacao"]["geral"]
    assert geral["n"] == 15 and geral["f1_macro"] > 0.5  # frases do mesmo molde do treino
    assert resultado["envelhecimento"] is not None
    assert "## teste" in relatorio(resultado)
    assert (pasta / "referencia.joblib").exists()
