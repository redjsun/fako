"""Classificador de veracidade: uma interface, uma implementação por modelo.

A API não sabe qual modelo está por trás (referência TF-IDF, BERTimbau...). Cada um é um
adaptador que devolve as duas fronteiras ordinais, P1 = P(> falso) e P2 = P(> enganoso), e a
regra de decisão abaixo, comum a todos, transforma isso em `Analise`. Trocar de modelo é
trocar o adaptador em `get_classificador()`; services e controllers não mudam.

Se o modelo não carregar, `get_classificador()` devolve um cliente que lança
`ClassificadorIndisponivel`: os services tratam e o jogo segue sem análise.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from app.core.config import get_settings

Limiar = Literal["admin", "jogador"]
Categoria = Literal["falso", "enganoso", "confere", "incerto", "opiniao"]
CATEGORIA_POR_CLASSE: tuple[Categoria, ...] = ("falso", "enganoso", "confere")
# Usados enquanto o modelo não traz o próprio limiares.json (calibrado na validação, #12).
LIMIARES_PADRAO: dict[str, float] = {"admin": 0.5, "jogador": 0.7}


class ClassificadorIndisponivel(Exception):
    """O modelo não está publicado ou não carregou."""


@dataclass
class Sinal:
    nome: str
    trecho: str


@dataclass
class Checagem:
    alegacao: str
    veredito: str
    url: str
    similaridade: float


@dataclass
class Analise:
    afirmacao: str
    categoria: Categoria
    nota: float | None  # 0 a 100; sem nota em opiniao e incerto
    confianca: float
    probabilidades: dict[str, float]
    versao_modelo: str
    quem_disse: str | None = None
    sinais: list[Sinal] = field(default_factory=list)
    sinais_fonte: list[str] = field(default_factory=list)
    checagem_parecida: Checagem | None = None
    contribuicoes: list[tuple[str, float]] = field(default_factory=list)  # só para o admin
    explicacao: str | None = None


class ClassificadorClient(Protocol):
    def analisar(self, afirmacao: str, limiar: Limiar) -> Analise: ...


def analise_das_fronteiras(
    afirmacao: str,
    p1: float,
    p2: float,
    limiar: float,
    versao_modelo: str,
) -> Analise:
    """Regra de decisão (doc/guia-classificacao.md §4), igual para todos os modelos.

    P(falso) = 1 − P1, P(enganoso) = P1 − P2, P(verdadeiro) = P2 e nota = 100 × (P1 + P2) / 2.
    Confiança abaixo do limiar vira `incerto`, sem nota firme.
    """
    p2 = min(p2, p1)
    probabilidades = {"falso": 1 - p1, "enganoso": p1 - p2, "verdadeiro": p2}
    valores = list(probabilidades.values())
    confianca = max(valores)
    if confianca < limiar:
        categoria: Categoria = "incerto"
        nota = None
    else:
        categoria = CATEGORIA_POR_CLASSE[valores.index(confianca)]
        nota = 100 * (p1 + p2) / 2
    return Analise(
        afirmacao=afirmacao,
        categoria=categoria,
        nota=nota,
        confianca=confianca,
        probabilidades=probabilidades,
        versao_modelo=versao_modelo,
    )


class FakeClassificador:
    """Sem modelo, determinístico: para desenvolvimento e testes."""

    versao = "fake"

    def analisar(self, afirmacao: str, limiar: Limiar) -> Analise:
        return analise_das_fronteiras(afirmacao, 0.5, 0.25, LIMIARES_PADRAO[limiar], self.versao)


class ClassificadorAusente:
    """Responde no lugar do modelo que não carregou."""

    def __init__(self, motivo: str):
        self.motivo = motivo

    def analisar(self, afirmacao: str, limiar: Limiar) -> Analise:
        raise ClassificadorIndisponivel(self.motivo)


def get_classificador() -> ClassificadorClient:
    settings = get_settings()
    provedor = settings.classificador_provider
    if provedor == "fake":
        return FakeClassificador()
    modelo = Path(settings.models_dir) / "atual"
    if not modelo.exists():
        return ClassificadorAusente(f"Nenhum modelo publicado em {modelo}")
    # Os adaptadores reais (referência TF-IDF, #9; BERTimbau, #10) entram aqui, lendo
    # `modelo` e o limiares.json dele.
    return ClassificadorAusente(f"Classificador não suportado: {provedor}")
