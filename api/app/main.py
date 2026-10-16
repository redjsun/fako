from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers

settings = get_settings()
# Sem um JWT_SECRET próprio a API não sobe: com o segredo de exemplo, qualquer um que lê o
# repositório assinaria tokens de administrador.
settings.exigir_segredo_jwt()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router)
