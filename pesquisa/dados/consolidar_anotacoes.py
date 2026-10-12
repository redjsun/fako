"""Importa as planilhas de anotação, mede a concordância e gera o rótulo final por id.

Uso:
    python pesquisa/dados/consolidar_anotacoes.py importar --rodada 1 pesquisa/data/anotacao/rodada-01-*.csv
    python pesquisa/dados/consolidar_anotacoes.py

Só biblioteca padrão. Arquivos em pesquisa/anotacoes/ (versionados, só `id` e rótulos):
- `rodada-NN.csv`: uma linha por item e anotador. `importar` lê as planilhas de trabalho
  preenchidas (sortear_anotacao.py), confere os valores, **tira o texto** e grava aqui.
- `adjudicacao.csv`: decisão da equipe nas discordâncias, com as mesmas colunas de rótulo.
- `consolidado.csv`: rótulo final por id, lido por preparar_dados.py e pesquisa/ml/dados.py.

Sem argumentos, imprime a concordância por campo nos itens com mais de um anotador
(concordância simples, kappa de Cohen entre cada par de anotadores e alfa de Krippendorff,
que serve para qualquer número) e grava o consolidado. O rótulo final é o da adjudicação,
quando houver; senão, o da maioria dos anotadores em cada campo. Itens sem maioria em algum
campo ficam pendentes (listados em pesquisa/data/anotacao/pendentes.csv) até a adjudicação.
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ANOTACOES = RAIZ / "anotacoes"
ADJUDICACAO = ANOTACOES / "adjudicacao.csv"
CONSOLIDADO = ANOTACOES / "consolidado.csv"
PENDENTES = RAIZ / "data" / "anotacao" / "pendentes.csv"
DATASET = RAIZ / "data" / "processed" / "dataset.jsonl"

# doc/guia-classificacao.md §7.
TIPOS = {
    "fora_escopo",
    "opiniao",
    "fabricado",
    "manipulado",
    "impostor",
    "falso_contexto",
    "enganoso",
    "falsa_conexao",
    "nenhum",
}
VERACIDADES = {"falso", "enganoso", "verdadeiro"}
SINAIS = ("pede_compartilhamento", "urgencia", "apelo_emocional", "ataque")
# Campos com concordância medida e rótulo final por maioria.
CAMPOS = ("tipo", "veracidade", *SINAIS)
COLUNAS_RODADA = ("id", "anotador", "tipo", "tipo_secundario", "veracidade", *SINAIS, "observacao")
COLUNAS_CONSOLIDADO = (
    "id",
    "tipo",
    "tipo_secundario",
    "veracidade",
    *SINAIS,
    "anotadores",
    "adjudicado",
)


class ErroAnotacao(ValueError):
    pass


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig", newline="") as entrada:
        return list(csv.DictReader(entrada))


def gravar_csv(caminho: Path, colunas, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def normalizar(linha: dict, anotador_padrao: str | None = None) -> dict | None:
    """Confere e limpa uma linha preenchida; None se o item ainda não foi anotado.

    Só as colunas de COLUNAS_RODADA passam: o texto da planilha de trabalho fica para trás.
    """
    item = linha.get("id", "").strip()
    tipo = (linha.get("tipo") or "").strip().lower()
    if not item or not tipo:
        return None
    if tipo not in TIPOS:
        raise ErroAnotacao(f"{item}: tipo desconhecido {tipo!r}")
    secundario = (linha.get("tipo_secundario") or "").strip().lower()
    if secundario and secundario not in TIPOS:
        raise ErroAnotacao(f"{item}: tipo_secundario desconhecido {secundario!r}")
    veracidade = (linha.get("veracidade") or "").strip().lower()
    if veracidade and veracidade not in VERACIDADES:
        raise ErroAnotacao(f"{item}: veracidade desconhecida {veracidade!r}")
    if tipo in ("opiniao", "fora_escopo"):
        veracidade = ""  # opinião não tem veracidade (guia §7)
    sinais = {}
    for sinal in SINAIS:
        valor = (linha.get(sinal) or "0").strip()
        if valor not in ("0", "1"):
            raise ErroAnotacao(f"{item}: {sinal} deve ser 0 ou 1, não {valor!r}")
        sinais[sinal] = valor
    anotador = (linha.get("anotador") or anotador_padrao or "").strip()
    if not anotador:
        raise ErroAnotacao(f"{item}: sem anotador")
    return {
        "id": item,
        "anotador": anotador,
        "tipo": tipo,
        "tipo_secundario": secundario,
        "veracidade": veracidade,
        **sinais,
        "observacao": (linha.get("observacao") or "").strip(),
    }


def splits_produto(dataset: Path = DATASET) -> dict[str, str]:
    if not dataset.exists():
        return {}
    with open(dataset, encoding="utf-8") as entrada:
        return {r["id"]: r["split_produto"] for r in map(json.loads, entrada)}


def importar(planilhas: list[Path], destino: Path, splits: dict[str, str]) -> tuple[int, int]:
    """Junta as planilhas preenchidas em `destino`, só com id e rótulos.

    Uma linha nova substitui a anterior do mesmo id e anotador. Itens de
    `split_produto=teste` são recusados: o teste não é anotado para treino.
    """
    linhas = {(r["id"], r["anotador"]): r for r in ler_csv(destino)} if destino.exists() else {}
    novas = vazias = 0
    for planilha in planilhas:
        for bruta in ler_csv(planilha):
            linha = normalizar(bruta)
            if linha is None:
                vazias += 1
                continue
            if splits.get(linha["id"]) == "teste":
                raise ErroAnotacao(f"{linha['id']}: item do teste não pode ser anotado para treino")
            linhas[(linha["id"], linha["anotador"])] = linha
            novas += 1
    gravar_csv(
        destino, COLUNAS_RODADA, sorted(linhas.values(), key=lambda r: (r["id"], r["anotador"]))
    )
    return novas, vazias


def kappa_cohen(pares: list[tuple[str, str]]) -> float | None:
    """Kappa de Cohen entre dois anotadores; None se a concordância esperada é total."""
    if not pares:
        return None
    n = len(pares)
    observada = sum(a == b for a, b in pares) / n
    primeiro, segundo = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    esperada = sum(primeiro[c] * segundo[c] for c in primeiro) / n**2
    if esperada == 1:
        return None
    return (observada - esperada) / (1 - esperada)


def alfa_krippendorff(unidades: list[list[str]]) -> float | None:
    """Alfa de Krippendorff nominal; aceita qualquer número de anotadores por item."""
    coincidencias: Counter = Counter()
    for valores in unidades:
        m = len(valores)
        if m < 2:
            continue
        for i, a in enumerate(valores):
            for j, b in enumerate(valores):
                if i != j:
                    coincidencias[a, b] += 1 / (m - 1)
    por_valor: Counter = Counter()
    for (a, _), n in coincidencias.items():
        por_valor[a] += n
    total = sum(por_valor.values())
    discordancia_observada = sum(n for (a, b), n in coincidencias.items() if a != b)
    discordancia_esperada = sum(
        por_valor[a] * por_valor[b] for a in por_valor for b in por_valor if a != b
    )
    if discordancia_esperada == 0:
        return None
    return 1 - (total - 1) * discordancia_observada / discordancia_esperada


def por_item(linhas: list[dict]) -> dict[str, list[dict]]:
    itens = defaultdict(list)
    for linha in linhas:
        itens[linha["id"]].append(linha)
    return itens


def concordancia(linhas: list[dict]) -> dict[str, dict]:
    """Por campo: itens com 2+ anotadores, concordância simples, kappa por par e alfa."""
    itens = [anotacoes for anotacoes in por_item(linhas).values() if len(anotacoes) > 1]
    resultado = {}
    for campo in CAMPOS:
        unidades = [[a[campo] for a in anotacoes] for anotacoes in itens]
        kappas = {}
        anotadores = sorted({a["anotador"] for anotacoes in itens for a in anotacoes})
        for x, y in combinations(anotadores, 2):
            pares = []
            for anotacoes in itens:
                valores = {a["anotador"]: a[campo] for a in anotacoes}
                if x in valores and y in valores:
                    pares.append((valores[x], valores[y]))
            if pares:
                kappas[f"{x}-{y}"] = kappa_cohen(pares)
        resultado[campo] = {
            "itens": len(unidades),
            "concordancia": (
                sum(len(set(u)) == 1 for u in unidades) / len(unidades) if unidades else None
            ),
            "kappa": kappas,
            "alfa": alfa_krippendorff(unidades),
        }
    return resultado


def maioria(valores: list[str]) -> str | None:
    """Valor com mais da metade dos votos, ou None."""
    valor, votos = Counter(valores).most_common(1)[0]
    return valor if votos * 2 > len(valores) else None


def consolidar(linhas: list[dict], adjudicacao: list[dict]) -> tuple[list[dict], list[str]]:
    """Rótulo final por id: a adjudicação, quando houver, ou a maioria em cada campo."""
    decididos = {
        linha["id"]: normalizar(linha, anotador_padrao="adjudicacao") for linha in adjudicacao
    }
    finais, pendentes = [], []
    for item, anotacoes in sorted(por_item(linhas).items()):
        if decidido := decididos.get(item):
            final, adjudicado = decidido, 1
        else:
            final = {campo: maioria([a[campo] for a in anotacoes]) for campo in CAMPOS}
            if None in final.values():
                pendentes.append(item)
                continue
            final["tipo_secundario"] = maioria([a["tipo_secundario"] for a in anotacoes]) or ""
            adjudicado = 0
        finais.append(
            {
                "id": item,
                **{coluna: final[coluna] for coluna in ("tipo", "tipo_secundario", *CAMPOS[1:])},
                "anotadores": len(anotacoes),
                "adjudicado": adjudicado,
            }
        )
    return finais, pendentes


def formatar(valor: float | None) -> str:
    return "  -  " if valor is None else f"{valor:5.2f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    comandos = parser.add_subparsers(dest="comando")
    importacao = comandos.add_parser("importar", help="planilhas preenchidas -> rodada-NN.csv")
    importacao.add_argument("--rodada", type=int, required=True)
    importacao.add_argument("planilhas", nargs="+", type=Path)
    args = parser.parse_args()

    try:
        if args.comando == "importar":
            destino = ANOTACOES / f"rodada-{args.rodada:02d}.csv"
            novas, vazias = importar(args.planilhas, destino, splits_produto())
            print(
                f"{destino.relative_to(RAIZ)}: {novas} anotações importadas, {vazias} itens em branco"
            )
            return

        linhas = [
            normalizar(linha)
            for arquivo in sorted(ANOTACOES.glob("rodada-*.csv"))
            for linha in ler_csv(arquivo)
        ]
        linhas = [linha for linha in linhas if linha]
        if not linhas:
            sys.exit("Nenhuma anotação em pesquisa/anotacoes/rodada-*.csv")
        adjudicacao = ler_csv(ADJUDICACAO) if ADJUDICACAO.exists() else []
    except ErroAnotacao as erro:
        sys.exit(f"Anotação inválida: {erro}")

    print(f"{len(linhas)} anotações de {len({linha['anotador'] for linha in linhas})} anotadores")
    print(f"{'campo':22} {'itens':>5} {'concord.':>8} {'alfa':>6}  kappa de Cohen por par")
    for campo, medida in concordancia(linhas).items():
        kappas = ", ".join(f"{par} {formatar(k).strip()}" for par, k in medida["kappa"].items())
        print(
            f"{campo:22} {medida['itens']:5} {formatar(medida['concordancia']):>8} "
            f"{formatar(medida['alfa']):>6}  {kappas}"
        )

    finais, pendentes = consolidar(linhas, adjudicacao)
    gravar_csv(CONSOLIDADO, COLUNAS_CONSOLIDADO, finais)
    print(f"{CONSOLIDADO.relative_to(RAIZ)}: {len(finais)} itens com rótulo final")
    print("por tipo:", dict(Counter(f["tipo"] for f in finais).most_common()))
    if pendentes:
        ids = set(pendentes)
        gravar_csv(PENDENTES, COLUNAS_RODADA, [linha for linha in linhas if linha["id"] in ids])
        print(f"{len(pendentes)} itens sem maioria, para adjudicar: {PENDENTES.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
