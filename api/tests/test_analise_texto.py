import pytest

from app.core.exceptions import ServiceUnavailableError
from app.ml.classificador import ClassificadorAusente, FakeClassificador
from app.ml.llm import LLMValidado
from app.services.analise_texto_service import AnaliseTextoService
from tests.test_llm import PedidoRoteirizado


class ClassificadorEspiao(FakeClassificador):
    def __init__(self):
        self.recebidos = []

    def analisar(self, afirmacao, limiar, enunciado=None):
        self.recebidos.append(afirmacao)
        return super().analisar(afirmacao, limiar)


def servico(resposta: str, classificador=None) -> AnaliseTextoService:
    return AnaliseTextoService(
        LLMValidado(PedidoRoteirizado(resposta)), classificador or ClassificadorEspiao()
    )


def test_opiniao_pura_vira_uma_analise_opiniao_sem_classificador():
    classificador = ClassificadorEspiao()
    texto = "Acho que esse governo é o pior da história."
    [analise] = servico('{"e_opiniao": true, "afirmacoes": []}', classificador).analisar(
        texto, "admin"
    )
    assert analise.categoria == "opiniao" and analise.nota is None
    assert analise.versao_modelo == "extrair_afirmacoes_v1"
    assert classificador.recebidos == []


def test_varias_afirmacoes_viram_uma_analise_cada_e_preservam_quem_disse():
    classificador = ClassificadorEspiao()
    resposta = (
        '{"e_opiniao": false, "afirmacoes": ['
        '{"texto": "A vacina causa infertilidade", "quem_disse": "deputado Fulano"}, '
        '{"texto": "O Ministério ampliou a vacinação", "quem_disse": null}, '
        '{"texto": "A campanha vai até dezembro", "quem_disse": null}]}'
    )
    analises = servico(resposta, classificador).analisar("matéria longa...", "admin")
    assert [a.quem_disse for a in analises] == ["deputado Fulano", None, None]
    # O classificador recebe só a afirmação, nunca "Fulano disse que...".
    assert classificador.recebidos == [
        "A vacina causa infertilidade",
        "O Ministério ampliou a vacinação",
        "A campanha vai até dezembro",
    ]


def test_opiniao_com_fatos_nao_e_opiniao():
    resposta = (
        '{"e_opiniao": true, "afirmacoes": [{"texto": "O dólar subiu 5%", "quem_disse": null}]}'
    )
    [analise] = servico(resposta).analisar("Absurdo! O dólar subiu 5%.", "admin")
    assert analise.categoria != "opiniao"


def test_extracao_invalida_e_classificador_fora_viram_503():
    with pytest.raises(ServiceUnavailableError, match="Extração"):
        AnaliseTextoService(
            LLMValidado(PedidoRoteirizado("nada", "nada")), FakeClassificador()
        ).analisar("texto", "admin")
    resposta = '{"e_opiniao": false, "afirmacoes": [{"texto": "X aconteceu", "quem_disse": null}]}'
    with pytest.raises(ServiceUnavailableError, match="Análise indisponível"):
        servico(resposta, ClassificadorAusente("sem modelo")).analisar("texto", "admin")
