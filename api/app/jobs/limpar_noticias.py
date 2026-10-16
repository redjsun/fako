"""Limpeza diária das notícias importadas há mais de NOTICIAS_RETENCAO_DIAS (30) dias.

Uso: python -m app.jobs.limpar_noticias [--dias N]

Apaga as que ninguém respondeu; as que algum jogador respondeu, ou que estão em jogo numa
partida, são arquivadas (saem do jogo e ficam para o histórico). Agendada em api/crontab.
"""

import argparse

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ml.classificador import FakeClassificador
from app.services.noticias_service import NoticiasService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dias", type=int, default=get_settings().noticias_retencao_dias)
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        # A limpeza não busca nem classifica notícias: provedores e classificador ficam de fora.
        limpeza = NoticiasService(db, [], FakeClassificador()).limpar(args.dias)
    print(f"{limpeza.apagadas} notícias apagadas, {limpeza.arquivadas} arquivadas")


if __name__ == "__main__":
    main()
