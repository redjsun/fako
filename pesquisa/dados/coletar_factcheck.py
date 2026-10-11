"""Coleta checagens em português pela Google Fact Check Tools API.

Uso:
    python pesquisa/dados/coletar_factcheck.py --descobrir    # quais agências aparecem em PT
    python pesquisa/dados/coletar_factcheck.py                # coleta todas as agências de AGENCIAS
    python pesquisa/dados/coletar_factcheck.py --sites aosfatos.org
    python pesquisa/dados/coletar_factcheck.py --incremental  # coleta diária: só o que é novo

Precisa da variável FACTCHECK_API_KEY (no ambiente ou no .env da raiz do repositório). A saída é
pesquisa/data/raw/factcheck/checagens.jsonl, uma linha por checagem (alegação + veredito), e
o resumo impresso no fim mostra os vereditos mais comuns para montar o mapeamento
verdadeiro/falso no preparo.

No modo --incremental, a paginação de cada agência para na primeira página que não traz
checagem nova: a API devolve as checagens da mais recente para a mais antiga. Cada execução
acrescenta uma linha em pesquisa/data/raw/factcheck/execucoes.jsonl, com as checagens novas e
as requisições por agência, para notar quando uma fonte para de trazer dados.
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from functools import partial
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "data" / "raw" / "factcheck" / "checagens.jsonl"
EXECUCOES = SAIDA.parent / "execucoes.jsonl"
ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

# Agências brasileiras de checagem, como a API registra o site do publicador (conferido
# com --descobrir). O observador.pt fica de fora por ser português de Portugal.
AGENCIAS = [
    "aosfatos.org",
    "estadao.com.br",
    "noticias.uol.com.br",
    "bol.uol.com.br",
    "checamos.afp.com",
    "projetocomprova.com.br",
    "www1.folha.uol.com.br",
    "oglobo.globo.com",
    "agenciatatu.com.br",
    "eleicoes.apublica.org",
    "nexojornal.com.br",
    # não apareceram na descoberta; mantidos para confirmar pelo filtro de site
    "lupa.uol.com.br",
    "g1.globo.com",
    "boatos.org",
    "e-farsas.com",
]

# Buscas genéricas usadas só para descobrir quais publicadores existem em PT.
TERMOS_DESCOBERTA = ["lula", "bolsonaro", "vacina", "eleição", "vídeo", "stf", "covid", "golpe"]


def chave_api() -> str:
    chave = os.environ.get("FACTCHECK_API_KEY")
    env = RAIZ.parent / ".env"  # .env da raiz do repositório
    if not chave and env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if linha.startswith("FACTCHECK_API_KEY="):
                chave = linha.split("=", 1)[1].strip()
    if not chave:
        sys.exit("Defina FACTCHECK_API_KEY no .env (veja .env.example).")
    return chave


class ErroAPI(Exception):
    pass


# Requisições feitas nesta execução, por agência, para o log da coleta.
requisicoes = Counter()


def requisitar(params: dict, tentativas: int = 6) -> dict:
    """GET com nova tentativa e espera crescente para 429 e erros 5xx (instabilidade)."""
    for tentativa in range(tentativas):
        requisicoes[params.get("reviewPublisherSiteFilter") or "descoberta"] += 1
        try:
            resposta = requests.get(ENDPOINT, params=params, timeout=60)
        except requests.RequestException as erro:
            ultimo = str(erro)
        else:
            if resposta.status_code == 200:
                return resposta.json()
            ultimo = f"{resposta.status_code}: {resposta.text[:200]}"
            if resposta.status_code != 429 and resposta.status_code < 500:
                break  # chave inválida, parâmetro errado: repetir não adianta
        time.sleep(2**tentativa)
    raise ErroAPI(ultimo)


def buscar(params: dict, chave: str, max_paginas: int, parar=None):
    """Percorre as páginas de claims:search e devolve os claims brutos.

    `parar(claims)`, se dado, recebe cada página: True encerra a paginação depois dela.
    """
    params = {**params, "languageCode": "pt", "pageSize": 100, "key": chave}
    for _ in range(max_paginas):
        corpo = requisitar(params)
        claims = corpo.get("claims", [])
        yield from claims
        if not corpo.get("nextPageToken") or (parar and parar(claims)):
            return
        params["pageToken"] = corpo["nextPageToken"]
        time.sleep(0.2)


def achatar(claim: dict) -> list[dict]:
    """Uma alegação pode ter várias checagens; gera uma linha por checagem."""
    return [
        {
            "alegacao": claim.get("text"),
            "autor_alegacao": claim.get("claimant"),
            "data_alegacao": (claim.get("claimDate") or "")[:10] or None,
            "agencia": review.get("publisher", {}).get("name"),
            "site_agencia": review.get("publisher", {}).get("site"),
            "url": review.get("url"),
            "titulo_checagem": review.get("title"),
            "data_checagem": (review.get("reviewDate") or "")[:10] or None,
            "veredito": review.get("textualRating"),
            "idioma": review.get("languageCode"),
        }
        for review in claim.get("claimReview", [])
    ]


def descobrir(chave: str):
    sites = Counter()
    for termo in TERMOS_DESCOBERTA:
        for claim in buscar({"query": termo}, chave, max_paginas=3):
            for linha in achatar(claim):
                sites[linha["site_agencia"]] += 1
    print("Publicadores encontrados em buscas genéricas (site: checagens):")
    for site, n in sites.most_common():
        print(f"  {site}: {n}")


def pagina_conhecida(claims: list[dict], site: str, conhecidas: set[str]) -> bool:
    """Nenhuma checagem da agência na página é nova: as páginas seguintes são mais antigas."""
    return all(
        linha["url"] in conhecidas
        for claim in claims
        for linha in achatar(claim)
        if linha["url"] and linha["site_agencia"] == site
    )


def registrar_execucao(novas: dict[str, int], incremental: bool, falhas: list[str]):
    linha = {
        "inicio": datetime.now().isoformat(timespec="seconds"),
        "incremental": incremental,
        "novas": novas,
        "requisicoes": dict(requisicoes),
        "falhas": falhas,
    }
    with open(EXECUCOES, "a", encoding="utf-8", newline="\n") as log:
        log.write(json.dumps(linha, ensure_ascii=False) + "\n")


def gravar(por_url: dict):
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as out:
        for url in sorted(por_url):
            out.write(json.dumps(por_url[url], ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--descobrir", action="store_true", help="lista publicadores em PT")
    parser.add_argument("--sites", nargs="*", default=AGENCIAS, help="sites das agências")
    parser.add_argument("--max-paginas", type=int, default=500, help="limite por agência")
    parser.add_argument(
        "--incremental", action="store_true", help="para cada agência quando não há nada novo"
    )
    args = parser.parse_args()
    chave = chave_api()

    if args.descobrir:
        descobrir(chave)
        return

    por_url = {}
    if SAIDA.exists():
        for linha in SAIDA.read_text(encoding="utf-8").splitlines():
            registro = json.loads(linha)
            por_url[registro["url"]] = registro

    falhas, novas = [], {}
    for site in args.sites:
        antes = len(por_url)
        # As URLs conhecidas são copiadas antes: cada página já entrou em por_url quando é avaliada.
        parar = partial(pagina_conhecida, site=site, conhecidas=set(por_url)) if args.incremental else None
        try:
            for claim in buscar({"reviewPublisherSiteFilter": site}, chave, args.max_paginas, parar):
                for linha in achatar(claim):
                    if linha["url"]:
                        por_url[linha["url"]] = linha
        except ErroAPI as erro:
            falhas.append(site)
            print(f"{site}: interrompido ({erro}); o que veio até aqui foi mantido")
        novas[site] = len(por_url) - antes
        print(f"{site}: {novas[site]} checagens novas em {requisicoes[site]} requisições")
        gravar(por_url)  # a cada agência, para não perder progresso
    registrar_execucao(novas, args.incremental, falhas)

    registros = list(por_url.values())
    print(f"\n{sum(novas.values())} checagens novas em {sum(requisicoes.values())} requisições")
    print(f"{len(registros)} checagens em {SAIDA.relative_to(RAIZ)}")
    print("Vereditos mais comuns:")
    for veredito, n in Counter((r["veredito"] or "").strip().lower() for r in registros).most_common(25):
        print(f"  {n:6}  {veredito}")
    anos = Counter((r["data_checagem"] or "????")[:4] for r in registros)
    print("Checagens por ano:", dict(sorted(anos.items())))
    if falhas:
        print(f"Agências incompletas (rode de novo com --sites): {' '.join(falhas)}")


if __name__ == "__main__":
    main()
