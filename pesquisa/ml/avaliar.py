"""Avaliação comum a todos os modelos de veracidade (issue #13).

Uso:
    python pesquisa/ml/avaliar.py --modelo models/2026-11/referencia
    python pesquisa/ml/avaliar.py --modelo models/2026-11/referencia models/2026-11/bert   # lado a lado
    python pesquisa/ml/avaliar.py --modelo models/2026-11/bert --teste    # uma vez por candidato

Contrato com os scripts de treino (#9, #10): a pasta do modelo tem
- `previsoes.jsonl`: uma linha por exemplo, `{"id", "split", "p1", "p2"}`, com as duas
  fronteiras ordinais P1 = P(veracidade > falso) e P2 = P(veracidade > enganoso), já
  calibradas. `gravar_previsoes()` grava nesse formato;
- `config.json` (opcional): `{"texto": "original" | "padronizado", "prompt": ..., "modelo_llm": ...}`,
  para carregar os mesmos exemplos de `dados.py`;
- `limiares.json` (opcional, #12): `{"admin": 0.6, "jogador": 0.8}`, a confiança mínima abaixo
  da qual a saída é `incerto`.

Das fronteiras às probabilidades e à nota (pipeline-fako/01): P(falso) = 1 − P1,
P(enganoso) = P1 − P2, P(verdadeiro) = P2 e nota = 100 × (P1 + P2) / 2. A confiança é a maior
das três probabilidades.

Métricas, por split e também por fonte, por base e por ano: F1 por classe e macro, AUC de cada
fronteira e AUC macro (uma classe contra o resto, como o teste de atalho), MAE da nota, kappa
ponderado quadrático, recall de falsos com 1% e 5% de verdadeiros marcados como falsos, ECE e
% de `incerto`. Diagnósticos: fatia "só checados", margem sobre o teste de atalho
(pesquisa/ml/saidas/atalho.json, #8), envelhecimento (checagens de 2024 na validação × de 2025
em diante no teste) e os 50 piores erros.

Saídas na pasta do modelo: `metricas.json`, `relatorio.md` e `confiabilidade.png` (se o
matplotlib estiver instalado). Durante o desenvolvimento só a `validacao` é avaliada; o
`teste` entra com --teste, uma vez por modelo candidato.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score, f1_score, roc_auc_score

from dados import CLASSES, DATASET, ORDEM, Exemplo, carregar

ATALHO = Path(__file__).resolve().parent / "saidas" / "atalho.json"
FAIXAS_ECE = 10
TAXAS_FALSO_ALARME = (0.01, 0.05)
MINIMO_GRUPO = 20  # grupos menores ficam no metricas.json, mas não nas tabelas do relatório
PIORES = 50
MAX_FONTES_RELATORIO = 15


# --- Contrato com o treino --------------------------------------------------------------


def gravar_previsoes(
    pasta: Path, previsoes: dict[str, tuple[list[Exemplo], np.ndarray, np.ndarray]], config: dict
):
    """Grava `previsoes.jsonl` e `config.json`: {split: (exemplos, p1, p2)}."""
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "previsoes.jsonl", "w", encoding="utf-8", newline="\n") as saida:
        for split, (exemplos, p1, p2) in previsoes.items():
            for exemplo, a, b in zip(exemplos, p1, p2, strict=True):
                linha = {"id": exemplo.id, "split": split, "p1": float(a), "p2": float(b)}
                saida.write(json.dumps(linha) + "\n")
    (pasta / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def ler_previsoes(pasta: Path) -> dict[str, tuple[float, float]]:
    with open(pasta / "previsoes.jsonl", encoding="utf-8") as entrada:
        return {(linha := json.loads(texto))["id"]: (linha["p1"], linha["p2"]) for texto in entrada}


def ler_json(caminho: Path) -> dict | None:
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None


# --- Métricas -----------------------------------------------------------------------------


def probabilidades(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """Matriz n x 3 (falso, enganoso, verdadeiro) a partir das duas fronteiras."""
    p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
    p2 = np.minimum(p2, p1)  # P1 >= P2 por construção no CORAL; aqui por segurança
    return np.column_stack([1 - p1, p1 - p2, p2])


def nota(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    return 100 * (np.asarray(p1, float) + np.asarray(p2, float)) / 2


def recall_com_falso_alarme(prob_falso: np.ndarray, y: np.ndarray, taxa: float) -> float | None:
    """Recall de falsos no limiar em que no máximo `taxa` dos verdadeiros viram falso.

    O limiar é o maior P(falso) entre os verdadeiros que ainda cabem na taxa; só conta como
    falso quem fica estritamente acima dele (empates contam contra o modelo).
    """
    falsos, verdadeiros = prob_falso[y == 0], np.sort(prob_falso[y == 2])[::-1]
    if not len(falsos) or not len(verdadeiros):
        return None
    permitidos = int(np.floor(taxa * len(verdadeiros)))
    limiar = verdadeiros[permitidos] if permitidos < len(verdadeiros) else -np.inf
    return float(np.mean(falsos > limiar))


def ece(proba: np.ndarray, y: np.ndarray, faixas: int = FAIXAS_ECE) -> tuple[float, list[dict]]:
    """Erro de calibração esperado da confiança (maior probabilidade) e as faixas do diagrama."""
    confianca, acerto = proba.max(axis=1), proba.argmax(axis=1) == y
    indices = np.minimum((confianca * faixas).astype(int), faixas - 1)
    erro, diagrama = 0.0, []
    for faixa in range(faixas):
        dentro = indices == faixa
        if not dentro.any():
            continue
        media_confianca, taxa_acerto = float(confianca[dentro].mean()), float(acerto[dentro].mean())
        erro += dentro.mean() * abs(taxa_acerto - media_confianca)
        diagrama.append(
            {
                "faixa": faixa,
                "n": int(dentro.sum()),
                "confianca": media_confianca,
                "acerto": taxa_acerto,
            }
        )
    return float(erro), diagrama


def auc(alvo: np.ndarray, pontuacao: np.ndarray) -> float | None:
    return float(roc_auc_score(alvo, pontuacao)) if 0 < alvo.sum() < len(alvo) else None


def metricas(y: np.ndarray, p1: np.ndarray, p2: np.ndarray, limiares: dict | None = None) -> dict:
    """Todas as métricas de um grupo. `y` em índices de CLASSES (0 falso, 1 enganoso, 2 verdadeiro)."""
    y = np.asarray(y, int)
    proba = probabilidades(p1, p2)
    previsto = proba.argmax(axis=1)
    f1 = f1_score(y, previsto, labels=[0, 1, 2], average=None, zero_division=0)
    presentes = sorted(set(y.tolist()))
    por_classe_auc = {CLASSES[c]: auc(y == c, proba[:, c]) for c in presentes}
    validas = [v for v in por_classe_auc.values() if v is not None]
    erro_calibracao, diagrama = ece(proba, y)
    resultado = {
        "n": len(y),
        "classes": {CLASSES[c]: int((y == c).sum()) for c in range(3)},
        "f1": {CLASSES[c]: float(f1[c]) for c in range(3) if c in presentes},
        "f1_macro": float(np.mean([f1[c] for c in presentes])),
        "auc_fronteira": {
            ">falso": auc(y > 0, proba[:, 1:].sum(axis=1)),
            ">enganoso": auc(y > 1, proba[:, 2]),
        },
        "auc_macro": float(np.mean(validas)) if validas else None,
        "mae_nota": float(np.mean(np.abs(nota(p1, p2) - 50 * y))),
        "kappa_quadratico": (
            float(cohen_kappa_score(y, previsto, labels=[0, 1, 2], weights="quadratic"))
            if len(set(y.tolist()) | set(previsto.tolist())) > 1
            else None
        ),
        **{
            f"recall_falsos_{round(taxa * 100)}pct": recall_com_falso_alarme(proba[:, 0], y, taxa)
            for taxa in TAXAS_FALSO_ALARME
        },
        "ece": erro_calibracao,
        "confiabilidade": diagrama,
    }
    if limiares:
        confianca = proba.max(axis=1)
        resultado["incerto"] = {onde: float(np.mean(confianca < t)) for onde, t in limiares.items()}
    return resultado


# --- Avaliação de um modelo ------------------------------------------------------------


def grupos(exemplos: list[Exemplo], chave) -> dict[str, list[int]]:
    indices = defaultdict(list)
    for i, exemplo in enumerate(exemplos):
        indices[str(chave(exemplo) if chave(exemplo) is not None else "sem")].append(i)
    return dict(indices)


def avaliar_split(exemplos: list[Exemplo], p1, p2, limiares: dict | None) -> dict:
    y = np.array([ORDEM[e.veracidade] for e in exemplos])

    def de(indices):
        return metricas(y[indices], p1[indices], p2[indices], limiares)

    checados = [i for i, e in enumerate(exemplos) if e.checado]
    return {
        "geral": de(list(range(len(exemplos)))),
        "checados": de(checados) if checados else None,
        **{
            f"por_{nome}": {
                valor: de(indices) for valor, indices in sorted(grupos(exemplos, chave).items())
            }
            for nome, chave in (
                ("base", lambda e: e.base),
                ("fonte", lambda e: e.fonte),
                ("ano", lambda e: e.ano),
                ("origem", lambda e: e.origem_rotulo),
            )
        },
    }


def piores_erros(exemplos: list[Exemplo], p1, p2, n: int = PIORES) -> list[dict]:
    """Erros com confiança alta: os primeiros pela probabilidade da classe errada prevista."""
    proba = probabilidades(p1, p2)
    previsto, confianca = proba.argmax(axis=1), proba.max(axis=1)
    erros = [i for i, e in enumerate(exemplos) if previsto[i] != ORDEM[e.veracidade]]
    erros.sort(key=lambda i: (-abs(previsto[i] - ORDEM[exemplos[i].veracidade]), -confianca[i]))
    return [
        {
            "id": exemplos[i].id,
            "texto": exemplos[i].texto,
            "veracidade": exemplos[i].veracidade,
            "previsto": CLASSES[previsto[i]],
            "confianca": float(confianca[i]),
            "nota": float(nota(p1[i], p2[i])),
            "fonte": exemplos[i].fonte,
            "ano": exemplos[i].ano,
            "tipo": exemplos[i].tipo or exemplos[i].tipo_sugerido,
        }
        for i in erros[:n]
    ]


def margem_atalho(atalho: dict | None, texto: str, por_split: dict) -> dict | None:
    """AUC macro do modelo menos a do teste de atalho, na mesma versão do texto."""
    if not atalho or texto not in atalho.get("versoes", {}):
        return None
    piso = atalho["versoes"][texto]["splits"]
    resultado = {}
    for split, medidas in por_split.items():
        modelo, base = medidas["geral"]["auc_macro"], piso.get(split, {}).get("auc_macro")
        if modelo is not None and base is not None:
            resultado[split] = {"modelo": modelo, "atalho": base, "margem": modelo - base}
    return resultado


def envelhecimento(por_split: dict, exemplos: dict[str, list[Exemplo]], p1, p2) -> dict | None:
    """Queda das checagens de 2024 (validação) para as de 2025 em diante (teste)."""
    if "validacao" not in por_split or "teste" not in por_split:
        return None
    resultado = {}
    for split, anos in (("validacao", lambda a: a == 2024), ("teste", lambda a: a and a >= 2025)):
        indices = [i for i, e in enumerate(exemplos[split]) if e.checado and anos(e.ano)]
        if not indices:
            return None
        y = np.array([ORDEM[exemplos[split][i].veracidade] for i in indices])
        medidas = metricas(y, p1[split][indices], p2[split][indices])
        resultado[split] = {k: medidas[k] for k in ("n", "f1_macro", "auc_macro", "mae_nota")}
    resultado["queda_f1_macro"] = (
        resultado["validacao"]["f1_macro"] - resultado["teste"]["f1_macro"]
    )
    return resultado


def avaliar(
    pasta: Path, dataset: Path = DATASET, teste: bool = False, atalho: Path = ATALHO
) -> dict:
    config = ler_json(pasta / "config.json") or {}
    limiares = ler_json(pasta / "limiares.json")
    texto = config.get("texto", "original")
    prompt = Path(config["prompt"]) if config.get("prompt") else None
    conjunto = carregar(texto, dataset, prompt, config.get("modelo_llm"))
    previsoes = ler_previsoes(pasta)

    splits = ("validacao", "teste") if teste else ("validacao",)
    exemplos, p1, p2, por_split, sem_previsao = {}, {}, {}, {}, {}
    for split in splits:
        com = [e for e in conjunto.splits[split] if e.id in previsoes]
        sem_previsao[split] = len(conjunto.splits[split]) - len(com)
        if not com:
            continue
        exemplos[split] = com
        p1[split] = np.array([previsoes[e.id][0] for e in com])
        p2[split] = np.array([previsoes[e.id][1] for e in com])
        por_split[split] = avaliar_split(com, p1[split], p2[split], limiares)

    return {
        "modelo": str(pasta),
        "config": config,
        "limiares": limiares,
        "dataset_sha256": conjunto.dataset_sha256,
        "texto": texto,
        "splits": por_split,
        "sem_previsao": sem_previsao,
        "atalho": margem_atalho(ler_json(atalho), texto, por_split),
        "envelhecimento": envelhecimento(por_split, exemplos, p1, p2),
        "piores": {s: piores_erros(exemplos[s], p1[s], p2[s]) for s in exemplos},
    }


# --- Relatório ------------------------------------------------------------------------


def numero(valor, formato: str = ".3f") -> str:
    return "—" if valor is None else format(valor, formato)


COLUNAS_TABELA = (
    ("n", "n", "d"),
    ("F1 macro", "f1_macro", ".3f"),
    ("F1 falso", ("f1", "falso"), ".3f"),
    ("F1 enganoso", ("f1", "enganoso"), ".3f"),
    ("F1 verdadeiro", ("f1", "verdadeiro"), ".3f"),
    ("AUC >falso", ("auc_fronteira", ">falso"), ".3f"),
    ("AUC >enganoso", ("auc_fronteira", ">enganoso"), ".3f"),
    ("MAE nota", "mae_nota", ".1f"),
    ("kappa quad.", "kappa_quadratico", ".3f"),
    ("recall falsos @1%", "recall_falsos_1pct", ".3f"),
    ("recall falsos @5%", "recall_falsos_5pct", ".3f"),
    ("ECE", "ece", ".3f"),
)


def valor(medidas: dict, chave):
    if isinstance(chave, tuple):
        return medidas.get(chave[0], {}).get(chave[1])
    return medidas.get(chave)


def tabela(linhas: dict[str, dict], titulo: str, limiares: dict | None = None) -> list[str]:
    colunas = list(COLUNAS_TABELA) + [
        (f"% incerto ({onde})", ("incerto", onde), ".1%") for onde in (limiares or {})
    ]
    saida = [
        f"| {titulo} | " + " | ".join(nome for nome, _, _ in colunas) + " |",
        "|---|" + "---:|" * len(colunas),
    ]
    for rotulo, medidas in linhas.items():
        celulas = [numero(valor(medidas, chave), formato) for _, chave, formato in colunas]
        saida.append(f"| {rotulo} | " + " | ".join(celulas) + " |")
    return saida + [""]


def relatorio(resultado: dict) -> str:
    linhas = [
        f"# Avaliação: `{resultado['modelo']}`",
        "",
        f"- texto: `{resultado['texto']}`; dataset sha256 `{resultado['dataset_sha256'][:16]}`",
        f"- limiares: {resultado['limiares'] or 'sem limiares.json'}",
        f"- exemplos sem previsão (ficaram fora): {resultado['sem_previsao']}",
        "",
    ]
    for split, medidas in resultado["splits"].items():
        limiares = resultado["limiares"]
        linhas += [f"## {split}", ""]
        gerais = {"geral": medidas["geral"]}
        if medidas["checados"]:
            gerais["só checados"] = medidas["checados"]
        linhas += tabela(gerais, "grupo", limiares)
        for nome in ("base", "origem", "ano", "fonte"):
            grupos_split = {
                g: m for g, m in medidas[f"por_{nome}"].items() if m["n"] >= MINIMO_GRUPO
            }
            if nome == "fonte":
                maiores = sorted(grupos_split.items(), key=lambda par: -par[1]["n"])
                grupos_split = dict(maiores[:MAX_FONTES_RELATORIO])
            if grupos_split:
                linhas += [f"### Por {nome} (n ≥ {MINIMO_GRUPO})", ""]
                linhas += tabela(grupos_split, nome, limiares)

    if resultado["atalho"]:
        linhas += [
            "## Margem sobre o teste de atalho (AUC macro)",
            "",
            "| split | modelo | atalho | margem |",
            "|---|---:|---:|---:|",
        ]
        for split, m in resultado["atalho"].items():
            linhas.append(
                f"| {split} | {m['modelo']:.3f} | {m['atalho']:.3f} | {m['margem']:+.3f} |"
            )
        linhas.append("")
    else:
        linhas += ["Sem `pesquisa/ml/saidas/atalho.json` para este texto: rode `make atalho`.", ""]

    if resultado["envelhecimento"]:
        e = resultado["envelhecimento"]
        linhas += [
            "## Envelhecimento (só checagens)",
            "",
            f"F1 macro {e['validacao']['f1_macro']:.3f} em 2024 (n = {e['validacao']['n']}) → "
            f"{e['teste']['f1_macro']:.3f} em 2025+ (n = {e['teste']['n']}): queda de "
            f"{e['queda_f1_macro']:+.3f}.",
            "",
        ]

    for split, piores in resultado["piores"].items():
        linhas += [f"## {len(piores)} piores erros: {split}", ""]
        for nome in ("fonte", "ano", "tipo"):
            contagem = Counter(str(p[nome]) for p in piores).most_common(8)
            linhas.append(f"- por {nome}: " + ", ".join(f"{k} {n}" for k, n in contagem))
        linhas += [
            "",
            "| verdadeiro | previsto | confiança | nota | fonte | ano | texto |",
            "|---|---|---:|---:|---|---|---|",
        ]
        for p in piores:
            texto = p["texto"].replace("|", "\\|").replace("\n", " ")[:160]
            linhas.append(
                f"| {p['veracidade']} | {p['previsto']} | {p['confianca']:.2f} | {p['nota']:.0f} | "
                f"{p['fonte']} | {p['ano']} | {texto} |"
            )
        linhas.append("")
    return "\n".join(linhas)


def diagrama_confiabilidade(resultado: dict, destino: Path) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    figura, eixo = plt.subplots(figsize=(5, 5))
    eixo.plot([0, 1], [0, 1], linestyle="--", color="gray", label="calibração perfeita")
    for split, medidas in resultado["splits"].items():
        faixas = medidas["geral"]["confiabilidade"]
        eixo.plot(
            [f["confianca"] for f in faixas],
            [f["acerto"] for f in faixas],
            marker="o",
            label=f"{split} (ECE {medidas['geral']['ece']:.3f})",
        )
    eixo.set(xlabel="confiança média", ylabel="taxa de acerto", xlim=(0, 1), ylim=(0, 1))
    eixo.legend(loc="upper left")
    figura.tight_layout()
    figura.savefig(destino, dpi=120)
    plt.close(figura)
    return True


def comparar(resultados: list[dict]) -> str:
    """Tabela lado a lado (geral de cada split) para a decisão de #35."""
    linhas = []
    for split in ("validacao", "teste"):
        medidas = {
            r["modelo"]: r["splits"][split]["geral"] for r in resultados if split in r["splits"]
        }
        if medidas:
            linhas += [f"## {split}", ""] + tabela(medidas, "modelo")
    margens = {r["modelo"]: r["atalho"] for r in resultados if r["atalho"]}
    if margens:
        linhas += [
            "Margem sobre o atalho (AUC macro, validação): "
            + ", ".join(
                f"{m} {a['validacao']['margem']:+.3f}"
                for m, a in margens.items()
                if "validacao" in a
            ),
            "",
        ]
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--modelo", type=Path, nargs="+", required=True, help="pasta(s) com previsoes.jsonl"
    )
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument(
        "--teste", action="store_true", help="inclui o teste (uma vez por candidato)"
    )
    parser.add_argument("--comparacao", type=Path, help="grava a tabela lado a lado em Markdown")
    args = parser.parse_args()
    if not args.dataset.exists():
        sys.exit(f"{args.dataset} não encontrado. Rode antes: make dados")

    resultados = []
    for pasta in args.modelo:
        if not (pasta / "previsoes.jsonl").exists():
            sys.exit(f"{pasta / 'previsoes.jsonl'} não encontrado")
        resultado = avaliar(pasta, args.dataset, args.teste)
        (pasta / "metricas.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (pasta / "relatorio.md").write_text(relatorio(resultado), encoding="utf-8")
        figura = diagrama_confiabilidade(resultado, pasta / "confiabilidade.png")
        resultados.append(resultado)
        print(f"{pasta}: metricas.json, relatorio.md" + (", confiabilidade.png" if figura else ""))

    tabela_lado_a_lado = comparar(resultados)
    print("\n" + tabela_lado_a_lado)
    if args.comparacao:
        args.comparacao.write_text(tabela_lado_a_lado, encoding="utf-8")
        print(f"Gravado {args.comparacao}")


if __name__ == "__main__":
    main()
