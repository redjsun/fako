"""Normalização do texto de entrada do classificador, igual à do treino.

O modelo aprendeu com o `texto_curto` do dataset (alegação checada ou título de matéria)
depois de `limpar()` de `pesquisa/ml/dados.py`. A API não importa código da pesquisa, então
`VEICULOS`, `limpar()` e os filtros de manchete (`motivo_filtro_portal()` de
`pesquisa/dados/preparar_dados.py`) estão copiados aqui. **Mudou lá, muda aqui.**

- `limpar()`: tira URLs e créditos de veículo nas pontas; mantém caixa e pontuação.
- `normalizar_manchete()`: o título de uma notícia externa no formato do `texto_curto`
  (entidades HTML, sufixo " - Veículo" do agregador, espaços) e depois `limpar()`.
- `motivo_descarte()`: por que a manchete não serve como afirmação verdadeira (os mesmos
  filtros das matérias de portal no treino, mais tamanho); None se serve.
"""

import html
import re

VEICULOS = (
    "G1",
    "g1",
    "UOL",
    "Folha",
    "Folha de S.Paulo",
    "Folha de São Paulo",
    "Estadão",
    "Estadão Conteúdo",
    "O Estado de S. Paulo",
    "O Globo",
    "Extra",
    "Veja",
    "Poder360",
    "CNN Brasil",
    "Agência Brasil",
    "Reuters",
    "AFP",
    "BBC",
    "BBC News Brasil",
    "Metrópoles",
    "R7",
    "Terra",
    "Jovem Pan",
    "InfoMoney",
    "Brasil de Fato",
    "Revista Oeste",
    "O Antagonista",
    "Agência Pública",
    "Jornal da USP",
    "Valor",
    "Valor Econômico",
)
# No começo do texto, só nomes que não são palavras comuns ("Veja: vídeo mostra..." é conteúdo).
AMBIGUOS_NO_INICIO = {"Veja", "Extra", "Terra", "Valor"}


def _alternativas(nomes) -> str:
    return "|".join(sorted((re.escape(n) for n in nomes), key=len, reverse=True))


_NOMES = _alternativas(VEICULOS)
_NOMES_INICIO = _alternativas(v for v in VEICULOS if v not in AMBIGUOS_NO_INICIO)
URL = re.compile(r"https?://\S+|www\.\S+")
CREDITO_FINAL = re.compile(
    rf"(?:\s*[|\-–—]\s*(?:{_NOMES})|\s*\((?:{_NOMES})\)|\s*Com informações d[aoe]s?\s+(?:{_NOMES}))\.?\s*$"
)
CREDITO_INICIAL = re.compile(rf"^\s*(?:\((?:{_NOMES})\)|(?:{_NOMES_INICIO}))\s*[:|\-–—]\s+")


def limpar(texto: str) -> str:
    """Tira URLs e créditos de veículo nas pontas; mantém caixa e pontuação."""
    texto = URL.sub(" ", texto)
    anterior = None
    while anterior != texto:
        anterior = texto
        texto = CREDITO_FINAL.sub("", texto)
        texto = CREDITO_INICIAL.sub("", texto)
    return re.sub(r"\s+", " ", texto).strip()


# Filtros das matérias de portal (preparar_dados.py): opinião, vídeo, pergunta, fala relatada.
SECOES_FORA = re.compile(
    r"/(opiniao|colunas?|colunistas?|blogs?|videos?|ao-vivo|podcasts?|publieditorial|"
    r"patrocinado|conteudo-patrocinado|especial-publicitario|editorial|artigos?|analise|"
    r"entrevistas?|charges?)/"
)
TITULO_FORA = re.compile(r"^\s*(ao vivo|opinião|análise|artigo|editorial|entrevista)\b", re.I)
RELATA_FALA = re.compile(
    r"\b(diz|dizem|disse|afirma|afirmam|afirmou|declara|declarou|alega|alegou|garante|"
    r"defende|nega|negou|critica|acusa|acusou|admite|avalia|aponta|cobra|promete|"
    r"prometeu|ataca|rebate|sugere|insinua|classifica)\b"
    r"|(^|[,;:]\s*)segundo\b",
    re.I,
)
ASPAS = re.compile(r"[\"“”«»]|‘[^’]+’|'[^']+'(?!\w)")
# Só nas manchetes externas: sem a URL da seção, o vídeo e a galeria aparecem no título.
TITULO_MIDIA = re.compile(r"^\s*(vídeos?|fotos?|galeria|podcast|quiz|veja)\b", re.I)
# Faixa de tamanho dos títulos do treino; fora dela não parece uma afirmação do jogo.
MINIMO_PALAVRAS = 5
MAXIMO_CARACTERES = 200


def normalizar_manchete(titulo: str, veiculo: str | None = None) -> str:
    """Título de notícia externa no formato do `texto_curto` do treino."""
    texto = html.unescape(titulo or "")
    texto = re.sub(r"\s+", " ", texto).strip()
    if veiculo:
        # Agregadores repetem o veículo no fim: "Manchete - Folha de S.Paulo", "Manchete | CNN".
        texto = re.sub(rf"\s*[|\-–—]\s*{re.escape(veiculo.strip())}\s*$", "", texto, flags=re.I)
    return limpar(texto)


def motivo_descarte(manchete: str, url: str = "") -> str | None:
    """Por que a manchete não vira afirmação verdadeira do jogo; None se serve."""
    if not manchete:
        return "sem título"
    if len(manchete.split()) < MINIMO_PALAVRAS or len(manchete) > MAXIMO_CARACTERES:
        return "tamanho"
    url = url.lower()
    if (
        SECOES_FORA.search(url)
        or "youtu" in url
        or TITULO_FORA.search(manchete)
        or TITULO_MIDIA.search(manchete)
    ):
        return "opinião, vídeo, ao vivo ou publicidade"
    if manchete.endswith("?"):
        return "pergunta"
    if RELATA_FALA.search(manchete) or ASPAS.search(manchete):
        return "relata fala"
    return None
