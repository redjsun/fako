"""Notícias externas viram rascunhos de afirmações do jogo, com a análise do classificador.

Fluxo: cada provedor entrega os textos (com mais de um, a quantidade pedida é dividida entre
eles, para equilibrar as falsas das checagens com as verdadeiras das manchetes); cada um é
normalizado para o formato do treino
(integrations/normalizacao.py), passa pelos filtros (os das matérias de portal nas manchetes;
tamanho, mídia, conclusão embutida e, opcionalmente, política nas alegações checadas), sai se
já existe no banco (mesma URL ou mesmo texto) e é analisado pelo classificador com o limiar do
admin. Manchete de veículo entra verdadeira (foi publicada); alegação checada entra com o lado
do veredito da agência (as enganosas ou ambíguas ficam de fora). Entram como rascunho, para a
revisão humana em /admin/questions/{id}/review, ou, com NOTICIAS_PUBLICAR_DIRETO, já validadas.
O rótulo nunca é o do classificador: a análise dele fica só como registro.

Se o classificador estiver indisponível, a notícia entra mesmo assim, sem análise.
"""

import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.classificador_client import (
    ClassificadorClient,
    ClassificadorIndisponivel,
)
from app.integrations.normalizacao import motivo_descarte, normalizar_manchete
from app.integrations.noticias_client import Noticia, NoticiasClient, NoticiasIndisponiveis
from app.models.category import Category
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.repositories.question_repository import QuestionRepository
from app.schemas.admin_schema import NewsDiscarded, NewsImportRequest, NewsImportResponse
from app.services import game_rules
from app.services.content_service import ContentService, to_admin_response

# Os filtros descartam boa parte das alegações checadas (a maioria é política ou depende de
# mídia): o provedor entrega um lote maior e a importação para ao chegar na quantidade pedida.
CANDIDATOS = 100


def explicacao(noticia: Noticia) -> str:
    quando = f" em {noticia.publicada_em:%d/%m/%Y}" if noticia.publicada_em else ""
    if noticia.veredito:
        agencia = noticia.veiculo or "uma agência de checagem"
        return f"Checado por {agencia}{quando}: {noticia.veredito}."
    veiculo = noticia.veiculo or "um veículo de imprensa"
    return f"Manchete publicada por {veiculo}{quando}."


def motivo(noticia: Noticia, texto: str) -> str | None:
    if noticia.veredito is None:
        return motivo_descarte(texto, noticia.url)
    if noticia.verdadeira is None:
        return f"veredito sem lado no jogo ({noticia.veredito})"
    sem_politica = get_settings().noticias_sem_politica
    return motivo_descarte(texto, noticia.url, checagem=True, sem_politica=sem_politica)


class NoticiasService:
    def __init__(
        self, db: Session, noticias: list[NoticiasClient], classificador: ClassificadorClient
    ) -> None:
        self.provedores = noticias
        self.classificador = classificador
        self.questions = QuestionRepository(db)
        self.content = ContentService(db)

    def importar(self, data: NewsImportRequest) -> NewsImportResponse:
        category = self.content.get_category(data.category)
        importadas, descartadas = [], []
        vistas: set[str] = set()
        falhas = []
        restante = data.quantity
        for posicao, provedor in enumerate(self.provedores):
            # Cada provedor fica com a sua parte do que falta; um fora do ar não derruba os outros.
            cota = math.ceil(restante / (len(self.provedores) - posicao))
            try:
                noticias = provedor.buscar(CANDIDATOS)
            except NoticiasIndisponiveis as erro:
                falhas.append(erro)
                continue
            antes = len(importadas)
            self._importar(noticias, cota, category, importadas, descartadas, vistas)
            restante -= len(importadas) - antes
        if falhas and len(falhas) == len(self.provedores):
            raise falhas[0]
        return NewsImportResponse(
            imported=[to_admin_response(q) for q in importadas], discarded=descartadas
        )

    def _importar(
        self,
        noticias: list[Noticia],
        cota: int,
        category: Category,
        importadas: list[Question],
        descartadas: list[NewsDiscarded],
        vistas: set[str],
    ) -> None:
        inicio = len(importadas)
        for noticia in noticias:
            if len(importadas) - inicio == cota:
                break
            # Nas checagens o "veículo" é a agência, que não aparece no texto da alegação.
            manchete = normalizar_manchete(
                noticia.titulo, None if noticia.veredito else noticia.veiculo
            )
            descarte = motivo(noticia, manchete)
            if descarte is None and (
                manchete.casefold() in vistas
                or self.questions.exists_by_statement_or_source(manchete, noticia.url)
            ):
                descarte = "já importada"
            if descarte:
                descartadas.append(NewsDiscarded(title=noticia.titulo, reason=descarte))
                continue
            vistas.add(manchete.casefold())
            importadas.append(self._rascunho(manchete, noticia, category))

    def _rascunho(self, manchete: str, noticia: Noticia, category: Category) -> Question:
        question = Question(
            statement=manchete,
            is_true=bool(noticia.verdadeira),
            reliability_reference=game_rules.default_reliability_reference(
                bool(noticia.verdadeira)
            ),
            explanation=explicacao(noticia),
            source=noticia.url[:500],
            category=category,
            status=QuestionStatus.DRAFT,
            origin=QuestionOrigin.NEWS,
        )
        if get_settings().noticias_publicar_direto:
            question.status = QuestionStatus.VALIDATED
            question.validated_at = datetime.now(timezone.utc)
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
