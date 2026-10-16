"""Notícias externas: uma interface, uma implementação por provedor.

As notícias viram afirmações do jogo pela curadoria (services/noticias_service.py). O
provedor só entrega o texto cru e os metadados; a normalização para o formato do treino
fica em ml/normalizacao.py, igual para todos os provedores.

- GNews: manchetes publicadas, sempre verdadeiras.
- Agência Brasil: manchetes da agência pública (EBC) pelos feeds RSS, sem chave; verdadeiras.
- Fact Check: alegações checadas por agências, com o veredito (quase sempre falsas).
- Boatos.org: boatos desmentidos, na voz de quem os espalhou; sempre falsos.
"""

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from itertools import zip_longest
from typing import Protocol

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.ml.normalizacao import normalizar_autor, normalizar_veredito, verdadeira_pelo_veredito


class NoticiasIndisponiveis(ServiceUnavailableError):
    """O provedor não respondeu, recusou a chave ou estourou a cota."""

    def __init__(self, message: str, codigo_http: int | None = None) -> None:
        super().__init__(message)
        self.codigo_http = codigo_http


@dataclass
class Noticia:
    titulo: str
    url: str
    veiculo: str | None
    publicada_em: datetime | None
    # O título da checagem ou o resumo da matéria: entra no "Por quê?" (Question.source_detail).
    descricao: str | None = None
    # Veredito da agência, só nas checagens; sem ele, a notícia é manchete publicada.
    veredito: str | None = None
    # None quando o veredito não tem lado no jogo (enganoso, ambíguo).
    verdadeira: bool | None = True
    # Onde a alegação circulou, nas checagens (`claimant` e `claimDate` da Fact Check API).
    # A API não traz o link do post; raspar a matéria da agência achou link em 3 de 21 páginas,
    # e nem sempre do post checado (às vezes da prova), então o link fica sendo o da checagem.
    origem_autor: str | None = None
    origem_data: date | None = None


class NoticiasClient(Protocol):
    def buscar(self, quantidade: int) -> list[Noticia]: ...


def data_iso(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        data = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Sem fuso, vale UTC: comparar datas com e sem fuso dá erro ou ordena pela hora local.
    return data if data.tzinfo else data.replace(tzinfo=timezone.utc)


def pedir_json(endereco: str, tempo_limite: float, provedor: str) -> dict:
    try:
        with urllib.request.urlopen(endereco, timeout=tempo_limite) as resposta:
            return json.load(resposta)
    except urllib.error.HTTPError as erro:
        raise NoticiasIndisponiveis(f"{provedor} respondeu {erro.code}", erro.code) from erro
    except (urllib.error.URLError, TimeoutError, ValueError) as erro:
        raise NoticiasIndisponiveis(f"{provedor} fora do ar: {erro}") from erro


class FakeNoticias:
    """Sem chamadas externas, determinístico: para desenvolvimento e testes."""

    MANCHETES = (
        "Ministério da Saúde amplia vacinação contra a gripe para todas as idades",
        "Anatel aprova regras para o uso do 5G em áreas rurais do país",
        "IBGE divulga nova estimativa da população dos municípios brasileiros",
        "Prefeitura anuncia mutirão de exames gratuitos neste fim de semana",
        "Vídeo: veja o momento em que o foguete decola",
    )

    def buscar(self, quantidade: int) -> list[Noticia]:
        return [
            Noticia(
                titulo=f"{manchete} - Portal Exemplo",
                url=f"https://exemplo.com.br/noticias/{i}",
                veiculo="Portal Exemplo",
                publicada_em=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
            )
            for i, manchete in enumerate(self.MANCHETES[:quantidade])
        ]


class GNewsClient:
    """Manchetes do Brasil, em português, pela API do GNews (https://gnews.io/docs/v4).

    Dos tópicos mais parecidos com os boatos checados (saúde, ciência, tecnologia, Brasil,
    mundo e economia): o "general" é quase só futebol e TV, que o jogador acerta sem pensar. Um
    pedido por tópico (10 manchetes no plano gratuito, até 60 candidatas; 6 dos 100 pedidos
    diários), intercalando os resultados.
    """

    URL = "https://gnews.io/api/v4/top-headlines"
    TOPICOS = ("health", "science", "technology", "nation", "world", "business")
    MAXIMO_POR_PEDIDO = 10  # limite do plano gratuito
    PAUSA = 1.2  # o plano gratuito aceita um pedido por segundo (429 se vierem juntos)

    def __init__(self, chave: str, tempo_limite: float = 10.0):
        if not chave:
            raise NoticiasIndisponiveis("Defina NOTICIAS_API_KEY para usar o GNews")
        self.chave = chave
        self.tempo_limite = tempo_limite

    def buscar(self, quantidade: int) -> list[Noticia]:
        por_topico = []
        for posicao, topico in enumerate(self.TOPICOS):
            if posicao:
                time.sleep(self.PAUSA)
            por_topico.append(self.do_topico(topico, quantidade))
        intercaladas = [n for grupo in zip_longest(*por_topico) for n in grupo if n]
        return intercaladas[:quantidade]

    def do_topico(self, topico: str, quantidade: int) -> list[Noticia]:
        parametros = {
            "category": topico,
            "lang": "pt",
            "country": "br",
            "max": min(quantidade, self.MAXIMO_POR_PEDIDO),
            "apikey": self.chave,
        }
        endereco = f"{self.URL}?{urllib.parse.urlencode(parametros)}"
        corpo = pedir_json(endereco, self.tempo_limite, "GNews")
        return [self.noticia(artigo) for artigo in corpo.get("articles", [])]

    @staticmethod
    def noticia(artigo: dict) -> Noticia:
        return Noticia(
            titulo=artigo.get("title") or "",
            url=artigo.get("url") or "",
            veiculo=(artigo.get("source") or {}).get("name"),
            publicada_em=data_iso(artigo.get("publishedAt")),
            descricao=artigo.get("description"),
        )


class AgenciaBrasilClient:
    """Manchetes da Agência Brasil (EBC) pelos feeds RSS, sem chave nem cota.

    Cada feed traz as 10 matérias mais recentes. A licença permite reproduzir citando a fonte,
    e o robots.txt não tem opt-out de robôs de IA. Os feeds são lidos na ordem de FEEDS até
    juntar `quantidade` manchetes, com a pausa do Crawl-delay do robots.txt (10 s) entre eles.
    """

    URL = "https://agenciabrasil.ebc.com.br/rss/{feed}/feed.xml"
    FEEDS = (
        "ultimasnoticias",
        "saude",
        "geral",
        "economia",
        "educacao",
        "internacional",
        "meio-ambiente",
        "direitos-humanos",
        "justica",
        "politica",
    )
    VEICULO = "Agência Brasil"
    PAUSA = 10.0

    def __init__(self, tempo_limite: float = 10.0):
        self.tempo_limite = tempo_limite

    def buscar(self, quantidade: int) -> list[Noticia]:
        por_url: dict[str, Noticia] = {}
        for posicao, feed in enumerate(self.FEEDS):
            if len(por_url) >= quantidade:
                break
            if posicao:
                time.sleep(self.PAUSA)
            for noticia in self.do_feed(feed):
                por_url.setdefault(noticia.url, noticia)
        return list(por_url.values())[:quantidade]

    def do_feed(self, feed: str) -> list[Noticia]:
        pedido = urllib.request.Request(
            self.URL.format(feed=feed), headers={"User-Agent": "FAKO/1.0"}
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.tempo_limite) as resposta:
                return self.noticias(resposta.read())
        except urllib.error.HTTPError as erro:
            raise NoticiasIndisponiveis(
                f"Agência Brasil respondeu {erro.code}", erro.code
            ) from erro
        except (urllib.error.URLError, TimeoutError, ElementTree.ParseError) as erro:
            raise NoticiasIndisponiveis(f"Agência Brasil fora do ar: {erro}") from erro

    @classmethod
    def noticias(cls, rss: bytes) -> list[Noticia]:
        return [
            Noticia(
                titulo=(item.findtext("title") or "").strip(),
                url=(item.findtext("link") or "").strip(),
                veiculo=cls.VEICULO,
                publicada_em=data_rfc822(item.findtext("pubDate")),
            )
            for item in ElementTree.fromstring(rss).iter("item")
        ]


def data_rfc822(texto: str | None) -> datetime | None:
    try:
        return parsedate_to_datetime(texto) if texto else None
    except (TypeError, ValueError):
        return None


class BoatosClient:
    """Boatos desmentidos pelo Boatos.org, pela API REST do WordPress, sem chave.

    Tudo o que o site publica é boato. O título é do checador ("...não passa de encenação"),
    então a alegação vem do parágrafo "Boato – ..." do início do texto, na voz de quem espalhou
    o boato. Publicação sem esse parágrafo fica de
    fora. O robots.txt não tem opt-out de robôs de IA.
    """

    URL = "https://www.boatos.org/wp-json/wp/v2/posts"
    VEICULO = "Boatos.org"
    MAXIMO_POR_PEDIDO = 100  # limite da API do WordPress
    PARAGRAFO = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
    PREFIXO_BOATO = re.compile(r"^\s*Boato\s*[–—-]\s*", re.I)

    def __init__(self, tempo_limite: float = 10.0):
        self.tempo_limite = tempo_limite

    def buscar(self, quantidade: int) -> list[Noticia]:
        parametros = {
            "per_page": min(quantidade, self.MAXIMO_POR_PEDIDO),
            "_fields": "date_gmt,link,title,content",
        }
        endereco = f"{self.URL}?{urllib.parse.urlencode(parametros)}"
        pedido = urllib.request.Request(endereco, headers={"User-Agent": "FAKO/1.0"})
        try:
            with urllib.request.urlopen(pedido, timeout=self.tempo_limite) as resposta:
                publicacoes = json.load(resposta)
        except urllib.error.HTTPError as erro:
            raise NoticiasIndisponiveis(f"Boatos.org respondeu {erro.code}", erro.code) from erro
        except (urllib.error.URLError, TimeoutError, ValueError) as erro:
            raise NoticiasIndisponiveis(f"Boatos.org fora do ar: {erro}") from erro
        boatos = (self.boato(publicacao) for publicacao in publicacoes)
        return [b for b in boatos if b]

    @classmethod
    def alegacao(cls, conteudo: str) -> str | None:
        """O texto do parágrafo "Boato – ...", sem o prefixo e sem as marcas de HTML."""
        for paragrafo in cls.PARAGRAFO.findall(conteudo or ""):
            texto = html.unescape(re.sub(r"<[^>]+>", "", paragrafo)).strip()
            if cls.PREFIXO_BOATO.match(texto):
                return cls.PREFIXO_BOATO.sub("", texto).strip() or None
        return None

    @classmethod
    def boato(cls, publicacao: dict) -> Noticia | None:
        alegacao = cls.alegacao((publicacao.get("content") or {}).get("rendered"))
        if not alegacao:
            return None
        data = publicacao.get("date_gmt")
        return Noticia(
            titulo=alegacao,
            url=publicacao.get("link") or "",
            veiculo=cls.VEICULO,
            publicada_em=data_iso(f"{data}Z" if data else None),
            descricao=html.unescape((publicacao.get("title") or {}).get("rendered") or ""),
            veredito="falso",
            verdadeira=False,
        )


class FactCheckClient:
    """Alegações checadas por agências brasileiras, pela Google Fact Check Tools API.

    https://developers.google.com/fact-check/tools/api. A API exige um termo de busca ou um
    site de agência; sem termo, cada agência devolve as checagens mais recentes primeiro. Junta
    as de todas as agências e fica com as mais recentes. Mesma lista de agências da coleta
    do dataset de treino, só as que aparecem na API.
    """

    URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    AGENCIAS = (
        "aosfatos.org",
        "estadao.com.br",
        "noticias.uol.com.br",
        "bol.uol.com.br",
        "checamos.afp.com",
        "projetocomprova.com.br",
        "www1.folha.uol.com.br",
        "oglobo.globo.com",
        "agenciatatu.com.br",
        "eleicoes.apublica.org",
        "nexojornal.com.br",
    )

    def __init__(self, chave: str, tempo_limite: float = 10.0):
        if not chave:
            raise NoticiasIndisponiveis("Defina FACTCHECK_API_KEY para usar a Fact Check API")
        self.chave = chave
        self.tempo_limite = tempo_limite

    def buscar(self, quantidade: int) -> list[Noticia]:
        checagens, falhas = [], []
        for site in self.AGENCIAS:
            try:
                checagens += self.da_agencia(site, quantidade)
            except NoticiasIndisponiveis as erro:
                # Chave recusada ou cota estourada valem para todas as agências; outra falha
                # (fora do ar, erro 5xx) perde só uma.
                if erro.codigo_http and erro.codigo_http < 500:
                    raise
                falhas.append(erro)
        if not checagens and falhas:
            raise falhas[0]
        checagens.sort(
            key=lambda c: c.publicada_em.timestamp() if c.publicada_em else 0, reverse=True
        )
        return checagens[:quantidade]

    def da_agencia(self, site: str, quantidade: int) -> list[Noticia]:
        parametros = {
            "reviewPublisherSiteFilter": site,
            "languageCode": "pt",
            "pageSize": quantidade,
            "key": self.chave,
        }
        endereco = f"{self.URL}?{urllib.parse.urlencode(parametros)}"
        corpo = pedir_json(endereco, self.tempo_limite, "Fact Check API")
        checagens = (self.checagem(claim, site) for claim in corpo.get("claims", []))
        return [c for c in checagens if c]

    @staticmethod
    def checagem(claim: dict, site: str) -> Noticia | None:
        """Uma alegação pode ter checagens de várias agências: fica a da agência pedida."""
        revisoes = claim.get("claimReview") or []
        revisao = next(
            (r for r in revisoes if (r.get("publisher") or {}).get("site") == site),
            revisoes[0] if revisoes else None,
        )
        if revisao is None:
            return None
        veredito = normalizar_veredito(revisao.get("textualRating"))
        if veredito is None:
            # Sem veredito a alegação passaria por manchete publicada (verdadeira).
            return None
        circulou_em = data_iso(claim.get("claimDate"))
        return Noticia(
            titulo=claim.get("text") or "",
            url=revisao.get("url") or "",
            veiculo=(revisao.get("publisher") or {}).get("name"),
            publicada_em=data_iso(revisao.get("reviewDate")),
            descricao=revisao.get("title"),
            veredito=veredito,
            verdadeira=verdadeira_pelo_veredito(veredito),
            origem_autor=normalizar_autor(claim.get("claimant")),
            origem_data=circulou_em.date() if circulou_em else None,
        )


def get_noticias_clients(nomes: str | None = None) -> list[NoticiasClient]:
    """Um ou mais provedores, separados por vírgula: "factcheck,gnews" traz falsas e verdadeiras.

    Sem `nomes`, os de NOTICIAS_PROVIDER.
    """
    settings = get_settings()
    construtores = {
        "fake": FakeNoticias,
        "gnews": lambda: GNewsClient(settings.noticias_api_key),
        "agenciabrasil": AgenciaBrasilClient,
        "factcheck": lambda: FactCheckClient(settings.factcheck_api_key),
        "boatos": BoatosClient,
    }
    nomes = settings.noticias_provider if nomes is None else nomes
    provedores = [p.strip() for p in nomes.split(",") if p.strip()]
    for provedor in provedores:
        if provedor not in construtores:
            raise NoticiasIndisponiveis(f"Provedor de notícias não suportado: {provedor}")
    if not provedores:
        raise NoticiasIndisponiveis("Defina NOTICIAS_PROVIDER")
    return [construtores[p]() for p in provedores]
