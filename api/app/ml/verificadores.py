"""Proteções automáticas sobre o que a LLM escreve (#21). Cada uma devolve o motivo da recusa,
ou None se passou; quem chama descarta o item recusado.

- `verificar_explicacao`: toda instituição, nome, número ou link citado na explicação precisa
  estar na análise que a LLM recebeu; e a explicação de `incerto` diz que o modelo não tem
  certeza. É uma heurística: nomes são sequências de palavras com maiúscula fora do início da
  frase, e siglas.
- `verificar_reescrita`: a questão reescrita precisa ser parecida com a alegação original
  (similaridade de embeddings acima do limiar). Pega troca de assunto; não pega a inversão de
  sentido ("não atirou" e "atirou" ficam com similaridade 0,84 no bge-m3).
- `verificar_negacao`: recusa a reescrita que ganha ou perde uma negação ("não", "nunca"...),
  a inversão mais comum. As outras ficam para o classificador e para a amostra do admin.
"""

import re

from app.ml.embeddings import EmbeddingsClient, sem_acento, similaridade

LINK = re.compile(r"https?://\S+|www\.\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|gov|br)\b")
NUMERO = re.compile(r"\d+(?:[.,]\d+)*")
SIGLA = re.compile(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}\b")
# Palavras com maiúscula seguidas, com "de", "da", "do"... no meio: "Ministério da Saúde".
NOME = re.compile(
    r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+(?:\s+(?:(?:de|da|do|das|dos|e)\s+)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+)*"
)
INICIO_DE_FRASE = re.compile(r"(?:^|[.!?:;]\s+|[\"“(]\s*)$")
NEGACAO = re.compile(r"\b(?:nao|nunca|jamais|nem|nenhuma?|ninguem|tampouco)\b")
INCERTEZA = re.compile(
    r"certeza|incert|seguranca|nao (?:da|e possivel) (?:para )?(?:saber|afirmar|dizer)"
)


def nomes(texto: str) -> list[str]:
    """Nomes próprios e siglas; a primeira palavra da frase só conta se vier seguida de outra."""
    encontrados = []
    for achado in NOME.finditer(texto):
        nome = achado.group()
        if INICIO_DE_FRASE.search(texto[: achado.start()]):
            _, _, nome = nome.partition(" ")
            nome = re.sub(r"^(?:(?:de|da|do|das|dos|e)\s+)", "", nome)
        if nome:
            encontrados.append(nome)
    return encontrados + SIGLA.findall(texto)


def citados(texto: str) -> set[str]:
    sem_links = LINK.sub(" ", texto)
    return {*LINK.findall(texto), *NUMERO.findall(sem_links), *nomes(sem_links)}


def verificar_explicacao(explicacao: str, entrada: str, categoria: str) -> str | None:
    base = sem_acento(entrada)
    inventados = sorted(termo for termo in citados(explicacao) if sem_acento(termo) not in base)
    if inventados:
        return f"cita o que não está na análise: {', '.join(inventados)}"
    if categoria == "incerto" and not INCERTEZA.search(sem_acento(explicacao)):
        return "categoria incerto sem dizer que o modelo não tem certeza"
    return None


def verificar_reescrita(
    original: str, reescrita: str, embeddings: EmbeddingsClient, limiar: float
) -> str | None:
    valor = similaridade(embeddings, original, reescrita)
    if valor < limiar:
        return f"reescrita pouco parecida com a original (similaridade {valor:.2f} < {limiar})"
    return None


def verificar_negacao(original: str, reescrita: str) -> str | None:
    if bool(NEGACAO.search(sem_acento(original))) != bool(NEGACAO.search(sem_acento(reescrita))):
        return "a reescrita ganhou ou perdeu uma negação (possível inversão de sentido)"
    return None
