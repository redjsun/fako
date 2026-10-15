from datetime import date, datetime

from app.integrations.noticias_client import (
    AgenciaBrasilClient,
    Noticia,
    NoticiasIndisponiveis,
    get_noticias_clients,
)
from app.jobs.coletar_avaliacao import coletar
from app.ml.llm import FakeLLMClient, LLMAusente

RECENTE = datetime(2026, 10, 10, 12, 0)

RSS = b"""<?xml version="1.0" encoding="utf-8" ?>
<rss version="2.0"><channel>
  <item>
    <title>IBGE estima safra de gr&#227;os recorde em 2026</title>
    <link>https://agenciabrasil.ebc.com.br/economia/noticia/2026-10/safra</link>
    <pubDate>Thu, 15 Oct 2026 10:18:00 -0300</pubDate>
  </item>
  <item><title>Sem data</title><link>https://agenciabrasil.ebc.com.br/x</link></item>
</channel></rss>"""


class Provedor:
    def __init__(self, noticias=None, erro=None):
        self.noticias, self.erro = noticias or [], erro

    def buscar(self, quantidade):
        if self.erro:
            raise self.erro
        return self.noticias[:quantidade]


def manchete(titulo, url, publicada_em=RECENTE):
    return Noticia(titulo=titulo, url=url, veiculo="Jornal", publicada_em=publicada_em)


def checagem(alegacao, url, veredito, verdadeira):
    return Noticia(
        titulo=alegacao,
        url=url,
        veiculo="Agência",
        publicada_em=RECENTE,
        veredito=veredito,
        verdadeira=verdadeira,
    )


def test_agencia_brasil_le_o_rss():
    primeira, sem_data = AgenciaBrasilClient.noticias(RSS)
    assert primeira.titulo == "IBGE estima safra de grãos recorde em 2026"
    assert primeira.veiculo == "Agência Brasil" and primeira.verdadeira is True
    assert primeira.publicada_em.date() == date(2026, 10, 15)
    assert sem_data.publicada_em is None


def test_agencia_brasil_para_quando_junta_a_quantidade(monkeypatch):
    cliente = AgenciaBrasilClient()
    lidos = []

    def do_feed(feed):
        lidos.append(feed)
        return [manchete(f"{feed} {i}", f"https://ab/{feed}/{i}") for i in range(10)]

    monkeypatch.setattr(cliente, "do_feed", do_feed)
    monkeypatch.setattr(cliente, "PAUSA", 0)
    assert len(cliente.buscar(15)) == 15
    assert lidos == list(AgenciaBrasilClient.FEEDS[:2])


def test_provedores_por_nome_sem_depender_do_env():
    [cliente] = get_noticias_clients("agenciabrasil")
    assert isinstance(cliente, AgenciaBrasilClient)


def test_coleta_no_formato_do_jogo_sem_o_que_o_treino_ja_viu():
    titulo = "Ministério da Saúde amplia vacinação contra a gripe para todas as idades"
    provedores = {
        "gnews": Provedor(
            [
                manchete(f"{titulo} - Jornal", "https://j/1"),
                manchete(titulo, "https://j/2"),  # a mesma manchete em outra URL
                manchete(
                    "Anatel aprova regras do 5G rural no país", "https://j/3", datetime(2026, 9, 1)
                ),
            ]
        ),
        "factcheck": Provedor(
            [
                checagem(
                    "Vacina contra a gripe contém um chip de rastreamento",
                    "https://a/1",
                    "falso",
                    False,
                ),
                checagem(
                    "Chá de boldo elimina o vírus da gripe em um dia",
                    "https://a/2",
                    "enganoso",
                    None,
                ),
                checagem(
                    "Remédio caseiro cura a dengue em dois dias", "https://a/3", "sem provas", None
                ),
            ]
        ),
        "fora": Provedor(erro=NoticiasIndisponiveis("cota")),
    }
    avisos = []
    linhas, descartes = coletar(
        provedores, FakeLLMClient(), 10, date(2026, 10, 7), avisar=avisos.append
    )
    assert [(linha["provedor"], linha["veracidade"], linha["is_true"]) for linha in linhas] == [
        ("gnews", "verdadeiro", True),
        ("factcheck", "falso", False),
        ("factcheck", "enganoso", False),
    ]
    assert linhas[0]["manchete"] == titulo and linhas[0]["afirmacao"] == titulo
    assert linhas[0]["n_afirmacoes"] == 1 and len(linhas[0]["id"]) == 16
    assert descartes["repetida"] == 1 and descartes["anterior ao treino"] == 1
    assert descartes["veredito sem lado no jogo (sem provas)"] == 1
    assert sum(descartes.values()) == 3
    assert any(aviso.startswith("fora: ") for aviso in avisos)


def test_sem_llm_a_afirmacao_fica_vazia():
    provedores = {
        "gnews": Provedor([manchete("Anatel aprova regras para o 5G rural no país", "https://j/1")])
    }
    [linha], _ = coletar(provedores, LLMAusente("sem LLM"), 10, date(2026, 10, 7))
    assert linha["afirmacao"] is None and linha["n_afirmacoes"] is None


def test_veracidade_em_tres_niveis_como_no_treino():
    from app.ml.normalizacao import veracidade_pelo_veredito

    assert veracidade_pelo_veredito("montagem") == "falso"
    assert veracidade_pelo_veredito("fora de contexto") == "enganoso"
    assert veracidade_pelo_veredito("comprovado") == "verdadeiro"
    assert veracidade_pelo_veredito("sem provas") is None


def test_boatos_le_a_alegacao_na_voz_do_boato():
    from app.integrations.noticias_client import BoatosClient

    publicacao = {
        "date_gmt": "2026-10-14T21:10:35",
        "link": "https://www.boatos.org/saude/cha-cura.html",
        "title": {"rendered": "Ch&aacute; de boldo n&atilde;o cura a dengue"},
        "content": {
            "rendered": "<p><b>Boato &#8211; Chá de boldo cura a dengue em dois dias.</b></p>"
            "<p>Análise</p><p>O conteúdo é falso.</p>"
        },
    }
    boato = BoatosClient.boato(publicacao)
    assert boato.titulo == "Chá de boldo cura a dengue em dois dias."
    assert boato.veredito == "falso" and boato.verdadeira is False
    assert boato.publicada_em.date() == date(2026, 10, 14) and boato.publicada_em.tzinfo
    assert boato.descricao == "Chá de boldo não cura a dengue"
    assert BoatosClient.boato({**publicacao, "content": {"rendered": "<p>Análise</p>"}}) is None
