"""Limpeza textual para inferência, alinhada com o pipeline oficial de treino.

Aplica as mesmas regras de `ml/dados.py:limpar_texto`:
1. Remove URLs.
2. Remove prefixos de agências/checagens (ex: "FATO OU FAKE: ", "COMPROVA: ").
3. Remove sufixos de portais e checadores (ex: "| G1", "- Lupa").
4. Remove assinaturas e créditos de autoria.
5. Normaliza espaços sem apagar pontuação expressiva ou alterar maiúsculas.
"""

from __future__ import annotations

import re

RE_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

RE_PREFIXO_VEICULO = re.compile(
    r"^(?:(?:FATO OU FAKE|É FATO|É FAKE|VERIFICAMOS|BOATO|CHECAGEM|CHEQUEI|COMPROVA)\s*[-–—:|]\s*)+",
    re.IGNORECASE,
)

RE_SUFIXO_BARRA = re.compile(r"\s*\|\s*[^|]{1,30}$")
RE_SUFIXO_TRAVESSAO = re.compile(
    r"\s*[-–—]\s*(?:Boatos\.org|Aos Fatos|Agência Lupa|Lupa|E-farsas|G1|UOL|Folha|Estadão|Comprova|AFP)\s*$",
    re.IGNORECASE,
)

RE_ASSINATURA_INICIO = re.compile(
    r"^(?:(?:Foto|Crédito|Fonte|Por|Da Redação)\s*:\s*[^.\n]+(?:\.|\n|\s*[-–—]\s*)\s*)",
    re.IGNORECASE,
)
RE_ASSINATURA_FIM = re.compile(
    r"\s*(?:[-–—|]\s*(?:Por\s+[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*|Da Redação)|(?:Foto|Crédito|Fonte|Por|Da Redação|Reportagem de)\s*:\s*[^.\n]+)\s*\.?$",
    re.IGNORECASE,
)

RE_ESPACOS = re.compile(r"[ \t]+")
RE_QUEBRAS = re.compile(r"\n\s*")


def limpar_texto(texto: str | None) -> str:
    """Aplica limpeza textual preservando rigorosamente maiúsculas e pontuação."""
    if not texto:
        return ""

    s = texto.strip()

    # 1. Remoção de URLs
    s = RE_URL.sub("", s)

    # 2. Remoção de prefixos de veículos/checagens
    s = RE_PREFIXO_VEICULO.sub("", s)

    # 3. Remoção de sufixos de portais
    s = RE_SUFIXO_BARRA.sub("", s)
    s = RE_SUFIXO_TRAVESSAO.sub("", s)

    # 4. Remoção de assinaturas (início ou fim)
    s = RE_ASSINATURA_INICIO.sub("", s)
    s = RE_ASSINATURA_FIM.sub("", s)

    # 5. Normalização de espaçamento sem apagar pontuação
    s = RE_ESPACOS.sub(" ", s)
    s = RE_QUEBRAS.sub("\n", s)

    return s.strip()
