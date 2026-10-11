"""Controller de rotas de inteligência artificial e inferência."""

from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.integrations.bertimbau_engine import BertimbauEngine, get_bertimbau_engine
from app.schemas.inference_schema import AnalyzeRequest, AnalyzeResponse
from app.services.inference_service import InferenceService

router = APIRouter(prefix="/ai", tags=["ai"])


def get_inference_service(
    engine: BertimbauEngine = Depends(get_bertimbau_engine),
) -> InferenceService:
    return InferenceService(engine)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    dependencies=[Depends(get_current_admin)],
    summary="Analisa a confiabilidade de uma afirmação usando BERTimbau Y1 e Y2",
)
def analyze_statement(
    data: AnalyzeRequest,
    service: InferenceService = Depends(get_inference_service),
) -> AnalyzeResponse:
    """Executa a inferência nos classificadores locais do BERTimbau.

    Acesso restrito a administradores nesta primeira etapa do projeto.
    """
    return service.analyze(data.statement)
