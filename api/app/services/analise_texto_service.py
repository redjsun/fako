"""Texto com várias afirmações vira uma análise por afirmação (#19).

Uma nota única para um texto inteiro esconderia a mentira no meio das verdades. A LLM extrai
as afirmações checáveis com quem disse cada uma; o classificador recebe só o texto da
afirmação, e o `quem_disse` vai junto na `Analise` ("o deputado disse X; X é falso"). Texto só
de opinião vira uma análise `opiniao`, sem classificador.

Usado pelo `POST /admin/ai/classify` com texto longo (#26) e pelas notícias da coleta diária.
"""

from app.core.exceptions import ServiceUnavailableError
from app.ml.classificador import (
    Analise,
    ClassificadorClient,
    ClassificadorIndisponivel,
    Limiar,
)
from app.ml.llm import VERSAO_PROMPT, LLMClient, RespostaInvalida


class AnaliseTextoService:
    def __init__(self, llm: LLMClient, classificador: ClassificadorClient) -> None:
        self.llm = llm
        self.classificador = classificador

    def analisar(self, texto: str, limiar: Limiar) -> list[Analise]:
        """Uma `Analise` por afirmação; lista vazia se o texto não tem o que checar."""
        try:
            extracao = self.llm.extrair_afirmacoes(texto)
        except RespostaInvalida as erro:
            raise ServiceUnavailableError(f"Extração de afirmações falhou: {erro}") from erro
        if extracao.e_opiniao:
            return [
                Analise(
                    afirmacao=texto,
                    categoria="opiniao",
                    nota=None,
                    confianca=1.0,
                    probabilidades={},
                    versao_modelo=VERSAO_PROMPT["extrair_afirmacoes"],
                )
            ]
        analises = []
        for afirmacao in extracao.afirmacoes:
            try:
                analise = self.classificador.analisar(afirmacao.texto, limiar)
            except ClassificadorIndisponivel as erro:
                raise ServiceUnavailableError(f"Análise indisponível: {erro}") from erro
            analise.quem_disse = afirmacao.quem_disse
            analises.append(analise)
        return analises
