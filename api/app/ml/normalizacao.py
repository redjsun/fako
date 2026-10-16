"""Normalização do texto de entrada do classificador, igual à do treino.

O modelo aprendeu com o `texto_curto` do dataset (alegação checada ou título de matéria)
depois desta mesma `limpar()`. `VEICULOS`, `limpar()`, os filtros de manchete e os vereditos
das agências são os do preparo do dataset de treino: mudar aqui muda o que o modelo recebe.

- `limpar()`: tira URLs e créditos de veículo nas pontas; mantém caixa e pontuação.
- `normalizar_manchete()`: o título de uma notícia externa no formato do `texto_curto`
  (entidades HTML, sufixo " - Veículo" do agregador, espaços) e depois `limpar()`.
- `motivo_descarte()`: por que a manchete não serve como afirmação verdadeira (os mesmos
  filtros das matérias de portal no treino, mais tamanho); None se serve. Alegações checadas
  passam pelo tamanho, como no treino, e pelos filtros próprios da publicação sem revisão:
  alegação que depende de mídia, que já traz a conclusão da agência e, opcionalmente, política.
- `verdadeira_pelo_veredito()`: o veredito da agência em verdadeiro/falso; None nos enganosos
  e ambíguos, que não viram afirmação do jogo.
- `normalizar_autor()`: quem fez a alegação (`claimant` da Fact Check API), para mostrar ao
  jogador onde ela circulou. Só desta API, não vem do treino.
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


# Filtros das matérias de portal (os do preparo do dataset): opinião, vídeo, pergunta, fala relatada.
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
# Também só nas manchetes externas: serviço (onde assistir, sorteio, horário) não é afirmação e
# envelhece em um dia.
TITULO_SERVICO = re.compile(
    r"\b(onde assistir|como assistir|que horas|hor[áa]rios?|transmite|transmiss[ãa]o|"
    r"escala[çc][ãa]o|palpites?|mega-sena|lotof[áa]cil|quina|loteria|sorteio|"
    r"resultado d[aoe]s?|confira|saiba como|veja como|passo a passo|hor[óo]scopo)\b",
    re.I,
)
# Matéria explicativa: o título anuncia uma explicação em vez de afirmar algo.
TITULO_EXPLICATIVO = re.compile(
    r"^\s*(o que|por que|porque|como|quando|onde|qual|quais|quem|você|entenda|saiba)\b"
    r"|\b(entenda|explica|explicam)\s*$",
    re.I,
)
# Faixa de tamanho dos títulos do treino; fora dela não parece uma afirmação do jogo.
MINIMO_PALAVRAS = 5
MAXIMO_CARACTERES = 200


# Só nas alegações checadas. Entram no jogo sem revisão humana, então o texto precisa se
# sustentar sozinho: sem a mídia que circulou e sem a resposta embutida.
CITA_MIDIA = re.compile(
    r"\b(fotos?|imagens?|imagem|v[íi]deos?|[áa]udios?|prints?|grava[çc][ãa]o|grava[çc][õo]es|"
    r"mapas?|gr[áa]ficos?|reportagem|post|postagem|publica[çc][ãa]o|tu[íi]te|live)\b",
    re.I,
)
TRAZ_CONCLUSAO = re.compile(
    r"\b(deep ?fake|fake news|boato|montagem)\b"
    r"|\b(é|são|foi|foram|era|eram)\s+(falso|falsa|falsos|falsas|fake|golpe|enganos[oa]s?|"
    r"verdadeir[oa]s?|editad[oa]s?|manipulad[oa]s?|gerad[oa]s?\s+por\s+ia)\b",
    re.I,
)
# Checagens de discurso: a fala do político em primeira pessoa não é afirmação sem o autor.
PRIMEIRA_PESSOA = re.compile(
    r"\b(eu|nós|meu|minha|meus|minhas|nosso|nossa|nossos|nossas|me|comigo)\b", re.I
)
# Trecho recortado, com contexto acrescentado pela agência entre colchetes.
COLCHETES = re.compile(r"\[|\]")
POLITICA = re.compile(
    r"\b(lula|bolsonaro|fl[áa]vio|michelle|janja|moraes|gilmar|dino|barroso|haddad|"
    r"tarc[íi]sio|alckmin|trump|maduro|milei|governo|censura|judici[áa]rio|"
    r"elei[çc][ãa]o|elei[çc][õo]es|eleitor\w*|eleit[oa]s?|urnas?|turno|vot\w*|"
    r"candidat\w*|presidente|presidencial|deputad\w*|senador\w*|vereador\w*|"
    r"partido\w*|petistas?|bolsonaristas?|esquerda|direita|comunis\w*|ditadura)\b",
    re.I,
)
# Siglas só em maiúsculas ("PT", e não "pt" de português).
SIGLAS_POLITICAS = re.compile(r"\b(PT|PL|PSDB|PSOL|MDB|STF|TSE|CPMI|CPI)\b")


def normalizar_manchete(titulo: str, veiculo: str | None = None) -> str:
    """Título de notícia externa no formato do `texto_curto` do treino."""
    texto = html.unescape(titulo or "")
    texto = re.sub(r"\s+", " ", texto).strip()
    if veiculo:
        # Agregadores repetem o veículo no fim: "Manchete - Folha de S.Paulo", "Manchete | CNN".
        texto = re.sub(rf"\s*[|\-–—]\s*{re.escape(veiculo.strip())}\s*$", "", texto, flags=re.I)
    return limpar(texto)


def motivo_descarte(
    manchete: str, url: str = "", checagem: bool = False, sem_politica: bool = False
) -> str | None:
    """Por que o texto não vira afirmação do jogo; None se serve.

    Com `checagem`, o texto é uma alegação checada por agência: no treino as alegações não
    passam pelos filtros de portal (pergunta, aspas, fala relatada fazem parte do boato), mas
    passam pelos de mídia, conclusão e fala recortada; com `sem_politica`, também pelo de
    política.
    """
    if not manchete:
        return "sem título"
    if len(manchete.split()) < MINIMO_PALAVRAS or len(manchete) > MAXIMO_CARACTERES:
        return "tamanho"
    if checagem:
        if CITA_MIDIA.search(manchete):
            return "depende de imagem, vídeo ou áudio"
        if TRAZ_CONCLUSAO.search(manchete):
            return "traz a conclusão da checagem"
        if PRIMEIRA_PESSOA.search(manchete) or COLCHETES.search(manchete):
            return "fala ou trecho recortado"
        if sem_politica and (POLITICA.search(manchete) or SIGLAS_POLITICAS.search(manchete)):
            return "política ou eleição"
        return None
    url = url.lower()
    if (
        SECOES_FORA.search(url)
        or "youtu" in url
        or TITULO_FORA.search(manchete)
        or TITULO_MIDIA.search(manchete)
    ):
        return "opinião, vídeo, ao vivo ou publicidade"
    if TITULO_SERVICO.search(manchete):
        return "serviço"
    if "?" in manchete or TITULO_EXPLICATIVO.search(manchete):
        return "pergunta ou explicativa"
    if RELATA_FALA.search(manchete) or ASPAS.search(manchete):
        return "relata fala"
    return None


# Vereditos das agências (os do preparo do dataset). Os enganosos e os ambíguos não têm lado no jogo.
VEREDITOS_FALSO = {"falso", "fake", "montagem", "predominantemente falso"}
# Meias-verdades: a veracidade "enganoso" do treino (fora do jogo binário, entram na avaliação).
VEREDITOS_ENGANOSO = {
    "enganoso",
    "distorcido",
    "fora de contexto",
    "sem contexto",
    "falta contexto",
    "exagerado",
    "impreciso",
    "não é bem assim",
    "parcialmente falso",
    "verdadeiro, mas...",
}
VEREDITOS_VERDADEIRO = {"verdadeiro", "comprovado", "fato"}


def normalizar_veredito(bruto: str | None) -> str | None:
    """Ex.: "Não_é_bem_assim" -> "não é bem assim"; "enganoso - texto..." -> "enganoso"."""
    veredito = (bruto or "").strip().lower().replace("_", " ").split(" - ")[0].strip()
    return veredito or None


def veracidade_pelo_veredito(veredito: str | None) -> str | None:
    """Os três níveis do treino (falso, enganoso, verdadeiro); None nos ambíguos."""
    if veredito in VEREDITOS_ENGANOSO:
        return "enganoso"
    lado = verdadeira_pelo_veredito(veredito)
    return None if lado is None else ("verdadeiro" if lado else "falso")


def verdadeira_pelo_veredito(veredito: str | None) -> bool | None:
    if veredito in VEREDITOS_FALSO:
        return False
    if veredito in VEREDITOS_VERDADEIRO:
        return True
    return None


# `claimant` da Fact Check API: em 97% das checagens vem preenchido, mas quase sempre com um
# rótulo genérico ("Boato de internet", "Várias fontes", "[site:name]").
PLATAFORMAS = {
    "whatsapp": "WhatsApp",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "kwai": "Kwai",
    "telegram": "Telegram",
    "twitter": "X (Twitter)",
}
REDES_SOCIAIS = "redes sociais"
AUTOR_GENERICO = re.compile(
    r"boato|rede[s]? socia|v[aá]rias fontes|m[uú]ltiplas fontes|fontes diversas|"
    r"desinforma|postage|publica[cç][oõ]es|posts?\b|internet|usu[aá]rios|perfis|viral|"
    r"^v[aá]rios$|v[ií]deos?\b|"
    r"^\W*\[?site|^\W*$",
    re.IGNORECASE,
)


def normalizar_autor(bruto: str | None) -> str | None:
    """ "Posts no Facebook" -> "Facebook"; "Boato de internet" -> "redes sociais";
    "Jair Bolsonaro" -> "Jair Bolsonaro"; vazio -> None."""
    autor = re.sub(r"\s+", " ", (bruto or "").strip().strip("\"'“”.")).strip()
    if not autor:
        return None
    minusculo = autor.lower()
    plataforma = next((nome for chave, nome in PLATAFORMAS.items() if chave in minusculo), None)
    if plataforma:
        return plataforma
    if minusculo == "x" or (re.search(r"\bx\b", minusculo) and AUTOR_GENERICO.search(autor)):
        return PLATAFORMAS["twitter"]
    if AUTOR_GENERICO.search(autor):
        return REDES_SOCIAIS
    return autor[:200]
