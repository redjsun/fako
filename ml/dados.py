"""Pipeline comum de preparação e carregamento de dados para ML do FAKO.

Este módulo é o ponto único de entrada para TF-IDF e BERTimbau.
Garante que ambos os modelos recebam exatamente os mesmos dados, com
o mesmo tratamento, mesmos filtros, mesmos pesos e mesmos splits.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator, Literal

logger = logging.getLogger("fako.ml.dados")

# Mapeamentos e constantes oficiais
CLASSES_VERACIDADE = ("falso", "enganoso", "verdadeiro")

MAPA_Y1 = {
    "falso": 0,
    "enganoso": 1,
    "verdadeiro": 1,
}

MAPA_Y2 = {
    "falso": 0,
    "enganoso": 0,
    "verdadeiro": 1,
}

PESOS_ORIGEM = {
    "agencia": 1.0,
    "curadoria": 1.0,
    "mensagem": 0.7,
    "equipe": 1.0,
    "jogo": 1.0,
    "confiavel": 1.0,
    "confiável": 1.0,
}

PESO_PADRAO = 1.0

# Regexes de limpeza textual
RE_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

# Prefixos comuns de agências e checagens (ex: "Boato – ", "FATO OU FAKE: ", "COMPROVA: ")
RE_PREFIXO_VEICULO = re.compile(
    r"^(?:(?:FATO OU FAKE|É FATO|É FAKE|VERIFICAMOS|BOATO|CHECAGEM|CHEQUEI|COMPROVA)\s*[-–—:|]\s*)+",
    re.IGNORECASE,
)

# Sufixos de portais e checadores após barra vertical ou travessão (ex: "| G1", "| Boatos.org", "- Lupa")
RE_SUFIXO_BARRA = re.compile(r"\s*\|\s*[^|]{1,30}$")
RE_SUFIXO_TRAVESSAO = re.compile(
    r"\s*[-–—]\s*(?:Boatos\.org|Aos Fatos|Agência Lupa|Lupa|E-farsas|G1|UOL|Folha|Estadão|Comprova|AFP)\s*$",
    re.IGNORECASE,
)

# Assinaturas e créditos comuns de matérias (início ou fim)
RE_ASSINATURA_INICIO = re.compile(
    r"^(?:(?:Foto|Crédito|Fonte|Por|Da Redação)\s*:\s*[^.\n]+(?:\.|\n|\s*[-–—]\s*)\s*)",
    re.IGNORECASE,
)
RE_ASSINATURA_FIM = re.compile(
    r"\s*(?:[-–—|]\s*(?:Por\s+[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*|Da Redação)|(?:Foto|Crédito|Fonte|Por|Da Redação|Reportagem de)\s*:\s*[^.\n]+)\s*\.?$",
    re.IGNORECASE,
)

# Espaços duplicados
RE_ESPACOS = re.compile(r"[ \t]+")
RE_QUEBRAS = re.compile(r"\n\s*")


def limpar_texto(texto: str | None) -> str:
    """Aplica limpeza textual preservando rigorosamente maiúsculas e pontuação.

    Regras aplicadas:
    1. Remove URLs (http, https, www).
    2. Remove prefixos e sufixos de veículos e agências de checagem.
    3. Remove assinaturas e créditos de autoria.
    4. Normaliza espaços excedentes.
    5. NÃO aplica .lower() (preserva maiúsculas/minúsculas).
    6. NÃO remove pontuação interrogativa, exclamativa ou expressiva.
    """
    if not texto:
        return ""

    s = texto.strip()

    # 1. Remoção de URLs
    s = RE_URL.sub("", s)

    # 2. Remoção de prefixos de veículos/checagens
    s = RE_PREFIXO_VEICULO.sub("", s)

    # 3. Remoção de sufixos de portais
    s = RE_SUFIXO_BARRA.sub("", s)
    s = RE_SUFIXO_TRAVESSAO.sub("", s)

    # 4. Remoção de assinaturas (início ou fim)
    s = RE_ASSINATURA_INICIO.sub("", s)
    s = RE_ASSINATURA_FIM.sub("", s)

    # 5. Normalização de espaçamento sem apagar pontuação
    s = RE_ESPACOS.sub(" ", s)
    s = RE_QUEBRAS.sub("\n", s)

    return s.strip()


@dataclass
class RegistroML:
    """Registro estruturado para uso nos modelos de ML."""

    id: str
    texto: str
    veracidade: str
    y1: int
    y2: int
    origem: str
    peso: float
    metadados: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "texto": self.texto,
            "veracidade": self.veracidade,
            "y1": self.y1,
            "y2": self.y2,
            "origem": self.origem,
            "peso": self.peso,
            "metadados": self.metadados,
        }

    def __getitem__(self, item: str) -> Any:
        if hasattr(self, item):
            return getattr(self, item)
        if item in self.metadados:
            return self.metadados[item]
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except KeyError:
            return default


@dataclass
class DadosML:
    """Estrutura consolidada dos dados preparados para treino e avaliação."""

    treino: list[RegistroML]
    validacao: list[RegistroML]
    teste: list[RegistroML]
    dataset_hash: str
    reserva: list[RegistroML] = field(default_factory=list)
    metadados: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        if hasattr(self, item):
            return getattr(self, item)
        if item in self.metadados:
            return self.metadados[item]
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except KeyError:
            return default

    def total_ativos(self) -> int:
        return len(self.treino) + len(self.validacao) + len(self.teste)

    def resumo(self) -> dict[str, Any]:
        def contar(splits: list[RegistroML]) -> dict[str, int]:
            c: dict[str, int] = {}
            for r in splits:
                c[r.veracidade] = c.get(r.veracidade, 0) + 1
            return c

        return {
            "dataset_hash": self.dataset_hash,
            "total_treino": len(self.treino),
            "total_validacao": len(self.validacao),
            "total_teste": len(self.teste),
            "total_reserva": len(self.reserva),
            "classes_treino": contar(self.treino),
            "classes_validacao": contar(self.validacao),
            "classes_teste": contar(self.teste),
        }


def calcular_dataset_hash(
    treino: list[RegistroML],
    validacao: list[RegistroML],
    teste: list[RegistroML],
) -> str:
    """Calcula um hash criptográfico (SHA-256) dos dados efetivamente usados.

    Considera os registros nos três splits (treino, validação e teste),
    ordenados de forma canônica por split e ID, incluindo o texto limpo,
    os alvos (veracidade, y1, y2) e o peso atribuído.
    """
    hasher = hashlib.sha256()

    splits = (("treino", treino), ("validacao", validacao), ("teste", teste))
    for nome_split, registros in splits:
        registros_ordenados = sorted(registros, key=lambda r: str(r.id))
        for r in registros_ordenados:
            linha_canonica = (
                f"{nome_split}:{r.id}:{r.texto}:{r.veracidade}:{r.y1}:{r.y2}:{r.peso:.4f}\n"
            )
            hasher.update(linha_canonica.encode("utf-8"))

    return hasher.hexdigest()


def carregar_anotacoes(caminho_anotacoes: Path | str | None) -> dict[str, dict[str, Any]]:
    """Carrega arquivos de anotação de equipe do diretório especificado.

    Suporta arquivos .jsonl, .json e .csv indexados pelo campo 'id'.
    """
    if not caminho_anotacoes:
        return {}

    caminho = Path(caminho_anotacoes)
    if not caminho.exists():
        return {}

    anotacoes: dict[str, dict[str, Any]] = {}

    arquivos = [caminho] if caminho.is_file() else sorted(caminho.glob("*"))

    for arq in arquivos:
        if arq.name.startswith(".") or arq.name.endswith(".md"):
            continue

        try:
            if arq.suffix.lower() == ".jsonl":
                with open(arq, encoding="utf-8") as f:
                    for linha in f:
                        linha = linha.strip()
                        if linha:
                            reg = json.loads(linha)
                            if "id" in reg:
                                anotacoes[str(reg["id"])] = reg
            elif arq.suffix.lower() == ".json":
                with open(arq, encoding="utf-8") as f:
                    conteudo = json.load(f)
                    if isinstance(conteudo, list):
                        for reg in conteudo:
                            if isinstance(reg, dict) and "id" in reg:
                                anotacoes[str(reg["id"])] = reg
                    elif isinstance(conteudo, dict):
                        for k, v in conteudo.items():
                            if isinstance(v, dict):
                                anotacoes[str(v.get("id", k))] = v
            elif arq.suffix.lower() == ".csv":
                with open(arq, encoding="utf-8", newline="") as f:
                    leitor = csv.DictReader(f)
                    for reg in leitor:
                        if "id" in reg and reg["id"]:
                            anotacoes[str(reg["id"])] = dict(reg)
        except Exception as e:
            logger.warning(f"Erro ao ler arquivo de anotação {arq}: {e}")

    return anotacoes


def obter_texto_padronizado(
    registro: dict[str, Any],
    versao_prompt: str,
    caminho_cache: Path | str | None = None,
) -> str | None:
    """Busca o texto padronizado via cache ou registro.

    A identificação do cache considera obrigatoriamente: id + versão do prompt.
    """
    reg_id = str(registro.get("id", ""))
    chave_cache = f"{reg_id}__{versao_prompt}"

    # 1. Verifica cache em disco, se configurado/existente
    if caminho_cache:
        pasta_cache = Path(caminho_cache)
        if pasta_cache.exists():
            arq_json = pasta_cache / f"{chave_cache}.json"
            if arq_json.exists():
                try:
                    dados = json.loads(arq_json.read_text(encoding="utf-8"))
                    if isinstance(dados, dict) and "texto_padronizado" in dados:
                        return str(dados["texto_padronizado"]).strip()
                    if isinstance(dados, str):
                        return dados.strip()
                except Exception as e:
                    logger.debug(f"Falha ao ler cache {arq_json}: {e}")

            arq_txt = pasta_cache / f"{chave_cache}.txt"
            if arq_txt.exists():
                try:
                    return arq_txt.read_text(encoding="utf-8").strip()
                except Exception as e:
                    logger.debug(f"Falha ao ler cache {arq_txt}: {e}")

    # 2. Verifica se o registro já traz versões padronizadas
    if "padronizacao" in registro and isinstance(registro["padronizacao"], dict):
        if versao_prompt in registro["padronizacao"]:
            return str(registro["padronizacao"][versao_prompt]).strip()

    if "texto_padronizado" in registro and registro.get("versao_prompt") == versao_prompt:
        return str(registro["texto_padronizado"]).strip()

    return None


def resolver_caminho_dataset(caminho: str | Path | None = None) -> Path:
    """Localiza o arquivo principal do dataset com base no ambiente."""
    if caminho:
        p = Path(caminho)
        if p.exists():
            return p
        raise FileNotFoundError(f"Arquivo de dataset não encontrado em: {p}")

    candidatos = [
        Path("data/processed/dataset.jsonl"),
        Path("/work/data/processed/dataset.jsonl"),
        Path(__file__).resolve().parent.parent / "data" / "processed" / "dataset.jsonl",
    ]

    for cand in candidatos:
        if cand.exists():
            return cand

    raise FileNotFoundError(
        "Arquivo data/processed/dataset.jsonl não encontrado. "
        "Execute 'make dados' ou 'python scripts/preparar_dados.py' para gerar a base processada."
    )


def resolver_caminho_anotacoes(caminho: str | Path | None = None) -> Path | None:
    if caminho:
        p = Path(caminho)
        return p if p.exists() else None

    candidatos = [
        Path("anotacoes"),
        Path("/work/anotacoes"),
        Path(__file__).resolve().parent.parent / "anotacoes",
    ]
    for cand in candidatos:
        if cand.exists():
            return cand
    return None


def resolver_caminho_cache(caminho: str | Path | None = None) -> Path | None:
    if caminho:
        p = Path(caminho)
        return p if p.exists() else None

    candidatos = [
        Path("data/cache/padronizacao"),
        Path("/work/data/cache/padronizacao"),
        Path(__file__).resolve().parent.parent / "data" / "cache" / "padronizacao",
    ]
    for cand in candidatos:
        if cand.exists():
            return cand
    return None


def carregar(
    texto: Literal["original", "padronizado"] = "original",
    versao_prompt: str = "v1",
    caminho_dataset: str | Path | None = None,
    caminho_anotacoes: str | Path | None = None,
    caminho_cache: str | Path | None = None,
    seed: int = 42,
    usar_splits_existentes: bool = True,
) -> DadosML:
    """Carrega e prepara os dados de forma reproduzível para ML.

    Parâmetros:
    - texto: 'original' (texto_curto com limpeza) ou 'padronizado' (via cache/LLM).
    - versao_prompt: versão do prompt utilizada no cache de padronização.
    - caminho_dataset: caminho para o dataset.jsonl (opcional).
    - caminho_anotacoes: diretório de anotações da equipe (opcional).
    - caminho_cache: diretório de cache de padronização (opcional).
    - seed: semente para reprodutibilidade.
    - usar_splits_existentes: se True, utiliza split_produto já calculado no dataset.
    """
    if texto not in ("original", "padronizado"):
        raise ValueError(f"Opção de texto inválida: '{texto}'. Escolha 'original' ou 'padronizado'.")

    caminho_dados = resolver_caminho_dataset(caminho_dataset)
    dir_anotacoes = resolver_caminho_anotacoes(caminho_anotacoes)
    dir_cache = resolver_caminho_cache(caminho_cache)

    anotacoes = carregar_anotacoes(dir_anotacoes)

    treino: list[RegistroML] = []
    validacao: list[RegistroML] = []
    teste: list[RegistroML] = []
    reserva: list[RegistroML] = []

    descartados_sem_texto = 0
    descartados_portal = 0
    total_lidos = 0

    with open(caminho_dados, encoding="utf-8") as f:
        for num_linha, linha in enumerate(f, start=1):
            linha = linha.strip()
            if not linha:
                continue

            total_lidos += 1
            registro = json.loads(linha)
            reg_id = str(registro.get("id", f"linha-{num_linha}"))

            # 1. Cruzamento com anotações por id
            anot = anotacoes.get(reg_id)
            if anot:
                # Anotação humana tem precedência em veracidade e campos anotados
                if "veracidade" in anot and anot["veracidade"] in CLASSES_VERACIDADE:
                    registro["veracidade"] = anot["veracidade"]
                if "tipo" in anot:
                    registro["tipo_anotado"] = anot["tipo"]
                registro["anotacao"] = anot

            # 2. Descarte de registros sem texto_curto
            texto_curto = registro.get("texto_curto")
            if not texto_curto or not str(texto_curto).strip():
                descartados_sem_texto += 1
                continue

            # 3. Preparação do texto (original limpo vs padronizado)
            if texto == "padronizado":
                texto_padrao = obter_texto_padronizado(registro, versao_prompt, dir_cache)
                texto_final = texto_padrao if texto_padrao else limpar_texto(texto_curto)
            else:
                texto_final = limpar_texto(texto_curto)

            if not texto_final:
                descartados_sem_texto += 1
                continue

            # 4. Veracidade, y1 e y2
            veracidade = str(registro.get("veracidade", "")).strip().lower()
            if veracidade not in CLASSES_VERACIDADE:
                # Ignora registros fora do escopo ou com veredito ambíguo
                continue

            y1 = MAPA_Y1[veracidade]
            y2 = MAPA_Y2[veracidade]

            # 5. Origem e pesos
            origem = str(
                registro.get("origem_rotulo")
                or registro.get("origem")
                or "agencia"
            ).strip().lower()

            # REGRA CRÍTICA: Registros de 'portal' NÃO devem entrar nos splits de ML
            if origem == "portal":
                descartados_portal += 1
                continue

            peso = PESOS_ORIGEM.get(origem, PESO_PADRAO)

            # 6. Metadados de auditoria (não são features de entrada do modelo)
            metadados = {
                "base": registro.get("base"),
                "fonte": registro.get("fonte"),
                "autor": registro.get("autor"),
                "data": registro.get("data"),
                "categoria": registro.get("categoria"),
                "url": registro.get("url"),
                "par_id": registro.get("par_id"),
                "veredito_original": registro.get("veredito_original"),
                "tipo_sugerido": registro.get("tipo_sugerido"),
                "anotacao": registro.get("anotacao"),
                "split_original": registro.get("split_produto") or registro.get("split"),
            }

            item = RegistroML(
                id=reg_id,
                texto=texto_final,
                veracidade=veracidade,
                y1=y1,
                y2=y2,
                origem=origem,
                peso=peso,
                metadados=metadados,
            )

            # 7. Distribuição dos splits
            split_alvo = str(
                registro.get("split_produto")
                or registro.get("split")
                or ""
            ).lower()

            # Reserva não entra nos splits de treino, validação ou teste
            if split_alvo == "reserva" or registro.get("reserva") is True:
                reserva.append(item)
                continue

            if usar_splits_existentes and split_alvo in ("treino", "validacao", "teste"):
                if split_alvo == "treino":
                    treino.append(item)
                elif split_alvo == "validacao":
                    validacao.append(item)
                elif split_alvo == "teste":
                    teste.append(item)
            elif split_alvo == "fora":
                # Fora do escopo do experimento de produto
                continue
            else:
                # Sorteio determinístico usando a seed fixa caso não haja split pré-definido
                hash_sorteio = int(
                    hashlib.sha256(f"{seed}-{reg_id}".encode()).hexdigest()[:8], 16
                ) / 0xFFFFFFFF
                if hash_sorteio < 0.80:
                    treino.append(item)
                elif hash_sorteio < 0.90:
                    validacao.append(item)
                else:
                    teste.append(item)

    # 8. Cálculo do dataset_hash
    d_hash = calcular_dataset_hash(treino, validacao, teste)

    metadados_gerais = {
        "texto_tipo": texto,
        "versao_prompt": versao_prompt if texto == "padronizado" else None,
        "seed": seed,
        "total_lidos": total_lidos,
        "descartados_sem_texto": descartados_sem_texto,
        "descartados_portal": descartados_portal,
        "dataset_hash": d_hash,
    }

    return DadosML(
        treino=treino,
        validacao=validacao,
        teste=teste,
        dataset_hash=d_hash,
        reserva=reserva,
        metadados=metadados_gerais,
    )


if __name__ == "__main__":
    import sys

    print("=== Pipeline de Dados ML - FAKO ===")
    try:
        dados = carregar(texto="original")
        resumo = dados.resumo()
        print(f"Dataset carregado com sucesso:")
        print(f"  Hash do experimento: {dados.dataset_hash}")
        print(f"  Treino:    {len(dados.treino)} registros {resumo['classes_treino']}")
        print(f"  Validação: {len(dados.validacao)} registros {resumo['classes_validacao']}")
        print(f"  Teste:     {len(dados.teste)} registros {resumo['classes_teste']}")
        print(f"  Reserva:   {len(dados.reserva)} registros")
        print(f"  Descartados sem texto_curto: {dados.metadados.get('descartados_sem_texto')}")
        print(f"  Descartados de portal:       {dados.metadados.get('descartados_portal')}")
    except FileNotFoundError as e:
        print(f"[AVISO] {e}")
        print("\nPara gerar a base real, execute:")
        print("  make dados")
        print("ou:")
        print("  bash scripts/baixar_dados.sh && python scripts/preparar_dados.py")
        print("\nPara rodar a suíte de testes unitários do pipeline:")
        print("  python3 -m unittest ml/test_dados.py")
