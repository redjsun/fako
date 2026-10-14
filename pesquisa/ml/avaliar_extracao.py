"""Avaliação da extração de afirmações em textos brasileiros (issue #19).

Uso:
    python pesquisa/ml/avaliar_extracao.py rodar --prompt api/app/ml/prompts/extrair_afirmacoes_v1.txt
    python pesquisa/ml/avaliar_extracao.py medir --prompt api/app/ml/prompts/extrair_afirmacoes_v1.txt

Mede o mesmo prompt da API e da padronização, com o extrator de padronizar.py.

Arquivos:
- `pesquisa/anotacoes/extracao-br.csv` (versionado): `id`, `e_opiniao` (0/1) e `quem_disse`
  (o autor a quem o texto atribui a afirmação principal, ou vazio), rotulados pela equipe.
  Pode ter a coluna `texto` quando o texto é da equipe; texto de terceiros nunca vai para o Git.
- `pesquisa/data/avaliacao/extracao-textos.csv` (fora do Git): `id` e `texto` dos textos de
  terceiros.
- `rodar` grava a saída da LLM em `pesquisa/data/avaliacao/extracao-<versao>.jsonl` (rodar de
  novo só pede os ids que faltam) e a planilha `extracao-<versao>-revisao.csv`, uma linha por
  afirmação, com a coluna `checavel` (0/1) para a equipe preencher.
- `medir` imprime: acerto de "é opinião?"; "quem disse" preservado nos textos que atribuem a
  afirmação a alguém (e lista os que viraram afirmação sem autor, o erro mais grave); e a
  proporção de afirmações checáveis na planilha revisada.
"""

import argparse
import csv
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

from padronizar import Extracao, carregar_prompt, extrator_fake, extrator_openai

RAIZ = Path(__file__).resolve().parent.parent
ROTULOS = RAIZ / "anotacoes" / "extracao-br.csv"
AVALIACAO = RAIZ / "data" / "avaliacao"
TEXTOS = AVALIACAO / "extracao-textos.csv"
COLUNAS_REVISAO = ("id", "n", "afirmacao", "quem_disse", "checavel", "observacao")


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig", newline="") as entrada:
        return list(csv.DictReader(entrada))


def carregar_itens(rotulos: Path = ROTULOS, textos: Path = TEXTOS) -> list[dict]:
    """Rótulos com o texto: o da própria linha ou o do arquivo local de textos."""
    locais = {}
    if textos.exists():
        locais = {linha["id"]: linha["texto"] for linha in ler_csv(textos)}
    itens = []
    for linha in ler_csv(rotulos):
        texto = (linha.get("texto") or "").strip() or locais.get(linha["id"], "").strip()
        if not texto:
            sys.exit(f"Sem texto para {linha['id']}: inclua em {textos.relative_to(RAIZ)}")
        itens.append(
            {
                "id": linha["id"],
                "texto": texto,
                "e_opiniao": linha["e_opiniao"].strip() == "1",
                "quem_disse": (linha.get("quem_disse") or "").strip() or None,
            }
        )
    return itens


def caminho_saida(versao: str, pasta: Path = AVALIACAO) -> Path:
    return pasta / f"extracao-{versao}.jsonl"


def ler_saidas(caminho: Path) -> dict[str, list[dict]]:
    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8") as entrada:
        linhas = (json.loads(linha) for linha in entrada if linha.strip())
        return {linha["id"]: linha["afirmacoes"] for linha in linhas}


def rodar(itens: list[dict], extrair: Callable[[str], Extracao], saida: Path) -> int:
    """Extrai os itens que faltam na saída; devolve quantos foram pedidos à LLM."""
    feitos = ler_saidas(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    pedidos = 0
    with open(saida, "a", encoding="utf-8") as destino:
        for item in itens:
            if item["id"] in feitos:
                continue
            extracao = extrair(item["texto"])
            linha = {"id": item["id"], "afirmacoes": extracao.afirmacoes}
            destino.write(json.dumps(linha, ensure_ascii=False) + "\n")
            feitos[item["id"]] = extracao.afirmacoes
            pedidos += 1
    # A planilha de revisão só ganha as linhas dos ids novos: o que a equipe preencheu fica.
    revisao = saida.with_name(f"{saida.stem}-revisao.csv")
    linhas = ler_csv(revisao) if revisao.exists() else []
    revisados = {linha["id"] for linha in linhas}
    for item in itens:
        if item["id"] in revisados:
            continue
        for n, afirmacao in enumerate(feitos[item["id"]], 1):
            linhas.append(
                {
                    "id": item["id"],
                    "n": n,
                    "afirmacao": afirmacao["texto"],
                    "quem_disse": afirmacao["quem_disse"] or "",
                    "checavel": "",
                    "observacao": "",
                }
            )
    with open(revisao, "w", encoding="utf-8-sig", newline="") as destino:
        escritor = csv.DictWriter(destino, fieldnames=COLUNAS_REVISAO)
        escritor.writeheader()
        escritor.writerows(linhas)
    return pedidos


def medir(itens: list[dict], saidas: dict[str, list[dict]], revisao: list[dict]) -> dict:
    avaliados = [item for item in itens if item["id"] in saidas]
    acertos_opiniao = sum(item["e_opiniao"] == (not saidas[item["id"]]) for item in avaliados)
    atribuidos = [item for item in avaliados if item["quem_disse"] and saidas[item["id"]]]
    sem_autor = [
        item["id"]
        for item in atribuidos
        if not any(afirmacao["quem_disse"] for afirmacao in saidas[item["id"]])
    ]
    marcadas = [linha for linha in revisao if linha["checavel"].strip() in ("0", "1")]
    checaveis = sum(linha["checavel"].strip() == "1" for linha in marcadas)
    return {
        "itens": len(avaliados),
        "acerto_opiniao": acertos_opiniao / len(avaliados) if avaliados else None,
        "atribuidos": len(atribuidos),
        "quem_disse_preservado": (1 - len(sem_autor) / len(atribuidos) if atribuidos else None),
        "sem_autor": sem_autor,
        "afirmacoes_revisadas": len(marcadas),
        "checaveis": checaveis / len(marcadas) if marcadas else None,
    }


def porcentagem(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.0%}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("acao", choices=("rodar", "medir"))
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--provedor", choices=("openai", "fake"), default="openai")
    args = parser.parse_args()
    if not ROTULOS.exists():
        sys.exit(f"{ROTULOS.relative_to(RAIZ)} não encontrado: rotule os textos antes")
    prompt = carregar_prompt(args.prompt)
    itens = carregar_itens()
    saida = caminho_saida(prompt.versao)

    if args.acao == "rodar":
        if args.provedor == "fake":
            extrair = extrator_fake
        else:
            base_url, modelo = os.environ.get("LLM_BASE_URL"), os.environ.get("LLM_MODEL")
            if not base_url or not modelo:
                sys.exit("Defina LLM_BASE_URL e LLM_MODEL no .env (ou use --provedor fake).")
            extra = json.loads(os.environ.get("LLM_EXTRA_BODY") or "{}")
            chave = os.environ.get("LLM_API_KEY")
            extrair = extrator_openai(prompt, base_url, modelo, chave, extra=extra)
        print(f"{rodar(itens, extrair, saida)} textos extraídos; saída em {saida}")
        return

    revisao = saida.with_name(f"{saida.stem}-revisao.csv")
    resultado = medir(itens, ler_saidas(saida), ler_csv(revisao) if revisao.exists() else [])
    print(f"prompt {prompt.versao}, {resultado['itens']} textos")
    print(f"acerto de 'é opinião?': {porcentagem(resultado['acerto_opiniao'])}")
    print(
        f"quem disse preservado: {porcentagem(resultado['quem_disse_preservado'])} "
        f"de {resultado['atribuidos']} textos com autor"
    )
    if resultado["sem_autor"]:
        print("viraram afirmação sem autor:", ", ".join(resultado["sem_autor"]))
    print(
        f"afirmações checáveis: {porcentagem(resultado['checaveis'])} "
        f"de {resultado['afirmacoes_revisadas']} revisadas"
    )


if __name__ == "__main__":
    main()
