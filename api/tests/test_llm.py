import json
from datetime import date

import pytest

from app.core.config import get_settings
from app.ml import llm as llm_client
from app.ml.classificador import Checagem, FakeClassificador, Sinal
from app.ml.llm import (
    PASTA_PROMPTS,
    VERSAO_PROMPT,
    ChecagemDeOrigem,
    FakeLLMClient,
    LLMAusente,
    LLMIndisponivel,
    LLMValidado,
    RespostaInvalida,
    entrada_da_explicacao,
    get_llm_client,
    ler_json,
    pedido_openai,
)

CHECAGEM = ChecagemDeOrigem(
    alegacao="Vacina da covid tem chip para rastrear a população",
    veredito="falso",
    agencia="Lupa",
    data=date(2021, 5, 10),
    link="https://lupa.teste/1",
)


class PedidoRoteirizado:
    """Devolve as respostas na ordem e guarda os prompts recebidos."""

    def __init__(self, *respostas: str):
        self.respostas = list(respostas)
        self.prompts: list[str] = []

    def __call__(self, prompt: str, esquema: dict) -> str:
        self.prompts.append(prompt)
        return self.respostas.pop(0)


@pytest.fixture
def settings_limpas():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_prompts_versionados_existem_e_a_versao_esta_no_nome():
    for nome, versao in VERSAO_PROMPT.items():
        assert versao.startswith(f"{nome}_v")
        assert (PASTA_PROMPTS / f"{versao}.txt").is_file()


def test_fake_e_deterministico():
    llm = FakeLLMClient()
    assert llm.gerar_questao(CHECAGEM) == llm.gerar_questao(CHECAGEM)
    assert llm.extrair_afirmacoes("Uma frase") == llm.extrair_afirmacoes("Uma frase")
    analise = FakeClassificador().analisar("x", "jogador")
    assert llm.explicar(analise) == llm.explicar(analise)


def test_gera_questao_valida_e_registra_a_versao_do_prompt():
    pedido = PedidoRoteirizado('{"statement": "A vacina tem um chip", "category": "saude"}')
    questao = LLMValidado(pedido).gerar_questao(CHECAGEM)
    assert questao.statement == "A vacina tem um chip"
    assert questao.versao_prompt == "gerar_questao_v1"
    assert CHECAGEM.alegacao in pedido.prompts[0] and "{alegacao}" not in pedido.prompts[0]


def test_resposta_invalida_tenta_mais_uma_vez():
    pedido = PedidoRoteirizado(
        "não sei",
        '```json\n{"e_opiniao": false, "afirmacoes": [{"texto": "X aconteceu", '
        '"quem_disse": "deputado"}]}\n```',
    )
    extracao = LLMValidado(pedido).extrair_afirmacoes("Deputado disse que X aconteceu")
    assert len(pedido.prompts) == 2
    assert extracao.afirmacoes[0].quem_disse == "deputado"


def test_duas_respostas_invalidas_descartam_o_item():
    pedido = PedidoRoteirizado('{"statement": ""}', '{"outro": 1}', "nunca chega aqui")
    with pytest.raises(RespostaInvalida, match="gerar_questao_v1"):
        LLMValidado(pedido).gerar_questao(CHECAGEM)
    assert len(pedido.prompts) == 2


def test_explicacao_nao_recebe_pesos_por_palavra():
    analise = FakeClassificador().analisar("A terra é plana", "admin")
    analise.contribuicoes = [("palavra_secreta", 0.9)]
    analise.sinais = [Sinal("urgencia", "URGENTE")]
    analise.checagem_parecida = Checagem("A terra é plana", "falso", "https://x.teste", 0.93)
    entrada = entrada_da_explicacao(analise)
    assert "contribuicoes" not in entrada
    pedido = PedidoRoteirizado('{"explicacao": "É parecida com uma checagem falsa."}')
    assert LLMValidado(pedido).explicar(analise) == "É parecida com uma checagem falsa."
    assert "palavra_secreta" not in pedido.prompts[0]
    assert "URGENTE" in pedido.prompts[0]


def test_ler_json_ignora_texto_em_volta():
    assert ler_json('Claro! {"a": 1} espero ter ajudado') == {"a": 1}
    with pytest.raises(ValueError):
        ler_json("sem json")


class RespostaHttp:
    def __init__(self, corpo: dict):
        self.corpo = json.dumps(corpo).encode()

    def __enter__(self):
        return self

    def __exit__(self, *erro):
        return False

    def read(self, *args):
        return self.corpo


def test_pedido_openai_envia_temperatura_esquema_e_chave(monkeypatch):
    enviados = []

    def urlopen(requisicao, timeout):
        enviados.append((requisicao, timeout))
        return RespostaHttp({"choices": [{"message": {"content": '{"ok": true}'}}]})

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", urlopen)
    pedir = pedido_openai(
        "http://llm.teste/v1/", "qwen3:8b", "chave", 0.3, 5, extra={"reasoning_effort": "none"}
    )
    assert pedir("prompt", {"type": "object"}) == '{"ok": true}'
    requisicao, timeout = enviados[0]
    corpo = json.loads(requisicao.data)
    assert requisicao.full_url == "http://llm.teste/v1/chat/completions"
    assert requisicao.get_header("Authorization") == "Bearer chave"
    assert corpo["temperature"] == 0.3 and corpo["reasoning_effort"] == "none"
    assert corpo["response_format"]["json_schema"]["schema"] == {"type": "object"}
    assert timeout == 5


def test_pedido_openai_fora_do_ar_vira_indisponivel(monkeypatch):
    def urlopen(requisicao, timeout):
        raise llm_client.urllib.error.URLError("recusada")

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", urlopen)
    with pytest.raises(LLMIndisponivel, match="fora do ar"):
        pedido_openai("http://llm.teste/v1", "m")("prompt", {})


def test_provedor_padrao_e_fake(settings_limpas, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    assert isinstance(get_llm_client(), FakeLLMClient)


def test_provedor_sem_configuracao_falha_de_forma_controlada(settings_limpas, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_BASE_URL", "")
    cliente = get_llm_client()
    assert isinstance(cliente, LLMAusente)
    with pytest.raises(LLMIndisponivel, match="LLM_BASE_URL"):
        cliente.gerar_questao(CHECAGEM)


def test_provedor_desconhecido_falha_de_forma_controlada(settings_limpas, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "outro")
    with pytest.raises(LLMIndisponivel, match="não suportado"):
        get_llm_client().extrair_afirmacoes("texto")


def test_provedor_openai_configurado(settings_limpas, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.teste/v1")
    monkeypatch.setenv("LLM_MODEL", "qwen3:8b")
    monkeypatch.setenv("LLM_EXTRA_BODY", '{"reasoning_effort": "none"}')
    assert isinstance(get_llm_client(), LLMValidado)
    assert get_settings().llm_extra_body == {"reasoning_effort": "none"}


def test_explicacao_com_fato_inventado_tenta_de_novo_e_depois_descarta():
    analise = FakeClassificador().analisar("A terra é plana", "admin")  # falso, não incerto
    pedido = PedidoRoteirizado(
        '{"explicacao": "A NASA já desmentiu essa afirmação várias vezes."}',
        '{"explicacao": "A análise automática classificou como falso."}',
    )
    assert "classificou" in LLMValidado(pedido).explicar(analise)
    pedido = PedidoRoteirizado(*['{"explicacao": "A NASA desmentiu em 1969 essa afirmação."}'] * 2)
    with pytest.raises(RespostaInvalida, match="NASA"):
        LLMValidado(pedido).explicar(analise)
