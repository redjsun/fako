"""LLM: gera texto (questões, afirmações, explicações); nunca decide o gabarito.

Uma interface, `LLMClient`, com duas implementações:

- `FakeLLMClient`: determinístico, sem chamadas externas, para desenvolvimento e testes;
- `LLMValidado`: qualquer endpoint compatível com a API de chat da OpenAI (o Ollama local, o
  proxy do LiteLLM ou um provedor hospedado); trocar de provedor é trocar `LLM_BASE_URL` e
  `LLM_MODEL`.

Os prompts ficam em `app/ml/prompts/`, com a versão no nome (`gerar_questao_v1.txt`); a versão
vai junto de cada questão e análise (`VERSAO_PROMPT`). Toda resposta é JSON e passa por um
esquema Pydantic: se não passar, o pedido é feito mais uma vez; se falhar de novo, lança
`RespostaInvalida` e quem chamou descarta o item. Uma resposta quebrada nunca vira questão.
A explicação também passa pelo verificador de fatos (`verificadores.py`): citar algo que não
está na análise conta como resposta inválida.

Se o provedor não estiver configurado, `get_llm_client()` devolve um cliente que lança
`LLMIndisponivel`, e a API sobe mesmo assim.
"""

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.ml.classificador import Analise
from app.ml.verificadores import verificar_explicacao

PASTA_PROMPTS = Path(__file__).resolve().parent / "prompts"
# Versão em uso de cada prompt; mudar a versão é criar um arquivo novo, nunca editar o antigo.
VERSAO_PROMPT = {
    "extrair_afirmacoes": "extrair_afirmacoes_v1",
    "gerar_questao": "gerar_questao_v1",
    "explicar": "explicar_v1",
}
TENTATIVAS = 2  # a primeira e mais uma, se a resposta vier fora do esquema


class LLMIndisponivel(ServiceUnavailableError):
    """O provedor não está configurado, não respondeu ou recusou o pedido."""


class RespostaInvalida(Exception):
    """A LLM respondeu fora do esquema nas duas tentativas: o item é descartado."""


class Afirmacao(BaseModel):
    texto: str = Field(min_length=3, max_length=300)
    quem_disse: str | None = None


class Extracao(BaseModel):
    """Opinião só quando não há nenhuma afirmação checável (prompt de extração, regra 8).
    Sem afirmações e sem opinião (uma pergunta, um convite) não há o que analisar."""

    e_opiniao: bool
    afirmacoes: list[Afirmacao] = Field(max_length=5)

    @model_validator(mode="after")
    def opiniao_sem_afirmacoes(self) -> "Extracao":
        self.e_opiniao = self.e_opiniao and not self.afirmacoes
        return self


class SaidaQuestao(BaseModel):
    statement: str = Field(min_length=10, max_length=300)
    category: str | None = None


class SaidaExplicacao(BaseModel):
    explicacao: str = Field(min_length=10, max_length=600)


@dataclass
class ChecagemDeOrigem:
    """Checagem de agência que origina uma questão: o gabarito e a fonte vêm daqui."""

    alegacao: str
    veredito: str
    agencia: str | None
    data: date | None
    link: str


@dataclass
class QuestaoGerada:
    statement: str
    category: str | None
    versao_prompt: str


class LLMClient(Protocol):
    def gerar_questao(self, checagem: ChecagemDeOrigem) -> QuestaoGerada: ...

    def extrair_afirmacoes(self, texto: str) -> Extracao: ...

    def explicar(self, analise: Analise) -> str: ...


def entrada_da_explicacao(analise: Analise) -> dict:
    """Só a análise estruturada; pesos por palavra (`contribuicoes`) nunca entram."""
    checagem = analise.checagem_parecida
    return {
        "afirmacao": analise.afirmacao,
        "quem_disse": analise.quem_disse,
        "categoria": analise.categoria,
        "nota": None if analise.nota is None else round(analise.nota),
        "confianca": round(analise.confianca, 2),
        "sinais": [asdict(sinal) for sinal in analise.sinais],
        "sinais_fonte": analise.sinais_fonte,
        "checagem_parecida": asdict(checagem) if checagem else None,
    }


class FakeLLMClient:
    """Sem chamadas externas, determinístico: para desenvolvimento e testes."""

    def gerar_questao(self, checagem: ChecagemDeOrigem) -> QuestaoGerada:
        return QuestaoGerada(
            statement=checagem.alegacao.strip(),
            category=None,
            versao_prompt=VERSAO_PROMPT["gerar_questao"],
        )

    def extrair_afirmacoes(self, texto: str) -> Extracao:
        texto = texto.strip()
        return Extracao(e_opiniao=False, afirmacoes=[Afirmacao(texto=texto)] if texto else [])

    def explicar(self, analise: Analise) -> str:
        if analise.categoria == "incerto":
            return "O modelo não tem certeza sobre esta afirmação."
        return f"A análise automática classificou esta afirmação como {analise.categoria}."


@lru_cache
def ler_prompt(nome: str) -> str:
    return (PASTA_PROMPTS / f"{VERSAO_PROMPT[nome]}.txt").read_text(encoding="utf-8")


def preencher(prompt: str, variaveis: dict[str, str]) -> str:
    """Troca `{nome}` pelo valor; os exemplos de JSON do prompt ficam como estão."""
    for nome, valor in variaveis.items():
        prompt = prompt.replace("{" + nome + "}", valor)
    return prompt


def ler_json(resposta: str) -> dict:
    """O primeiro objeto JSON da resposta, mesmo cercado de ```json ou de texto."""
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", resposta.strip())
    for inicio in (i for i, c in enumerate(texto) if c == "{"):
        try:
            valor, _ = json.JSONDecoder().raw_decode(texto, inicio)
        except json.JSONDecodeError:
            continue
        if isinstance(valor, dict):
            return valor
    raise ValueError(f"sem objeto JSON na resposta: {resposta[:200]!r}")


# Recebe o prompt preenchido e o JSON Schema da saída; devolve o texto da resposta.
Pedido = Callable[[str, dict], str]
Saida = TypeVar("Saida", bound=BaseModel)
# Recebe a saída já no esquema; devolve o motivo da recusa, ou None se passou.
Verificacao = Callable[[Saida], str | None]


class LLMValidado:
    """Preenche o prompt versionado, pede à LLM e valida a resposta no esquema."""

    def __init__(self, pedir: Pedido) -> None:
        self.pedir = pedir

    def _gerar(
        self,
        nome: str,
        variaveis: dict[str, str],
        esquema: type[Saida],
        verificar: Verificacao | None = None,
    ) -> Saida:
        prompt = preencher(ler_prompt(nome), variaveis)
        erros = []
        for _ in range(TENTATIVAS):
            resposta = self.pedir(prompt, esquema.model_json_schema())
            try:
                saida = esquema.model_validate(ler_json(resposta))
            except (ValueError, ValidationError) as erro:
                erros.append(str(erro).splitlines()[0])
                continue
            motivo = verificar(saida) if verificar else None
            if motivo is None:
                return saida
            erros.append(motivo)
        raise RespostaInvalida(f"{VERSAO_PROMPT[nome]}: {'; '.join(erros)}")

    def gerar_questao(self, checagem: ChecagemDeOrigem) -> QuestaoGerada:
        saida = self._gerar(
            "gerar_questao",
            {
                "alegacao": checagem.alegacao,
                "veredito": checagem.veredito,
                "agencia": checagem.agencia or "não informada",
                "data": checagem.data.isoformat() if checagem.data else "não informada",
            },
            SaidaQuestao,
        )
        return QuestaoGerada(
            statement=saida.statement.strip(),
            category=saida.category,
            versao_prompt=VERSAO_PROMPT["gerar_questao"],
        )

    def extrair_afirmacoes(self, texto: str) -> Extracao:
        return self._gerar("extrair_afirmacoes", {"texto": texto}, Extracao)

    def explicar(self, analise: Analise) -> str:
        entrada = json.dumps(entrada_da_explicacao(analise), ensure_ascii=False, indent=2)
        saida = self._gerar(
            "explicar",
            {"analise": entrada},
            SaidaExplicacao,
            lambda s: verificar_explicacao(s.explicacao, entrada, analise.categoria),
        )
        return saida.explicacao.strip()


def pedido_openai(
    base_url: str,
    modelo: str,
    chave: str = "",
    temperatura: float = 0.2,
    tempo_limite: float = 120.0,
    esquema: bool = True,
    extra: dict | None = None,
) -> Pedido:
    """POST em /chat/completions (Ollama, LiteLLM ou provedor hospedado)."""
    url = base_url.rstrip("/") + "/chat/completions"
    cabecalhos = {"Content-Type": "application/json"}
    if chave:
        cabecalhos["Authorization"] = f"Bearer {chave}"

    def pedir(prompt: str, esquema_saida: dict) -> str:
        corpo = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperatura,
            **(extra or {}),
        }
        if esquema:
            corpo["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "saida", "schema": esquema_saida},
            }
        requisicao = urllib.request.Request(url, json.dumps(corpo).encode(), cabecalhos)
        try:
            with urllib.request.urlopen(requisicao, timeout=tempo_limite) as resposta:
                dados = json.load(resposta)
            return dados["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as erro:
            raise LLMIndisponivel(f"LLM respondeu {erro.code}") from erro
        except (urllib.error.URLError, TimeoutError) as erro:
            raise LLMIndisponivel(f"LLM fora do ar: {erro}") from erro
        except (ValueError, KeyError, IndexError, TypeError) as erro:
            raise LLMIndisponivel(f"Resposta inesperada do provedor: {erro}") from erro

    return pedir


class LLMAusente:
    """Responde no lugar do provedor que não está configurado."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo

    def gerar_questao(self, checagem: ChecagemDeOrigem) -> QuestaoGerada:
        raise LLMIndisponivel(self.motivo)

    def extrair_afirmacoes(self, texto: str) -> Extracao:
        raise LLMIndisponivel(self.motivo)

    def explicar(self, analise: Analise) -> str:
        raise LLMIndisponivel(self.motivo)


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "fake":
        return FakeLLMClient()
    if settings.llm_provider != "openai":
        return LLMAusente(f"Provedor de LLM não suportado: {settings.llm_provider}")
    if not settings.llm_base_url or not settings.llm_model:
        return LLMAusente("Defina LLM_BASE_URL e LLM_MODEL no .env")
    return LLMValidado(
        pedido_openai(
            settings.llm_base_url,
            settings.llm_model,
            settings.llm_api_key,
            settings.llm_temperatura,
            settings.llm_tempo_limite,
            settings.llm_esquema,
            settings.llm_extra_body,
        )
    )
