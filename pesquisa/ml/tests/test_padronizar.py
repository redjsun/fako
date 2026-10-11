import csv
import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from padronizar import (
    ESQUEMA_AFIRMACOES,
    Extracao,
    Prompt,
    aplicar,
    carregar_prompt,
    exportar,
    extrator_openai,
    filtrar_splits,
    interpretar_resposta,
    ler_cache,
    padronizar,
    texto_de_entrada,
)

REGISTROS = [
    {"id": "a", "texto_curto": "Vacina causa autismo", "texto": "longo a"},
    {"id": "b", "texto_curto": None, "texto": "Matéria longa sem título curto."},
    {"id": "c", "texto_curto": "", "texto": ""},
]


class ExtratorContador:
    """Extrator falso que conta as chamadas e responde por texto."""

    def __init__(self, respostas: dict[str, list[str]] | None = None):
        self.chamadas: list[str] = []
        self.respostas = respostas or {}

    def __call__(self, texto: str) -> Extracao:
        self.chamadas.append(texto)
        textos = self.respostas.get(texto, [texto])
        afirmacoes = [{"texto": t, "quem_disse": None} for t in textos]
        return Extracao(afirmacoes=afirmacoes, tokens_entrada=10)


@pytest.fixture
def prompt():
    return Prompt(versao="v1", texto="Extraia as afirmações de: {texto}")


def silencioso(_: str) -> None:
    pass


def test_carregar_prompt_le_a_versao_do_nome(tmp_path):
    arquivo = tmp_path / "extrair_afirmacoes_v3.txt"
    arquivo.write_text("prompt", encoding="utf-8")
    assert carregar_prompt(arquivo).versao == "v3"


def test_carregar_prompt_exige_versao(tmp_path):
    arquivo = tmp_path / "extrair_afirmacoes.txt"
    arquivo.write_text("prompt", encoding="utf-8")
    with pytest.raises(ValueError):
        carregar_prompt(arquivo)


def test_preencher_usa_o_marcador_ou_acrescenta_no_fim():
    assert Prompt("v1", "A {texto} B").preencher("x") == "A x B"
    assert Prompt("v1", "Extraia:\n").preencher("x") == "Extraia:\n\nx"


def test_texto_de_entrada_prefere_o_curto_e_cai_no_longo():
    assert texto_de_entrada(REGISTROS[0]) == "Vacina causa autismo"
    assert texto_de_entrada(REGISTROS[1]) == "Matéria longa sem título curto."
    assert texto_de_entrada(REGISTROS[2]) is None


def test_filtrar_splits_deixa_de_fora_reserva_e_fora():
    splits = ("treino", "validacao", "teste", "reserva", "fora")
    registros = [{"id": s, "split_produto": s} for s in splits]
    filtrados = filtrar_splits(registros, ["treino", "validacao", "teste"])
    assert [r["id"] for r in filtrados] == ["treino", "validacao", "teste"]
    assert len(list(filtrar_splits(registros, None))) == 5


UM = {"texto": "um", "quem_disse": None}


@pytest.mark.parametrize(
    "resposta, esperado",
    [
        (
            '{"e_opiniao": false, "afirmacoes": [{"texto": "vacina causa infertilidade", '
            '"quem_disse": "deputado Fulano"}, {"texto": "um", "quem_disse": null}]}',
            [{"texto": "vacina causa infertilidade", "quem_disse": "deputado Fulano"}, UM],
        ),
        ('```json\n{"afirmacoes": [{"texto": "um"}]}\n```', [UM]),
        ('Aqui está: {"afirmacoes": [{"texto": " um ", "quem_disse": ""}]} fim', [UM]),
        ('{"e_opiniao": true, "afirmacoes": []}', []),
    ],
)
def test_interpretar_resposta(resposta, esperado):
    assert interpretar_resposta(resposta) == esperado


@pytest.mark.parametrize(
    "resposta",
    [
        "Não há afirmações.",
        '["um", "dois"]',  # lista solta, sem o objeto da #19
        '{"afirmacoes": [{"texto": ""}]}',
        '{"afirmacoes": [{"texto": "um", "quem_disse": 3}]}',
    ],
)
def test_interpretar_resposta_rejeita_formato_desconhecido(resposta):
    with pytest.raises(ValueError):
        interpretar_resposta(resposta)


def test_padronizar_extrai_do_texto_longo_quando_falta_o_curto(tmp_path, prompt):
    extrator = ExtratorContador()
    cache = tmp_path / "padronizado_v1.jsonl"
    relatorio = padronizar(REGISTROS, prompt, extrator, cache, log=silencioso)
    assert sorted(extrator.chamadas) == ["Matéria longa sem título curto.", "Vacina causa autismo"]
    assert relatorio.processados == 2
    assert relatorio.sem_texto == 1
    assert relatorio.tokens_entrada == 20
    assert set(ler_cache(cache, prompt, "")) == {"a", "b"}


def test_segunda_rodada_nao_chama_a_llm_para_o_que_esta_em_cache(tmp_path, prompt):
    cache = tmp_path / "padronizado_v1.jsonl"
    padronizar(REGISTROS, prompt, ExtratorContador(), cache, log=silencioso)
    extrator = ExtratorContador()
    novo = {"id": "d", "texto_curto": "Frase nova", "texto": ""}
    relatorio = padronizar([*REGISTROS, novo], prompt, extrator, cache, log=silencioso)
    assert extrator.chamadas == ["Frase nova"]
    assert relatorio.em_cache == 2


def test_prompt_alterado_sem_trocar_versao_refaz_o_cache(tmp_path, prompt):
    cache = tmp_path / "padronizado_v1.jsonl"
    padronizar(REGISTROS, prompt, ExtratorContador(), cache, log=silencioso)
    alterado = Prompt(versao="v1", texto=prompt.texto + " Seja breve.")
    extrator = ExtratorContador()
    padronizar(REGISTROS, alterado, extrator, cache, log=silencioso)
    assert len(extrator.chamadas) == 2


def test_falha_da_llm_nao_entra_no_cache_e_e_refeita(tmp_path, prompt):
    def quebrado(texto: str) -> Extracao:
        raise TimeoutError("sem resposta")

    cache = tmp_path / "padronizado_v1.jsonl"
    relatorio = padronizar(REGISTROS, prompt, quebrado, cache, log=silencioso)
    assert relatorio.falhas == 2
    assert ler_cache(cache, prompt, "") == {}
    extrator = ExtratorContador()
    padronizar(REGISTROS, prompt, extrator, cache, log=silencioso)
    assert len(extrator.chamadas) == 2


def test_limite_e_paralelo(tmp_path, prompt):
    registros = [{"id": str(i), "texto_curto": f"frase {i}", "texto": ""} for i in range(20)]
    cache = tmp_path / "padronizado_v1.jsonl"
    relatorio = padronizar(
        registros, prompt, ExtratorContador(), cache, paralelo=4, limite=7, log=silencioso
    )
    assert relatorio.processados == 7
    linhas = cache.read_text(encoding="utf-8").splitlines()
    assert len({json.loads(linha)["id"] for linha in linhas}) == 7


def test_aplicar_usa_a_primeira_afirmacao_e_marca_a_quantidade(tmp_path, prompt):
    respostas = {
        "Vacina causa autismo": ["Vacina causa autismo", "Governo esconde dados"],
        "Matéria longa sem título curto.": [],  # opinião
    }
    cache = tmp_path / "padronizado_v1.jsonl"
    padronizar(REGISTROS, prompt, ExtratorContador(respostas), cache, log=silencioso)
    a, b, c = aplicar(REGISTROS, ler_cache(cache, prompt, ""))
    assert (a["texto_padronizado"], a["n_afirmacoes"]) == ("Vacina causa autismo", 2)
    assert (b["texto_padronizado"], b["n_afirmacoes"]) == (None, 0)
    assert (c["texto_padronizado"], c["n_afirmacoes"]) == (None, None)
    assert a["texto_curto"] == "Vacina causa autismo"  # o original continua no registro


def test_trocar_o_modelo_refaz_o_cache(tmp_path, prompt):
    cache = tmp_path / "padronizado_v1.jsonl"
    padronizar(REGISTROS, prompt, ExtratorContador(), cache, modelo="qwen-a", log=silencioso)
    extrator = ExtratorContador()
    padronizar(REGISTROS, prompt, extrator, cache, modelo="qwen-b", log=silencioso)
    assert len(extrator.chamadas) == 2
    assert set(ler_cache(cache, prompt, "qwen-a")) == set(ler_cache(cache, prompt, "qwen-b"))
    assert {json.loads(linha)["modelo"] for linha in cache.read_text().splitlines()} == {
        "qwen-a",
        "qwen-b",
    }


RESPOSTA_OK = {
    "choices": [{"message": {"content": '{"afirmacoes": [{"texto": "Y", "quem_disse": "X"}]}'}}],
    "usage": {"prompt_tokens": 42, "completion_tokens": 7},
}


def servidor_falso(respostas: list[tuple[int, dict]]):
    """Servidor local que responde, em ordem, com (status, corpo) e guarda os pedidos."""
    pedidos = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            pedidos.append(
                {
                    "caminho": self.path,
                    "auth": self.headers.get("Authorization"),
                    "corpo": json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                }
            )
            status, corpo = respostas[len(pedidos) - 1]
            self.send_response(status)
            self.end_headers()
            self.wfile.write(json.dumps(corpo).encode())

        def log_message(self, *args):
            pass

    servidor = HTTPServer(("127.0.0.1", 0), Handler)

    def atender():
        for _ in respostas:
            servidor.handle_request()

    threading.Thread(target=atender, daemon=True).start()
    return servidor, f"http://127.0.0.1:{servidor.server_port}/v1", pedidos


def test_extrator_openai_envia_o_prompt_o_esquema_e_le_o_uso(prompt):
    servidor, base_url, pedidos = servidor_falso([(200, RESPOSTA_OK)])
    extracao = extrator_openai(prompt, base_url, "qwen-x", "chave")("texto do registro")
    servidor.server_close()

    assert extracao == Extracao([{"texto": "Y", "quem_disse": "X"}], 42, 7)
    (pedido,) = pedidos
    assert pedido["caminho"] == "/v1/chat/completions"
    assert pedido["auth"] == "Bearer chave"
    corpo = pedido["corpo"]
    assert corpo["model"] == "qwen-x"
    assert corpo["temperature"] == 0
    assert corpo["messages"][0]["content"] == "Extraia as afirmações de: texto do registro"
    assert corpo["response_format"]["type"] == "json_schema"
    assert corpo["response_format"]["json_schema"]["schema"] == ESQUEMA_AFIRMACOES


def test_extrator_openai_sem_esquema_trunca_e_acrescenta_o_corpo_extra(prompt):
    servidor, base_url, pedidos = servidor_falso([(200, RESPOSTA_OK)])
    extra = {"enable_thinking": False}
    extrair = extrator_openai(
        prompt, base_url, "qwen-x", None, esquema=False, max_caracteres=5, extra=extra
    )
    extrair("texto muito longo")
    servidor.server_close()

    corpo = pedidos[0]["corpo"]
    assert "response_format" not in corpo
    assert corpo["enable_thinking"] is False
    assert corpo["messages"][0]["content"] == "Extraia as afirmações de: texto"
    assert pedidos[0]["auth"] is None


def test_extrator_openai_tenta_de_novo_em_429_e_5xx(prompt):
    servidor, base_url, pedidos = servidor_falso(
        [(429, {"error": "limite"}), (503, {"error": "fora"}), (200, RESPOSTA_OK)]
    )
    esperas = []
    extrair = extrator_openai(prompt, base_url, "qwen-x", None, dormir=esperas.append)
    extracao = extrair("texto")
    servidor.server_close()

    assert len(pedidos) == 3
    assert esperas == [2.0, 4.0]
    assert extracao.afirmacoes == [{"texto": "Y", "quem_disse": "X"}]


def test_extrator_openai_nao_insiste_em_erro_do_pedido(prompt):
    servidor, base_url, pedidos = servidor_falso([(400, {"error": "pedido inválido"})])
    esperas = []
    extrair = extrator_openai(prompt, base_url, "qwen-x", None, dormir=esperas.append)
    with pytest.raises(urllib.error.HTTPError):
        extrair("texto")
    servidor.server_close()
    assert len(pedidos) == 1 and esperas == []


def test_amostra_com_limite_mantem_os_pares_juntos(tmp_path, prompt):
    registros = [
        {
            "id": f"fakebr-{rotulo}-{par}",
            "base": "fakebr",
            "par_id": par,
            "texto": f"{rotulo} {par}",
        }
        for par in range(30)
        for rotulo in ("fake", "true")
    ]
    cache = tmp_path / "padronizado_v1.jsonl"
    padronizar(registros, prompt, ExtratorContador(), cache, limite=10, log=silencioso)
    ids = {json.loads(linha)["id"] for linha in cache.read_text(encoding="utf-8").splitlines()}
    pares = {i.rsplit("-", 1)[1] for i in ids}
    assert len(ids) == 10 and len(pares) == 5  # 5 pares completos, não 10 falsas
    assert pares != {"0", "1", "2", "3", "4"}  # espalhados, não os primeiros


def test_exportar_poe_o_original_ao_lado_da_afirmacao(tmp_path, prompt):
    registros = [
        {"id": "a", "base": "fakebr", "veracidade": "falso", "texto": "Texto longo da notícia."},
        {"id": "b", "base": "fakebr", "veracidade": "verdadeiro", "texto": "Outro texto."},
    ]
    cache = {
        "a": {
            "afirmacoes": [
                {"texto": "Afirmação 1", "quem_disse": "Fulano"},
                {"texto": "Afirmação 2"},
            ]
        }
    }
    destino = tmp_path / "conferencia.csv"
    assert exportar(registros, cache, destino) == 1
    linhas = list(csv.DictReader(open(destino, encoding="utf-8-sig")))
    assert linhas[0]["texto_original"] == "Texto longo da notícia."
    assert linhas[0]["afirmacao_1"] == "Afirmação 1" and linhas[0]["quem_disse_1"] == "Fulano"
    assert linhas[0]["n_afirmacoes"] == "2" and linhas[0]["demais_afirmacoes"] == "Afirmação 2"
