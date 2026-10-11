"""Notícias externas viram rascunhos de afirmações do jogo, com a análise do classificador.

Fluxo: o provedor entrega as manchetes; cada uma é normalizada para o formato do treino
(integrations/normalizacao.py), passa pelos mesmos filtros das matérias de portal, sai se já
existe no banco (mesma URL ou mesmo texto) e é analisada pelo classificador com o limiar do
admin. Entra como rascunho verdadeiro (manchete de veículo publicada), com a fonte e a análise
gravadas para a revisão humana em /admin/questions/{id}/review; nada vai direto ao jogador.

Se o classificador estiver indisponível, a notícia entra mesmo assim, sem análise.
"""

from sqlalchemy.orm import Session

from app.integrations.classificador_client import (
    ClassificadorClient,
    ClassificadorIndisponivel,
)
from app.integrations.normalizacao import motivo_descarte, normalizar_manchete
from app.integrations.noticias_client import Noticia, NoticiasClient
from app.models.category import Category
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.repositories.question_repository import QuestionRepository
from app.schemas.admin_schema import NewsDiscarded, NewsImportRequest, NewsImportResponse
from app.services.content_service import ContentService, to_admin_response


def explicacao(noticia: Noticia) -> str:
    veiculo = noticia.veiculo or "um veículo de imprensa"
    quando = f" em {noticia.publicada_em:%d/%m/%Y}" if noticia.publicada_em else ""
    return f"Manchete publicada por {veiculo}{quando}."


class NoticiasService:
    def __init__(
        self, db: Session, noticias: NoticiasClient, classificador: ClassificadorClient
    ) -> None:
        self.noticias = noticias
        self.classificador = classificador
        self.questions = QuestionRepository(db)
        self.content = ContentService(db)

    def importar(self, data: NewsImportRequest) -> NewsImportResponse:
        category = self.content.get_category(data.category)
        importadas, descartadas = [], []
        vistas: set[str] = set()
        for noticia in self.noticias.buscar(category.slug, data.quantity):
            manchete = normalizar_manchete(noticia.titulo, noticia.veiculo)
            motivo = motivo_descarte(manchete, noticia.url)
            if motivo is None and (
                manchete.casefold() in vistas
                or self.questions.exists_by_statement_or_source(manchete, noticia.url)
            ):
                motivo = "já importada"
            if motivo:
                descartadas.append(NewsDiscarded(title=noticia.titulo, reason=motivo))
                continue
            vistas.add(manchete.casefold())
            importadas.append(self._rascunho(manchete, noticia, category))
        return NewsImportResponse(
            imported=[to_admin_response(q) for q in importadas], discarded=descartadas
        )

    def _rascunho(self, manchete: str, noticia: Noticia, category: Category) -> Question:
        question = Question(
            statement=manchete,
            is_true=True,
            explanation=explicacao(noticia),
            source=noticia.url[:500],
            category=category,
            status=QuestionStatus.DRAFT,
            origin=QuestionOrigin.NEWS,
        )
        try:
            analise = self.classificador.analisar(manchete, "admin")
        except ClassificadorIndisponivel:
            analise = None
        if analise:
            question.model_category = analise.categoria
            question.model_score = analise.nota
            question.model_confidence = analise.confianca
            question.model_version = analise.versao_modelo
        return self.questions.add(question)
