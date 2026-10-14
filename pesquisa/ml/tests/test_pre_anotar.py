import csv
import importlib.util
import sys
from pathlib import Path

import pytest

DADOS = Path(__file__).resolve().parents[2] / "dados"
sys.path.insert(0, str(DADOS))  # pre_anotar importa consolidar_anotacoes, vizinho dele
spec = importlib.util.spec_from_file_location("pre_anotar", DADOS / "pre_anotar.py")
pre_anotar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pre_anotar)

COLUNAS = ("id", "texto_curto", "veredito_original", "tipo", "anotador", "observacao")


def planilha(caminho: Path, anotador: str, ids: list[str]):
    with open(caminho, "w", encoding="utf-8-sig", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=COLUNAS)
        escritor.writeheader()
        for id_ in ids:
            escritor.writerow(
                {"id": id_, "texto_curto": f"texto {id_}", "veredito_original": "falso",
                 "tipo": "", "anotador": anotador, "observacao": ""}
            )  # fmt: skip


def test_interpretar_valida_tipo_e_sinais():
    sugestao = pre_anotar.interpretar(
        '```json\n{"tipo": "fabricado", "pede_compartilhamento": 1, "urgencia": 0, '
        '"apelo_emocional": 0, "ataque": 0}\n```'
    )
    assert sugestao == {
        "tipo": "fabricado",
        "pede_compartilhamento": "1",
        "urgencia": "0",
        "apelo_emocional": "0",
        "ataque": "0",
    }
    with pytest.raises(ValueError):
        pre_anotar.interpretar('{"tipo": "boato", "urgencia": 0}')


def test_sugere_e_esconde_nos_itens_de_concordancia(tmp_path, monkeypatch):
    monkeypatch.setattr(pre_anotar, "PLANILHAS", tmp_path)
    planilha(tmp_path / "rodada-02-ana.csv", "ana", ["comum", "a1"])
    planilha(tmp_path / "rodada-02-bruno.csv", "bruno", ["comum", "b1"])
    pedidos = []

    def sugerir(texto, veredito):
        pedidos.append(texto)
        sinais = dict.fromkeys(pre_anotar.SINAIS, "0")
        return {"tipo": "fabricado", **sinais, "urgencia": "1"}

    assert pre_anotar.sugerir_rodada(2, sugerir) == (3, 0, 1)
    ana = {linha["id"]: linha for linha in pre_anotar.ler_csv(tmp_path / "rodada-02-ana.csv")}
    assert ana["a1"]["sugestao_tipo"] == "fabricado" and ana["a1"]["sugestao_sinais"] == "urgencia"
    assert ana["comum"]["sugestao_tipo"] == "" and ana["comum"]["sugestao_sinais"] == ""
    # O cache guarda também a sugestão escondida, para medir a LLM contra os humanos.
    cache = pre_anotar.ler_csv(tmp_path / "rodada-02-llm.csv")
    assert {linha["id"] for linha in cache} == {"comum", "a1", "b1"}

    # Rodar de novo não pede nada à LLM.
    assert pre_anotar.sugerir_rodada(2, sugerir)[0] == 0
    assert len(pedidos) == 3


def test_comparar_llm_com_humanos():
    def linha(id_, anotador, tipo, urgencia="0"):
        sinais = dict.fromkeys(pre_anotar.SINAIS, "0")
        return {"id": id_, "anotador": anotador, "tipo": tipo, **sinais, "urgencia": urgencia}

    humanas = [
        linha("1", "ana", "fabricado"), linha("1", "bruno", "fabricado"),
        linha("2", "ana", "opiniao"), linha("2", "bruno", "opiniao"),
        linha("3", "ana", "enganoso", "1"), linha("3", "bruno", "enganoso", "1"),
        linha("4", "ana", "solo"),  # só um anotador: não entra
    ]  # fmt: skip
    llm = {
        "1": linha("1", "llm", "fabricado"),
        "2": linha("2", "llm", "fabricado"),
        "3": linha("3", "llm", "enganoso", "1"),
    }
    resultado = pre_anotar.comparar(humanas, llm)
    assert resultado["tipo"]["humanos"] == pytest.approx(1)
    assert resultado["tipo"]["llm"] < 1 and resultado["tipo"]["manter"] is False
    assert resultado["urgencia"]["manter"] is True
