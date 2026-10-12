"""Dados de treino comuns a todos os experimentos de ML (issue #7).

Uso:
    from dados import carregar
    conjunto = carregar()                       # texto_curto original, limpo
    conjunto = carregar(texto="padronizado", prompt=Path(...), modelo="qwen...")  # #20
    conjunto.splits["treino"]                   # lista de Exemplo

    python pesquisa/ml/dados.py                 # contagens por split e classe

O teste de atalho (#8), a referência (#9) e o BERTimbau (#10) leem os dados só por aqui:
mesmos registros, mesma limpeza e mesmos pesos, para a comparação entre eles valer.

Regras:
- Lê pesquisa/data/processed/dataset.jsonl. Entram os splits do protocolo B (`treino`,
  `validacao`, `teste`); `reserva` e `fora` ficam de fora.
- **Sem `origem_rotulo=portal`**: as matérias de portais são verdadeiras por suposição e não
  entram no dataset selecionado (#6, #37). `incluir_portal=True` existe só para diagnóstico.
- Texto `original`: o `texto_curto`; registros sem ele ficam de fora. Texto `padronizado`:
  a primeira afirmação extraída pela LLM, do cache de padronizar.py (#20), com o mesmo
  prompt e o mesmo modelo do uso; registros sem afirmação (opinião) ficam de fora.
- Limpeza: tira URLs, créditos e nomes de veículo nas pontas do texto ("| G1",
  "(Estadão Conteúdo)", "Com informações da Folha"). Mantém maiúsculas e pontuação.
- Anotações da equipe (#5), quando existirem, entram pelo `id` a partir de
  pesquisa/anotacoes/consolidado.csv: o `tipo` vem dali, a `veracidade` anotada substitui a
  original e a origem vira `equipe`.
- Alvos ordinais: `y1` = veracidade > falso e `y2` = veracidade > enganoso.
- `checado`: há veredito de agência (`veredito_original`), para a fatia "só checados".
- Peso por `origem_rotulo`, de ORIGEM_ROTULO_PESO em preparar_dados.py.
- Fonte, autor, data e categoria nunca viram variáveis do modelo: servem só para split,
  métricas e pesos.
"""

import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from padronizar import aplicar, caminho_cache, carregar_prompt, ler_cache

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "processed" / "dataset.jsonl"
ANOTACOES = RAIZ / "anotacoes" / "consolidado.csv"

SPLITS = ("treino", "validacao", "teste")
CLASSES = ("falso", "enganoso", "verdadeiro")
ORDEM = {c: i for i, c in enumerate(CLASSES)}


def _preparar_dados():
    """preparar_dados.py fica em pesquisa/dados/, fora do caminho de importação daqui."""
    caminho = RAIZ / "dados" / "preparar_dados.py"
    spec = importlib.util.spec_from_file_location("preparar_dados", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


ORIGEM_ROTULO_PESO = {
    origem: peso
    for origem, peso in _preparar_dados().ORIGEM_ROTULO_PESO.items()
    if origem != "portal"
}

VEICULOS = (
    "G1",
    "g1",
    "UOL",
    "Folha",
    "Folha de S.Paulo",
    "Folha de São Paulo",
    "Estadão",
    "Estadão Conteúdo",
    "O Estado de S. Paulo",
    "O Globo",
    "Extra",
    "Veja",
    "Poder360",
    "CNN Brasil",
    "Agência Brasil",
    "Reuters",
    "AFP",
    "BBC",
    "BBC News Brasil",
    "Metrópoles",
    "R7",
    "Terra",
    "Jovem Pan",
    "InfoMoney",
    "Brasil de Fato",
    "Revista Oeste",
    "O Antagonista",
    "Agência Pública",
    "Jornal da USP",
    "Valor",
    "Valor Econômico",
)
# No começo do texto, só nomes que não são palavras comuns ("Veja: vídeo mostra..." é conteúdo).
AMBIGUOS_NO_INICIO = {"Veja", "Extra", "Terra", "Valor"}


def _alternativas(nomes) -> str:
    return "|".join(sorted((re.escape(n) for n in nomes), key=len, reverse=True))


_NOMES = _alternativas(VEICULOS)
_NOMES_INICIO = _alternativas(v for v in VEICULOS if v not in AMBIGUOS_NO_INICIO)
URL = re.compile(r"https?://\S+|www\.\S+")
# Créditos no fim: "| G1", "- Folha", "— Estadão Conteúdo", "(Reuters)",
# "Com informações da Agência Brasil".
CREDITO_FINAL = re.compile(
    rf"(?:\s*[|\-–—]\s*(?:{_NOMES})|\s*\((?:{_NOMES})\)|\s*Com informações d[aoe]s?\s+(?:{_NOMES}))\.?\s*$"
)
# Créditos no começo: "G1:", "(Reuters) -", "Folha -".
CREDITO_INICIAL = re.compile(rf"^\s*(?:\((?:{_NOMES})\)|(?:{_NOMES_INICIO}))\s*[:|\-–—]\s+")


def limpar(texto: str) -> str:
    """Tira URLs e créditos de veículo nas pontas; mantém caixa e pontuação."""
    texto = URL.sub(" ", texto)
    anterior = None
    while anterior != texto:
        anterior = texto
        texto = CREDITO_FINAL.sub("", texto)
        texto = CREDITO_INICIAL.sub("", texto)
    return re.sub(r"\s+", " ", texto).strip()


def alvos(veracidade: str) -> tuple[int, int]:
    """Alvos ordinais: (veracidade > falso, veracidade > enganoso)."""
    ordem = ORDEM[veracidade]
    return int(ordem > 0), int(ordem > 1)


@dataclass
class Exemplo:
    id: str
    texto: str
    veracidade: str
    y1: int
    y2: int
    tipo: str | None
    tipo_sugerido: str | None
    ano: int | None
    fonte: str | None
    base: str
    origem_rotulo: str
    peso: float
    checado: bool


@dataclass
class Conjunto:
    texto: str
    dataset_sha256: str
    splits: dict[str, list[Exemplo]] = field(default_factory=dict)
    prompt: dict | None = None

    def contagens(self) -> dict[str, dict[str, int]]:
        return {
            split: {c: n for c, n in Counter(e.veracidade for e in exemplos).items()}
            for split, exemplos in self.splits.items()
        }


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_anotacoes(caminho: Path = ANOTACOES) -> dict[str, dict]:
    """Rótulo final da equipe por id (saída da consolidação da #5), se existir."""
    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return {linha["id"]: linha for linha in csv.DictReader(arquivo)}


def exemplo(registro: dict, texto: str, anotacao: dict | None) -> Exemplo | None:
    veracidade, origem, tipo = registro["veracidade"], registro["origem_rotulo"], None
    if anotacao:
        tipo = anotacao.get("tipo") or None
        veracidade = anotacao.get("veracidade") or veracidade
        origem = "equipe"
    if veracidade not in ORDEM:
        return None
    y1, y2 = alvos(veracidade)
    data = registro.get("data") or ""
    return Exemplo(
        id=registro["id"],
        texto=texto,
        veracidade=veracidade,
        y1=y1,
        y2=y2,
        tipo=tipo,
        tipo_sugerido=registro.get("tipo_sugerido"),
        ano=int(data[:4]) if data[:4].isdigit() else None,
        fonte=registro.get("fonte"),
        base=registro["base"],
        origem_rotulo=origem,
        peso=ORIGEM_ROTULO_PESO.get(origem, 1.0),
        checado=registro["origem_rotulo"] == "agencia" and bool(registro.get("veredito_original")),
    )


def carregar(
    texto: str = "original",
    dataset: Path = DATASET,
    prompt: Path | None = None,
    modelo: str | None = None,
    anotacoes: Path = ANOTACOES,
    incluir_portal: bool = False,
) -> Conjunto:
    """Treino, validação e teste, já limpos e com alvos e pesos."""
    if texto not in ("original", "padronizado"):
        raise ValueError(f"texto deve ser 'original' ou 'padronizado', não {texto!r}")
    conjunto = Conjunto(texto=texto, dataset_sha256=sha256(dataset))
    conjunto.splits = {s: [] for s in SPLITS}

    registros = []
    with open(dataset, encoding="utf-8") as entrada:
        for linha in entrada:
            r = json.loads(linha)
            if r["split_produto"] in SPLITS and (incluir_portal or r["origem_rotulo"] != "portal"):
                registros.append(r)

    campo = "texto_curto"
    if texto == "padronizado":
        if prompt is None or not modelo:
            raise ValueError("texto='padronizado' exige o prompt e o modelo da padronização")
        p = carregar_prompt(prompt)
        cache = ler_cache(caminho_cache(p.versao, dataset.parent), p, modelo)
        registros = list(aplicar(registros, cache))
        conjunto.prompt = {"versao": p.versao, "sha1": p.sha1, "modelo": modelo}
        campo = "texto_padronizado"

    rotulos = ler_anotacoes(anotacoes)
    for r in registros:
        bruto = (r.get(campo) or "").strip()
        limpo = limpar(bruto) if bruto else ""
        if not limpo:
            continue
        e = exemplo(r, limpo, rotulos.get(r["id"]))
        if e:
            conjunto.splits[r["split_produto"]].append(e)
    return conjunto


def main():
    if not DATASET.exists():
        sys.exit(f"{DATASET} não encontrado. Rode antes: make dados")
    conjunto = carregar()
    print(f"dataset.jsonl sha256 {conjunto.dataset_sha256[:16]}...  texto {conjunto.texto}")
    print(f"  {'split':10} " + " ".join(f"{c:>10}" for c in CLASSES) + "      total  checados")
    for split, exemplos in conjunto.splits.items():
        n = Counter(e.veracidade for e in exemplos)
        checados = sum(e.checado for e in exemplos)
        print(
            f"  {split:10} "
            + " ".join(f"{n[c]:10}" for c in CLASSES)
            + f" {len(exemplos):10} {checados:9}"
        )


if __name__ == "__main__":
    main()
