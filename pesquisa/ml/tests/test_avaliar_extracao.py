import csv

from avaliar_extracao import carregar_itens, ler_csv, ler_saidas, medir, rodar
from padronizar import Extracao


def escrever(caminho, colunas, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)


def test_texto_vem_da_linha_ou_do_arquivo_local(tmp_path):
    rotulos, textos = tmp_path / "rotulos.csv", tmp_path / "textos.csv"
    escrever(
        rotulos,
        ("id", "e_opiniao", "quem_disse", "texto"),
        [
            {"id": "proprio", "e_opiniao": "1", "quem_disse": "", "texto": "Acho ruim."},
            {"id": "terceiro", "e_opiniao": "0", "quem_disse": "deputado", "texto": ""},
        ],
    )
    escrever(textos, ("id", "texto"), [{"id": "terceiro", "texto": "Deputado disse que X."}])
    itens = carregar_itens(rotulos, textos)
    assert [i["texto"] for i in itens] == ["Acho ruim.", "Deputado disse que X."]
    assert itens[0]["e_opiniao"] and itens[1]["quem_disse"] == "deputado"


def test_rodar_retoma_e_medir_conta_opiniao_quem_disse_e_checaveis(tmp_path):
    itens = [
        {"id": "a", "texto": "Acho ruim.", "e_opiniao": True, "quem_disse": None},
        {"id": "b", "texto": "Deputado disse X.", "e_opiniao": False, "quem_disse": "deputado"},
        {"id": "c", "texto": "Ministro disse Y.", "e_opiniao": False, "quem_disse": "ministro"},
    ]
    respostas = {
        "Acho ruim.": [],
        "Deputado disse X.": [{"texto": "X", "quem_disse": "deputado"}],
        "Ministro disse Y.": [{"texto": "Y", "quem_disse": None}],  # perdeu o autor
    }
    pedidos = []

    def extrair(texto):
        pedidos.append(texto)
        return Extracao(afirmacoes=respostas[texto])

    saida = tmp_path / "extracao-v1.jsonl"
    assert rodar(itens[:2], extrair, saida) == 2
    assert rodar(itens, extrair, saida) == 1  # só o que faltava
    assert len(pedidos) == 3

    revisao = ler_csv(saida.with_name("extracao-v1-revisao.csv"))
    assert [linha["afirmacao"] for linha in revisao] == ["X", "Y"]
    revisao[0]["checavel"], revisao[1]["checavel"] = "1", "0"

    resultado = medir(itens, ler_saidas(saida), revisao)
    assert resultado["acerto_opiniao"] == 1
    assert resultado["atribuidos"] == 2 and resultado["quem_disse_preservado"] == 0.5
    assert resultado["sem_autor"] == ["c"]
    assert resultado["checaveis"] == 0.5
