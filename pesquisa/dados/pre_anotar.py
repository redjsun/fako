"""Pré-anotação pela LLM: sugere o tipo e os 4 sinais nas planilhas de uma rodada (#21, uso 3).

Uso:
    python pesquisa/dados/pre_anotar.py sugerir --rodada 2
    python pesquisa/dados/pre_anotar.py comparar --rodada 2

Só biblioteca padrão. A LLM é a mesma da padronização (LLM_BASE_URL, LLM_MODEL, LLM_API_KEY,
LLM_EXTRA_BODY), com o prompt api/app/prompts/pre_anotar_v1.txt.

- `sugerir`: lê as planilhas de trabalho pesquisa/data/anotacao/rodada-NN-<anotador>.csv
  (sortear_anotacao.py), pede a sugestão de cada id (cache em rodada-NN-llm.csv, fora do Git:
  rodar de novo só pede os ids que faltam) e acrescenta às planilhas as colunas `sugestao_tipo`
  e `sugestao_sinais`. Nos itens anotados por mais de uma pessoa (concordância) a sugestão
  fica **escondida**, para medir a LLM contra os humanos sem que ela influencie a anotação.
  O `consolidar_anotacoes.py importar` ignora as colunas de sugestão.
- `comparar`: depois de importada a rodada, mede nos itens de concordância o kappa da LLM com
  cada humano e o dos humanos entre si, por campo. Se o da LLM for menor, a sugestão daquele
  campo sai das próximas planilhas.
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from consolidar_anotacoes import SINAIS, TIPOS, kappa_cohen

RAIZ = Path(__file__).resolve().parent.parent
PLANILHAS = RAIZ / "data" / "anotacao"
ANOTACOES = RAIZ / "anotacoes"
PROMPT = RAIZ.parent / "api" / "app" / "prompts" / "pre_anotar_v1.txt"

CAMPOS = ("tipo", *SINAIS)
COLUNAS_SUGESTAO = ("sugestao_tipo", "sugestao_sinais")
ESQUEMA = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": sorted(TIPOS)},
        **{sinal: {"type": "integer", "enum": [0, 1]} for sinal in SINAIS},
    },
    "required": list(CAMPOS),
    "additionalProperties": False,
}
TENTATIVAS = 2


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig", newline="") as entrada:
        return list(csv.DictReader(entrada))


def gravar_csv(caminho: Path, colunas, linhas, bom: bool = False):
    with open(caminho, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def interpretar(resposta: str) -> dict:
    """{"tipo", 4 sinais} validado; ValueError se fora do esquema."""
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", resposta.strip())
    inicio = texto.find("{")
    if inicio < 0:
        raise ValueError(f"sem JSON: {resposta[:200]!r}")
    valor, _ = json.JSONDecoder().raw_decode(texto, inicio)
    if not isinstance(valor, dict) or valor.get("tipo") not in TIPOS:
        raise ValueError(f"tipo inválido: {resposta[:200]!r}")
    sugestao = {"tipo": valor["tipo"]}
    for sinal in SINAIS:
        if valor.get(sinal) not in (0, 1, "0", "1", True, False):
            raise ValueError(f"{sinal} inválido: {resposta[:200]!r}")
        sugestao[sinal] = str(int(valor[sinal]))
    return sugestao


def sugeridor_llm(base_url: str, modelo: str, chave: str | None, extra: dict, prompt: str):
    url = base_url.rstrip("/") + "/chat/completions"
    cabecalhos = {"Content-Type": "application/json"}
    if chave:
        cabecalhos["Authorization"] = f"Bearer {chave}"

    def sugerir(texto: str, veredito: str) -> dict:
        conteudo = prompt.replace("{texto}", texto).replace("{veredito}", veredito or "sem")
        corpo = {
            "model": modelo,
            "messages": [{"role": "user", "content": conteudo}],
            "temperature": 0.2,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "pre_anotacao", "schema": ESQUEMA},
            },
            **extra,
        }
        erros = []
        for _ in range(TENTATIVAS):
            requisicao = urllib.request.Request(url, json.dumps(corpo).encode(), cabecalhos)
            with urllib.request.urlopen(requisicao, timeout=120) as resposta:
                dados = json.load(resposta)
            try:
                return interpretar(dados["choices"][0]["message"]["content"])
            except ValueError as erro:
                erros.append(str(erro))
        raise ValueError("; ".join(erros))

    return sugerir


def planilhas_da_rodada(rodada: int) -> dict[str, Path]:
    """{anotador: planilha}, sem o cache da LLM."""
    prefixo = f"rodada-{rodada:02d}-"
    return {
        caminho.stem.removeprefix(prefixo): caminho
        for caminho in sorted(PLANILHAS.glob(f"{prefixo}*.csv"))
        if caminho.stem != f"{prefixo}llm"
    }


def ids_comuns(planilhas: dict[str, list[dict]]) -> set[str]:
    contagem = Counter(linha["id"] for linhas in planilhas.values() for linha in linhas)
    return {id_ for id_, vezes in contagem.items() if vezes > 1}


def sugerir_rodada(rodada: int, sugerir) -> tuple[int, int, int]:
    """Preenche as sugestões; devolve (pedidas à LLM, falhas, escondidas por planilha)."""
    caminhos = planilhas_da_rodada(rodada)
    if not caminhos:
        sys.exit(f"Nenhuma planilha da rodada {rodada} em {PLANILHAS}; rode sortear_anotacao.py")
    planilhas = {anotador: ler_csv(caminho) for anotador, caminho in caminhos.items()}
    cache_caminho = PLANILHAS / f"rodada-{rodada:02d}-llm.csv"
    cache = (
        {linha["id"]: linha for linha in ler_csv(cache_caminho)} if cache_caminho.exists() else {}
    )

    pedidas = falhas = 0
    for linhas in planilhas.values():
        for linha in linhas:
            if linha["id"] in cache:
                continue
            try:
                cache[linha["id"]] = {
                    "id": linha["id"],
                    **sugerir(linha["texto_curto"], linha["veredito_original"]),
                }
            except (OSError, ValueError, KeyError, IndexError) as erro:  # rede, timeout, esquema
                print(f"{linha['id']}: {erro}", file=sys.stderr)
                falhas += 1
                continue
            pedidas += 1
            gravar_csv(cache_caminho, ("id", *CAMPOS), cache.values())

    comuns = ids_comuns(planilhas)
    for anotador, linhas in planilhas.items():
        for linha in linhas:
            sugestao = cache.get(linha["id"]) if linha["id"] not in comuns else None
            linha["sugestao_tipo"] = sugestao["tipo"] if sugestao else ""
            linha["sugestao_sinais"] = (
                " ".join(s for s in SINAIS if sugestao[s] == "1") if sugestao else ""
            )
        colunas = [c for c in linhas[0] if c not in COLUNAS_SUGESTAO] + list(COLUNAS_SUGESTAO)
        gravar_csv(caminhos[anotador], colunas, linhas, bom=True)
    return pedidas, falhas, len(comuns)


def media(valores: list[float | None]) -> float | None:
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else None


def comparar(humanas: list[dict], llm: dict[str, dict]) -> dict[str, dict]:
    """Por campo, nos itens com mais de um humano: kappa médio humano × humano e LLM × humano."""
    por_item = defaultdict(dict)
    for linha in humanas:
        por_item[linha["id"]][linha["anotador"]] = linha
    comuns = {id_: anotadores for id_, anotadores in por_item.items() if len(anotadores) > 1}
    anotadores = sorted({a for por_anotador in comuns.values() for a in por_anotador})
    resultado = {}
    for campo in CAMPOS:
        entre_humanos = [
            kappa_cohen([
                (itens[a][campo], itens[b][campo])
                for itens in comuns.values() if a in itens and b in itens
            ])
            for a, b in combinations(anotadores, 2)
        ]  # fmt: skip
        com_llm = [
            kappa_cohen([
                (llm[id_][campo], itens[a][campo])
                for id_, itens in comuns.items() if a in itens and id_ in llm
            ])
            for a in anotadores
        ]  # fmt: skip
        humanos, maquina = media(entre_humanos), media(com_llm)
        resultado[campo] = {
            "humanos": humanos,
            "llm": maquina,
            "manter": None if humanos is None or maquina is None else maquina >= humanos,
        }
    return resultado


def formatar(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.2f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("acao", choices=("sugerir", "comparar"))
    parser.add_argument("--rodada", type=int, required=True)
    args = parser.parse_args()

    if args.acao == "sugerir":
        base_url, modelo = os.environ.get("LLM_BASE_URL"), os.environ.get("LLM_MODEL")
        if not base_url or not modelo:
            sys.exit("Defina LLM_BASE_URL e LLM_MODEL no .env.")
        extra = json.loads(os.environ.get("LLM_EXTRA_BODY") or "{}")
        sugerir = sugeridor_llm(
            base_url, modelo, os.environ.get("LLM_API_KEY"), extra, PROMPT.read_text("utf-8")
        )
        pedidas, falhas, escondidas = sugerir_rodada(args.rodada, sugerir)
        print(
            f"{pedidas} sugestões novas, {falhas} falhas, "
            f"{escondidas} itens de concordância sem sugestão"
        )
        return

    humanas = ANOTACOES / f"rodada-{args.rodada:02d}.csv"
    cache = PLANILHAS / f"rodada-{args.rodada:02d}-llm.csv"
    if not humanas.exists() or not cache.exists():
        sys.exit(
            f"Faltam {humanas.relative_to(RAIZ)} (importar) ou {cache.relative_to(RAIZ)} (sugerir)"
        )
    resultado = comparar(ler_csv(humanas), {linha["id"]: linha for linha in ler_csv(cache)})
    print(f"{'campo':<24}{'humanos':>9}{'LLM':>9}  sugestão")
    for campo, valores in resultado.items():
        decisao = {True: "manter", False: "tirar", None: "sem dados"}[valores["manter"]]
        print(
            f"{campo:<24}{formatar(valores['humanos']):>9}{formatar(valores['llm']):>9}  {decisao}"
        )


if __name__ == "__main__":
    main()
