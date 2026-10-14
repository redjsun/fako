"""Notícias externas: uma interface, uma implementação por provedor.

As notícias viram afirmações do jogo pela curadoria (services/noticias_service.py). O
provedor só entrega o texto cru e os metadados; a normalização para o formato do treino
fica em ml/normalizacao.py, igual para todos os provedores.

- GNews: manchetes publicadas, sempre verdadeiras.
- Fact Check: alegações checadas por agências, com o veredito (quase sempre falsas).
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from itertools import zip_longest
from typing import Protocol

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.ml.normalizacao import normalizar_veredito, verdadeira_pelo_veredito


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
    descricao: str | None = None
    # Veredito da agência, só nas checagens; sem ele, a notícia é manchete publicada.
    veredito: str | None = None
    # None quando o veredito não tem lado no jogo (enganoso, ambíguo).
    verdadeira: bool | None = True


class NoticiasClient(Protocol):
    def buscar(self, quantidade: int) -> list[Noticia]: ...


def data_iso(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


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
                publicada_em=datetime(2026, 10, 1, 12, 0),
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


class FactCheckClient:
    """Alegações checadas por agências brasileiras, pela Google Fact Check Tools API.

    https://developers.google.com/fact-check/tools/api. A API exige um termo de busca ou um
    site de agência; sem termo, cada agência devolve as checagens mais recentes primeiro. Junta
    as de todas as agências e fica com as mais recentes. Mesma lista de agências da coleta
    (pesquisa/dados/coletar_factcheck.py), só as que aparecem na API.
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
        return Noticia(
            titulo=claim.get("text") or "",
            url=revisao.get("url") or "",
            veiculo=(revisao.get("publisher") or {}).get("name"),
            publicada_em=data_iso(revisao.get("reviewDate")),
            descricao=revisao.get("title"),
            veredito=veredito,
            verdadeira=verdadeira_pelo_veredito(veredito),
        )


def get_noticias_clients() -> list[NoticiasClient]:
    """Um ou mais provedores, separados por vírgula: "factcheck,gnews" traz falsas e verdadeiras."""
    settings = get_settings()
    construtores = {
        "fake": FakeNoticias,
        "gnews": lambda: GNewsClient(settings.noticias_api_key),
        "factcheck": lambda: FactCheckClient(settings.factcheck_api_key),
    }
    provedores = [p.strip() for p in settings.noticias_provider.split(",") if p.strip()]
    for provedor in provedores:
        if provedor not in construtores:
            raise NoticiasIndisponiveis(f"Provedor de notícias não suportado: {provedor}")
    if not provedores:
        raise NoticiasIndisponiveis("Defina NOTICIAS_PROVIDER")
    return [construtores[p]() for p in provedores]
