"""Unifica as bases de pesquisa/data/raw/ em pesquisa/data/processed/dataset.jsonl.

Uso: python pesquisa/dados/preparar_dados.py   (só biblioteca padrão)

Cada linha do JSONL é uma notícia com os campos:
    id, base, fonte, rotulo, veracidade, veredito_original, tipo_sugerido, titulo, texto,
    texto_curto, categoria, data, autor, url, par_id, metricas, split, split_produto,
    origem_rotulo, tipo, sinais

- `base`: de onde vem o rótulo (fakebr, fakerecogna, faketrue, factcheck, fakenewsbr,
  verdadeiras). Os boatos do Boatos.org entram só como a parte falsa do FakeRecogna.
- `origem_rotulo`: por que o rótulo é confiável (agencia, curadoria, portal,
  portal_verificado, mensagem ou equipe), para pesar os exemplos no treino (ver
  ORIGEM_ROTULO_PESO). `portal_verificado`: matéria de portal que passou nos filtros e na
  auditoria (#6, ver verificar_portais).
- `tipo` e `sinais`: só nos itens anotados pela equipe (pesquisa/anotacoes/consolidado.csv,
  ver aplicar_anotacoes); nos demais, null.
- `veracidade`: falso, enganoso ou verdadeiro. `rotulo` é a versão binária (fake ou true)
  e fica vazio (null) nos enganosos, que só existem nas bases com veredito de agência.
- `veredito_original`: o veredito da agência, normalizado; `tipo_sugerido`: o tipo de
  conteúdo que ele indica (rótulo fraco, ver doc/guia-classificacao.md).
- `fonte`: domínio de onde veio o texto, para medir o atalho de fonte.
- `texto`: a versão mais longa disponível. `texto_curto`: a frase curta equivalente
  (alegação checada ou título da matéria), para treinar no formato das perguntas do jogo.
- `split` (protocolo A, "referência"): por base (ver BASES_TREINO). Fake.br e
  FakeRecogna são o treino, com 10% separados para validação; todo o resto é teste.
  Mede quanto as bases públicas generalizam para fontes que o modelo não viu.
- `split_produto` (protocolo B, "produto"): o modelo que vai para o jogo, em `treino`,
  `validacao` e `teste`. As bases pareadas (Fake.br, FakeRecogna, FakeTrue.Br) são
  sorteadas por par em 80/10/10; as checagens e os portais vão por data (treino de 2016 a
  2023, validação em 2024, teste de 2025 em diante); as mensagens de WhatsApp e de COVID
  ficam no treino. Ficam `fora` os registros sem data, os anteriores a 2016 e as
  quase-duplicatas, e viram `reserva` os portais e os que sobram no equilíbrio (ver
  definir_split_produto e equilibrar).

Registros repetidos (mesma URL ou mesmo início de texto) entram uma vez só, na primeira
base lida. As bases de treino são lidas primeiro, então uma checagem do teste que repete
uma do treino sai do teste. Quase-duplicatas (o mesmo boato reescrito) de um registro de
treino ou validação viram `fora` nos splits posteriores, nos dois protocolos.
"""

import csv
import hashlib
import json
import re
import sys
import zlib
from datetime import date
from pathlib import Path

csv.field_size_limit(2**31 - 1)

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
SAIDA = RAIZ / "data" / "processed" / "dataset.jsonl"
ANOTACOES = RAIZ / "anotacoes" / "consolidado.csv"

MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Ordem das linhas dos arquivos *-meta.txt do Fake.br (ver README do corpus).
METRICAS_FAKEBR = [
    "n_tokens", "n_palavras", "n_types", "n_links", "n_maiusculas", "n_verbos",
    "n_verbos_subj_imp", "n_substantivos", "n_adjetivos", "n_adverbios", "n_modais",
    "n_pron_1e2_sing", "n_pron_1_plural", "n_pronomes", "pausalidade", "n_caracteres",
    "media_tam_sentenca", "media_tam_palavra", "pct_erros_ortografia", "emotividade",
    "diversidade",
]


def parse_data(bruto: str) -> str | None:
    """Converte os vários formatos de data do Fake.br e do FakeRecogna para ISO.

    Procura a data em qualquer posição, porque há prefixos e sufixos como
    "Publicado em 04/05/21 10:52" e "27/03/2020 18h25Atualizada em ...".
    """
    s = bruto.strip()
    try:
        if m := re.search(r"(?<!\d)(\d{4})[-/](\d{2})[-/](\d{2})(?!\d)", s):
            a, mes, d = map(int, m.groups())
        elif m := re.search(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})(?!\d)", s):
            d, mes, a = map(int, m.groups())
            if mes > 12:  # alguns registros vêm como M/D/AAAA
                d, mes = mes, d
            if a < 100:
                a += 2000
        elif m := re.search(r"(\d{1,2}) de (\w+) de (\d{4})", s):
            d, a = int(m[1]), int(m[3])
            mes = MESES[m[2].lower()]
        else:
            return None
        if a < 2000:  # há datas digitadas errado na origem, como 0201-...
            return None
        return date(a, mes, d).isoformat()
    except (ValueError, KeyError):
        return None


# Vereditos das agências em três níveis de veracidade. Os falsos viram rótulo "fake"; as
# meias-verdades viram veracidade "enganoso", sem rótulo binário, para não misturar com o
# falso. Sátira (fora do escopo) e vereditos ambíguos (insustentável, sem provas,
# impossível provar, discutível...) ficam de fora.
VEREDITOS_FALSO = {"falso", "fake", "montagem", "predominantemente falso"}
VEREDITOS_ENGANOSO = {
    "enganoso", "distorcido", "fora de contexto", "sem contexto", "falta contexto",
    "exagerado", "impreciso", "não é bem assim", "parcialmente falso", "verdadeiro, mas...",
}
VEREDITOS_VERDADEIRO = {"verdadeiro", "comprovado", "fato"}

# Rótulo fraco de tipo (doc/guia-classificacao.md, seção 3), para pré-preencher a anotação.
TIPO_POR_VEREDITO = {
    **dict.fromkeys(("falso", "fake", "predominantemente falso"), "fabricado"),
    "montagem": "manipulado",
    **dict.fromkeys(("fora de contexto", "sem contexto", "falta contexto"), "falso_contexto"),
    **dict.fromkeys(
        ("enganoso", "distorcido", "exagerado", "impreciso", "não é bem assim",
         "parcialmente falso", "verdadeiro, mas..."),
        "enganoso",
    ),
    **dict.fromkeys(VEREDITOS_VERDADEIRO, "nenhum"),
}


def normalizar_veredito(bruto: str | None) -> str | None:
    """Ex.: "Não_é_bem_assim" -> "não é bem assim"; "enganoso - texto..." -> "enganoso"."""
    veredito = (bruto or "").strip().lower().replace("_", " ").split(" - ")[0].strip()
    return veredito or None


def veracidade_do_veredito(veredito: str | None) -> str | None:
    if veredito in VEREDITOS_FALSO:
        return "falso"
    if veredito in VEREDITOS_ENGANOSO:
        return "enganoso"
    if veredito in VEREDITOS_VERDADEIRO:
        return "verdadeiro"
    return None


ROTULO_POR_VERACIDADE = {"falso": "fake", "verdadeiro": "true", "enganoso": None}
VERACIDADE_POR_ROTULO = {"fake": "falso", "true": "verdadeiro"}

# Sub-bases da FakenewsBR usadas como falsas. Ficam de fora: traduções do inglês
# (EXT_LIARBR, EXT_AVERITECBR), português de Portugal (FC_POLIGRAFO, FC_OBSERVADOR),
# texto de checador (LLM4BR_300), Kaggle sem licença com rótulos misturados (fakes) e o
# Fake.br, que já lemos do original.
FAKENEWSBR_INCLUIR = {
    "FC_G1", "FC_LUPA", "FC_EFARSAS", "FC_BEREIA", "FC_SBT", "FC_BOATOS", "FC_BOATOS_VIRAL",
    "FC_AFP", "FC_COMPROVA", "FC_AOSFATOS", "FC_UOL", "FC_ESTADAO", "FC_FOLHA", "FC_APUBLICA",
    "FC_TATU", "FC_GFC", "FC_NEXO",
    "FakeWhatsApp.BR_2018", "COVID19.BR",  # mensagens anotadas, sem veredito de agência
}
# Nas mensagens, "true" quer dizer "não é desinformação" (não há veredito de agência), e as
# duas classes entram, no mesmo formato de texto. Nas sub-bases de agência, as verdadeiras
# só entram com veredito, e os falsos são amostrados em equilibrar().
FAKENEWSBR_MENSAGENS = {"FakeWhatsApp.BR_2018", "COVID19.BR"}


BASES_TREINO = {"fakebr", "fakerecogna"}
FRACAO_VALIDACAO = 0.10


# Protocolo B, por data, para as checagens e os portais: treino de INICIO_TREINO até a
# validação, validação no ano anterior ao teste. Antes de 2016 quase só há falsas
# (checagens antigas), e a época viraria pista do rótulo. As meias-verdades (veracidade
# "enganoso") se concentram de 2023 em diante, por isso o treino vai até 2023.
INICIO_TREINO = "2016"
INICIO_VALIDACAO = "2024"
INICIO_TESTE = "2025"
# Bases pareadas por assunto (ou sem data confiável para todos os registros): sorteio por
# grupo, para as duas notícias de um par ficarem do mesmo lado e para validação e teste
# também terem verdadeiros, que as checagens recentes quase não têm.
BASES_POR_GRUPO = {"fakebr", "fakerecogna", "faketrue"}
FRACAO_TREINO_GRUPO, FRACAO_VALIDACAO_GRUPO = 0.80, 0.10


def fracao(grupo: str) -> float:
    """Número determinístico em [0, 1] a partir do hash do grupo."""
    return int(hashlib.sha1(grupo.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def sorteio_validacao(grupo: str) -> bool:
    """Sorteio determinístico de FRACAO_VALIDACAO dos registros (protocolo A)."""
    return fracao(grupo) < FRACAO_VALIDACAO


def definir_split_produto(registro: dict) -> str:
    """Protocolo B: o modelo do jogo, em treino, validação e teste.

    - Bases pareadas (BASES_POR_GRUPO): 80/10/10 por par (ou por registro, no FakeRecogna).
    - Mensagens de WhatsApp e de COVID (FAKENEWSBR_MENSAGENS): treino. São de 2018 e 2020, e
      a COVID19.BR não tem data.
    - Checagens (Fact Check API, FakenewsBR) e portais: por data. A Fact Check API segue a
      regra: as checagens até 2023 ensinam o enganoso, e as de 2024 em diante, que o
      modelo não vê, são a validação e o teste.
    Registros sem data, ou anteriores a INICIO_TREINO, ficam `fora`.
    """
    base = registro["base"]
    if base in BASES_POR_GRUPO:
        grupo = f"{base}-par-{registro['par_id']}" if registro["par_id"] is not None else registro["id"]
        sorteio = fracao(grupo)
        if sorteio < FRACAO_TREINO_GRUPO:
            return "treino"
        return "validacao" if sorteio < FRACAO_TREINO_GRUPO + FRACAO_VALIDACAO_GRUPO else "teste"
    if base == "fakenewsbr" and registro["fonte"] in FAKENEWSBR_MENSAGENS:
        return "treino"
    data = registro["data"]
    if not data or data < INICIO_TREINO:
        return "fora"
    if data >= INICIO_TESTE:
        return "teste"
    if data >= INICIO_VALIDACAO:
        return "validacao"
    return "treino"


# Peso de cada origem de rótulo no treino (doc da pipeline, 04): o rótulo de portal é
# verdadeiro por suposição (fica fora do dataset selecionado, ver equilibrar), e o "true"
# das mensagens quer dizer só "não é desinformação". `equipe` (#5), `jogo` (revisões do
# admin, #29) e `portal_verificado` (#6) entram com 1,0 até a validação dizer outra coisa.
ORIGEM_ROTULO_PESO = {
    "agencia": 1.0, "curadoria": 1.0, "portal": 0.7, "mensagem": 0.7,
    "equipe": 1.0, "jogo": 1.0, "portal_verificado": 1.0,
}


def origem_rotulo(registro: dict) -> str:
    base, falso = registro["base"], registro["veracidade"] != "verdadeiro"
    if base == "fakebr":
        return "curadoria"
    if base in ("fakerecogna", "faketrue"):  # falsas do Boatos.org; verdadeiras de portal
        return "agencia" if falso else "portal"
    if base == "verdadeiras":
        return "portal"
    if base == "fakenewsbr" and registro["fonte"] in FAKENEWSBR_MENSAGENS:
        return "mensagem"
    return "agencia"


SINAIS = ("pede_compartilhamento", "urgencia", "apelo_emocional", "ataque")


def aplicar_anotacoes(registros: list[dict], caminho: Path = ANOTACOES) -> int:
    """Rótulo final da equipe (consolidar_anotacoes.py, #5), juntado pelo id.

    O registro ganha `tipo` e `sinais`, a veracidade anotada substitui a original e a origem
    vira `equipe`. O split é o do registro. Sátira (`fora_escopo`) sai dos dois protocolos;
    opinião não tem veracidade anotada e fica com a original.
    """
    if not caminho.exists():
        return 0
    with open(caminho, encoding="utf-8", newline="") as entrada:
        rotulos = {linha["id"]: linha for linha in csv.DictReader(entrada)}
    aplicados = 0
    for registro in registros:
        if not (rotulo := rotulos.get(registro["id"])):
            continue
        registro["tipo"] = rotulo["tipo"]
        registro["sinais"] = {sinal: int(rotulo[sinal]) for sinal in SINAIS}
        if rotulo["veracidade"]:
            registro["veracidade"] = rotulo["veracidade"]
            registro["rotulo"] = ROTULO_POR_VERACIDADE[rotulo["veracidade"]]
        registro["origem_rotulo"] = "equipe"
        if rotulo["tipo"] == "fora_escopo":
            registro["split"] = registro["split_produto"] = "fora"
        aplicados += 1
    return aplicados


# Dataset de verdadeiros confiáveis (#6, doc/dataset-verdadeiras.md): matérias de portal que
# passam nos filtros, de veículos aprovados na auditoria manual, viram `portal_verificado`.
VEICULOS_VERIFICADOS = RAIZ / "anotacoes" / "veiculos-verificados.csv"
AUDITORIA_VERDADEIRAS = RAIZ / "anotacoes" / "auditoria-verdadeiras.csv"
# Seções que não são notícia factual: opinião, vídeo, ao vivo, publicidade, entrevista.
SECOES_FORA = re.compile(
    r"/(opiniao|colunas?|colunistas?|blogs?|videos?|ao-vivo|podcasts?|publieditorial|"
    r"patrocinado|conteudo-patrocinado|especial-publicitario|editorial|artigos?|analise|"
    r"entrevistas?|charges?)/"
)
TITULO_FORA = re.compile(r"^\s*(ao vivo|opinião|análise|artigo|editorial|entrevista)\b", re.I)
# Matéria que relata a fala de alguém: a matéria pode estar certa e a afirmação, falsa.
RELATA_FALA = re.compile(
    r"\b(diz|dizem|disse|afirma|afirmam|afirmou|declara|declarou|alega|alegou|garante|"
    r"defende|nega|negou|critica|acusa|acusou|admite|avalia|aponta|cobra|promete|"
    r"prometeu|ataca|rebate|sugere|insinua|classifica)\b"
    r"|(^|[,;:]\s*)segundo\b",  # "Segundo a PF, ...", mas não "em segundo turno"
    re.I,
)
ASPAS = re.compile(r"[\"“”«»]|‘[^’]+’|'[^']+'(?!\w)")


def motivo_filtro_portal(registro: dict) -> str | None:
    """Por que a matéria de portal não serve como verdadeiro confiável; None se passa."""
    titulo = (registro.get("texto_curto") or "").strip()
    if not titulo:
        return "sem título"
    url = (registro.get("url") or "").lower()
    if SECOES_FORA.search(url) or "youtu" in url or TITULO_FORA.search(titulo):
        return "opinião, vídeo, ao vivo ou publicidade"
    if titulo.endswith("?"):
        return "pergunta"
    if RELATA_FALA.search(titulo) or ASPAS.search(titulo):
        return "relata fala"
    return None


def verificar_portais(
    registros: list[dict],
    veiculos: Path = VEICULOS_VERIFICADOS,
    auditoria: Path = AUDITORIA_VERDADEIRAS,
) -> dict[str, int]:
    """Marca `portal_verificado` nas matérias que passam nos filtros, de veículo aprovado.

    Os veículos aprovados vêm de auditar_verdadeiras.py (`aceito=1`); sem esse arquivo,
    nenhuma matéria vira verificada. Itens que a auditoria achou com problema ficam `portal`.
    """
    if not veiculos.exists():
        return {}
    with open(veiculos, encoding="utf-8", newline="") as entrada:
        aprovados = {linha["fonte"] for linha in csv.DictReader(entrada) if linha["aceito"] == "1"}
    com_problema = set()
    if auditoria.exists():
        with open(auditoria, encoding="utf-8", newline="") as entrada:
            com_problema = {
                linha["id"] for linha in csv.DictReader(entrada) if linha["problema"] != "nenhum"
            }
    motivos: dict[str, int] = {}
    for registro in registros:
        if registro["origem_rotulo"] != "portal" or registro["base"] != "verdadeiras":
            continue
        motivo = motivo_filtro_portal(registro)
        if motivo is None and registro["fonte"] not in aprovados:
            motivo = "veículo não aprovado"
        if motivo is None and registro["id"] in com_problema:
            motivo = "problema na auditoria"
        if motivo is None:
            registro["origem_rotulo"] = "portal_verificado"
            motivo = "verificado"
        motivos[motivo] = motivos.get(motivo, 0) + 1
    return motivos


def definir_split(base: str, grupo: str) -> str:
    """Treino ou validação para as bases de treino; teste para as demais.

    O sorteio da validação é determinístico (hash do grupo) e por grupo: no Fake.br o
    grupo é o par, para as duas notícias do mesmo assunto ficarem do mesmo lado.
    """
    if base not in BASES_TREINO:
        return "teste"
    return "validacao" if sorteio_validacao(grupo) else "treino"


def dominio(url: str) -> str | None:
    achado = re.search(r"https?://(?:www\d?\.)?([^/]+)", url or "")
    return achado[1] if achado else None


def ler_fakebr():
    """Textos de size_normalized_texts/, a versão que o corpus recomenda para treino: em cada
    par, o texto mais longo é cortado no tamanho do mais curto, o que tira o atalho de
    tamanho. Os metadados só existem em full_texts/ e as métricas descrevem o texto completo.

    A numeração das duas versões é a mesma, salvo dois pares: 586 e 1607 só existem em
    full_texts/ e 697 e 1468 só em size_normalized_texts/, sem metadados. Ficam de fora.
    """
    base = RAW / "Fake.br-Corpus" / "size_normalized_texts"
    pasta_meta = RAW / "Fake.br-Corpus" / "full_texts"
    for rotulo in ("fake", "true"):
        pasta = base / rotulo
        for arq in sorted(pasta.glob("*.txt"), key=lambda p: int(p.stem)):
            meta = pasta_meta / f"{rotulo}-meta-information" / f"{arq.stem}-meta.txt"
            if not meta.exists():
                continue
            linhas = meta.read_text(encoding="utf-8-sig").split("\n")
            autor, url, categoria, data_bruta = (linha.strip() for linha in linhas[:4])
            metricas = {
                nome: None if valor == "None" else float(valor)
                for nome, valor in zip(METRICAS_FAKEBR, linhas[4:25])
            }
            yield {
                "id": f"fakebr-{rotulo}-{arq.stem}",
                "base": "fakebr",
                "fonte": dominio(url),
                "rotulo": rotulo,
                "titulo": None,
                "texto": arq.read_text(encoding="utf-8-sig").strip(),
                "texto_curto": None,
                "categoria": categoria,
                "data": parse_data(data_bruta),
                "autor": None if autor in ("", "None") else autor,
                "url": url,
                "par_id": int(arq.stem),
                "metricas": metricas,
                "split": definir_split("fakebr", f"fakebr-par-{arq.stem}"),
            }


def ler_boatos():
    """Checagens coletadas por pesquisa/dados/coletar_boatos.py.

    São as URLs do Boatos.org no FakeRecogna (2019–2021), que formam a parte falsa do
    FakeRecogna reconstruído. Boatos mais recentes não são coletados: falsos recentes já vêm
    da Fact Check API, e o que falta para o equilíbrio são verdadeiros.
    """
    arquivo = RAW / "boatos" / "boatos.jsonl"
    if not arquivo.exists():
        print("pesquisa/data/raw/boatos/boatos.jsonl não encontrado; rode pesquisa/dados/coletar_boatos.py")
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        # No layout antigo, a alegação "Boato – ..." já é a mensagem inteira.
        texto = r.get("texto_boato") or r.get("alegacao")
        if r.get("status") != 200 or not texto or r["origem"] != "fakerecogna":
            continue
        if any(secao in r["url"] for secao in ("/english/", "/espanol/", "/lista/")):
            continue
        base = "fakerecogna"
        identificador = "boatos-" + r["url"].rsplit("/", 1)[-1].removesuffix(".html")
        yield {
            "id": identificador,
            "base": base,
            "fonte": "boatos.org",
            "rotulo": "fake",
            "titulo": r.get("alegacao"),
            "texto": texto,
            "texto_curto": r.get("alegacao"),
            "categoria": r.get("categoria"),
            "data": r.get("data"),
            "autor": None,
            "url": r["url"],
            "par_id": None,
            "metricas": None,
            "split": definir_split(base, identificador),
        }


SUFIXO_PORTAL = re.compile(r"\s*\|\s*[^|]{1,30}$")


def ler_noticias():
    """Verdadeiras do FakeRecogna, recoletadas por pesquisa/dados/coletar_noticias.py (treino)."""
    arquivo = RAW / "noticias" / "noticias.jsonl"
    if not arquivo.exists():
        print("pesquisa/data/raw/noticias/noticias.jsonl não encontrado; rode pesquisa/dados/coletar_noticias.py")
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        if r.get("status") != 200 or not r.get("texto"):
            continue
        identificador = "noticia-" + hashlib.sha1(r["url"].encode()).hexdigest()[:12]
        # O título da página do G1 termina com "| G1": tirado, senão o nome do portal vira
        # pista do rótulo (nenhuma falsa termina assim).
        titulo = SUFIXO_PORTAL.sub("", r.get("titulo") or "") or None
        yield {
            "id": identificador,
            "base": "fakerecogna",
            "fonte": r["dominio"],
            "rotulo": "true",
            "titulo": titulo,
            "texto": r["texto"],
            "texto_curto": titulo,
            "categoria": r.get("categoria"),
            "data": r.get("data") or parse_data(r.get("data_fakerecogna") or ""),
            "autor": None,
            "url": r["url"],
            "par_id": None,
            "metricas": None,
            "split": definir_split("fakerecogna", identificador),
        }


def ler_faketrue():
    """FakeTrue.Br: pares de falsa (Boatos.org) e verdadeira (G1, Folha, UOL) do mesmo assunto.

    O texto vem da origem em minúsculas, sem hífens e com alguns números corrompidos. Só a
    falsa tem título (a alegação); a verdadeira é só o corpo da matéria. A data sai da URL
    da verdadeira (/AAAA/MM/DD/) e vale para o par: a URL da falsa quase nunca tem data.
    """
    arquivo = RAW / "FakeTrue.Br" / "FakeTrueBr_corpus.csv"
    if not arquivo.exists():
        print("pesquisa/data/raw/FakeTrue.Br/ não encontrado; rode pesquisa/dados/baixar_dados.sh")
        return
    with open(arquivo, encoding="utf-8", newline="") as f:
        for par, r in enumerate(csv.DictReader(f)):
            m = re.search(r"/(20\d\d)/(\d\d)/(\d\d)/", r["link_t"])
            data = parse_data("-".join(m.groups())) if m else None
            comum = {"categoria": None, "data": data, "autor": None, "par_id": par, "metricas": None}
            yield {
                **comum,
                "id": f"faketrue-fake-{par}",
                "base": "faketrue",
                "fonte": dominio(r["link_f"]),
                "rotulo": "fake",
                "titulo": r["title_fake"].strip() or None,
                "texto": r["fake"].strip(),
                "texto_curto": r["title_fake"].strip() or None,
                "url": r["link_f"],
                "split": definir_split("faketrue", f"faketrue-par-{par}"),
            }
            yield {
                **comum,
                "id": f"faketrue-true-{par}",
                "base": "faketrue",
                "fonte": dominio(r["link_t"]),
                "rotulo": "true",
                "titulo": None,
                "texto": r["true"].strip(),
                "texto_curto": None,
                "url": r["link_t"],
                "split": definir_split("faketrue", f"faketrue-par-{par}"),
            }


def ler_factcheck():
    """Alegações checadas pela Google Fact Check API (pesquisa/dados/coletar_factcheck.py)."""
    arquivo = RAW / "factcheck" / "checagens.jsonl"
    if not arquivo.exists():
        print("pesquisa/data/raw/factcheck/checagens.jsonl não encontrado; rode pesquisa/dados/coletar_factcheck.py")
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        veredito = normalizar_veredito(r.get("veredito"))
        veracidade = veracidade_do_veredito(veredito)
        if not veracidade or not r.get("alegacao"):
            continue
        ano_url = re.search(r"/(20\d\d)/", r["url"])
        data = r.get("data_checagem") or r.get("data_alegacao") or (f"{ano_url[1]}-01-01" if ano_url else None)
        yield {
            "id": "factcheck-" + hashlib.sha1(r["url"].encode()).hexdigest()[:12],
            "base": "factcheck",
            "fonte": r.get("site_agencia"),
            "rotulo": ROTULO_POR_VERACIDADE[veracidade],
            "veracidade": veracidade,
            "veredito_original": veredito,
            "titulo": None,
            "texto": r["alegacao"],
            "texto_curto": r["alegacao"],
            "categoria": None,
            "data": data,
            "autor": r.get("autor_alegacao"),
            "url": r["url"],
            "par_id": None,
            "metricas": None,
            "split": definir_split("factcheck", r["url"]),
        }


def ler_fakenewsbr():
    """FakenewsBR v6 (variante pública), só das sub-bases em FAKENEWSBR_INCLUIR.

    Nas sub-bases de agência, as verdadeiras só entram com veredito: são alegações
    checadas, do mesmo gênero de texto das falsas, ao contrário das matérias de portal. Nas
    mensagens anotadas (FAKENEWSBR_MENSAGENS), entram as duas classes, sem veredito.
    """
    arquivo = RAW / "FakenewsBR_v6_public.csv"
    if not arquivo.exists():
        print("pesquisa/data/raw/FakenewsBR_v6_public.csv não encontrado; rode pesquisa/dados/baixar_dados.sh")
        return
    with open(arquivo, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["dataset_name"] not in FAKENEWSBR_INCLUIR:
                continue
            veredito = normalizar_veredito(r["factcheck_rating"])
            if r["label"] == "fake":
                veracidade = veracidade_do_veredito(veredito) if veredito else "falso"
                if veracidade == "verdadeiro":  # rótulo e veredito em conflito
                    continue
            elif r["label"] == "true" and r["dataset_name"] in FAKENEWSBR_MENSAGENS:
                veracidade = "verdadeiro"
            elif r["label"] == "true":
                veracidade = veracidade_do_veredito(veredito)
                if veracidade != "verdadeiro":
                    continue
            else:
                continue
            if not veracidade:
                continue
            texto = (r["text_no_url"] or r["text"]).strip()
            if not texto:
                continue
            data = r["date_iso"] or None
            yield {
                "id": f"fakenewsbr-{r['rid']}",
                "base": "fakenewsbr",
                "fonte": dominio(r["url_review"]) or r["dataset_name"],
                "rotulo": ROTULO_POR_VERACIDADE[veracidade],
                "veracidade": veracidade,
                "veredito_original": veredito,
                "titulo": None,
                "texto": texto,
                # Nas sub-bases de agência o texto já é a alegação curta; nas de mensagens, não.
                "texto_curto": texto if r["source_type"] == "news" else None,
                "categoria": None,
                "data": data,
                "autor": r["factcheck_claimant"] or None,
                "url": r["url_review"] or None,
                "par_id": None,
                "metricas": None,
                "split": definir_split("fakenewsbr", f"fakenewsbr-{r['rid']}"),
            }


def ler_verdadeiras():
    """CSV próprio de matérias de portais (pesquisa/dados/coletar_verdadeiras.py)."""
    arquivo = RAW / "verdadeiras" / "verdadeiras.csv"
    if not arquivo.exists():
        print("pesquisa/data/raw/verdadeiras/verdadeiras.csv não encontrado; rode pesquisa/dados/coletar_verdadeiras.py")
        return
    with open(arquivo, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            yield {
                "id": f"verdadeira-{r['id']}",
                "base": "verdadeiras",
                "fonte": dominio(r["url"]),
                "rotulo": "true",
                "titulo": r["titulo"],
                "texto": r["texto"],
                "texto_curto": r["titulo"],
                "categoria": r["linha_editorial"],
                "data": r["data"] or None,
                "autor": None,
                "url": r["url"],
                "par_id": None,
                "metricas": None,
                "split": definir_split("verdadeiras", r["id"]),
            }


# Ordem de prioridade na deduplicação: as bases pareadas primeiro (Fake.br, o FakeRecogna,
# que está dentro de ler_boatos e ler_noticias, e o FakeTrue.Br, cujas falsas repetem
# parte do FakeRecogna), depois as checagens e os portais.
LEITORES = (
    ler_fakebr, ler_boatos, ler_noticias, ler_faketrue, ler_factcheck, ler_fakenewsbr,
    ler_verdadeiras,
)


def chave_url(url: str | None) -> str | None:
    if not url:
        return None
    return re.sub(r"^https?://(www\d?\.)?", "", url.strip().lower()).rstrip("/")


def chave_texto(texto: str) -> str:
    return re.sub(r"[^a-z0-9à-ü]+", "", texto.lower())[:120]


# Quase-duplicatas: o mesmo boato é checado de novo anos depois, com outras palavras, e
# escapa da chave exata acima. MinHash com LSH sobre trigramas de palavras do texto curto
# (ou do início do texto) acha os candidatos; a similaridade de Jaccard confirma.
PALAVRAS_QUASE_DUPLICATA = 40
JACCARD_QUASE_DUPLICATA = 0.6
BANDAS, LINHAS_POR_BANDA = 8, 4
_PRIMO = (1 << 61) - 1
_PERMUTACOES = [
    (int(hashlib.sha1(f"a{i}".encode()).hexdigest(), 16) % _PRIMO | 1,
     int(hashlib.sha1(f"b{i}".encode()).hexdigest(), 16) % _PRIMO)
    for i in range(BANDAS * LINHAS_POR_BANDA)
]
# Ordem dos splits: um registro que repete outro de um split anterior sai do seu.
ORDEM_SPLIT = {"treino": 0, "validacao": 1}


def trigramas(registro: dict) -> frozenset[int]:
    texto = registro["texto_curto"] or registro["texto"]
    palavras = re.findall(r"[a-z0-9à-ü]+", texto.lower())[:PALAVRAS_QUASE_DUPLICATA]
    if len(palavras) < 3:
        return frozenset()
    return frozenset(
        zlib.crc32(" ".join(palavras[i:i + 3]).encode()) for i in range(len(palavras) - 2)
    )


def grupos_quase_duplicatas(registros: list[dict]) -> list[int]:
    """Devolve, para cada registro, o índice do representante do seu grupo (union-find)."""
    pai = list(range(len(registros)))

    def raiz(i: int) -> int:
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    conjuntos = [trigramas(r) for r in registros]
    baldes: dict[tuple, int] = {}
    for i, sh in enumerate(conjuntos):
        if not sh:
            continue
        assinatura = [min((a * h + b) % _PRIMO for h in sh) for a, b in _PERMUTACOES]
        for banda in range(BANDAS):
            chave = (banda, *assinatura[banda * LINHAS_POR_BANDA:(banda + 1) * LINHAS_POR_BANDA])
            primeiro = baldes.setdefault(chave, i)
            if primeiro == i or raiz(primeiro) == raiz(i):
                continue
            outro = conjuntos[primeiro]
            if len(sh & outro) / len(sh | outro) >= JACCARD_QUASE_DUPLICATA:
                pai[raiz(i)] = raiz(primeiro)
    return [raiz(i) for i in range(len(registros))]


def remover_vazamento(registros: list[dict]) -> dict[str, int]:
    """Tira do split posterior quem repete, quase igual, um registro de treino ou validação.

    Mover para o treino quebraria a ordem temporal, então o registro posterior sai: vira
    `fora` no protocolo B e no A. Entre os splits de teste, repetir não vaza nada.
    """
    grupos = grupos_quase_duplicatas(registros)
    removidos = {"split": 0, "split_produto": 0}
    for protocolo in removidos:
        primeiro_split: dict[int, int] = {}
        for grupo, registro in zip(grupos, registros):
            ordem = ORDEM_SPLIT.get(registro[protocolo], 2)
            primeiro_split[grupo] = min(primeiro_split.get(grupo, 2), ordem)
        for grupo, registro in zip(grupos, registros):
            ordem = ORDEM_SPLIT.get(registro[protocolo], 2)
            if registro[protocolo] != "fora" and ordem > primeiro_split[grupo]:
                registro[protocolo] = "fora"
                removidos[protocolo] += 1
    return removidos


SPLITS_PRODUTO = ("treino", "validacao", "teste")
# Em validação e teste entram todos os enganosos e todos os verdadeiros, e falsos até esta
# proporção do número de enganosos.
PROPORCAO_AVALIACAO = 1.5


def equilibrar(registros: list[dict]) -> dict[str, int]:
    """Equilibra as classes do protocolo B; o que sobra vira `reserva`.

    1. FakenewsBR, sub-bases de agência: entram os enganosos e os verdadeiros checados, e
       só uma amostra dos falsos de cada agência, até o maior entre os enganosos e os
       verdadeiros dela no split. Sem nenhum falso, a agência viraria pista de "não é falso".
    2. Portais (`origem_rotulo=portal`): saem do protocolo B. O "verdadeiro" deles é
       suposição, então não completam os verdadeiros (#6, #7).
    3. Treino: todos os falsos, enganosos e verdadeiros que sobram. Os verdadeiros ficam
       abaixo dos falsos; os pesos por classe no treino compensam.
    4. Validação e teste: todos os enganosos e os verdadeiros; falsos até
       PROPORCAO_AVALIACAO vezes os enganosos.
    5. Portais verificados (#6): completam os verdadeiros de cada split até o número de
       falsos; o que passa disso vira reserva.
    A amostra é determinística (ordem pelo hash do id), para o dataset ser reproduzível. O
    hash leva um prefixo próprio: sem ele, a ordem repetiria o sorteio do split (no
    FakeRecogna o grupo é o próprio id), e os registros de validação e teste, que têm hash
    alto, seriam sempre os últimos da fila e os primeiros a sair.
    `reserva` não é dado ruim: é o que fica de fora para manter o equilíbrio.
    """
    ativos = sorted(
        (r for r in registros if r["split_produto"] in SPLITS_PRODUTO),
        key=lambda r: hashlib.sha1(f"equilibrio-{r['id']}".encode()).hexdigest(),
    )
    reserva: dict[str, int] = {}

    def guardar(registro: dict, motivo: str):
        registro["split_produto"] = "reserva"
        reserva[motivo] = reserva.get(motivo, 0) + 1

    def de_agencia(r: dict) -> bool:
        return r["base"] == "fakenewsbr" and r["fonte"] not in FAKENEWSBR_MENSAGENS

    for r in ativos:
        if r["origem_rotulo"] == "portal":
            guardar(r, "portais (fora do dataset selecionado)")
    ativos = [r for r in ativos if r["split_produto"] != "reserva"]

    por_agencia: dict[tuple, int] = {}
    for r in ativos:
        if de_agencia(r):
            chave = (r["split_produto"], r["fonte"], r["veracidade"])
            por_agencia[chave] = por_agencia.get(chave, 0) + 1
    usados: dict[tuple, int] = {}
    for r in ativos:
        if de_agencia(r) and r["veracidade"] == "falso":
            chave = (r["split_produto"], r["fonte"])
            limite = max(por_agencia.get((*chave, "enganoso"), 0), por_agencia.get((*chave, "verdadeiro"), 0))
            if usados.get(chave, 0) >= limite:
                guardar(r, "falsos de agência da FakenewsBR")
            else:
                usados[chave] = usados.get(chave, 0) + 1

    for split in SPLITS_PRODUTO:
        do_split = [r for r in ativos if r["split_produto"] == split]
        falsos = [r for r in do_split if r["veracidade"] == "falso"]
        enganosos = [r for r in do_split if r["veracidade"] == "enganoso"]
        if split != "treino":
            for r in falsos[int(PROPORCAO_AVALIACAO * len(enganosos)):]:
                guardar(r, f"{split}: falso")
            falsos = falsos[: int(PROPORCAO_AVALIACAO * len(enganosos))]
        verificados = [r for r in do_split if r["origem_rotulo"] == "portal_verificado"]
        outros_verdadeiros = sum(
            r["veracidade"] == "verdadeiro" and r["origem_rotulo"] != "portal_verificado"
            for r in do_split
        )
        for r in verificados[max(len(falsos) - outros_verdadeiros, 0):]:
            guardar(r, f"{split}: portal verificado além dos falsos")
    return reserva


def main():
    if not RAW.exists():
        sys.exit("pesquisa/data/raw/ não encontrado. Rode antes: bash pesquisa/dados/baixar_dados.sh")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    registros, repetidos = [], {}
    urls_vistas, textos_vistos = set(), set()
    for leitor in LEITORES:
        for registro in leitor():
            url, texto = chave_url(registro["url"]), chave_texto(registro["texto"])
            # No Fake.br várias notícias compartilham a URL da página inicial do site,
            # então ali só o texto conta para achar repetição.
            ja_visto = texto in textos_vistos or (
                url in urls_vistas and registro["base"] != "fakebr"
            )
            if ja_visto:
                repetidos[registro["base"]] = repetidos.get(registro["base"], 0) + 1
                continue
            textos_vistos.add(texto)
            if url and registro["base"] != "fakebr":
                urls_vistas.add(url)
            if "veracidade" not in registro:  # bases sem veredito de agência
                registro["veracidade"] = VERACIDADE_POR_ROTULO[registro["rotulo"]]
                registro["veredito_original"] = None
            registro["tipo_sugerido"] = TIPO_POR_VEREDITO.get(registro["veredito_original"])
            registro["origem_rotulo"] = origem_rotulo(registro)
            registro["split_produto"] = definir_split_produto(registro)
            registro["tipo"] = registro["sinais"] = None
            registros.append(registro)
    portais = verificar_portais(registros)
    anotados = aplicar_anotacoes(registros)
    removidos = remover_vazamento(registros)
    reserva = equilibrar(registros)
    contagem, com_curto = {}, {}
    with open(SAIDA, "w", encoding="utf-8", newline="\n") as out:
        for registro in registros:
            out.write(json.dumps(registro, ensure_ascii=False) + "\n")
            for protocolo in ("split", "split_produto"):
                chave = (protocolo, registro[protocolo], registro["veracidade"])
                contagem[chave] = contagem.get(chave, 0) + 1
                if registro["texto_curto"]:
                    com_curto[chave] = com_curto.get(chave, 0) + 1
    for protocolo, nome in (("split", "A (referência)"), ("split_produto", "B (produto)")):
        print(f"Protocolo {nome}:            total  com texto_curto")
        for (prot, split, veracidade), n in sorted(contagem.items()):
            if prot == protocolo:
                print(f"  {split:15} {veracidade:10} {n:6} {com_curto.get((prot, split, veracidade), 0):6}")
    print("matérias de portal (portal_verificado, ou o motivo de ficar fora):", portais)
    print("anotados pela equipe (origem_rotulo=equipe):", anotados)
    print("repetidos descartados por base:", repetidos)
    print("quase-duplicatas de treino/validação tiradas dos splits posteriores:", removidos)
    print("reserva (fora do protocolo B só pelo equilíbrio):", reserva)
    print(f"Gerado {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
