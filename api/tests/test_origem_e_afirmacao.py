"""Origem da alegação na resposta e afirmação extraída para o modelo padronizado."""

from datetime import date, datetime

import pytest

from app.core.config import get_settings
from app.ml.classificador import FakeClassificador
from app.ml.llm import Afirmacao, Extracao, FakeLLMClient, LLMIndisponivel
from app.models.question import Question
from app.services.classificador_service import ClassificadorService
from app.services.match_service import origem_da_afirmacao
from app.services.noticias_service import NoticiasService, explicacao
from tests.test_noticias import checagem, noticia


class ClassificadorPadronizado(FakeClassificador):
    texto_de_entrada = "padronizado"

    def __init__(self):
        self.recebidos = []

    def analisar(self, afirmacao, limiar):
        self.recebidos.append(afirmacao)
        return super().analisar(afirmacao, limiar)


class LLMQueExtrai(FakeLLMClient):
    def extrair_afirmacoes(self, texto):
        return Extracao(e_opiniao=False, afirmacoes=[Afirmacao(texto="Afirmação extraída")])


class LLMFora(FakeLLMClient):
    def extrair_afirmacoes(self, texto):
        raise LLMIndisponivel("fora do ar")


@pytest.mark.parametrize(
    "autor, inicio",
    [
        (None, "Circulou nas redes sociais em 30/09/2026."),
        ("WhatsApp", "Circulou no WhatsApp em 30/09/2026."),
        ("Jair Bolsonaro", "Afirmação de Jair Bolsonaro em 30/09/2026."),
    ],
)
def test_explicacao_da_checagem_destaca_onde_circulou(autor, inicio):
    falsa = checagem("Vacina contém chip", "falso", False)
    falsa.origem_autor, falsa.origem_data = autor, date(2026, 9, 30)
    assert explicacao(falsa) == f"{inicio} Agência Teste checou e concluiu que é falsa."


def test_explicacao_da_manchete_cita_o_veiculo():
    manchete = noticia("Prefeitura abre vagas em creches")
    manchete.publicada_em = datetime(2026, 10, 14)
    assert explicacao(manchete) == "Manchete publicada por Jornal Teste em 14/10/2026."


def test_origem_na_resposta_e_nula_nas_questoes_sem_origem():
    alegacao = Question(origin_author="WhatsApp", origin_date=date(2026, 9, 30))
    materia = Question(origin_author="G1", origin_link="https://g1.globo.com/x")
    assert origem_da_afirmacao(alegacao).kind == "alegacao"
    assert origem_da_afirmacao(alegacao).when == date(2026, 9, 30)
    assert origem_da_afirmacao(materia).kind == "materia"
    assert origem_da_afirmacao(Question()) is None


def test_afirmacao_extraida_so_com_modelo_padronizado():
    padronizado = NoticiasService(None, [], ClassificadorPadronizado(), LLMQueExtrai())
    assert padronizado.afirmacao("Manchete qualquer") == "Afirmação extraída"
    original = NoticiasService(None, [], FakeClassificador(), LLMQueExtrai())
    assert original.afirmacao("Manchete qualquer") is None
    sem_llm = NoticiasService(None, [], ClassificadorPadronizado(), LLMFora())
    assert sem_llm.afirmacao("Manchete qualquer") is None


@pytest.fixture
def palpite_ligado(monkeypatch):
    monkeypatch.setenv("CLASSIFICADOR_NO_JOGO", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_palpite_usa_a_afirmacao_extraida_com_modelo_padronizado(palpite_ligado):
    classificador = ClassificadorPadronizado()
    servico = ClassificadorService(classificador)
    servico.palpite_do_jogo("Manchete do jogo", "Afirmação extraída")
    servico.palpite_do_jogo("Questão humana", None)
    assert classificador.recebidos == ["Afirmação extraída", "Questão humana"]


def test_palpite_ignora_a_afirmacao_com_modelo_original(palpite_ligado):
    classificador = ClassificadorPadronizado()
    classificador.texto_de_entrada = "original"
    ClassificadorService(classificador).palpite_do_jogo("Manchete do jogo", "Afirmação extraída")
    assert classificador.recebidos == ["Manchete do jogo"]
