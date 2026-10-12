"""Auditoria manual do dataset de verdadeiros confiáveis (#6, doc/dataset-verdadeiras.md).

Uso:
    python pesquisa/dados/auditar_verdadeiras.py sortear --itens 200 --revisores ana bruno
    python pesquisa/dados/auditar_verdadeiras.py importar pesquisa/data/auditoria/auditoria-*.csv
    python pesquisa/dados/auditar_verdadeiras.py medir

Só biblioteca padrão.
- `sortear`: das matérias de portal do `dataset.jsonl` que passam nos filtros
  (`motivo_filtro_portal` em preparar_dados.py), fora do teste, sorteia `--itens`
  estratificados por veículo (hash do id com prefixo próprio, reproduzível). Cada revisor
  recebe todos os itens numa planilha em pesquisa/data/auditoria/ (fora do Git, com título e
  URL para conferir).
- `importar`: confere as planilhas preenchidas, tira o texto e grava
  pesquisa/anotacoes/auditoria-verdadeiras.csv (`id`, `fonte`, `revisor`, `problema`,
  `observacao`).
- `medir`: ruído (proporção de itens com problema, com intervalo de confiança de Wilson de
  95%) no total e por veículo, e kappa de Cohen entre os revisores. Um item tem problema se
  algum revisor marcou (critério conservador). Veículo com ruído acima de 2 x LIMITE_RUIDO
  sai; se o ruído dos que ficam é no máximo LIMITE_RUIDO, eles são gravados como aceitos em
  pesquisa/anotacoes/veiculos-verificados.csv, que o preparar_dados.py lê para marcar
  `origem_rotulo=portal_verificado`.
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from itertools import combinations, zip_longest
from pathlib import Path

from consolidar_anotacoes import formatar, kappa_cohen
from preparar_dados import definir_split_produto, motivo_filtro_portal

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "processed" / "dataset.jsonl"
PLANILHAS = RAIZ / "data" / "auditoria"
AUDITORIA = RAIZ / "anotacoes" / "auditoria-verdadeiras.csv"
VEICULOS = RAIZ / "anotacoes" / "veiculos-verificados.csv"

PROBLEMAS = {"nenhum", "erro_factual", "exagero", "relata_fala_falsa", "opiniao"}
LIMITE_RUIDO = 0.05
COLUNAS_PLANILHA = (
    "id",
    "fonte",
    "data",
    "url",
    "texto_curto",
    "problema",
    "revisor",
    "observacao",
)
COLUNAS_AUDITORIA = ("id", "fonte", "revisor", "problema", "observacao")
COLUNAS_VEICULOS = (
    "fonte",
    "itens",
    "com_problema",
    "ruido",
    "ic_inferior",
    "ic_superior",
    "aceito",
)


class ErroAuditoria(ValueError):
    pass


def ordem(chave: str) -> str:
    return hashlib.sha1(f"auditoria-{chave}".encode()).hexdigest()


def candidatos(registros) -> list[dict]:
    """Matérias de portal que passam nos filtros, fora do teste e dos registros `fora`."""
    return [
        r
        for r in registros
        if r["base"] == "verdadeiras"
        and r["split_produto"] != "fora"
        and definir_split_produto(r) in ("treino", "validacao")
        and motivo_filtro_portal(r) is None
    ]


def sortear(registros: list[dict], itens: int) -> list[dict]:
    """Um item de cada veículo por vez, na ordem do hash do id."""
    por_fonte = defaultdict(list)
    for r in sorted(registros, key=lambda r: ordem(r["id"])):
        por_fonte[r["fonte"]].append(r)
    grupos = [por_fonte[fonte] for fonte in sorted(por_fonte, key=ordem)]
    return [r for rodada in zip_longest(*grupos) for r in rodada if r is not None][:itens]


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig", newline="") as entrada:
        return list(csv.DictReader(entrada))


def gravar_csv(caminho: Path, colunas, linhas, codificacao: str = "utf-8"):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding=codificacao, newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def normalizar(linha: dict) -> dict | None:
    """Só id, fonte, revisor, problema e observação; None se o item não foi revisado."""
    problema = (linha.get("problema") or "").strip().lower()
    if not problema:
        return None
    if problema not in PROBLEMAS:
        raise ErroAuditoria(f"{linha.get('id')}: problema desconhecido {problema!r}")
    revisor = (linha.get("revisor") or "").strip()
    if not revisor:
        raise ErroAuditoria(f"{linha.get('id')}: sem revisor")
    return {
        "id": linha["id"].strip(),
        "fonte": linha["fonte"].strip(),
        "revisor": revisor,
        "problema": problema,
        "observacao": (linha.get("observacao") or "").strip(),
    }


def importar(planilhas: list[Path], destino: Path = AUDITORIA) -> tuple[int, int]:
    linhas = {(r["id"], r["revisor"]): r for r in ler_csv(destino)} if destino.exists() else {}
    novas = vazias = 0
    for planilha in planilhas:
        for bruta in ler_csv(planilha):
            linha = normalizar(bruta)
            if linha is None:
                vazias += 1
                continue
            linhas[(linha["id"], linha["revisor"])] = linha
            novas += 1
    ordenadas = sorted(linhas.values(), key=lambda r: (r["id"], r["revisor"]))
    gravar_csv(destino, COLUNAS_AUDITORIA, ordenadas)
    return novas, vazias


def wilson(sucessos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson para uma proporção."""
    if total == 0:
        return 0.0, 1.0
    p = sucessos / total
    centro = (p + z**2 / (2 * total)) / (1 + z**2 / total)
    margem = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / (1 + z**2 / total)
    return max(centro - margem, 0.0), min(centro + margem, 1.0)


def medir(linhas: list[dict], limite: float = LIMITE_RUIDO) -> dict:
    """Ruído por veículo e no total, kappa entre revisores e veículos aceitos."""
    por_item = defaultdict(list)
    for linha in linhas:
        por_item[linha["id"]].append(linha)
    fonte_do_item = {item: revisoes[0]["fonte"] for item, revisoes in por_item.items()}
    problema = {
        item: any(r["problema"] != "nenhum" for r in revisoes)
        for item, revisoes in por_item.items()
    }

    kappas = {}
    revisores = sorted({linha["revisor"] for linha in linhas})
    for a, b in combinations(revisores, 2):
        pares = []
        for revisoes in por_item.values():
            valores = {r["revisor"]: r["problema"] for r in revisoes}
            if a in valores and b in valores:
                pares.append((valores[a], valores[b]))
        if pares:
            binarios = [(x != "nenhum", y != "nenhum") for x, y in pares]
            kappas[f"{a}-{b}"] = {
                "itens": len(pares),
                "problema": kappa_cohen(pares),
                "tem_problema": kappa_cohen(binarios),
            }

    veiculos = []
    for fonte in sorted(set(fonte_do_item.values())):
        itens = [item for item, f in fonte_do_item.items() if f == fonte]
        com_problema = sum(problema[item] for item in itens)
        inferior, superior = wilson(com_problema, len(itens))
        ruido = com_problema / len(itens)
        veiculos.append(
            {
                "fonte": fonte,
                "itens": len(itens),
                "com_problema": com_problema,
                "ruido": round(ruido, 4),
                "ic_inferior": round(inferior, 4),
                "ic_superior": round(superior, 4),
                "aceito": int(ruido <= 2 * limite),
            }
        )
    mantidos = [
        item
        for item, f in fonte_do_item.items()
        if f in {v["fonte"] for v in veiculos if v["aceito"]}
    ]
    com_problema = sum(problema[item] for item in mantidos)
    ruido = com_problema / len(mantidos) if mantidos else 1.0
    aceito = bool(mantidos) and ruido <= limite
    if not aceito:
        for v in veiculos:
            v["aceito"] = 0
    return {
        "itens": len(por_item),
        "com_problema": sum(problema.values()),
        "ruido_total": sum(problema.values()) / len(por_item) if por_item else None,
        "ic_total": wilson(sum(problema.values()), len(por_item)),
        "itens_mantidos": len(mantidos),
        "ruido_mantidos": ruido,
        "ic_mantidos": wilson(com_problema, len(mantidos)),
        "aceito": aceito,
        "kappas": kappas,
        "veiculos": veiculos,
    }


def porcentagem(intervalo: tuple[float, float]) -> str:
    return f"[{intervalo[0]:.1%}, {intervalo[1]:.1%}]"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    comandos = parser.add_subparsers(dest="comando", required=True)
    sorteio = comandos.add_parser("sortear")
    sorteio.add_argument("--itens", type=int, default=200)
    sorteio.add_argument("--revisores", nargs="+", required=True)
    importacao = comandos.add_parser("importar")
    importacao.add_argument("planilhas", nargs="+", type=Path)
    comandos.add_parser("medir")
    args = parser.parse_args()

    try:
        if args.comando == "sortear":
            if not DATASET.exists():
                sys.exit(f"{DATASET.relative_to(RAIZ)} não encontrado; rode antes: make dados")
            with open(DATASET, encoding="utf-8") as entrada:
                registros = candidatos(map(json.loads, entrada))
            amostra = sortear(registros, args.itens)
            for revisor in args.revisores:
                destino = PLANILHAS / f"auditoria-{revisor}.csv"
                linhas = [
                    {
                        **{c: r.get(c) or "" for c in COLUNAS_PLANILHA},
                        "problema": "",
                        "revisor": revisor,
                    }
                    for r in amostra
                ]
                gravar_csv(destino, COLUNAS_PLANILHA, linhas, codificacao="utf-8-sig")
                print(f"{destino.relative_to(RAIZ)}: {len(linhas)} itens")
            por_fonte = defaultdict(int)
            for r in amostra:
                por_fonte[r["fonte"]] += 1
            print(f"{len(amostra)} de {len(registros)} candidatos; por veículo: {dict(por_fonte)}")
            return

        if args.comando == "importar":
            novas, vazias = importar(args.planilhas)
            print(f"{AUDITORIA.relative_to(RAIZ)}: {novas} revisões importadas, {vazias} em branco")
            return

        if not AUDITORIA.exists():
            sys.exit(f"{AUDITORIA.relative_to(RAIZ)} não encontrado; rode antes o importar")
        resultado = medir(ler_csv(AUDITORIA))
    except ErroAuditoria as erro:
        sys.exit(f"Auditoria inválida: {erro}")

    print(
        f"{resultado['itens']} itens, {resultado['com_problema']} com problema: ruído "
        f"{resultado['ruido_total']:.1%} {porcentagem(resultado['ic_total'])}"
    )
    for par, kappa in resultado["kappas"].items():
        print(
            f"kappa de Cohen {par} ({kappa['itens']} itens): tipo de problema "
            f"{formatar(kappa['problema'])}, tem problema {formatar(kappa['tem_problema'])}"
        )
    print(f"{'veículo':28} {'itens':>5} {'probl.':>6} {'ruído':>6}  IC 95%           aceito")
    for v in resultado["veiculos"]:
        intervalo = porcentagem((v["ic_inferior"], v["ic_superior"]))
        print(
            f"{v['fonte']:28} {v['itens']:5} {v['com_problema']:6} {v['ruido']:6.1%}  {intervalo:16} {v['aceito']}"
        )
    situacao = "aceito" if resultado["aceito"] else f"recusado (limite {LIMITE_RUIDO:.0%})"
    print(
        f"Veículos mantidos: {resultado['itens_mantidos']} itens, ruído "
        f"{resultado['ruido_mantidos']:.1%} {porcentagem(resultado['ic_mantidos'])}: dataset {situacao}"
    )
    gravar_csv(VEICULOS, COLUNAS_VEICULOS, resultado["veiculos"])
    print(f"Gravado {VEICULOS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
