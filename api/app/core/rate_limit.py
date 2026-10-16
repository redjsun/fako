"""Limite de tentativas de login erradas, em memória.

Conta as falhas numa janela de tempo por usuário (de uma mesma origem) e por origem (qualquer
usuário), para barrar tanto a força bruta numa conta quanto o teste de muitas contas. Vale por
processo: com mais de um worker, ou atrás de um proxy (a origem vira o IP do proxy), o limite
precisa ir para o proxy ou para um armazenamento compartilhado.
"""

import threading
import time
from collections import defaultdict, deque

from app.core.exceptions import TooManyRequestsError

JANELA_SEGUNDOS = 15 * 60
FALHAS_POR_USUARIO = 5
FALHAS_POR_ORIGEM = 20


class LimiteDeTentativas:
    def __init__(
        self,
        janela_segundos: float = JANELA_SEGUNDOS,
        falhas_por_usuario: int = FALHAS_POR_USUARIO,
        falhas_por_origem: int = FALHAS_POR_ORIGEM,
    ) -> None:
        self.janela_segundos = janela_segundos
        self.limites = {"usuario": falhas_por_usuario, "origem": falhas_por_origem}
        self.falhas: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.trava = threading.Lock()

    @staticmethod
    def _chaves(origem: str, username: str) -> list[tuple[str, str]]:
        return [("usuario", f"{origem}|{username.casefold()}"), ("origem", origem)]

    def _recentes(self, chave: tuple[str, str], agora: float) -> deque[float]:
        falhas = self.falhas[chave]
        while falhas and agora - falhas[0] > self.janela_segundos:
            falhas.popleft()
        return falhas

    def verificar(self, origem: str, username: str) -> None:
        agora = time.monotonic()
        with self.trava:
            for chave in self._chaves(origem, username):
                if len(self._recentes(chave, agora)) >= self.limites[chave[0]]:
                    raise TooManyRequestsError(
                        "Muitas tentativas de login. Espere alguns minutos e tente de novo."
                    )

    def registrar_falha(self, origem: str, username: str) -> None:
        agora = time.monotonic()
        with self.trava:
            for chave in self._chaves(origem, username):
                self._recentes(chave, agora).append(agora)

    def registrar_sucesso(self, origem: str, username: str) -> None:
        """O acerto zera as falhas daquele usuário; as da origem continuam contando."""
        with self.trava:
            self.falhas.pop(self._chaves(origem, username)[0], None)

    def limpar(self) -> None:
        with self.trava:
            self.falhas.clear()


limite_de_login = LimiteDeTentativas()
