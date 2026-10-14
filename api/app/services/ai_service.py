"""Apoio da LLM e do classificador à curadoria.

- `generate()`: checagens de agência viram rascunhos de questões. A LLM só reescreve a
  alegação no formato do jogo; o gabarito (`is_true`) e a fonte vêm da checagem, nunca da LLM
  nem do classificador. Resposta da LLM fora do esquema, reescrita pouco parecida com a
  alegação original (troca de assunto, `verificar_reescrita`) ou com negação a mais ou a menos
  (`verificar_negacao`) descartam a checagem. Por enquanto as
  checagens vêm dos provedores de notícias (`NOTICIAS_PROVIDER=factcheck`); o job diário (#23)
  troca a origem pelas checagens recentes do dataset.
- `classify()`: análise de uma afirmação pelo classificador, com o limiar do admin.
"""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.integrations.classificador_client import ClassificadorClient, ClassificadorIndisponivel
from app.integrations.embeddings_client import EmbeddingsClient, FakeEmbeddings
from app.integrations.llm_client import ChecagemDeOrigem, LLMClient, RespostaInvalida
from app.integrations.noticias_client import Noticia, NoticiasClient, NoticiasIndisponiveis
from app.integrations.verificadores import verificar_negacao, verificar_reescrita
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.repositories.question_repository import QuestionRepository
from app.schemas.admin_schema import (
    AIClassifyRequest,
    AIClassifyResponse,
    AIGenerateRequest,
    QuestionAdminResponse,
)
from app.services import game_rules
from app.services.content_service import ContentService, to_admin_response
from app.services.noticias_service import CANDIDATOS, explicacao, fonte


def checagem_de_origem(noticia: Noticia) -> ChecagemDeOrigem:
    return ChecagemDeOrigem(
        alegacao=noticia.titulo,
        veredito=noticia.veredito or "",
        agencia=noticia.veiculo,
        data=noticia.publicada_em.date() if noticia.publicada_em else None,
        link=noticia.url,
    )


class AIService:
    def __init__(
        self,
        db: Session,
        llm: LLMClient,
        classificador: ClassificadorClient,
        noticias: Sequence[NoticiasClient] = (),
        embeddings: EmbeddingsClient | None = None,
    ) -> None:
        self.llm = llm
        self.embeddings = embeddings or FakeEmbeddings()
        self.classificador = classificador
        self.provedores = list(noticias)
        self.questions = QuestionRepository(db)
        self.content = ContentService(db)

    def checagens(self) -> list[Noticia]:
        """Checagens com lado no jogo (verdadeira ou falsa); enganosas e ambíguas ficam fora."""
        candidatas, falhas = [], []
        for provedor in self.provedores:
            try:
                candidatas += provedor.buscar(CANDIDATOS)
            except NoticiasIndisponiveis as erro:
                falhas.append(erro)
        if falhas and len(falhas) == len(self.provedores):
            raise falhas[0]
        return [n for n in candidatas if n.veredito and n.verdadeira is not None]

    def generate(self, data: AIGenerateRequest) -> list[QuestionAdminResponse]:
        category = self.content.get_category(data.category)
        rascunhos: list[Question] = []
        vistas: set[str] = set()
        for noticia in self.checagens():
            if len(rascunhos) == data.quantity:
                break
            if fonte(noticia) in vistas or self.questions.exists_by_statement_or_source(
                noticia.titulo, fonte(noticia)
            ):
                continue  # checagem que já virou questão
            vistas.add(fonte(noticia))
            try:
                gerada = self.llm.gerar_questao(checagem_de_origem(noticia))
            except RespostaInvalida:
                continue  # saída fora do esquema duas vezes: a checagem é descartada
            limiar = get_settings().similaridade_minima_reescrita
            if verificar_negacao(noticia.titulo, gerada.statement) or verificar_reescrita(
                noticia.titulo, gerada.statement, self.embeddings, limiar
            ):
                continue
            is_true = bool(noticia.verdadeira)
            # Nunca publica direto; a revisão acontece em /admin/questions/{id}/review.
            rascunhos.append(
                self.questions.add(
                    Question(
                        statement=gerada.statement,
                        is_true=is_true,
                        reliability_reference=game_rules.default_reliability_reference(is_true),
                        explanation=explicacao(noticia),
                        source=fonte(noticia),
                        category=category,
                        status=QuestionStatus.DRAFT,
                        origin=QuestionOrigin.AI,
                    )
                )
            )
        return [to_admin_response(q) for q in rascunhos]

    def classify(self, data: AIClassifyRequest) -> AIClassifyResponse:
        try:
            analise = self.classificador.analisar(data.statement, "admin")
        except ClassificadorIndisponivel as erro:
            raise ServiceUnavailableError(f"Análise indisponível: {erro}") from erro
        nota = "sem nota" if analise.nota is None else f"nota {analise.nota:.0f}"
        return AIClassifyResponse(
            suggested_is_true=analise.categoria == "confere",
            confidence=analise.confianca,
            rationale=(
                f"Classificador {analise.versao_modelo}: {analise.categoria} ({nota}, "
                f"confiança {analise.confianca:.0%})."
            ),
        )
