"""Embeddings de frases: uma interface, usada como vem, sem treino.

- `FakeEmbeddings`: saco de palavras com hash, determinístico, para desenvolvimento e testes;
- `EmbeddingsHttp`: `/embeddings` de um endpoint compatível com a API da OpenAI; com o Ollama,
  o `bge-m3` (multilíngue, 1024 dimensões): `ollama pull bge-m3`.

Hoje servem à verificação da reescrita das questões (#21); o índice de evidências (#15) usa o
mesmo modelo.
"""

import hashlib
import json
import math
import re
import unicodedata
import urllib.error
import urllib.request
from typing import Protocol

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError

Vetor = list[float]


class EmbeddingsIndisponiveis(ServiceUnavailableError):
    """O provedor não está configurado ou não respondeu."""


class EmbeddingsClient(Protocol):
    def vetores(self, textos: list[str]) -> list[Vetor]: ...


def cosseno(a: Vetor, b: Vetor) -> float:
    produto = sum(x * y for x, y in zip(a, b, strict=True))
    normas = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return produto / normas if normas else 0.0


def similaridade(embeddings: EmbeddingsClient, a: str, b: str) -> float:
    vetor_a, vetor_b = embeddings.vetores([a, b])
    return cosseno(vetor_a, vetor_b)


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


class FakeEmbeddings:
    """Sem modelo: cada palavra soma 1 numa posição sorteada pelo hash."""

    DIMENSOES = 256

    def vetores(self, textos: list[str]) -> list[Vetor]:
        resultado = []
        for texto in textos:
            vetor = [0.0] * self.DIMENSOES
            for palavra in re.findall(r"\w+", sem_acento(texto)):
                posicao = int(hashlib.sha1(palavra.encode()).hexdigest(), 16) % self.DIMENSOES
                vetor[posicao] += 1.0
            resultado.append(vetor)
        return resultado


class EmbeddingsHttp:
    def __init__(self, base_url: str, modelo: str, chave: str = "", tempo_limite: float = 60):
        self.url = base_url.rstrip("/") + "/embeddings"
        self.modelo = modelo
        self.tempo_limite = tempo_limite
        self.cabecalhos = {"Content-Type": "application/json"}
        if chave:
            self.cabecalhos["Authorization"] = f"Bearer {chave}"

    def vetores(self, textos: list[str]) -> list[Vetor]:
        corpo = json.dumps({"model": self.modelo, "input": textos}).encode()
        requisicao = urllib.request.Request(self.url, corpo, self.cabecalhos)
        try:
            with urllib.request.urlopen(requisicao, timeout=self.tempo_limite) as resposta:
                dados = json.load(resposta)
            itens = sorted(dados["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in itens]
        except urllib.error.HTTPError as erro:
            raise EmbeddingsIndisponiveis(f"Embeddings respondeu {erro.code}") from erro
        except (urllib.error.URLError, TimeoutError) as erro:
            raise EmbeddingsIndisponiveis(f"Embeddings fora do ar: {erro}") from erro
        except (ValueError, KeyError, TypeError) as erro:
            raise EmbeddingsIndisponiveis(f"Resposta inesperada de embeddings: {erro}") from erro


class EmbeddingsAusentes:
    def __init__(self, motivo: str) -> None:
        self.motivo = motivo

    def vetores(self, textos: list[str]) -> list[Vetor]:
        raise EmbeddingsIndisponiveis(self.motivo)


def get_embeddings() -> EmbeddingsClient:
    settings = get_settings()
    if settings.embeddings_provider == "fake":
        return FakeEmbeddings()
    if settings.embeddings_provider != "openai":
        return EmbeddingsAusentes(
            f"Provedor de embeddings não suportado: {settings.embeddings_provider}"
        )
    base_url = settings.embeddings_base_url or settings.llm_base_url
    if not base_url or not settings.embeddings_model:
        return EmbeddingsAusentes("Defina EMBEDDINGS_BASE_URL (ou LLM_BASE_URL) e EMBEDDINGS_MODEL")
    return EmbeddingsHttp(base_url, settings.embeddings_model, settings.llm_api_key)
