"""Importação diária de notícias dos provedores de NOTICIAS_PROVIDER (ex.: factcheck,gnews).

Uso: python -m app.jobs.importar_noticias [--quantidade N]

Traz até NOTICIAS_POR_DIA (50) notícias, metade falsas e metade verdadeiras no máximo (um lado
curto não é completado com o outro), publicadas dentro da janela de retenção
(NOTICIAS_RETENCAO_DIAS), com a mesma normalização, filtros e deduplicação de
`POST /admin/news/import`. Entram como rascunho ou, com NOTICIAS_PUBLICAR_DIRETO, já
validadas. Agendada em api/crontab (serviço agendador-api).
"""

import argparse
import math
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.integrations.noticias_client import NoticiasIndisponiveis, get_noticias_clients
from app.ml.classificador import get_classificador
from app.ml.llm import get_llm_client
from app.services.noticias_service import NoticiasService


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quantidade", type=int, default=settings.noticias_por_dia)
    args = parser.parse_args()
    try:
        with SessionLocal.begin() as db:
            service = NoticiasService(
                db, get_noticias_clients(), get_classificador(), get_llm_client()
            )
            resultado = service.importar_lote(
                settings.noticias_categoria,
                args.quantidade,
                max_idade_dias=settings.noticias_retencao_dias,
                por_lado=math.ceil(args.quantidade / 2),
            )
    except NoticiasIndisponiveis as erro:
        sys.exit(f"Importação de notícias falhou: {erro.message}")
    falsas = sum(not q.is_true for q in resultado.imported)
    print(
        f"{len(resultado.imported)} notícias importadas ({falsas} falsas, "
        f"{len(resultado.imported) - falsas} verdadeiras), {len(resultado.discarded)} descartadas"
    )


if __name__ == "__main__":
    main()
