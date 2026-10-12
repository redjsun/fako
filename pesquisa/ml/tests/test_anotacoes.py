import csv
import importlib.util
from pathlib import Path

import pytest

DADOS = Path(__file__).resolve().parents[2] / "dados"


def modulo(nome: str):
    """Os scripts de pesquisa/dados/ ficam fora do caminho de importação de pesquisa/ml/."""
    spec = importlib.util.spec_from_file_location(nome, DADOS / f"{nome}.py")
    carregado = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(carregado)
    return carregado


consolidar = modulo("consolidar_anotacoes")
sortear = modulo("sortear_anotacao")
preparar = modulo("preparar_dados")

SINAIS_ZERO = dict.fromkeys(consolidar.SINAIS, "0")


def anotacao(item, anotador, tipo="fabricado", veracidade="falso", **sinais):
    return {
        "id": item,
        "anotador": anotador,
        "tipo": tipo,
        "tipo_secundario": "",
        "veracidade": veracidade,
        **SINAIS_ZERO,
        **sinais,
        "observacao": "",
    }


def escrever(caminho: Path, linhas: list[dict]):
    with open(caminho, "w", encoding="utf-8-sig", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)


def test_kappa_cohen_concordancia_total_parcial_e_indefinida():
    assert consolidar.kappa_cohen([("a", "a"), ("b", "b")]) == 1
    # observada 0,5; esperada 0,5 -> kappa 0
    assert consolidar.kappa_cohen([("a", "a"), ("a", "b"), ("b", "a"), ("b", "b")]) == 0
    assert consolidar.kappa_cohen([("a", "a"), ("a", "a")]) is None


def test_alfa_krippendorff_exemplo_conhecido():
    # Dois anotadores, quatro itens: alfa nominal = 1 - (n - 1) * 4 / 32, com n = 8
    unidades = [["a", "a"], ["a", "b"], ["b", "b"], ["b", "a"]]
    assert consolidar.alfa_krippendorff(unidades) == pytest.approx(1 - 7 * 4 / 32)
    assert consolidar.alfa_krippendorff([["a", "a", "a"], ["b", "b"]]) == 1
    assert consolidar.alfa_krippendorff([["a"], ["b"]]) is None


def test_normalizar_tira_texto_valida_e_zera_veracidade_de_opiniao():
    bruta = {
        **anotacao("x1", "ana", tipo="Opiniao", veracidade="falso", urgencia="1"),
        "texto_curto": "texto do veículo",
        "veredito_original": "falso",
    }
    linha = consolidar.normalizar(bruta)
    assert "texto_curto" not in linha and "veredito_original" not in linha
    assert linha["tipo"] == "opiniao" and linha["veracidade"] == "" and linha["urgencia"] == "1"
    assert consolidar.normalizar({"id": "x2", "tipo": ""}) is None
    with pytest.raises(consolidar.ErroAnotacao):
        consolidar.normalizar(anotacao("x3", "ana", tipo="boato"))
    with pytest.raises(consolidar.ErroAnotacao):
        consolidar.normalizar(anotacao("x4", "ana", ataque="2"))


def test_importar_grava_so_id_e_rotulos_e_recusa_teste(tmp_path):
    planilha = tmp_path / "rodada-01-ana.csv"
    escrever(
        planilha,
        [
            {**anotacao("x1", "ana"), "texto_curto": "texto do veículo"},
            {**anotacao("x2", "ana", tipo=""), "texto_curto": "não anotado"},
        ],
    )
    destino = tmp_path / "rodada-01.csv"
    assert consolidar.importar([planilha], destino, {"x1": "treino"}) == (1, 1)
    conteudo = destino.read_text(encoding="utf-8")
    assert "texto do veículo" not in conteudo
    assert conteudo.splitlines()[0] == ",".join(consolidar.COLUNAS_RODADA)

    with pytest.raises(consolidar.ErroAnotacao, match="teste"):
        consolidar.importar([planilha], destino, {"x1": "teste"})


def test_consolidar_por_maioria_adjudicacao_e_pendentes():
    linhas = [
        anotacao("x1", "ana"),
        anotacao("x1", "bia"),
        anotacao("x2", "ana", tipo="enganoso", veracidade="enganoso"),
        anotacao("x2", "bia", tipo="fabricado"),
        anotacao("x3", "ana", tipo="enganoso", veracidade="enganoso"),
        anotacao("x3", "bia"),
        anotacao("x4", "ana", tipo="nenhum", veracidade="verdadeiro", ataque="1"),
    ]
    adjudicacao = [{**anotacao("x3", ""), "tipo": "enganoso", "veracidade": "enganoso"}]
    finais, pendentes = consolidar.consolidar(linhas, adjudicacao)
    por_id = {f["id"]: f for f in finais}
    assert pendentes == ["x2"]
    assert por_id["x1"]["tipo"] == "fabricado" and por_id["x1"]["adjudicado"] == 0
    assert por_id["x3"]["veracidade"] == "enganoso" and por_id["x3"]["adjudicado"] == 1
    assert por_id["x4"]["ataque"] == "1" and por_id["x4"]["anotadores"] == 1


def test_concordancia_so_nos_itens_com_mais_de_um_anotador():
    linhas = [
        anotacao("x1", "ana"),
        anotacao("x1", "bia"),
        anotacao("x2", "ana", tipo="enganoso"),
        anotacao("x2", "bia", tipo="fabricado"),
        anotacao("x3", "ana"),
    ]
    tipo = consolidar.concordancia(linhas)["tipo"]
    assert tipo["itens"] == 2 and tipo["concordancia"] == 0.5
    assert set(tipo["kappa"]) == {"ana-bia"}


def registro(item, veracidade="falso", split="treino", **outros):
    return {
        "id": item,
        "base": "factcheck",
        "fonte": "aosfatos.org",
        "data": "2020-01-01",
        "veracidade": veracidade,
        "rotulo": preparar.ROTULO_POR_VERACIDADE[veracidade],
        "split": "teste",
        "split_produto": split,
        "origem_rotulo": "agencia",
        "texto_curto": f"alegação {item}",
        "tipo_sugerido": "fabricado",
        **outros,
    }


def test_sorteio_fora_do_teste_estratificado_e_deterministico():
    registros = [registro(f"f{i}") for i in range(20)]
    registros += [registro(f"v{i}", veracidade="verdadeiro") for i in range(3)]
    registros += [registro("t1", split="teste"), registro("p1", origem_rotulo="portal")]
    registros += [registro("a1"), registro("s1", texto_curto="")]
    candidatos = sortear.candidatos(registros, excluir={"a1"})
    assert {r["id"] for r in candidatos}.isdisjoint({"t1", "p1", "a1", "s1"})

    amostra = sortear.sortear(candidatos, 6, rodada=1)
    assert sum(r["veracidade"] == "verdadeiro" for r in amostra) == 3  # classes alternadas
    assert amostra == sortear.sortear(candidatos, 6, rodada=1)

    por_anotador, comuns = sortear.distribuir(amostra, ["ana", "bia"], 0.5, rodada=1)
    assert comuns == 3
    ids_ana = {r["id"] for r in por_anotador["ana"]}
    ids_bia = {r["id"] for r in por_anotador["bia"]}
    assert len(ids_ana & ids_bia) == 3 and ids_ana | ids_bia == {r["id"] for r in amostra}


def test_preparar_dados_aplica_anotacoes_com_origem_equipe(tmp_path):
    consolidado = tmp_path / "consolidado.csv"
    consolidar.gravar_csv(
        consolidado,
        consolidar.COLUNAS_CONSOLIDADO,
        [
            {
                "id": "x1",
                "tipo": "enganoso",
                "tipo_secundario": "",
                "veracidade": "enganoso",
                **SINAIS_ZERO,
                "urgencia": "1",
                "anotadores": 2,
                "adjudicado": 0,
            },
            {
                "id": "x2",
                "tipo": "fora_escopo",
                "tipo_secundario": "",
                "veracidade": "",
                **SINAIS_ZERO,
                "anotadores": 1,
                "adjudicado": 0,
            },
        ],
    )
    registros = [registro("x1"), registro("x2"), registro("x3")]
    assert preparar.aplicar_anotacoes(registros, consolidado) == 2
    x1, x2, x3 = registros
    assert x1["origem_rotulo"] == "equipe" and x1["tipo"] == "enganoso"
    assert x1["veracidade"] == "enganoso" and x1["rotulo"] is None
    assert x1["sinais"]["urgencia"] == 1 and x1["sinais"]["ataque"] == 0
    assert x2["split_produto"] == "fora" and x2["veracidade"] == "falso"
    assert x3["origem_rotulo"] == "agencia"
