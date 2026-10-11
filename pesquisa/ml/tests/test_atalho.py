import random

import pytest

from atalho import (
    N_PESOS,
    ModeloAtalho,
    auc,
    mesmos_registros,
    primeira_palavra,
    rodar,
    variaveis_de_forma,
)
from dados import Exemplo, alvos


def test_variaveis_de_forma():
    v = variaveis_de_forma("URGENTE: vacina tem 5G! 🚨 Compartilhe.")
    assert v["palavras"] == 5
    assert v["% caixa alta"] == pytest.approx(40)  # URGENTE e 5G
    assert v["!"] and v["dois-pontos"] and v["número"] and v["emoji"]
    assert v["termina com ponto"] and v["começa com maiúscula"]
    assert not (v["?"] or v["aspas"] or v["tudo minúsculo"])


def test_variaveis_de_forma_texto_vazio_nao_quebra():
    v = variaveis_de_forma("")
    assert v["palavras"] == 0 and v["% caixa alta"] == 0


def test_primeira_palavra_ignora_pontuacao_e_caixa():
    assert primeira_palavra("“Vídeo mostra...") == "vídeo"
    assert primeira_palavra("!!!") is None


def exemplo(id_: str, texto: str, classe: str) -> Exemplo:
    y1, y2 = alvos(classe)
    return Exemplo(
        id_, texto, classe, y1, y2, None, None, 2020, None, "teste", "agencia", 1.0, True
    )


def splits_sinteticos(n: int, forma_entrega: bool, semente: int = 0) -> dict[str, list[Exemplo]]:
    """Falsos terminam com ponto e verdadeiros não, se forma_entrega; senão, forma aleatória."""
    rnd = random.Random(semente)
    splits = {"treino": [], "validacao": [], "teste": []}
    for i in range(n):
        classe = ("falso", "enganoso", "verdadeiro")[i % 3]
        ponto = classe == "falso" if forma_entrega else rnd.random() < 0.5
        palavras = rnd.randint(5, 15)
        texto = " ".join(
            rnd.choice(["vacina", "governo", "lula", "covid"]) for _ in range(palavras)
        )
        split = ("treino", "treino", "validacao", "teste")[i % 4]
        splits[split].append(exemplo(str(i), texto.capitalize() + ("." if ponto else ""), classe))
    return splits


def test_forma_que_entrega_a_classe_da_auc_alta():
    resultado = rodar(splits_sinteticos(600, forma_entrega=True))
    assert resultado["splits"]["validacao"]["auc_por_classe"]["falso"] > 0.95


def test_forma_aleatoria_fica_perto_do_acaso():
    resultado = rodar(splits_sinteticos(1200, forma_entrega=False))
    for split in ("validacao", "teste"):
        assert 0.4 < resultado["splits"][split]["auc_macro"] < 0.6


def test_rodar_lista_os_pesos_por_classe():
    resultado = rodar(splits_sinteticos(300, forma_entrega=True))
    assert len(resultado["pesos"]) == N_PESOS
    assert set(resultado["pesos"][0]) == {"variavel", "falso", "enganoso", "verdadeiro"}
    assert resultado["pesos"][0]["variavel"] == "termina com ponto"


def test_auc_ignora_classe_ausente_no_split():
    modelo = ModeloAtalho().fit(["Um.", "dois", "Três.", "quatro"], ["falso", "verdadeiro"] * 2)
    medida = auc(modelo, ["Cinco.", "seis"], ["falso", "falso"])
    assert medida == {"registros": 2, "auc_macro": None, "auc_por_classe": {}}


def test_rodar_exige_duas_classes_no_treino():
    splits = {"treino": [exemplo("a", "a", "falso")], "teste": [exemplo("b", "b", "verdadeiro")]}
    with pytest.raises(ValueError):
        rodar(splits)


def test_mesmos_registros_filtra_por_id():
    splits = splits_sinteticos(12, forma_entrega=True)
    filtrado = mesmos_registros(splits, {"0", "2"})
    assert [e.id for e in filtrado["treino"]] == ["0"]
    assert [e.id for e in filtrado["validacao"]] == ["2"]
    assert filtrado["teste"] == []
