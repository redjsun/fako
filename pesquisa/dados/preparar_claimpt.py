"""Monta pesquisa/data/processed/claimpt.jsonl a partir do ClaimPT (LIAAD/INESC TEC).

Uso: python pesquisa/dados/preparar_claimpt.py   (só biblioteca padrão)

O ClaimPT são notícias da agência Lusa, em português europeu, com trechos anotados como
afirmação (claim) ou não-afirmação. Não há rótulo de veracidade, por isso ele fica fora do
dataset.jsonl: serve para avaliar a extração de afirmações pela LLM (pipeline-fako, 03,
uso 3.2), inclusive o "quem disse" (claimer).

Origem dos dados, nesta ordem:
    pesquisa/data/raw/ClaimPT-completo/   o dataset completo (1.308 artigos), obtido pelo Data Use
                                 Agreement e copiado à mão, com a mesma estrutura da amostra
    pesquisa/data/raw/ClaimPT/dataset_sample/   a amostra pública (20 artigos), de baixar_dados.sh

Cada pasta tem um annotations.jsonl (uma linha por artigo) e news_articles/*.txt.

Cada linha da saída é um artigo:
    id, base, documento, amostra, topico, data, titulo, texto, anotado,
    afirmacoes      [{id, trecho, inicio, fim, topico, partes, quem_disse, objeto, tempo}]
    nao_afirmacoes  [{id, trecho, inicio, fim}]
`inicio` e `fim` são posições de caractere em `texto`. `partes`, `quem_disse`, `objeto` e
`tempo` são listas de {texto, inicio, fim}, porque na origem podem vir como um objeto ou
como uma lista: a afirmação pode ser descontínua (duas partes no texto) e quem disse pode
ser citado várias vezes ("Netanyahu", "o primeiro-ministro israelita"). Trechos cujas
posições não batem com o texto são descartados e contados no resumo.

A licença é CC BY-NC-ND 4.0: uso não comercial e sem redistribuir versões derivadas. A
saída fica em pesquisa/data/, que está no .gitignore.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
ORIGENS = (
    (RAW / "ClaimPT-completo", False),
    (RAW / "ClaimPT" / "dataset_sample", True),
)
SAIDA = RAIZ / "data" / "processed" / "claimpt.jsonl"

MESES_ABREV = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def parse_data(bruto: str) -> str | None:
    """Ex.: "04 dez 2023" -> "2023-12-04"."""
    m = re.fullmatch(r"(\d{1,2}) (\w{3})\w* (\d{4})", (bruto or "").strip().lower())
    if not m or m[2] not in MESES_ABREV:
        return None
    try:
        return date(int(m[3]), MESES_ABREV[m[2]], int(m[1])).isoformat()
    except ValueError:
        return None


def trechos(bruto, texto: str, descartados: dict) -> list[dict]:
    """{text, begin, end}, lista deles ou string da origem -> [{texto, inicio, fim}].

    Uma string sem posições (acontece no `time`) vira um trecho com inicio e fim nulos.
    """
    if not bruto:
        return []
    if isinstance(bruto, str):
        return [{"texto": bruto, "inicio": None, "fim": None}]
    saida = []
    for t in bruto if isinstance(bruto, list) else [bruto]:
        if not t.get("text"):
            continue
        if texto[t["begin"]:t["end"]] != t["text"]:
            descartados["subtrechos"] += 1
            continue
        saida.append({"texto": t["text"], "inicio": t["begin"], "fim": t["end"]})
    return saida


def ler_artigos(pasta: Path, amostra: bool, descartados: dict):
    for linha in (pasta / "annotations.jsonl").read_text(encoding="utf-8").splitlines():
        doc = json.loads(linha)
        # As posições da origem contam a quebra de linha como um caractere; o open() em modo
        # texto converte o CRLF dos arquivos em LF, e as posições batem.
        with open(pasta / "news_articles" / doc["document"], encoding="utf-8") as f:
            texto = f.read()
        afirmacoes, nao_afirmacoes = [], []
        for item in doc["items"]:
            inicio, fim = item["begin_character"], item["end_character"]
            if texto[inicio:fim] != item["text_segment"]:
                descartados["trechos"] += 1
                continue
            base = {"id": item["id"], "trecho": item["text_segment"], "inicio": inicio, "fim": fim}
            if not item["claim"]:
                nao_afirmacoes.append(base)
                continue
            afirmacoes.append({
                **base,
                "topico": item.get("claim_topic"),
                "partes": trechos(item.get("claim_span"), texto, descartados),
                "quem_disse": trechos(item.get("claimer"), texto, descartados),
                "objeto": trechos(item.get("claim_object"), texto, descartados),
                "tempo": trechos(item.get("time"), texto, descartados),
            })
        yield {
            "id": "claimpt-" + doc["document"].removesuffix(".txt"),
            "base": "claimpt",
            "documento": doc["document"],
            "amostra": amostra,
            "topico": doc.get("news_article_topic"),
            "data": parse_data(doc.get("publication_time")),
            "titulo": texto.split("\n", 1)[0].strip(),
            "texto": texto,
            "anotado": bool(doc["items"]),
            "afirmacoes": afirmacoes,
            "nao_afirmacoes": nao_afirmacoes,
        }


def main():
    origem = next(((pasta, amostra) for pasta, amostra in ORIGENS if (pasta / "annotations.jsonl").exists()), None)
    if not origem:
        sys.exit("ClaimPT não encontrado em pesquisa/data/raw/. Rode antes: bash pesquisa/dados/baixar_dados.sh")
    pasta, amostra = origem
    print(f"Lendo {pasta.relative_to(RAIZ)}" + (" (amostra de 20 artigos)" if amostra else ""))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    artigos = afirmacoes = nao_afirmacoes = com_quem_disse = 0
    descartados = {"trechos": 0, "subtrechos": 0}
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as out:
        for artigo in ler_artigos(pasta, amostra, descartados):
            out.write(json.dumps(artigo, ensure_ascii=False) + "\n")
            artigos += 1
            afirmacoes += len(artigo["afirmacoes"])
            nao_afirmacoes += len(artigo["nao_afirmacoes"])
            com_quem_disse += sum(1 for a in artigo["afirmacoes"] if a["quem_disse"])
    print(f"artigos: {artigos}  afirmações: {afirmacoes} ({com_quem_disse} com quem disse)  "
          f"não-afirmações: {nao_afirmacoes}")
    print("descartados por posição que não bate com o texto:", descartados)
    print(f"Gerado {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
