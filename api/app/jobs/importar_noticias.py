"""Importação diária de notícias dos provedores de NOTICIAS_PROVIDER (ex.: factcheck,gnews).

Uso: python -m app.jobs.importar_noticias [--quantidade N]

Traz até NOTICIAS_POR_DIA notícias publicadas dentro da janela de retenção
(NOTICIAS_RETENCAO_DIAS), com a mesma normalização, filtros e deduplicação de
`POST /admin/news/import`. Entram como rascunho ou, com NOTICIAS_PUBLICAR_DIRETO, já
validadas. Agendada em api/crontab (serviço agendador-api).
"""

import argparse
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.integrations.noticias_client import NoticiasIndisponiveis, get_noticias_clients
from app.ml.classificador import get_classificador
from app.services.noticias_service import NoticiasService


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quantidade", type=int, default=settings.noticias_por_dia)
    args = parser.parse_args()
    try:
        with SessionLocal.begin() as db:
            service = NoticiasService(db, get_noticias_clients(), get_classificador())
            resultado = service.importar_lote(
                settings.noticias_categoria, args.quantidade, settings.noticias_retencao_dias
            )
    except NoticiasIndisponiveis as erro:
        sys.exit(f"Importação de notícias falhou: {erro.message}")
    print(f"{len(resultado.imported)} notícias importadas, {len(resultado.discarded)} descartadas")


if __name__ == "__main__":
    main()
