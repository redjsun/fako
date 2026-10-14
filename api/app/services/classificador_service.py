"""Uso do classificador de veracidade fora da curadoria de notícias.

- `analisar()`: auditoria pelo admin, com o limiar do admin e os termos que mais pesaram.
- `palpite_do_jogo()`: o palpite mostrado ao jogador depois da resposta, com o limiar do
  jogador (abaixo dele, `incerto`) e só se `CLASSIFICADOR_NO_JOGO` estiver ligado. Sem modelo,
  devolve None e o jogo segue sem palpite.
"""

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.ml.classificador import (
    ClassificadorClient,
    ClassificadorIndisponivel,
)
from app.ml.normalizacao import limpar
from app.schemas.admin_schema import ClassifierAnalyzeResponse
from app.schemas.match_schema import ModelGuess


class ClassificadorService:
    def __init__(self, classificador: ClassificadorClient) -> None:
        self.classificador = classificador

    def analisar(self, statement: str) -> ClassifierAnalyzeResponse:
        try:
            analise = self.classificador.analisar(statement, "admin")
        except ClassificadorIndisponivel as erro:
            raise ServiceUnavailableError(f"Classificador indisponível: {erro}") from erro
        return ClassifierAnalyzeResponse(
            statement=statement,
            normalized_statement=limpar(statement),
            category=analise.categoria,
            score=analise.nota,
            confidence=analise.confianca,
            probabilities=analise.probabilidades,
            model_version=analise.versao_modelo,
            contributions=analise.contribuicoes,
        )

    def palpite_do_jogo(self, statement: str, claim_text: str | None = None) -> ModelGuess | None:
        """`claim_text` (a afirmação extraída na importação) só entra se o modelo publicado foi
        treinado no texto padronizado; senão, o enunciado como o jogador leu."""
        if not get_settings().classificador_no_jogo:
            return None
        padronizado = self.classificador.texto_de_entrada == "padronizado"
        entrada = claim_text if padronizado and claim_text else statement
        try:
            analise = self.classificador.analisar(entrada, "jogador")
        except ClassificadorIndisponivel:
            return None
        return ModelGuess(
            category=analise.categoria,
            score=analise.nota,
            confidence=analise.confianca,
            model_version=analise.versao_modelo,
        )
