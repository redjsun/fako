"""Classificador de veracidade: uma interface, uma implementação por modelo.

A API não sabe qual modelo está por trás (referência TF-IDF, BERTimbau...). Cada um é um
adaptador que devolve as duas fronteiras ordinais, P1 = P(> falso) e P2 = P(> enganoso), e a
regra de decisão abaixo, comum a todos, transforma isso em `Analise`. Trocar de modelo é
trocar o adaptador em `get_classificador()`; services e controllers não mudam.

Se o modelo não carregar, `get_classificador()` devolve um cliente que lança
`ClassificadorIndisponivel`: os services tratam e o jogo segue sem análise.
"""

import json
import math
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
    # "original", "padronizado" ou "hibrido": o texto em que o modelo foi treinado. Fora do
    # original, a entrada é a afirmação extraída pela LLM (Question.claim_text), não o
    # enunciado cru.
    texto_de_entrada: str

    # `enunciado`: o texto como o jogador leu, quando a entrada é a afirmação extraída. Só o
    # conjunto usa (o membro do texto original recebe o enunciado); os outros o ignoram.
    def analisar(self, afirmacao: str, limiar: Limiar, enunciado: str | None = None) -> Analise: ...


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
    texto_de_entrada = "original"

    def analisar(self, afirmacao: str, limiar: Limiar, enunciado: str | None = None) -> Analise:
        return analise_das_fronteiras(afirmacao, 0.5, 0.25, LIMIARES_PADRAO[limiar], self.versao)


class ReferenciaTfidf:
    """Referência TF-IDF + regressão logística ordinal.

    Lê o `referencia.joblib` da pasta publicada: um dicionário só com objetos do
    scikit-learn (`vetorizador`, `fronteira_1`, `fronteira_2`) e a `versao`. A frase passa
    pela mesma `limpar()` do treino antes de virar TF-IDF. Se houver `calibracao.json`
    (Platt por fronteira, ajustado na validação), as fronteiras são calibradas antes da regra de
    decisão; `texto_de_entrada` diz se o modelo foi treinado no texto original ou no
    padronizado pela LLM (`config.json`).
    """

    ARQUIVO = "referencia.joblib"

    def __init__(self, pasta: Path):
        import joblib  # só quem usa este adaptador precisa do scikit-learn carregado

        self.modelo = joblib.load(pasta / self.ARQUIVO)
        self.versao = self.modelo.get("versao", pasta.name)
        self.limiares = ler_limiares(pasta)
        self.calibracao = ler_json(pasta / "calibracao.json")
        self.texto_de_entrada = (ler_json(pasta / "config.json") or {}).get("texto", "original")

    def fronteiras(self, texto: str) -> tuple[float, float]:
        matriz = self.modelo["vetorizador"].transform([texto])
        p1 = float(self.modelo["fronteira_1"].predict_proba(matriz)[0, 1])
        p2 = min(float(self.modelo["fronteira_2"].predict_proba(matriz)[0, 1]), p1)
        return calibradas(p1, p2, self.calibracao)

    def contribuicoes(self, texto: str, n: int = 8) -> list[tuple[str, float]]:
        """Termos que mais pesaram na fronteira 1 (negativo puxa para falso). Só o admin vê."""
        linha = self.modelo["vetorizador"].transform([texto]).tocsr()
        nomes = self.modelo["vetorizador"].get_feature_names_out()
        valores = linha.data * self.modelo["fronteira_1"].coef_[0][linha.indices]
        ordem = sorted(range(len(valores)), key=lambda i: -abs(valores[i]))[:n]
        return [(legivel(nomes[linha.indices[i]]), float(valores[i])) for i in ordem]

    def analisar(self, afirmacao: str, limiar: Limiar, enunciado: str | None = None) -> Analise:
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


class BertOnnx:
    """BERTimbau com cabeça ordinal CORAL, exportado para ONNX.

    Lê da pasta publicada o `modelo.onnx`, o `tokenizer.json` e o `onnx.json` (`max_tokens`,
    `versao`) gravados na exportação, e roda com `onnxruntime` na CPU, sem
    PyTorch. Mesma limpeza, calibração (`calibracao.json`), limiares e regra de decisão da
    referência. Não há contribuições por palavra: o admin vê só a análise.
    """

    ARQUIVO = "modelo.onnx"

    def __init__(self, pasta: Path):
        import onnxruntime  # só quem usa este adaptador carrega o runtime
        from tokenizers import Tokenizer

        meta = ler_json(pasta / "onnx.json") or {}
        self.sessao = onnxruntime.InferenceSession(
            str(pasta / self.ARQUIVO), providers=["CPUExecutionProvider"]
        )
        self.tokenizador = Tokenizer.from_file(str(pasta / "tokenizer.json"))
        self.tokenizador.no_padding()
        self.tokenizador.enable_truncation(max_length=meta.get("max_tokens", 96))
        self.versao = meta.get("versao", pasta.name)
        self.limiares = ler_limiares(pasta)
        self.calibracao = ler_json(pasta / "calibracao.json")
        self.texto_de_entrada = (ler_json(pasta / "config.json") or {}).get("texto", "original")

    def fronteiras(self, texto: str) -> tuple[float, float]:
        import numpy as np

        codificado = self.tokenizador.encode(texto)
        logits = self.sessao.run(
            ["logits"],
            {
                "input_ids": np.array([codificado.ids], dtype=np.int64),
                "attention_mask": np.array([codificado.attention_mask], dtype=np.int64),
            },
        )[0][0]
        p1 = 1 / (1 + math.exp(-float(logits[0])))
        p2 = min(1 / (1 + math.exp(-float(logits[1]))), p1)
        return calibradas(p1, p2, self.calibracao)

    def analisar(self, afirmacao: str, limiar: Limiar, enunciado: str | None = None) -> Analise:
        texto = limpar(afirmacao) or afirmacao.strip()
        p1, p2 = self.fronteiras(texto)
        return analise_das_fronteiras(afirmacao, p1, p2, self.limiares[limiar], self.versao)


def calibradas(p1: float, p2: float, calibracao: dict | None) -> tuple[float, float]:
    """As fronteiras depois do Platt de `calibracao.json`, se houver; P1 >= P2 sempre."""
    if calibracao:
        p1 = platt(p1, calibracao["fronteira_1"])
        p2 = platt(p2, calibracao["fronteira_2"])
    return p1, min(p2, p1)


def ler_json(arquivo: Path) -> dict | None:
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else None


def platt(p: float, parametros: dict[str, float]) -> float:
    """sigmoide(a · logit(p) + b), a mesma da calibração do modelo."""
    p = min(max(p, 1e-6), 1 - 1e-6)
    return 1 / (1 + math.exp(-(parametros["a"] * math.log(p / (1 - p)) + parametros["b"])))


def ler_limiares(pasta: Path) -> dict[str, float]:
    """`limiares.json` do modelo, se houver (calibrado na validação, #12); senão o padrão."""
    arquivo = pasta / "limiares.json"
    if not arquivo.exists():
        return dict(LIMIARES_PADRAO)
    return {**LIMIARES_PADRAO, **json.loads(arquivo.read_text(encoding="utf-8"))}


class ConjuntoBert:
    """Dois BERTimbau publicados juntos, com a média das fronteiras já calibradas de cada um.

    `conjunto.json` lista os membros (subpastas no formato de `BertOnnx`, cada uma com a sua
    calibração) e os pesos, mais os limiares e a versão do conjunto. O membro treinado no texto
    original recebe o enunciado (a manchete, como o jogador leu); o do texto híbrido, a
    afirmação extraída. Os dois erram em notícias diferentes: nas 225 notícias do jogo de
    15/10/2026, a média 50/50 teve 88% de acerto balanceado, contra 82% e 78% de cada um
    (doc/avaliacao-jogo.md).
    """

    ARQUIVO = "conjunto.json"
    texto_de_entrada = "hibrido"

    def __init__(self, pasta: Path):
        meta = ler_json(pasta / self.ARQUIVO) or {}
        self.membros = [(BertOnnx(pasta / m["pasta"]), float(m["peso"])) for m in meta["membros"]]
        self.limiares = {**LIMIARES_PADRAO, **meta.get("limiares", {})}
        self.versao = meta.get("versao", pasta.name)

    def fronteiras(self, afirmacao: str, enunciado: str | None = None) -> tuple[float, float]:
        p1 = p2 = 0.0
        for membro, peso in self.membros:
            bruto = enunciado if membro.texto_de_entrada == "original" and enunciado else afirmacao
            a, b = membro.fronteiras(limpar(bruto) or bruto.strip())
            p1, p2 = p1 + peso * a, p2 + peso * b
        total = sum(peso for _, peso in self.membros)
        return p1 / total, min(p2, p1) / total

    def analisar(self, afirmacao: str, limiar: Limiar, enunciado: str | None = None) -> Analise:
        p1, p2 = self.fronteiras(afirmacao, enunciado)
        return analise_das_fronteiras(afirmacao, p1, p2, self.limiares[limiar], self.versao)


ADAPTADORES = {"referencia": ReferenciaTfidf, "bert": BertOnnx, "conjunto": ConjuntoBert}


class ClassificadorAusente:
    """Responde no lugar do modelo que não carregou."""

    texto_de_entrada = "original"

    def __init__(self, motivo: str):
        self.motivo = motivo

    def analisar(self, afirmacao: str, limiar: Limiar, enunciado: str | None = None) -> Analise:
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
    except Exception as erro:  # arquivo corrompido ou de outra versão da biblioteca
        return ClassificadorAusente(f"O modelo em {modelo} não carregou: {erro}")
