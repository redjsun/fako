"""Rotas de cadastro e login."""

from fastapi import APIRouter, Depends, Request, status

from app.core.database import SessaoDaRequisicao
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_service(db: SessaoDaRequisicao) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, service: AuthService = Depends(get_service)) -> TokenResponse:
    return service.register(data)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest, request: Request, service: AuthService = Depends(get_service)
) -> TokenResponse:
    origem = request.client.host if request.client else "desconhecida"
    return service.login(data, origem)
