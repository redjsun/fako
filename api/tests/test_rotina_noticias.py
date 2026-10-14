import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ml.classificador import FakeClassificador
from app.models.category import Category
from app.models.level import Level
from app.models.match import Match, MatchAnswer
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.models.user import User
from app.services.noticias_service import NoticiasService
from tests.test_noticias import NoticiasDeTeste, checagem, noticia

AGORA = datetime.now(timezone.utc)


@pytest.fixture
def db(monkeypatch):
    # Os padrões, independentes do .env de quem roda os testes.
    monkeypatch.setenv("NOTICIAS_PUBLICAR_DIRETO", "false")
    monkeypatch.setenv("NOTICIAS_SEM_POLITICA", "false")
    get_settings.cache_clear()
    with SessionLocal() as sessao:
        yield sessao
        sessao.rollback()  # nada do teste fica no banco
    get_settings.cache_clear()


def questao(db, dias: int, origem=QuestionOrigin.NEWS) -> Question:
    q = Question(
        statement=f"Notícia {uuid.uuid4().hex}",
        is_true=True,
        reliability_reference=90,
        explanation="Manchete publicada.",
        source=f"https://jornal.teste/{uuid.uuid4().hex}",
        category=db.scalar(select(Category).limit(1)),
        status=QuestionStatus.VALIDATED,
        origin=origem,
        created_at=AGORA - timedelta(days=dias),
    )
    db.add(q)
    db.flush()
    return q


def partida(db) -> Match:
    user = User(username=f"jogador_{uuid.uuid4().hex[:8]}", password_hash="x")
    db.add(user)
    db.flush()
    match = Match(user_id=user.id, level_id=db.scalar(select(Level.id).limit(1)))
    db.add(match)
    db.flush()
    return match


def test_limpeza_apaga_as_vencidas_e_arquiva_as_que_estao_em_uso(db):
    vencida = questao(db, dias=31)
    respondida = questao(db, dias=40)
    em_jogo = questao(db, dias=35)
    recente = questao(db, dias=5)
    humana_antiga = questao(db, dias=90, origem=QuestionOrigin.HUMAN)
    match = partida(db)
    db.add(MatchAnswer(match_id=match.id, question_id=respondida.id, answer=True, is_correct=True))
    match.current_question_id = em_jogo.id
    db.flush()
    ids = {vencida.id, respondida.id, em_jogo.id, recente.id, humana_antiga.id}

    limpeza = NoticiasService(db, [], FakeClassificador()).limpar(dias=30)
    db.expire_all()

    restantes = {q.id: q.status for q in db.scalars(select(Question).where(Question.id.in_(ids)))}
    assert vencida.id not in restantes
    assert restantes[respondida.id] == QuestionStatus.ARCHIVED
    assert restantes[em_jogo.id] == QuestionStatus.ARCHIVED
    assert restantes[recente.id] == QuestionStatus.VALIDATED
    assert restantes[humana_antiga.id] == QuestionStatus.VALIDATED  # só notícias saem
    assert limpeza.apagadas >= 1 and limpeza.arquivadas >= 2


def test_importacao_diaria_ignora_noticias_fora_da_janela(db):
    velha = checagem(f"Alegação velha {uuid.uuid4().hex[:6]}", "Falso", False)
    velha.publicada_em = AGORA - timedelta(days=60)
    nova = noticia(f"Ministério anuncia campanha de vacinação {uuid.uuid4().hex[:6]}")
    nova.publicada_em = AGORA - timedelta(days=1)
    service = NoticiasService(db, [NoticiasDeTeste([velha, nova])], FakeClassificador())

    resultado = service.importar_lote("saude", 15, max_idade_dias=30)

    assert [q.source for q in resultado.imported] == [nova.url]
    assert [d.reason for d in resultado.discarded] == ["notícia antiga"]


def test_arquivada_nao_volta_ao_jogo(db):
    q = questao(db, dias=40)
    match = partida(db)
    db.add(MatchAnswer(match_id=match.id, question_id=q.id, answer=True, is_correct=True))
    db.flush()
    NoticiasService(db, [], FakeClassificador()).limpar(dias=30)
    validadas = db.scalars(select(Question.id).where(Question.status == QuestionStatus.VALIDATED))
    assert q.id not in set(validadas)


def test_importacao_diaria_equilibra_falsas_e_verdadeiras(db):
    marca = uuid.uuid4().hex[:6]
    checagens = [
        checagem(f"Chá de {marca} cura a dengue em {i} dias", "Falso", False) for i in range(5)
    ]
    checagens.append(checagem(f"Governo distribuiu {marca} vacinas em outubro", "Verdadeiro", True))
    manchetes = [
        noticia(f"Prefeitura {marca} inaugura posto de saúde no bairro {i}") for i in range(5)
    ]
    for item in checagens + manchetes:
        item.publicada_em = AGORA - timedelta(days=1)
    service = NoticiasService(
        db, [NoticiasDeTeste(checagens), NoticiasDeTeste(manchetes)], FakeClassificador()
    )

    resultado = service.importar_lote("saude", 6, max_idade_dias=30, por_lado=3)

    lados = [q.is_true for q in resultado.imported]
    assert lados.count(False) == 3 and lados.count(True) == 3
    # A checagem verdadeira conta no lado das verdadeiras: entram só 2 manchetes.
    assert sum(q.source.startswith("https://jornal.teste") for q in resultado.imported) == 2


def test_lado_curto_nao_e_completado_com_o_outro(db):
    marca = uuid.uuid4().hex[:6]
    checagens = [
        checagem(f"Chá de {marca} cura a gripe em {i} dias", "Falso", False) for i in range(6)
    ]
    for item in checagens:
        item.publicada_em = AGORA - timedelta(days=1)
    service = NoticiasService(db, [NoticiasDeTeste(checagens)], FakeClassificador())

    resultado = service.importar_lote("saude", 6, max_idade_dias=30, por_lado=3)

    assert [q.is_true for q in resultado.imported] == [False, False, False]
