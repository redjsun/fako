"""Configuração de cada execução de treino, num arquivo TOML em pesquisa/ml/configs/.

Uso nos scripts de treino (#9, #10):
    config = carregar_configuracao(Path("pesquisa/ml/configs/referencia.toml"))
    conjunto = carregar(**config.argumentos_dados())
    ...
    gravar_previsoes(config.saida, previsoes, config.registro(conjunto.dataset_sha256))

Um arquivo descreve uma execução inteira: dados (dataset, texto original ou padronizado),
modelo, hiperparâmetros, sementes e pasta de saída. Ele é versionado no Git, e o seu conteúdo
e o hash vão para o `config.json` ao lado das previsões, junto com o hash do dataset. Assim
dá para refazer qualquer resultado do relatório, e o avaliar.py carrega os mesmos exemplos.

Seções:
    nome = "referencia"              # identifica a execução
    modelo = "referencia" | "bert"   # qual script de treino
    saida = "models/2026-11/referencia"
    [dados]   dataset, texto ("original" ou "padronizado"), prompt, modelo_llm (padrão: LLM_MODEL)
    [treino]  hiperparâmetros do modelo (livres, cada script lê os seus)
    sementes = [13, 42, 7]

Caminhos relativos são da raiz do repositório, como os comandos.
"""

import hashlib
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
CONFIGS = Path(__file__).resolve().parent / "configs"
MODELOS = ("referencia", "bert", "atalho")
TEXTOS = ("original", "padronizado")


class ErroConfiguracao(ValueError):
    pass


@dataclass
class Configuracao:
    nome: str
    modelo: str
    saida: Path
    dataset: Path
    texto: str = "original"
    prompt: Path | None = None
    modelo_llm: str | None = None
    treino: dict = field(default_factory=dict)
    sementes: list[int] = field(default_factory=lambda: [42])
    arquivo: Path | None = None
    sha1: str = ""

    def argumentos_dados(self) -> dict:
        """Argumentos de dados.carregar() para esta execução."""
        return {
            "texto": self.texto,
            "dataset": self.dataset,
            "prompt": self.prompt,
            "modelo": self.modelo_llm,
        }

    def registro(self, dataset_sha256: str) -> dict:
        """O que vai para o config.json do modelo (lido pelo avaliar.py)."""
        return {
            "nome": self.nome,
            "modelo": self.modelo,
            "texto": self.texto,
            "prompt": str(self.prompt) if self.prompt else None,
            "modelo_llm": self.modelo_llm,
            "treino": self.treino,
            "sementes": self.sementes,
            "configuracao": str(self.arquivo) if self.arquivo else None,
            "configuracao_sha1": self.sha1,
            "dataset_sha256": dataset_sha256,
        }


def caminho(valor: str | None, raiz: Path) -> Path | None:
    if not valor:
        return None
    p = Path(valor)
    return p if p.is_absolute() else raiz / p


def carregar_configuracao(arquivo: Path, raiz: Path = RAIZ_REPOSITORIO) -> Configuracao:
    """Lê e confere um arquivo de configuração."""
    bruto = arquivo.read_bytes()
    dados = tomllib.loads(bruto.decode("utf-8"))
    for chave in ("nome", "modelo", "saida"):
        if not dados.get(chave):
            raise ErroConfiguracao(f"{arquivo.name}: falta `{chave}`")
    if dados["modelo"] not in MODELOS:
        raise ErroConfiguracao(f"{arquivo.name}: modelo deve ser um de {MODELOS}")
    secao_dados = dados.get("dados", {})
    texto = secao_dados.get("texto", "original")
    if texto not in TEXTOS:
        raise ErroConfiguracao(f"{arquivo.name}: dados.texto deve ser um de {TEXTOS}")
    modelo_llm = secao_dados.get("modelo_llm") or os.environ.get("LLM_MODEL") or None
    if texto == "padronizado" and not (secao_dados.get("prompt") and modelo_llm):
        raise ErroConfiguracao(
            f"{arquivo.name}: texto padronizado exige dados.prompt e o modelo da padronização "
            "(dados.modelo_llm ou LLM_MODEL)"
        )
    sementes = dados.get("sementes", [42])
    if not sementes or not all(isinstance(s, int) for s in sementes):
        raise ErroConfiguracao(f"{arquivo.name}: sementes deve ser uma lista de inteiros")
    return Configuracao(
        nome=dados["nome"],
        modelo=dados["modelo"],
        saida=caminho(dados["saida"], raiz),
        dataset=caminho(secao_dados.get("dataset", "pesquisa/data/processed/dataset.jsonl"), raiz),
        texto=texto,
        prompt=caminho(secao_dados.get("prompt"), raiz),
        modelo_llm=modelo_llm,
        treino=dados.get("treino", {}),
        sementes=sementes,
        arquivo=arquivo,
        sha1=hashlib.sha1(bruto).hexdigest(),
    )
