from types import SimpleNamespace

from app.jobs.reanalisar_questoes import reanalisar
from app.ml.classificador import FakeClassificador
from app.ml.llm import FakeLLMClient


class Registro(FakeClassificador):
    def __init__(self, texto_de_entrada="original"):
        self.texto_de_entrada = texto_de_entrada
        self.entradas = []

    def analisar(self, afirmacao, limiar):
        self.entradas.append((afirmacao, limiar))
        return super().analisar(afirmacao, limiar)


def questao(statement, versao, claim_text=None):
    return SimpleNamespace(
        statement=statement,
        claim_text=claim_text,
        model_category=None,
        model_score=None,
        model_confidence=None,
        model_version=versao,
    )


def test_refaz_so_as_de_outra_versao_com_o_limiar_do_admin():
    antiga, atual = questao("Manchete antiga", "referencia-2026-10-07"), questao("Atual", "fake")
    classificador = Registro()
    assert reanalisar([antiga, atual], classificador, todas=False) == (1, 0)
    assert classificador.entradas == [("Manchete antiga", "admin")]
    assert antiga.model_version == "fake" and antiga.model_category and antiga.model_confidence


def test_todas_e_afirmacao_extraida_no_modelo_padronizado():
    com_afirmacao = questao("Manchete", "fake", claim_text="Afirmação extraída")
    sem_afirmacao = questao("Outra manchete", None)
    classificador = Registro("hibrido")
    assert reanalisar([com_afirmacao, sem_afirmacao], classificador, todas=True) == (2, 0)
    assert [e for e, _ in classificador.entradas] == ["Afirmação extraída", "Outra manchete"]


def test_modelo_hibrido_extrai_a_afirmacao_que_falta_e_reanalisa():
    classificador = Registro("hibrido")
    sem_afirmacao = questao("Manchete sem afirmação", classificador.versao)
    com_afirmacao = questao("Manchete", classificador.versao, claim_text="Já extraída")
    resultado = reanalisar([sem_afirmacao, com_afirmacao], classificador, False, FakeLLMClient())
    assert resultado == (1, 1)
    assert sem_afirmacao.claim_text == "Manchete sem afirmação"
    assert classificador.entradas == [("Manchete sem afirmação", "admin")]


def test_modelo_original_nao_chama_a_llm():
    classificador = Registro("original")
    questao_sem = questao("Manchete", None)
    assert reanalisar([questao_sem], classificador, False, FakeLLMClient()) == (1, 0)
    assert questao_sem.claim_text is None
