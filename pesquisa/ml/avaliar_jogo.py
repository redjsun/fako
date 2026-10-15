"""Acertos dos modelos nas notícias do jogo (factcheck, GNews e Agência Brasil).

Uso:
    python pesquisa/ml/avaliar_jogo.py --modelo models/2026-11/referencia models/2026-11/bert

O conjunto vem de `make coletar-avaliacao` (api/app/jobs/coletar_avaliacao.py): notícias
publicadas depois do fim do dataset de treino, pelo mesmo caminho da importação do jogo, uma
coleta por arquivo em pesquisa/data/avaliacao/. Aqui:

- as coletas são juntadas sem repetir `id` (URL) nem texto, e sai o que já está no dataset de
  treino (mesma URL, ou mesmo texto curto ou título depois da `limpar()`), em qualquer split;
- cada modelo recebe o texto que a API daria a ele (`texto` do config.json): a manchete no
  modelo do texto original; a afirmação extraída (ou a manchete, se não houve) no
  padronizado e no híbrido. Mesma `limpar()` e mesma calibração (`calibracao.json`) da API;
- o jogo é binário (`is_true`), e o modelo, ordinal: acerta a verdadeira quando a classe mais
  provável é `verdadeiro`, e a falsa quando é `falso` ou `enganoso`. As checagens enganosas,
  fora do jogo hoje (decisão 01), contam como falsas ("não é verdade") e têm o acerto à parte.

Medidas: acerto, acerto balanceado (média do acerto nas verdadeiras e nas falsas, que não
depende da proporção da coleta), AUC da nota de confiabilidade (100 × (P1 + P2) / 2, a barra do
jogo) e o acerto com um corte na nota escolhido numa metade do conjunto e medido na outra
(as duas metades pelo hash do `id`; a média das duas). O corte mostra quanto o modelo
acertaria com a régua ajustada à proporção do jogo, sem medir no que serviu para escolhê-la.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

from avaliar import auc, ler_json, nota, probabilidades
from calibrar import aplicar
from dados import DATASET, limpar

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "avaliacao"


def chave_texto(texto: str | None) -> str:
    """Texto comparável: sem caixa, acentos à parte, pontuação e espaços."""
    return re.sub(r"\W+", " ", (texto or "").casefold()).strip()


def ler_coletas(pasta: Path = PASTA) -> list[dict]:
    """As linhas de todas as coletas, a primeira de cada `id` e de cada manchete."""
    linhas, vistos = [], set()
    for arquivo in sorted(pasta.glob("*.jsonl")):
        for texto in arquivo.read_text(encoding="utf-8").splitlines():
            if not texto.strip():
                continue
            linha = json.loads(texto)
            chaves = {linha["id"], chave_texto(linha["manchete"])}
            if chaves & vistos:
                continue
            vistos |= chaves
            linhas.append(linha)
    return linhas


def vistos_no_treino(dataset: Path = DATASET) -> set[str]:
    """URLs e textos (texto curto e título) do dataset, em qualquer split."""
    vistos = set()
    with open(dataset, encoding="utf-8") as entrada:
        for texto in entrada:
            registro = json.loads(texto)
            if registro.get("url"):
                vistos.add(registro["url"])
            for campo in ("texto_curto", "titulo"):
                if registro.get(campo):
                    vistos.add(chave_texto(limpar(registro[campo])))
    return vistos - {""}


def sem_o_que_o_treino_viu(linhas: list[dict], vistos: set[str]) -> list[dict]:
    return [
        linha
        for linha in linhas
        if linha["url"] not in vistos
        and chave_texto(limpar(linha["manchete"])) not in vistos
        and chave_texto(limpar(linha.get("afirmacao") or "")) not in vistos
    ]


def texto_de_entrada(linha: dict, texto: str) -> str:
    """O texto que a API passa ao classificador (Question.claim_text ou a manchete)."""
    bruto = (
        linha["manchete"] if texto == "original" else linha.get("afirmacao") or linha["manchete"]
    )
    return limpar(bruto) or bruto.strip()


def veracidade(linha: dict) -> str:
    """Coletas antigas não têm `veracidade`: sai do gabarito binário."""
    return linha.get("veracidade") or ("verdadeiro" if linha["is_true"] else "falso")


def metade(identificador: str) -> int:
    return int(hashlib.sha1(identificador.encode()).hexdigest(), 16) % 2


def acerto_balanceado(certo: np.ndarray, y: np.ndarray) -> float | None:
    if not 0 < y.sum() < len(y):
        return None
    return float((certo[y].mean() + certo[~y].mean()) / 2)


def melhor_corte(pontuacao: np.ndarray, y: np.ndarray) -> float:
    """O corte na nota com o maior acerto balanceado (verdadeira se nota >= corte)."""
    candidatos = np.unique(pontuacao)
    return float(
        max(candidatos, key=lambda corte: acerto_balanceado((pontuacao >= corte) == y, y) or 0)
    )


def corte_cruzado(pontuacao: np.ndarray, y: np.ndarray, metades: np.ndarray) -> dict | None:
    """Corte escolhido numa metade e medido na outra, nos dois sentidos."""
    medidas, cortes = [], []
    for escolha in (0, 1):
        a, b = metades == escolha, metades != escolha
        if not (0 < y[a].sum() < a.sum() and 0 < y[b].sum() < b.sum()):
            return None
        corte = melhor_corte(pontuacao[a], y[a])
        cortes.append(corte)
        medidas.append(acerto_balanceado((pontuacao[b] >= corte) == y[b], y[b]))
    return {"acerto_balanceado": float(np.mean(medidas)), "cortes": cortes}


def medir(linhas: list[dict], p1: np.ndarray, p2: np.ndarray) -> dict:
    y = np.array([linha["is_true"] for linha in linhas], bool)
    classe = probabilidades(p1, p2).argmax(axis=1)  # 0 falso, 1 enganoso, 2 verdadeiro
    certo = np.where(y, classe == 2, classe < 2)
    pontuacao = nota(p1, p2)
    metades = np.array([metade(linha["id"]) for linha in linhas])
    provedores = Counter(linha["provedor"] for linha in linhas)
    niveis = np.array([veracidade(linha) for linha in linhas])
    return {
        "n": len(linhas),
        "verdadeiras": int(y.sum()),
        "acerto": float(certo.mean()) if len(certo) else None,
        "acerto_verdadeiras": float(certo[y].mean()) if y.any() else None,
        "acerto_falsas": float(certo[~y].mean()) if (~y).any() else None,
        "acerto_balanceado": acerto_balanceado(certo, y),
        "auc_nota": auc(y.astype(int), pontuacao),
        "corte_cruzado": corte_cruzado(pontuacao, y, metades),
        "por_provedor": {
            nome: float(certo[[linha["provedor"] == nome for linha in linhas]].mean())
            for nome in provedores
        },
        "por_veracidade": {
            nivel: float(certo[niveis == nivel].mean()) for nivel in sorted(set(niveis))
        },
    }


def fronteiras_do_modelo(pasta: Path, textos: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """P1 e P2 calibradas como na API (referência TF-IDF ou BERTimbau)."""
    from treinar_referencia import ARQUIVO_MODELO

    if (pasta / ARQUIVO_MODELO).exists():
        import joblib

        from treinar_referencia import fronteiras

        p1, p2 = fronteiras(textos, joblib.load(pasta / ARQUIVO_MODELO))
    else:
        from treinar_bert import carregar_modelo, fronteiras

        p1, p2 = fronteiras(textos, carregar_modelo(pasta))
    calibracao = ler_json(pasta / "calibracao.json")
    return aplicar(p1, p2, calibracao) if calibracao else (p1, p2)


def porcentagem(valor) -> str:
    return "–" if valor is None else f"{100 * valor:.1f}%"


def tabela(resultados: dict[str, dict]) -> str:
    linhas = [
        "| Modelo | Texto | Acerto | Verdadeiras | Falsas | Balanceado | AUC nota | Corte cruzado |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nome, r in resultados.items():
        cruzado = r["corte_cruzado"]["acerto_balanceado"] if r["corte_cruzado"] else None
        auc_nota = "–" if r["auc_nota"] is None else f"{r['auc_nota']:.3f}"
        linhas.append(
            f"| {nome} | {r['texto']} | {porcentagem(r['acerto'])} | "
            f"{porcentagem(r['acerto_verdadeiras'])} | {porcentagem(r['acerto_falsas'])} | "
            f"{porcentagem(r['acerto_balanceado'])} | {auc_nota} | {porcentagem(cruzado)} |"
        )
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--modelo", type=Path, nargs="+", required=True)
    parser.add_argument("--coletas", type=Path, default=PASTA)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--json", type=Path, help="grava as medidas neste arquivo")
    args = parser.parse_args()

    coletadas = ler_coletas(args.coletas)
    linhas = sem_o_que_o_treino_viu(coletadas, vistos_no_treino(args.dataset))
    if not linhas:
        raise SystemExit(f"Nenhuma notícia em {args.coletas} (rode make coletar-avaliacao)")
    provedores = Counter((linha["provedor"], veracidade(linha)) for linha in linhas)
    print(
        f"{len(linhas)} notícias ({len(coletadas) - len(linhas)} já no treino, fora); "
        + ", ".join(f"{p} {v}: {n}" for (p, v), n in sorted(provedores.items()))
    )

    resultados = {}
    for pasta in args.modelo:
        texto = (ler_json(pasta / "config.json") or {}).get("texto", "original")
        entradas = [texto_de_entrada(linha, texto) for linha in linhas]
        resultados[pasta.name] = {
            "texto": texto,
            **medir(linhas, *fronteiras_do_modelo(pasta, entradas)),
        }
    print(tabela(resultados))
    for nome, r in resultados.items():
        por_provedor = ", ".join(f"{p} {porcentagem(v)}" for p, v in r["por_provedor"].items())
        por_nivel = ", ".join(f"{n} {porcentagem(v)}" for n, v in r["por_veracidade"].items())
        print(f"{nome}: acerto por provedor: {por_provedor}; por veracidade: {por_nivel}")
    if args.json:
        args.json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
