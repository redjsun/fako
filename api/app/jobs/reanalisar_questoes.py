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

Nas notícias, o "Por quê?" (`model_explanation`, a LLM explicando a avaliação do classificador)
é refeito junto com a análise, e também quando falta; as questões criadas à mão mantêm a
explicação delas.
"""

import argparse
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.ml.classificador import ClassificadorClient, ClassificadorIndisponivel, get_classificador
from app.ml.llm import LLMClient, get_llm_client
from app.models.question import Question, QuestionOrigin
from app.services.classificador_service import ClassificadorService
from app.services.noticias_service import (
    afirmacao_extraida,
    dados_da_explicacao,
    explicacao_didatica,
)

LOTE = 10  # questões por commit: uma queda no meio não desfaz o que já foi feito


def reanalisar(
    questoes: list[Question],
    classificador: ClassificadorClient,
    todas: bool,
    llm: LLMClient | None = None,
    salvar=lambda: None,
) -> tuple[int, int]:
    """Atualiza a análise (e a afirmação, se faltar); devolve (reanalisadas, extraídas)."""
    padronizado = classificador.texto_de_entrada != "original"
    servico = ClassificadorService(classificador)
    reanalisadas = extraidas = 0
    for posicao, question in enumerate(questoes, start=1):
        if posicao % LOTE == 0:
            salvar()
        nova_afirmacao = False
        if padronizado and llm is not None and not question.claim_text:
            question.claim_text = afirmacao_extraida(llm, question.statement)
            nova_afirmacao = question.claim_text is not None
            extraidas += nova_afirmacao
        refazer = todas or nova_afirmacao or question.model_version != classificador.versao
        noticia = question.origin == QuestionOrigin.NEWS
        if noticia and llm is not None and (refazer or not question.model_explanation):
            analise_jogo = servico.analise_do_jogo(question.statement, question.claim_text)
            if analise_jogo is not None:
                question.model_explanation = explicacao_didatica(
                    llm, dados_da_explicacao(question, analise_jogo)
                )
        if not refazer:
            continue
        entrada = question.claim_text if padronizado and question.claim_text else question.statement
        analise = classificador.analisar(entrada, "admin", enunciado=question.statement)
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
        with SessionLocal() as db:
            questoes = list(db.scalars(select(Question).order_by(Question.id)))
            reanalisadas, extraidas = reanalisar(
                questoes, classificador, args.todas, get_llm_client(), salvar=db.commit
            )
            db.commit()
    except ClassificadorIndisponivel as erro:
        sys.exit(f"Classificador indisponível: {erro}")
    print(
        f"{reanalisadas} de {len(questoes)} questões reanalisadas com {classificador.versao}; "
        f"{extraidas} ganharam a afirmação extraída"
    )


if __name__ == "__main__":
    main()
