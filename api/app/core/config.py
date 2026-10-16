"""Configurações da aplicação (camada de infraestrutura).

Os valores podem ser sobrescritos por variáveis de ambiente (ver `.env.example`).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings

# Valor que já foi o padrão do código e do .env.example: público, nunca aceito.
SEGREDO_JWT_DE_EXEMPLO = "troque-este-segredo-em-producao"
TAMANHO_MINIMO_SEGREDO_JWT = 32  # bytes; o HS256 pede uma chave de pelo menos 256 bits


class Settings(BaseSettings):
    app_name: str = "Fake News Snake API"
    version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "postgresql+psycopg://fako:fako@localhost:5432/fako"

    # Sem padrão utilizável: a API não sobe sem um segredo próprio (exigir_segredo_jwt). As
    # migrations e os seeds não usam o segredo e rodam sem ele.
    jwt_secret: str = ""
    jwt_expires_minutes: int = 60 * 24

    # Provedor usado por integrations/ai_client.py; "fake" roda sem chamadas externas.
    ai_provider: str = "fake"

    # Classificador de veracidade (integrations/classificador_client.py): "fake" roda sem modelo;
    # os modelos publicados ficam em models_dir/atual.
    classificador_provider: str = "fake"
    models_dir: str = "/app/models"
    # Mostra ao jogador, no feedback da resposta, o palpite do classificador (limiar do jogador).
    classificador_no_jogo: bool = False

    # Notícias externas (integrations/noticias_client.py): "fake" roda sem chave; "gnews" usa
    # a API do GNews (gnews.io, plano gratuito de 100 pedidos por dia), com noticias_api_key;
    # "factcheck" usa a Google Fact Check Tools API (checagens de agências), com
    # factcheck_api_key, a mesma chave da coleta da pesquisa.
    # Mais de um, separados por vírgula ("factcheck,gnews"): a quantidade é dividida entre eles.
    noticias_provider: str = "fake"
    noticias_api_key: str = ""
    factcheck_api_key: str = ""
    # Notícias entram já validadas, sem revisão humana: as checagens com o rótulo do veredito
    # da agência, as manchetes como verdadeiras.
    noticias_publicar_direto: bool = False
    # Descarta alegações checadas sobre política e eleição.
    noticias_sem_politica: bool = False
    # Dispositivo do motor BERTimbau Y1/Y2 (integrations/bertimbau_engine.py)
    ai_device: str = "cpu"

    def exigir_segredo_jwt(self) -> str:
        """O segredo dos tokens; recusa o vazio, o de exemplo e os curtos demais."""
        segredo = self.jwt_secret
        if segredo == SEGREDO_JWT_DE_EXEMPLO or len(segredo.encode()) < TAMANHO_MINIMO_SEGREDO_JWT:
            raise RuntimeError(
                f"Defina JWT_SECRET com {TAMANHO_MINIMO_SEGREDO_JWT} bytes ou mais (e diferente do "
                "valor de exemplo). Para gerar um: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return segredo


@lru_cache
def get_settings() -> Settings:
    return Settings()
