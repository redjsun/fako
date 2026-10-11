"""Recoleta o texto original das notícias verdadeiras do FakeRecogna.

Uso:
    python pesquisa/dados/coletar_noticias.py                # todas as URLs recuperáveis
    python pesquisa/dados/coletar_noticias.py --amostra 200

O FakeRecogna só traz o texto lematizado, então baixamos as páginas de novo (cache em
pesquisa/data/raw/noticias/paginas/) e extraímos título, data e corpo da matéria. A saída é
pesquisa/data/raw/noticias/noticias.jsonl, com uma linha por URL.
"""

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from http_cache import baixar

RAIZ = Path(__file__).resolve().parent.parent
FAKERECOGNA = RAIZ / "data" / "raw" / "FakeRecogna.csv"
DESTINO = RAIZ / "data" / "raw" / "noticias"
PAGINAS = DESTINO / "paginas"
SAIDA = DESTINO / "noticias.jsonl"

# O UOL Notícias e o UOL Economia bloqueiam qualquer acesso automatizado (403 da Akamai,
# até no robots.txt). Não tentamos contornar; essas URLs ficam de fora.
BLOQUEADOS = ("noticias.uol.com.br", "economia.uol.com.br")
MIN_CARACTERES_PARAGRAFO = 40


def urls_verdadeiras() -> dict[str, dict]:
    if not FAKERECOGNA.exists():
        sys.exit("pesquisa/data/raw/FakeRecogna.csv não encontrado. Rode antes: bash pesquisa/dados/baixar_dados.sh")
    with open(FAKERECOGNA, encoding="utf-8", newline="") as f:
        return {
            linha["URL"].strip(): linha
            for linha in csv.DictReader(f)
            if linha["Classe"].startswith("1")
            and not any(dominio in linha["URL"] for dominio in BLOQUEADOS)
        }


def corpo_da_materia(sopa: BeautifulSoup) -> str | None:
    """O corpo é o grupo de parágrafos com mais texto, agrupados pela assinatura do
    elemento pai (tag + classes).

    Agrupar pela assinatura, e não pelo elemento, cobre o G1, que põe cada parágrafo num
    div próprio. Evita um seletor por site: G1 (div.content-text), UOL (div.text) e
    Extra (div.story) caem todos nessa regra.
    """
    for lixo in sopa(["script", "style", "figure", "figcaption", "aside", "nav", "footer"]):
        lixo.decompose()
    texto_por_pai = Counter()
    paragrafos_por_pai = {}
    for p in sopa.find_all("p"):
        texto = re.sub(r"\s+", " ", p.get_text(" ")).strip()
        if len(texto) < MIN_CARACTERES_PARAGRAFO:
            continue
        assinatura = (p.parent.name, " ".join(p.parent.get("class", [])))
        texto_por_pai[assinatura] += len(texto)
        paragrafos_por_pai.setdefault(assinatura, []).append(texto)
    if not texto_por_pai:
        return None
    melhor, _ = texto_por_pai.most_common(1)[0]
    return "\n".join(paragrafos_por_pai[melhor])


def extrair(url: str, html: str) -> dict:
    sopa = BeautifulSoup(html, "html.parser")
    titulo = sopa.find("meta", property="og:title") or sopa.find("h1")
    publicada = sopa.find("meta", property="article:published_time")
    publicada = publicada.get("content") if publicada else None
    if not publicada:  # G1
        tempo = sopa.find("time", itemprop="datePublished")
        publicada = tempo.get("datetime") if tempo else None
    if not publicada:
        achada = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
        publicada = achada[1] if achada else None
    dominio = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return {
        "url": url,
        "dominio": dominio[1] if dominio else None,
        "titulo": (titulo.get("content") if titulo.name == "meta" else titulo.get_text(" ")).strip()
        if titulo
        else None,
        "data": publicada[:10] if publicada else None,
        "texto": corpo_da_materia(sopa),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--amostra", type=int, help="coleta só N URLs sorteadas")
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--intervalo", type=float, default=1.0, help="segundos entre requisições")
    args = parser.parse_args()

    fonte = urls_verdadeiras()
    urls = sorted(fonte)
    if args.amostra:
        urls = random.Random(args.semente).sample(urls, min(args.amostra, len(urls)))
    print(f"{len(urls)} URLs a processar")

    existentes = {}
    if SAIDA.exists():
        for linha in SAIDA.read_text(encoding="utf-8").splitlines():
            registro = json.loads(linha)
            existentes[registro["url"]] = registro

    for i, url in enumerate(urls, 1):
        html, status = baixar(url, PAGINAS, args.intervalo)
        registro = extrair(url, html) if html else {"url": url}
        registro.setdefault("data", None)
        registro.update(
            status=status,
            categoria=fonte[url]["Categoria"],
            data_fakerecogna=fonte[url]["Data"].strip(),
        )
        existentes[url] = registro
        if i % 50 == 0:
            print(f"  {i}/{len(urls)}")

    DESTINO.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as out:
        for url in sorted(existentes):
            out.write(json.dumps(existentes[url], ensure_ascii=False) + "\n")

    processados = [existentes[u] for u in urls]
    ok = [r for r in processados if r["status"] == 200]
    print(f"baixadas: {len(ok)}/{len(processados)}")
    print(f"com texto: {sum(bool(r.get('texto')) for r in ok)}")
    print("status:", dict(Counter(r["status"] for r in processados)))
    print(f"Gerado {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
