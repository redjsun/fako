"""Conjunto de avaliação no formato do jogo: notícias recentes pelo mesmo caminho da importação.

Uso:
    python -m app.jobs.coletar_avaliacao [--provedores factcheck,boatos,gnews,agenciabrasil]
        [--quantidade 100] [--desde 2026-10-07] > avaliacao.jsonl

Cada provedor traz até `quantidade` notícias publicadas a partir de `desde` (o dia seguinte ao
fim do dataset de treino, para o modelo não ser medido no que já viu). Passam pela mesma
normalização, pelos mesmos descartes e pela mesma extração de afirmação da importação
(services/noticias_service.py). Nada vai para o banco: cada notícia vira uma linha JSON na
saída, com a manchete (o `statement` do jogo), a primeira afirmação extraída (o `claim_text`),
a `veracidade` em três níveis e o gabarito binário (`is_true`). As checagens enganosas, que a
importação descarta (o jogo é binário, decisão 01 em aberto), entram aqui com
`is_true` falso, como "não é verdade"; as de veredito ambíguo ficam de fora. A medição fica em
pesquisa/ml/avaliar_jogo.py.

A extração usa a LLM de LLM_* (LLM_PROVIDER=openai); sem ela, `afirmacao` sai vazia.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date, datetime, timezone

from app.core.config import get_settings
from app.integrations.noticias_client import (
    NoticiasClient,
    NoticiasIndisponiveis,
    get_noticias_clients,
)
from app.ml.llm import LLMClient, LLMIndisponivel, RespostaInvalida, get_llm_client
from app.ml.normalizacao import motivo_descarte, normalizar_manchete, veracidade_pelo_veredito
from app.services.noticias_service import motivo

PROVEDORES = "factcheck,boatos,gnews,agenciabrasil"
DESDE = date(2026, 10, 7)  # o dataset de treino vai até 06/10/2026


def afirmacoes(llm: LLMClient, manchete: str) -> list[str] | None:
    """As afirmações extraídas, como na importação; None se a LLM falhou."""
    try:
        return [a.texto for a in llm.extrair_afirmacoes(manchete).afirmacoes]
    except (LLMIndisponivel, RespostaInvalida):
        return None


def veracidade(noticia) -> str | None:
    if noticia.veredito is None:
        return "verdadeiro"  # manchete publicada, como na importação
    return veracidade_pelo_veredito(noticia.veredito)


def descarte_da_avaliacao(noticia, manchete: str) -> str | None:
    """O descarte da importação, menos o de veredito enganoso."""
    if noticia.veredito and veracidade(noticia) == "enganoso":
        sem_politica = get_settings().noticias_sem_politica
        return motivo_descarte(manchete, noticia.url, checagem=True, sem_politica=sem_politica)
    return motivo(noticia, manchete)


def coletar(
    provedores: dict[str, NoticiasClient],
    llm: LLMClient,
    quantidade: int,
    desde: date,
    avisar=lambda mensagem: None,
) -> tuple[list[dict], dict[str, int]]:
    """As linhas de avaliação e a contagem de descartes por motivo."""
    linhas, descartes, vistas = [], {}, set()
    coletada_em = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for nome, cliente in provedores.items():
        try:
            noticias = cliente.buscar(quantidade)
        except NoticiasIndisponiveis as erro:
            avisar(f"{nome}: {erro.message}")
            continue
        for noticia in noticias:
            manchete = normalizar_manchete(
                noticia.titulo, None if noticia.veredito else noticia.veiculo
            )
            if noticia.publicada_em and noticia.publicada_em.date() < desde:
                descarte = "anterior ao treino"
            elif noticia.url in vistas or manchete.casefold() in vistas:
                descarte = "repetida"
            else:
                descarte = descarte_da_avaliacao(noticia, manchete)
            if descarte:
                descartes[descarte] = descartes.get(descarte, 0) + 1
                continue
            vistas.update({noticia.url, manchete.casefold()})
            extraidas = afirmacoes(llm, manchete)
            linhas.append(
                {
                    "id": hashlib.sha1(noticia.url.encode()).hexdigest()[:16],
                    "provedor": nome,
                    "url": noticia.url,
                    "veiculo": noticia.veiculo,
                    "publicada_em": noticia.publicada_em.isoformat()
                    if noticia.publicada_em
                    else None,
                    "veredito": noticia.veredito,
                    "veracidade": veracidade(noticia),
                    "is_true": veracidade(noticia) == "verdadeiro",
                    "manchete": manchete,
                    "afirmacao": extraidas[0] if extraidas else None,
                    "n_afirmacoes": None if extraidas is None else len(extraidas),
                    "coletada_em": coletada_em,
                }
            )
            avisar(f"{nome}: {len(linhas)} {manchete[:70]}")
    return linhas, descartes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--provedores", default=PROVEDORES)
    parser.add_argument("--quantidade", type=int, default=100, help="notícias por provedor")
    parser.add_argument("--desde", type=date.fromisoformat, default=DESDE)
    args = parser.parse_args()
    nomes = [n.strip() for n in args.provedores.split(",") if n.strip()]
    provedores = {}
    for nome in nomes:
        try:
            [provedores[nome]] = get_noticias_clients(nome)
        except NoticiasIndisponiveis as erro:
            print(f"{nome}: {erro.message}", file=sys.stderr)
    linhas, descartes = coletar(
        provedores,
        get_llm_client(),
        args.quantidade,
        args.desde,
        avisar=lambda mensagem: print(mensagem, file=sys.stderr),
    )
    for linha in linhas:
        print(json.dumps(linha, ensure_ascii=False))
    por_veracidade = Counter(linha["veracidade"] for linha in linhas)
    sem_afirmacao = sum(linha["afirmacao"] is None for linha in linhas)
    print(
        f"{len(linhas)} notícias {dict(por_veracidade)}, "
        f"{sem_afirmacao} sem afirmação extraída; descartadas: {descartes}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
