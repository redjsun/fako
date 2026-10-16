from types import SimpleNamespace

from app.jobs.reanalisar_questoes import reanalisar
from app.ml.classificador import FakeClassificador
from app.ml.llm import FakeLLMClient
from app.models.question import QuestionOrigin


class Registro(FakeClassificador):
    def __init__(self, texto_de_entrada="original"):
        self.texto_de_entrada = texto_de_entrada
        self.entradas = []

    def analisar(self, afirmacao, limiar):
        self.entradas.append((afirmacao, limiar))
        return super().analisar(afirmacao, limiar)


def questao(statement, versao, claim_text=None, origin=QuestionOrigin.HUMAN):
    return SimpleNamespace(
        statement=statement,
        claim_text=claim_text,
        origin=origin,
        is_true=False,
        explanation="Circulou nas redes sociais. Aos Fatos checou e concluiu que é falsa.",
        model_explanation=None,
        source_detail=None,
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


def test_noticia_ganha_o_por_que_da_llm_sobre_a_avaliacao_do_jogo():
    classificador = Registro("hibrido")
    noticia = questao(
        "Vacina contém chip", classificador.versao, "Vacina contém chip", QuestionOrigin.NEWS
    )
    seed = questao(
        "Lavar as mãos reduz doenças", classificador.versao, "Lavar as mãos reduz doenças"
    )
    reanalisar([noticia, seed], classificador, False, FakeLLMClient())
    assert noticia.model_explanation.startswith(
        "O classificador do jogo não teve segurança para avaliar esta afirmação."
    )
    assert "Aos Fatos checou" in noticia.model_explanation
    assert ("Vacina contém chip", "jogador") in classificador.entradas
    assert seed.model_explanation is None


def test_por_que_do_jogo_so_usa_a_explicacao_do_modelo_publicado(monkeypatch):
    from app.core.config import get_settings
    from app.services.match_service import MatchService

    monkeypatch.setenv("CLASSIFICADOR_NO_JOGO", "true")
    get_settings.cache_clear()
    try:
        servico = MatchService(None, Registro())
        atual = questao("Manchete", "fake")
        atual.model_explanation = "O classificador avaliou como não confiável."
        antiga = questao("Manchete", "outro-modelo")
        antiga.model_explanation = "Explicação de outro modelo."
        assert servico.explicacao(atual) == "O classificador avaliou como não confiável."
        assert servico.explicacao(antiga) == antiga.explanation
        monkeypatch.setenv("CLASSIFICADOR_NO_JOGO", "false")
        get_settings.cache_clear()
        assert servico.explicacao(atual) == atual.explanation
    finally:
        get_settings.cache_clear()


def test_detalhe_guardado_entra_no_por_que_refeito():
    from app.services.noticias_service import dados_da_explicacao

    noticia = questao("Vacina contém chip", "fake", origin=QuestionOrigin.NEWS)
    noticia.source_detail = "Vacinas não têm chips de rastreamento"
    analise = Registro().analisar("Vacina contém chip", "jogador")
    dados = dados_da_explicacao(noticia, analise)
    assert dados["detalhe"] == "Vacinas não têm chips de rastreamento"
    assert dados["tipo"] == "checagem" and dados["gabarito"] == "não confiável"


def test_salva_em_lotes_para_nao_perder_o_trabalho():
    from app.jobs.reanalisar_questoes import LOTE

    salvamentos = []
    questoes = [questao(f"Manchete {i}", "antiga") for i in range(2 * LOTE + 3)]
    reanalisar(questoes, Registro(), False, salvar=lambda: salvamentos.append(1))
    assert len(salvamentos) == 2
