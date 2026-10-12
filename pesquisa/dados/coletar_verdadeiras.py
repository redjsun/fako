"""Monta um CSV próprio de notícias verdadeiras a partir de portais brasileiros.

Uso:
    python pesquisa/dados/coletar_verdadeiras.py                       # todos os portais, 2018 a hoje
    python pesquisa/dados/coletar_verdadeiras.py --por-janela 2 --portais poder360 veja
    python pesquisa/dados/coletar_verdadeiras.py --de 2024-01 --ate 2024-03   # teste rápido

Usa a API REST do WordPress (100 matérias por requisição, com título, linha fina,
texto e data). Cada mês é dividido em 6 janelas de ~5 dias, e de cada janela vêm as
N matérias mais recentes. Janelas curtas espalham a amostra por vários dias do mês,
em vez de concentrá-la no último dia de cada período. As respostas ficam em cache em
pesquisa/data/raw/verdadeiras/api/. Os portais são coletados em paralelo, cada um gravando o
próprio CSV em pesquisa/data/raw/verdadeiras/portais/; no fim eles são juntados em
pesquisa/data/raw/verdadeiras/verdadeiras.csv.

Critérios dos portais:
- linhas editoriais variadas, para o modelo não aprender "qual site" é verdadeiro;
- robots.txt sem bloqueio a robôs de treino de IA (GPTBot, CCBot, Google-Extended,
  ClaudeBot...). Portais com esse opt-out ficam de fora mesmo que a API esteja aberta.
"""

import argparse
import csv
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from http_cache import baixar

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "data" / "raw" / "verdadeiras"
CACHE = DESTINO / "api"
PARCIAIS = DESTINO / "portais"  # um CSV por portal, juntados em SAIDA no fim
SAIDA = DESTINO / "verdadeiras.csv"

# Verificados em 2026-10-01: API WordPress aberta e robots.txt sem opt-out de IA.
# A CNN Brasil também tem a API aberta, mas ignora os filtros de data e fica de fora.
PORTAIS = {
    "poder360": ("www.poder360.com.br", "centro"),
    "veja": ("veja.abril.com.br", "centro"),
    "brasildefato": ("www.brasildefato.com.br", "esquerda"),
    "apublica": ("apublica.org", "esquerda"),
    "revistaoeste": ("revistaoeste.com", "direita"),
    "oantagonista": ("oantagonista.com.br", "direita"),
    "jovempan": ("jovempan.com.br", "direita"),
    "jornalusp": ("jornal.usp.br", "ciencia"),
    "infomoney": ("www.infomoney.com.br", "economia"),
}
CAMPOS = ["id", "portal", "linha_editorial", "url", "data", "titulo", "linha_fina",
          "primeiro_paragrafo", "texto", "n_palavras"]
MIN_CARACTERES_PARAGRAFO = 40


def texto_limpo(fragmento: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragmento or ""))).strip()


def paragrafos(conteudo: str) -> list[str]:
    """Parágrafos do corpo, sem legendas, embeds e chamadas curtas ("Leia mais")."""
    conteudo = re.sub(r"<(figure|figcaption|script|style|blockquote)[^>]*>.*?</\1>", " ", conteudo or "",
                      flags=re.S | re.I)
    trechos = [texto_limpo(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", conteudo, flags=re.S | re.I)]
    return [t for t in trechos if len(t) >= MIN_CARACTERES_PARAGRAFO and not t.lower().startswith("leia")]


def janelas(inicio: date, fim: date):
    """Janelas de ~5 dias: 1–5, 6–10, 11–15, 16–20, 21–25 e 26 até o fim do mês."""
    atual = inicio
    while atual < fim:
        proximo_mes = (atual.replace(day=28) + timedelta(days=4)).replace(day=1)
        cortes = [atual.replace(day=d) for d in (1, 6, 11, 16, 21, 26)] + [proximo_mes]
        for a, b in zip(cortes, cortes[1:]):
            if a < fim:
                yield a, min(b, fim)
        atual = proximo_mes


def coletar_portal(nome: str, dominio: str, inicio: date, fim: date, n: int, intervalo: float):
    pasta = CACHE / nome
    for a, b in janelas(inicio, fim):
        params = {
            "per_page": n, "orderby": "date", "order": "desc",
            "after": f"{a.isoformat()}T00:00:00", "before": f"{b.isoformat()}T00:00:00",
            "_fields": "id,date,link,title,excerpt,content",
        }
        corpo, status = baixar(f"https://{dominio}/wp-json/wp/v2/posts?{urlencode(params)}", pasta, intervalo)
        if status != 200 or not corpo:
            print(f"  {nome} {a}: status {status}")
            continue
        try:
            posts = json.loads(corpo)
        except json.JSONDecodeError:
            print(f"  {nome} {a}: resposta não é JSON")
            continue
        yield from posts


def registro(nome: str, linha: str, post: dict) -> dict | None:
    corpo = paragrafos(post.get("content", {}).get("rendered", ""))
    titulo = texto_limpo(post.get("title", {}).get("rendered", ""))
    if not titulo or not corpo:
        return None
    texto = "\n".join(corpo)
    return {
        "id": f"{nome}-{post['id']}",
        "portal": nome,
        "linha_editorial": linha,
        "url": post.get("link"),
        "data": (post.get("date") or "")[:10],
        "titulo": titulo,
        "linha_fina": texto_limpo(post.get("excerpt", {}).get("rendered", "")) or None,
        "primeiro_paragrafo": corpo[0],
        "texto": texto,
        "n_palavras": len(texto.split()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--portais", nargs="*", default=list(PORTAIS), choices=list(PORTAIS))
    parser.add_argument("--de", default="2018-01", help="mês inicial (AAAA-MM)")
    parser.add_argument("--ate", default=None, help="mês final, exclusivo (AAAA-MM); padrão: hoje")
    parser.add_argument("--por-janela", type=int, default=4, help="matérias por portal e janela de ~5 dias")
    parser.add_argument("--intervalo", type=float, default=1.0, help="segundos entre requisições")
    args = parser.parse_args()

    inicio = date.fromisoformat(f"{args.de}-01")
    fim = date.fromisoformat(f"{args.ate}-01") if args.ate else date.today()

    # Um portal por thread: os servidores são diferentes, então o intervalo entre
    # requisições continua valendo por site, e o tempo total é o do portal mais lento.
    with ThreadPoolExecutor(max_workers=len(args.portais)) as executor:
        tarefas = [
            executor.submit(coletar_e_gravar, nome, inicio, fim, args.por_janela, args.intervalo)
            for nome in args.portais
        ]
        for tarefa in tarefas:
            tarefa.result()  # propaga erros das threads

    registros = {}
    for parcial in sorted(PARCIAIS.glob("*.csv")):
        registros.update(ler(parcial))
    gravar(SAIDA, registros)
    print(f"\n{len(registros)} matérias em {SAIDA.relative_to(RAIZ)}")


def coletar_e_gravar(nome: str, inicio: date, fim: date, n: int, intervalo: float):
    dominio, linha = PORTAIS[nome]
    parcial = PARCIAIS / f"{nome}.csv"
    registros = ler(parcial)
    antes = len(registros)
    for i, post in enumerate(coletar_portal(nome, dominio, inicio, fim, n, intervalo), 1):
        r = registro(nome, linha, post)
        if r:
            registros[r["id"]] = r
        if i % 200 == 0:
            gravar(parcial, registros)  # salva o progresso de tempos em tempos
    gravar(parcial, registros)
    print(f"{nome}: {len(registros) - antes} matérias novas ({len(registros)} no total)", flush=True)


def ler(arquivo: Path) -> dict:
    if not arquivo.exists():
        return {}
    with open(arquivo, encoding="utf-8", newline="") as f:
        return {linha["id"]: linha for linha in csv.DictReader(f)}


def gravar(arquivo: Path, registros: dict):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with open(arquivo, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        escritor.writeheader()
        for chave in sorted(registros):
            escritor.writerow(registros[chave])


if __name__ == "__main__":
    main()
