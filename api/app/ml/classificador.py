"""Classificador de veracidade: uma interface, uma implementação por modelo.

A API não sabe qual modelo está por trás (referência TF-IDF, BERTimbau...). Cada um é um
adaptador que devolve as duas fronteiras ordinais, P1 = P(> falso) e P2 = P(> enganoso), e a
regra de decisão abaixo, comum a todos, transforma isso em `Analise`. Trocar de modelo é
trocar o adaptador em `get_classificador()`; services e controllers não mudam.

Se o modelo não carregar, `get_classificador()` devolve um cliente que lança
`ClassificadorIndisponivel`: os services tratam e o jogo segue sem análise.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

from app.core.config import get_settings
from app.ml.normalizacao import limpar

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


class ReferenciaTfidf:
    """Referência TF-IDF + regressão logística ordinal (pesquisa/ml/treinar_referencia.py).

    Lê o `referencia.joblib` da pasta publicada: um dicionário só com objetos do
    scikit-learn (`vetorizador`, `fronteira_1`, `fronteira_2`) e a `versao`. A frase passa
    pela mesma `limpar()` do treino antes de virar TF-IDF.
    """

    ARQUIVO = "referencia.joblib"

    def __init__(self, pasta: Path):
        import joblib  # só quem usa este adaptador precisa do scikit-learn carregado

        self.modelo = joblib.load(pasta / self.ARQUIVO)
        self.versao = self.modelo.get("versao", pasta.name)
        self.limiares = ler_limiares(pasta)

    def fronteiras(self, texto: str) -> tuple[float, float]:
        matriz = self.modelo["vetorizador"].transform([texto])
        p1 = float(self.modelo["fronteira_1"].predict_proba(matriz)[0, 1])
        p2 = float(self.modelo["fronteira_2"].predict_proba(matriz)[0, 1])
        return p1, min(p2, p1)

    def contribuicoes(self, texto: str, n: int = 8) -> list[tuple[str, float]]:
        """Termos que mais pesaram na fronteira 1 (negativo puxa para falso). Só o admin vê."""
        linha = self.modelo["vetorizador"].transform([texto]).tocsr()
        nomes = self.modelo["vetorizador"].get_feature_names_out()
        valores = linha.data * self.modelo["fronteira_1"].coef_[0][linha.indices]
        ordem = sorted(range(len(valores)), key=lambda i: -abs(valores[i]))[:n]
        return [(legivel(nomes[linha.indices[i]]), float(valores[i])) for i in ordem]

    def analisar(self, afirmacao: str, limiar: Limiar) -> Analise:
        texto = limpar(afirmacao) or afirmacao.strip()
        p1, p2 = self.fronteiras(texto)
        analise = analise_das_fronteiras(afirmacao, p1, p2, self.limiares[limiar], self.versao)
        if limiar == "admin":
            analise.contribuicoes = self.contribuicoes(texto)
        return analise


def legivel(variavel: str) -> str:
    """ "palavras__lula disse" -> "lula disse"; "caracteres__ vac" -> "[ vac]"."""
    tipo, _, termo = variavel.partition("__")
    return f"[{termo}]" if tipo == "caracteres" else termo


def ler_limiares(pasta: Path) -> dict[str, float]:
    """`limiares.json` do modelo, se houver (calibrado na validação, #12); senão o padrão."""
    arquivo = pasta / "limiares.json"
    if not arquivo.exists():
        return dict(LIMIARES_PADRAO)
    return {**LIMIARES_PADRAO, **json.loads(arquivo.read_text(encoding="utf-8"))}


ADAPTADORES = {"referencia": ReferenciaTfidf}


class ClassificadorAusente:
    """Responde no lugar do modelo que não carregou."""

    def __init__(self, motivo: str):
        self.motivo = motivo

    def analisar(self, afirmacao: str, limiar: Limiar) -> Analise:
        raise ClassificadorIndisponivel(self.motivo)


@lru_cache(maxsize=4)
def _carregar(provedor: str, pasta: Path, modificado: float) -> ClassificadorClient:
    """Carrega uma vez por modelo publicado; republicar (outra data de modificação) recarrega."""
    return ADAPTADORES[provedor](pasta)


def get_classificador() -> ClassificadorClient:
    settings = get_settings()
    provedor = settings.classificador_provider
    if provedor == "fake":
        return FakeClassificador()
    if provedor not in ADAPTADORES:
        return ClassificadorAusente(f"Classificador não suportado: {provedor}")
    modelo = Path(settings.models_dir) / "atual"
    arquivo = modelo / ADAPTADORES[provedor].ARQUIVO
    if not arquivo.exists():
        return ClassificadorAusente(f"Nenhum modelo publicado em {modelo}")
    try:
        return _carregar(provedor, modelo, arquivo.stat().st_mtime)
    except Exception as erro:  # arquivo corrompido ou de outra versão do scikit-learn
        return ClassificadorAusente(f"O modelo em {modelo} não carregou: {erro}")
