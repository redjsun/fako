from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.integrations.bertimbau_engine import get_bertimbau_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Carrega os modelos BERTimbau uma única vez durante o startup
    engine = get_bertimbau_engine()
    engine.load()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router)
