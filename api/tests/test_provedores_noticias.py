from datetime import date, datetime

from app.integrations.noticias_client import (
    AgenciaBrasilClient,
    BoatosClient,
    Noticia,
    get_noticias_clients,
)
from app.ml.normalizacao import veracidade_pelo_veredito

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


def manchete(titulo, url, publicada_em=RECENTE):
    return Noticia(titulo=titulo, url=url, veiculo="Jornal", publicada_em=publicada_em)


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


def test_veracidade_do_veredito_em_tres_niveis():
    assert veracidade_pelo_veredito("montagem") == "falso"
    assert veracidade_pelo_veredito("fora de contexto") == "enganoso"
    assert veracidade_pelo_veredito("comprovado") == "verdadeiro"
    assert veracidade_pelo_veredito("sem provas") is None


def test_boatos_le_a_alegacao_na_voz_do_boato():
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
