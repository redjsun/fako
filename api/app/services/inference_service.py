"""Serviço de aplicação para orquestração da inferência com o BERTimbau.

Aplica limpeza de texto, executa os modelos através do BertimbauEngine,
organiza as saídas técnicas e traduz os resultados para a semântica educativa do FAKO.
"""

from __future__ import annotations

import logging

from app.integrations.bertimbau_engine import BertimbauEngine
from app.schemas.inference_schema import (
    AnalyzeResponse,
    EducationalAssessment,
    ModelMetadataResponse,
    ModelTargetResult,
)
from app.services.text_cleaner import limpar_texto

logger = logging.getLogger("fako.api.inference_service")

DISCLAIMER_TEXTO = (
    "Esta análise constitui uma estimativa estatística automatizada de modelos de "
    "linguagem (BERTimbau) para fins educativos e de reflexão crítica. Não representa "
    "comprovação factual definitiva nem verificação jornalística independente da "
    "veracidade da informação."
)

METHODOLOGY_NOTE = (
    "Aviso metodológico: Os escores softmax apresentados refletem as pontuações "
    "internas do classificador e NÃO constituem probabilidades estatisticamente calibradas."
)


class InferenceService:
    """Coordena a análise de afirmações e regras pedagógicas de negócio."""

    def __init__(self, engine: BertimbauEngine) -> None:
        self.engine = engine

    def analyze(self, raw_statement: str) -> AnalyzeResponse:
        """Executa a análise de confiabilidade de uma afirmação."""
        cleaned = limpar_texto(raw_statement)
        # Se a limpeza apagou todo o texto (ex: apenas uma URL), usa o texto original aparado
        statement_for_inference = cleaned if len(cleaned) >= 5 else raw_statement.strip()

        logger.debug("Executando inferência para: '%s'", statement_for_inference)
        raw_result = self.engine.predict(statement_for_inference)

        pred_y1 = raw_result["pred_y1"]
        probs_y1 = raw_result["probs_y1"]
        pred_y2 = raw_result["pred_y2"]
        probs_y2 = raw_result["probs_y2"]

        # 1. Estruturação técnica do classificador Y1
        label_y1 = "falso" if pred_y1 == 0 else "nao_falso"
        scores_y1 = {
            "falso": round(float(probs_y1[0]), 4),
            "nao_falso": round(float(probs_y1[1]), 4),
        }
        y1_result = ModelTargetResult(
            target="Y1",
            target_description="É mais do que falso?",
            predicted_class=pred_y1,
            predicted_label=label_y1,
            softmax_scores=scores_y1,
        )

        # 2. Estruturação técnica do classificador Y2
        label_y2 = "nao_verdadeiro" if pred_y2 == 0 else "verdadeiro"
        scores_y2 = {
            "nao_verdadeiro": round(float(probs_y2[0]), 4),
            "verdadeiro": round(float(probs_y2[1]), 4),
        }
        y2_result = ModelTargetResult(
            target="Y2",
            target_description="É estritamente verdadeiro?",
            predicted_class=pred_y2,
            predicted_label=label_y2,
            softmax_scores=scores_y2,
        )

        # 3. Avaliação Educativa e Tratamento de Inconsistência Lógica (Y1=0 e Y2=1)
        educational = self._evaluate_educational_status(pred_y1, pred_y2)

        model_info = ModelMetadataResponse(
            model_name=raw_result.get("model_name", "BERTimbau"),
            version=raw_result.get("version", "1.0.0"),
            device=raw_result.get("device", "cpu"),
            training_timestamp=raw_result.get("training_timestamp"),
            dataset_hash=raw_result.get("dataset_hash"),
        )

        return AnalyzeResponse(
            statement=raw_statement,
            cleaned_statement=statement_for_inference,
            educational_assessment=educational,
            y1=y1_result,
            y2=y2_result,
            model_info=model_info,
            disclaimer=DISCLAIMER_TEXTO,
            methodology_note=METHODOLOGY_NOTE,
        )

    @staticmethod
    def _evaluate_educational_status(pred_y1: int, pred_y2: int) -> EducationalAssessment:
        """Determina a interpretação pedagógica com base nas predições conjuntas."""
        # Caso inconsistente: Y1 aponta 'falso' e Y2 aponta 'verdadeiro'
        if pred_y1 == 0 and pred_y2 == 1:
            return EducationalAssessment(
                status="inconclusivo",
                label="Inconclusivo / Análise Divergente",
                summary=(
                    "Os classificadores geraram previsões conflitantes (Y1 apontou falso, "
                    "mas Y2 apontou verdadeiro). Esta estimativa não é conclusiva e "
                    "exige averiguação independente em fontes primárias."
                ),
                is_inconclusive=True,
            )

        if pred_y1 == 0 and pred_y2 == 0:
            return EducationalAssessment(
                status="nao_confiavel",
                label="Não Confiável",
                summary=(
                    "O modelo estimou características e linguagem associadas a desinformação, "
                    "boatos ou alegações não sustentadas por fatos."
                ),
                is_inconclusive=False,
            )

        if pred_y1 == 1 and pred_y2 == 1:
            return EducationalAssessment(
                status="confiavel",
                label="Confiável",
                summary=(
                    "O modelo estimou padrões compatíveis com informações comumente reportadas "
                    "como verídicas em veículos consolidados."
                ),
                is_inconclusive=False,
            )

        # pred_y1 == 1 and pred_y2 == 0
        return EducationalAssessment(
            status="atencao_ou_enganoso",
            label="Requer Atenção / Parcialmente Enganoso",
            summary=(
                "O modelo indicou que a afirmação pode conter distorções, omissões de "
                "contexto ou meias-verdades, não sendo estritamente factual."
            ),
            is_inconclusive=False,
        )
