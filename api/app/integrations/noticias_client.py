"""Notícias externas: uma interface, uma implementação por provedor.

As notícias viram afirmações do jogo pela curadoria (services/noticias_service.py). O
provedor só entrega a manchete crua e os metadados; a normalização para o formato do treino
fica em integrations/normalizacao.py, igual para todos os provedores.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError


class NoticiasIndisponiveis(ServiceUnavailableError):
    """O provedor não respondeu, recusou a chave ou estourou a cota."""


@dataclass
class Noticia:
    titulo: str
    url: str
    veiculo: str | None
    publicada_em: datetime | None
    descricao: str | None = None


class NoticiasClient(Protocol):
    def buscar(self, categoria: str, quantidade: int) -> list[Noticia]: ...


class FakeNoticias:
    """Sem chamadas externas, determinístico: para desenvolvimento e testes."""

    MANCHETES = (
        "Ministério da Saúde amplia vacinação contra a gripe para todas as idades",
        "Anatel aprova regras para o uso do 5G em áreas rurais do país",
        "IBGE divulga nova estimativa da população dos municípios brasileiros",
        "Prefeitura anuncia mutirão de exames gratuitos neste fim de semana",
        "Vídeo: veja o momento em que o foguete decola",
    )

    def buscar(self, categoria: str, quantidade: int) -> list[Noticia]:
        return [
            Noticia(
                titulo=f"{manchete} - Portal Exemplo",
                url=f"https://exemplo.com.br/{categoria}/{i}",
                veiculo="Portal Exemplo",
                publicada_em=datetime(2026, 10, 1, 12, 0),
            )
            for i, manchete in enumerate(self.MANCHETES[:quantidade])
        ]


class GNewsClient:
    """Manchetes do Brasil, em português, pela API do GNews (https://gnews.io/docs/v4)."""

    URL = "https://gnews.io/api/v4/top-headlines"
    # Slug da categoria do jogo -> tópico do GNews.
    TOPICOS = {"saude": "health", "tecnologia": "technology", "conhecimentos-gerais": "science"}
    MAXIMO_POR_PEDIDO = 10  # limite do plano gratuito

    def __init__(self, chave: str, tempo_limite: float = 10.0):
        if not chave:
            raise NoticiasIndisponiveis("Defina NOTICIAS_API_KEY para usar o GNews")
        self.chave = chave
        self.tempo_limite = tempo_limite

    def buscar(self, categoria: str, quantidade: int) -> list[Noticia]:
        parametros = {
            "category": self.TOPICOS.get(categoria, "general"),
            "lang": "pt",
            "country": "br",
            "max": min(quantidade, self.MAXIMO_POR_PEDIDO),
            "apikey": self.chave,
        }
        endereco = f"{self.URL}?{urllib.parse.urlencode(parametros)}"
        try:
            with urllib.request.urlopen(endereco, timeout=self.tempo_limite) as resposta:
                corpo = json.load(resposta)
        except urllib.error.HTTPError as erro:
            raise NoticiasIndisponiveis(f"GNews respondeu {erro.code}") from erro
        except (urllib.error.URLError, TimeoutError, ValueError) as erro:
            raise NoticiasIndisponiveis(f"GNews fora do ar: {erro}") from erro
        return [self.noticia(artigo) for artigo in corpo.get("articles", [])]

    @staticmethod
    def noticia(artigo: dict) -> Noticia:
        publicada = artigo.get("publishedAt")
        return Noticia(
            titulo=artigo.get("title") or "",
            url=artigo.get("url") or "",
            veiculo=(artigo.get("source") or {}).get("name"),
            publicada_em=datetime.fromisoformat(publicada.replace("Z", "+00:00"))
            if publicada
            else None,
            descricao=artigo.get("description"),
        )


def get_noticias_client() -> NoticiasClient:
    settings = get_settings()
    if settings.noticias_provider == "fake":
        return FakeNoticias()
    if settings.noticias_provider == "gnews":
        return GNewsClient(settings.noticias_api_key)
    raise NoticiasIndisponiveis(f"Provedor de notícias não suportado: {settings.noticias_provider}")
