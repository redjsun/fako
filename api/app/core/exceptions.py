"""Erros de negócio e sua tradução para respostas HTTP.

Os services levantam estas exceções sem conhecer HTTP; o handler registrado em
`main.py` converte cada uma no status correspondente.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class UnauthorizedError(DomainError):
    status_code = 401


class BusinessRuleError(DomainError):
    status_code = 422


class ServiceUnavailableError(DomainError):
    status_code = 503


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
