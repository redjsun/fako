import csv
import sys
from pathlib import Path

import pytest

# Os scripts de pesquisa/dados/ importam uns aos outros pelo nome, como ao rodar da pasta.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "dados"))

import auditar_verdadeiras as auditoria  # noqa: E402
import preparar_dados as preparar  # noqa: E402


def materia(item, titulo, fonte="poder360.com.br", data="2020-05-01", url=None, **outros):
    return {
        "id": item,
        "base": "verdadeiras",
        "fonte": fonte,
        "veracidade": "verdadeiro",
        "texto_curto": titulo,
        "url": url or f"https://{fonte}/brasil/{item}/",
        "data": data,
        "par_id": None,
        "origem_rotulo": "portal",
        "split_produto": "treino",
        **outros,
    }


@pytest.mark.parametrize(
    "titulo, url, motivo",
    [
        ("Câmara aprova reforma tributária em segundo turno", None, None),
        ("Ministro diz que inflação vai cair", None, "relata fala"),
        ('Senado aprova fim da "saidinha" de presos', None, "relata fala"),
        ("Barroso: “Vivemos um momento grave”", None, "relata fala"),
        ("Segundo a PF, operação prendeu 10", None, "relata fala"),
        ("Como fica o debate público no Brasil?", None, "pergunta"),
        ("Ao vivo: votação no Congresso", None, "opinião, vídeo, ao vivo ou publicidade"),
        (
            "O aprendizado na universidade",
            "https://jornal.usp.br/artigos/x/",
            "opinião, vídeo, ao vivo ou publicidade",
        ),
        (
            "Copa: Brasil vence a Sérvia",
            "https://veja.abril.com.br/coluna/radar/x/",
            "opinião, vídeo, ao vivo ou publicidade",
        ),
        ("Gota d'água para o governo", None, None),
        ("Veja o vídeo", "https://youtu.be/abc", "opinião, vídeo, ao vivo ou publicidade"),
        ("", None, "sem título"),
    ],
)
def test_filtros_das_materias_de_portal(titulo, url, motivo):
    assert preparar.motivo_filtro_portal(materia("m", titulo, url=url)) == motivo


def escrever_veiculos(caminho: Path, aceitos: dict[str, int]):
    with open(caminho, "w", encoding="utf-8", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=["fonte", "aceito"])
        escritor.writeheader()
        escritor.writerows({"fonte": f, "aceito": a} for f, a in aceitos.items())


def test_verificar_portais_so_veiculo_aceito_e_sem_problema_na_auditoria(tmp_path):
    veiculos = tmp_path / "veiculos.csv"
    escrever_veiculos(veiculos, {"poder360.com.br": 1, "veja.abril.com.br": 0})
    revisoes = tmp_path / "auditoria.csv"
    auditoria.gravar_csv(
        revisoes,
        auditoria.COLUNAS_AUDITORIA,
        [
            {"id": "m3", "fonte": "poder360.com.br", "revisor": "ana", "problema": "nenhum"},
            {"id": "m3", "fonte": "poder360.com.br", "revisor": "bia", "problema": "exagero"},
        ],
    )
    registros = [
        materia("m1", "Câmara aprova reforma"),
        materia("m2", "Câmara aprova reforma", fonte="veja.abril.com.br"),
        materia("m3", "Câmara aprova reforma"),
        materia("m4", "Ministro diz que vai sair"),
        {**materia("m5", "Câmara aprova reforma"), "base": "factcheck", "origem_rotulo": "agencia"},
    ]
    motivos = preparar.verificar_portais(registros, veiculos, revisoes)
    assert [r["origem_rotulo"] for r in registros] == [
        "portal_verificado",
        "portal",
        "portal",
        "portal",
        "agencia",
    ]
    assert motivos == {
        "verificado": 1,
        "veículo não aprovado": 1,
        "problema na auditoria": 1,
        "relata fala": 1,
    }
    sem_arquivo = [materia("m1", "Câmara aprova reforma")]
    assert preparar.verificar_portais(sem_arquivo, tmp_path / "nao-existe.csv") == {}
    assert sem_arquivo[0]["origem_rotulo"] == "portal"


def test_equilibrar_completa_verdadeiros_ate_os_falsos_com_portais_verificados():
    registros = [
        {
            "id": f"f{i}",
            "base": "factcheck",
            "fonte": "x",
            "veracidade": "falso",
            "origem_rotulo": "agencia",
            "split_produto": "treino",
        }
        for i in range(5)
    ]
    registros += [
        {
            "id": "v0",
            "base": "factcheck",
            "fonte": "x",
            "veracidade": "verdadeiro",
            "origem_rotulo": "agencia",
            "split_produto": "treino",
        }
    ]
    registros += [
        {**materia(f"p{i}", "Câmara aprova"), "origem_rotulo": "portal_verificado"}
        for i in range(10)
    ]
    reserva = preparar.equilibrar(registros)
    ativos = [r for r in registros if r["split_produto"] == "treino"]
    assert sum(r["veracidade"] == "verdadeiro" for r in ativos) == 5
    assert reserva == {"treino: portal verificado além dos falsos": 6}


def test_candidatos_da_auditoria_fora_do_teste_e_com_filtro():
    registros = [
        materia("a", "Câmara aprova reforma"),
        materia("b", "Câmara aprova reforma", data="2025-02-01"),  # teste por data
        materia("c", "Ministro diz que vai sair"),
        materia("d", "Câmara aprova reforma", split_produto="fora"),
        materia("e", "Câmara aprova reforma", data="2024-03-01"),
    ]
    assert [r["id"] for r in auditoria.candidatos(registros)] == ["a", "e"]


def test_sorteio_da_auditoria_alterna_veiculos_e_e_reproduzivel():
    registros = [materia(f"p{i}", "t") for i in range(10)]
    registros += [materia(f"v{i}", "t", fonte="veja.abril.com.br") for i in range(2)]
    amostra = auditoria.sortear(registros, 4)
    assert sum(r["fonte"] == "veja.abril.com.br" for r in amostra) == 2
    assert amostra == auditoria.sortear(list(reversed(registros)), 4)


def test_wilson():
    inferior, superior = auditoria.wilson(10, 200)
    assert inferior == pytest.approx(0.0274, abs=1e-3)
    assert superior == pytest.approx(0.0896, abs=1e-3)
    assert auditoria.wilson(0, 0) == (0.0, 1.0)


def revisao(item, revisor, problema="nenhum", fonte="poder360.com.br"):
    return {"id": item, "fonte": fonte, "revisor": revisor, "problema": problema, "observacao": ""}


def test_medir_ruido_kappa_e_veiculo_acima_do_limite():
    linhas = []
    for i in range(40):
        linhas += [revisao(f"p{i}", "ana"), revisao(f"p{i}", "bia")]
    linhas[1] = revisao("p0", "bia", "exagero")  # 1 de 40 no poder360: 2,5%
    for i in range(10):
        problema = "erro_factual" if i < 3 else "nenhum"  # 3 de 10 na veja: 30%
        linhas += [
            revisao(f"v{i}", "ana", problema, "veja.abril.com.br"),
            revisao(f"v{i}", "bia", problema, "veja.abril.com.br"),
        ]
    resultado = auditoria.medir(linhas)
    veiculos = {v["fonte"]: v for v in resultado["veiculos"]}
    assert veiculos["poder360.com.br"]["aceito"] == 1
    assert veiculos["veja.abril.com.br"]["aceito"] == 0
    assert resultado["ruido_total"] == pytest.approx(4 / 50)
    assert resultado["ruido_mantidos"] == pytest.approx(1 / 40) and resultado["aceito"]
    assert resultado["kappas"]["ana-bia"]["itens"] == 50

    so_problemas = [revisao(f"x{i}", "ana", "exagero") for i in range(3)]
    so_problemas.append(revisao("x9", "ana"))
    recusado = auditoria.medir(so_problemas)
    assert not recusado["aceito"]
    assert all(v["aceito"] == 0 for v in recusado["veiculos"])


def test_importar_tira_texto_e_valida(tmp_path):
    planilha = tmp_path / "auditoria-ana.csv"
    auditoria.gravar_csv(
        planilha,
        auditoria.COLUNAS_PLANILHA,
        [
            {
                "id": "m1",
                "fonte": "poder360.com.br",
                "texto_curto": "título do veículo",
                "url": "https://x",
                "problema": "Nenhum",
                "revisor": "ana",
            },
            {
                "id": "m2",
                "fonte": "poder360.com.br",
                "texto_curto": "outro",
                "problema": "",
                "revisor": "ana",
            },
        ],
    )
    destino = tmp_path / "auditoria-verdadeiras.csv"
    assert auditoria.importar([planilha], destino) == (1, 1)
    conteudo = destino.read_text(encoding="utf-8")
    assert "título do veículo" not in conteudo and "https://x" not in conteudo
    with pytest.raises(auditoria.ErroAuditoria):
        auditoria.normalizar({"id": "m3", "fonte": "f", "revisor": "ana", "problema": "boato"})
