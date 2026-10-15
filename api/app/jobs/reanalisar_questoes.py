"""Refaz a análise do classificador guardada nas questões, com o modelo publicado.

Uso: python -m app.jobs.reanalisar_questoes [--todas]

A importação grava a análise na questão (`model_category`, `model_score`, `model_confidence`,
`model_version`), que o admin vê na curadoria. Ao publicar outro modelo (make publicar), as
análises antigas continuam lá; este job refaz as que vieram de outra versão (`--todas` refaz
todas). Mesma entrada da importação: a afirmação extraída (`claim_text`) se o modelo foi
treinado no texto padronizado ou híbrido; senão, o enunciado.

Com um modelo padronizado ou híbrido, as questões sem `claim_text` (importadas quando o modelo
era do texto original, ou criadas à mão) ganham a afirmação extraída pela LLM, com o mesmo
prompt da importação, e são reanalisadas. É essa afirmação que o palpite do jogo usa. Sem LLM,
ficam sem ela e o classificador recebe o enunciado.
"""

import argparse
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.ml.classificador import ClassificadorClient, ClassificadorIndisponivel, get_classificador
from app.ml.llm import LLMClient, get_llm_client
from app.models.question import Question
from app.services.noticias_service import afirmacao_extraida


def reanalisar(
    questoes: list[Question],
    classificador: ClassificadorClient,
    todas: bool,
    llm: LLMClient | None = None,
) -> tuple[int, int]:
    """Atualiza a análise (e a afirmação, se faltar); devolve (reanalisadas, extraídas)."""
    padronizado = classificador.texto_de_entrada != "original"
    reanalisadas = extraidas = 0
    for question in questoes:
        nova_afirmacao = False
        if padronizado and llm is not None and not question.claim_text:
            question.claim_text = afirmacao_extraida(llm, question.statement)
            nova_afirmacao = question.claim_text is not None
            extraidas += nova_afirmacao
        if not (todas or nova_afirmacao or question.model_version != classificador.versao):
            continue
        entrada = question.claim_text if padronizado and question.claim_text else question.statement
        analise = classificador.analisar(entrada, "admin")
        question.model_category = analise.categoria
        question.model_score = analise.nota
        question.model_confidence = analise.confianca
        question.model_version = analise.versao_modelo
        reanalisadas += 1
    return reanalisadas, extraidas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--todas", action="store_true", help="refaz também as da versão atual")
    args = parser.parse_args()
    try:
        classificador = get_classificador()
        with SessionLocal.begin() as db:
            questoes = list(db.scalars(select(Question).order_by(Question.id)))
            reanalisadas, extraidas = reanalisar(
                questoes, classificador, args.todas, get_llm_client()
            )
    except ClassificadorIndisponivel as erro:
        sys.exit(f"Classificador indisponível: {erro}")
    print(
        f"{reanalisadas} de {len(questoes)} questões reanalisadas com {classificador.versao}; "
        f"{extraidas} ganharam a afirmação extraída"
    )


if __name__ == "__main__":
    main()
