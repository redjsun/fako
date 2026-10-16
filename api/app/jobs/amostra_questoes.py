"""Planilha de avaliação das questões geradas pela LLM, para a amostra do admin (#21).

Uso:
    python -m app.jobs.amostra_questoes sortear [--itens 50] [--semente 1] > amostra.csv
    python -m app.jobs.amostra_questoes medir < amostra.csv

- `sortear`: sorteia questões de origem `ai` (rascunhos e publicadas) e escreve em CSV a
  afirmação, o gabarito, a fonte e a explicação, com as colunas que o admin preenche:
  `gabarito_correto` e `reescrita_fiel` (0/1; a reescrita manteve o sentido da checagem) e
  `explicacao_com_fato_novo` (0/1; a explicação cita algo que não está na análise).
- `medir`: lê a planilha preenchida e mede a % de questões com erro (gabarito errado ou
  reescrita infiel) e de explicações com fato novo, com o intervalo de Wilson de 95%. Acima de
  5% de questões com erro, a publicação automática deve parar (#23, #27).
"""

import argparse
import csv
import math
import random
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.question import Question, QuestionOrigin

LIMITE_ERRO = 0.05
COLUNAS = (
    "question_id",
    "status",
    "statement",
    "is_true",
    "source",
    "explanation",
    "gabarito_correto",
    "reescrita_fiel",
    "explicacao_com_fato_novo",
    "observacao",
)


def linhas_da_amostra(questoes: list[Question], itens: int, semente: int) -> list[dict]:
    sorteadas = random.Random(semente).sample(questoes, min(itens, len(questoes)))
    return [
        {
            "question_id": q.id,
            "status": q.status.value,
            "statement": q.statement,
            "is_true": int(q.is_true),
            "source": q.source,
            "explanation": q.explanation,
            "gabarito_correto": "",
            "reescrita_fiel": "",
            "explicacao_com_fato_novo": "",
            "observacao": "",
        }
        for q in sorted(sorteadas, key=lambda q: q.id)
    ]


def wilson(sucessos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 1.0
    p = sucessos / total
    centro = (p + z * z / (2 * total)) / (1 + z * z / total)
    margem = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return max(0.0, centro - margem), min(1.0, centro + margem)


def medir(linhas: list[dict]) -> dict:
    def marcado(linha: dict, coluna: str) -> bool:
        return linha[coluna].strip() in ("0", "1")

    questoes = [
        linha
        for linha in linhas
        if marcado(linha, "gabarito_correto") and marcado(linha, "reescrita_fiel")
    ]
    com_erro = sum(
        linha["gabarito_correto"].strip() == "0" or linha["reescrita_fiel"].strip() == "0"
        for linha in questoes
    )
    explicacoes = [linha for linha in linhas if marcado(linha, "explicacao_com_fato_novo")]
    com_fato_novo = sum(linha["explicacao_com_fato_novo"].strip() == "1" for linha in explicacoes)
    return {
        "questoes": len(questoes),
        "com_erro": com_erro,
        "taxa_erro": com_erro / len(questoes) if questoes else None,
        "intervalo_erro": wilson(com_erro, len(questoes)),
        "explicacoes": len(explicacoes),
        "taxa_fato_novo": com_fato_novo / len(explicacoes) if explicacoes else None,
        "intervalo_fato_novo": wilson(com_fato_novo, len(explicacoes)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("acao", choices=("sortear", "medir"))
    parser.add_argument("--itens", type=int, default=50)
    parser.add_argument("--semente", type=int, default=1)
    args = parser.parse_args()

    if args.acao == "sortear":
        with SessionLocal() as db:
            questoes = list(
                db.scalars(select(Question).where(Question.origin == QuestionOrigin.AI))
            )
        escritor = csv.DictWriter(sys.stdout, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas_da_amostra(questoes, args.itens, args.semente))
        return

    resultado = medir(list(csv.DictReader(sys.stdin)))
    if resultado["taxa_erro"] is None:
        sys.exit("Nenhuma questão com gabarito_correto e reescrita_fiel preenchidos.")
    minimo, maximo = resultado["intervalo_erro"]
    print(
        f"questões com erro: {resultado['com_erro']}/{resultado['questoes']} "
        f"({resultado['taxa_erro']:.1%}, IC 95% {minimo:.1%} a {maximo:.1%})"
    )
    if resultado["taxa_fato_novo"] is not None:
        minimo, maximo = resultado["intervalo_fato_novo"]
        print(
            f"explicações com fato novo: {resultado['taxa_fato_novo']:.1%} de "
            f"{resultado['explicacoes']} (IC 95% {minimo:.1%} a {maximo:.1%})"
        )
    if resultado["taxa_erro"] > LIMITE_ERRO:
        print(f"Acima de {LIMITE_ERRO:.0%}: pausar a publicação automática.")


if __name__ == "__main__":
    main()
