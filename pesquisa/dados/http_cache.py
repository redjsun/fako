"""Download com cache em disco e intervalo entre requisições, usado pelos coletores."""

import hashlib
import time
from pathlib import Path

import requests

HEADERS = {"User-Agent": "grupo11-challenge1/1.0 (pesquisa academica sobre desinformacao)"}


def baixar(url: str, pasta_cache: Path, intervalo: float) -> tuple[str | None, int]:
    """Devolve (html, status). Páginas já baixadas vêm do cache, sem requisição."""
    cache = pasta_cache / f"{hashlib.sha1(url.encode()).hexdigest()}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8"), 200
    time.sleep(intervalo)
    try:
        resposta = requests.get(url, headers=HEADERS, timeout=60)
    except requests.RequestException:
        return None, 0
    if resposta.status_code != 200:
        return None, resposta.status_code
    # Sem charset no cabeçalho, o requests assume ISO-8859-1; os sites daqui são UTF-8.
    if "charset" not in resposta.headers.get("Content-Type", "").lower():
        resposta.encoding = "utf-8"
    pasta_cache.mkdir(parents=True, exist_ok=True)
    cache.write_text(resposta.text, encoding="utf-8")
    return resposta.text, 200
