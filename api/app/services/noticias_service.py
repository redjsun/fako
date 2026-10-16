"""Notícias externas viram rascunhos de afirmações do jogo, com a análise do classificador.

Fluxo: cada provedor entrega os textos (com mais de um, a quantidade pedida é dividida entre
eles, para equilibrar as falsas das checagens com as verdadeiras das manchetes); cada um é
normalizado para o formato do treino
(ml/normalizacao.py), passa pelos filtros (os das matérias de portal nas manchetes;
tamanho, mídia, conclusão embutida e, opcionalmente, política nas alegações checadas), sai se
já existe no banco (mesma URL ou mesmo texto) e é analisado pelo classificador com o limiar do
admin. Manchete de veículo entra verdadeira (foi publicada); alegação checada entra com o lado
do veredito da agência (as enganosas ou ambíguas ficam de fora). Entram como rascunho, para a
revisão humana em /admin/questions/{id}/review, ou, com NOTICIAS_PUBLICAR_DIRETO, já validadas.
O rótulo nunca é o do classificador: a análise dele fica só como registro.

Se o classificador estiver indisponível, a notícia entra mesmo assim, sem análise. Se o
modelo publicado foi treinado no texto padronizado pela LLM, a manchete passa antes pelo mesmo
prompt de extração (`claim_text`), e é essa afirmação que o classificador recebe, aqui e no
palpite mostrado ao jogador.

Ao jogador, a explicação destaca **onde a alegação circulou** (quem publicou e quando, do
`claimant` da Fact Check API; nas manchetes, o veículo), e a checagem fica como apoio em
`source`.

Rotina diária (app/jobs/): `importar_lote()` traz as notícias do dia, só as publicadas dentro
da janela de retenção e equilibradas (`por_lado`: até 25 falsas e 25 verdadeiras; um lado
curto não é completado com o outro); `limpar()` tira do banco as importadas há mais de
NOTICIAS_RETENCAO_DIAS (30). As que algum jogador respondeu, ou que estão em jogo numa partida,
são arquivadas em vez de apagadas: saem do jogo e ficam para o histórico e a revisão.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.noticias_client import Noticia, NoticiasClient, NoticiasIndisponiveis
from app.ml.classificador import (
    Analise,
    ClassificadorClient,
    ClassificadorIndisponivel,
)
from app.ml.llm import LLMClient, LLMIndisponivel, RespostaInvalida
from app.ml.normalizacao import (
    PLATAFORMAS,
    REDES_SOCIAIS,
    motivo_descarte,
    normalizar_manchete,
)
from app.models.category import Category
from app.models.question import Question, QuestionOrigin, QuestionStatus
from app.repositories.question_repository import QuestionRepository
from app.schemas.admin_schema import NewsDiscarded, NewsImportRequest, NewsImportResponse
from app.services import game_rules
from app.services.classificador_service import ClassificadorService
from app.services.content_service import ContentService, to_admin_response

# Os filtros descartam boa parte das alegações checadas (a maioria é política ou depende de
# mídia): o provedor entrega um lote maior e a importação para ao chegar na quantidade pedida.
CANDIDATOS = 100


def onde_circulou(autor: str | None) -> str:
    """ "redes sociais" -> "Circulou nas redes sociais"; "WhatsApp" -> "Circulou no WhatsApp";
    "Jair Bolsonaro" -> "Afirmação de Jair Bolsonaro"."""
    if not autor or autor == REDES_SOCIAIS:
        return "Circulou nas redes sociais"
    if autor in PLATAFORMAS.values():
        return f"Circulou no {autor}"
    return f"Afirmação de {autor}"


def afirmacao_extraida(llm: LLMClient, manchete: str) -> str | None:
    """A primeira afirmação extraída pelo prompt da padronização (#20); None sem afirmação
    (opinião) ou com a LLM fora."""
    try:
        extracao = llm.extrair_afirmacoes(manchete)
    except (LLMIndisponivel, RespostaInvalida):
        return None
    return extracao.afirmacoes[0].texto if extracao.afirmacoes else None


AVALIACAO = {
    "falso": "não confiável",
    "enganoso": "enganosa",
    "confere": "confiável",
    "incerto": "incerto",
}


def seguranca(confianca: float) -> str:
    return "alta" if confianca >= 0.75 else "média" if confianca >= 0.6 else "baixa"


def dados_da_explicacao(
    question: Question, analise: Analise, noticia: Noticia | None = None
) -> dict:
    """O que a LLM recebe para escrever o "Por quê?": a avaliação do classificador (limiar do
    jogador), o gabarito e a fonte dele, nada mais.

    A `fonte` é a explicação factual da importação ("Aos Fatos checou e concluiu que é falsa",
    "Manchete publicada por..."); sem a notícia (questões já no banco), vem da própria questão.
    """
    avaliacao = AVALIACAO.get(analise.categoria, analise.categoria)
    gabarito = "confiável" if question.is_true else "não confiável"
    checagem = bool(noticia.veredito) if noticia else "checou e concluiu" in question.explanation
    return {
        "afirmacao": question.statement,
        "ja_escrito": frase_do_classificador(avaliacao, seguranca(analise.confianca)),
        "gabarito": gabarito,
        # Enganosa conta como não confiável no jogo, que é uma barra de confiabilidade.
        "concorda": None
        if avaliacao == "incerto"
        else (avaliacao == "confiável") == question.is_true,
        "tipo": "checagem" if checagem else "manchete",
        "fonte": explicacao(noticia) if noticia else question.explanation,
        "detalhe": ((noticia.descricao or None) if noticia else question.source_detail),
    }


def frase_do_classificador(avaliacao: str, nivel: str) -> str:
    """A primeira frase do "Por quê?", escrita aqui e não pela LLM, para não variar."""
    if avaliacao == "incerto":
        return "O classificador do jogo não teve segurança para avaliar esta afirmação."
    return (
        f"O classificador do jogo avaliou esta afirmação como {avaliacao}, com {nivel} segurança."
    )


def explicacao_didatica(llm: LLMClient, dados: dict) -> str | None:
    """O "Por quê?": a frase do classificador e o resto escrito pela LLM; None se ela falhar ou
    citar o que não está nos dados (o jogador vê a explicação factual)."""
    try:
        return f"{dados['ja_escrito']} {llm.explicar_resposta(dados)}"
    except (LLMIndisponivel, RespostaInvalida):
        return None


def explicacao(noticia: Noticia) -> str:
    if noticia.veredito:
        data = noticia.origem_data or (noticia.publicada_em and noticia.publicada_em.date())
        quando = f" em {data:%d/%m/%Y}" if data else ""
        agencia = noticia.veiculo or "Uma agência de checagem"
        lado = "verdadeira" if noticia.verdadeira else "falsa"
        circulou = onde_circulou(noticia.origem_autor)
        return f"{circulou}{quando}. {agencia} checou e concluiu que é {lado}."
    quando = f" em {noticia.publicada_em:%d/%m/%Y}" if noticia.publicada_em else ""
    veiculo = noticia.veiculo or "um veículo de imprensa"
    return f"Manchete publicada por {veiculo}{quando}."


def fonte(noticia: Noticia) -> str:
    """URL gravada em Question.source (String(500)); a deduplicação compara com esta."""
    return noticia.url[:500]


@dataclass
class Limpeza:
    apagadas: int
    arquivadas: int


def antiga(noticia: Noticia, limite: datetime | None) -> bool:
    if limite is None or noticia.publicada_em is None:
        return False
    publicada = noticia.publicada_em
    if publicada.tzinfo is None:
        publicada = publicada.replace(tzinfo=timezone.utc)
    return publicada < limite


def motivo(noticia: Noticia, texto: str) -> str | None:
    if noticia.veredito is None:
        return motivo_descarte(texto, noticia.url)
    if noticia.verdadeira is None:
        return f"veredito sem lado no jogo ({noticia.veredito})"
    sem_politica = get_settings().noticias_sem_politica
    return motivo_descarte(texto, noticia.url, checagem=True, sem_politica=sem_politica)


class NoticiasService:
    def __init__(
        self,
        db: Session,
        noticias: list[NoticiasClient],
        classificador: ClassificadorClient,
        llm: LLMClient | None = None,
    ) -> None:
        self.provedores = noticias
        self.classificador = classificador
        self.llm = llm
        self.por_lado: int | None = None
        self.questions = QuestionRepository(db)
        self.content = ContentService(db)

    def importar(self, data: NewsImportRequest) -> NewsImportResponse:
        return self.importar_lote(data.category, data.quantity)

    def importar_lote(
        self,
        categoria: str,
        quantidade: int,
        max_idade_dias: int | None = None,
        por_lado: int | None = None,
    ) -> NewsImportResponse:
        """Importa até `quantidade` notícias; com `max_idade_dias`, descarta as mais velhas, e
        com `por_lado`, importa no máximo esse tanto de falsas e esse tanto de verdadeiras."""
        category = self.content.get_category(categoria)
        limite = (
            datetime.now(timezone.utc) - timedelta(days=max_idade_dias)
            if max_idade_dias is not None
            else None
        )
        importadas, descartadas = [], []
        vistas: set[str] = set()
        falhas = []
        restante = quantidade
        self.por_lado = por_lado
        for posicao, provedor in enumerate(self.provedores):
            # Cada provedor fica com a sua parte do que falta; um fora do ar não derruba os outros.
            # Com `por_lado`, quem equilibra é o teto de cada lado, não a parte do provedor.
            cota = (
                restante
                if por_lado is not None
                else math.ceil(restante / (len(self.provedores) - posicao))
            )
            try:
                noticias = provedor.buscar(CANDIDATOS)
            except NoticiasIndisponiveis as erro:
                falhas.append(erro)
                continue
            antes = len(importadas)
            recentes = []
            for noticia in noticias:
                if antiga(noticia, limite):
                    descartadas.append(NewsDiscarded(title=noticia.titulo, reason="notícia antiga"))
                else:
                    recentes.append(noticia)
            self._importar(recentes, cota, category, importadas, descartadas, vistas)
            restante -= len(importadas) - antes
        if falhas and len(falhas) == len(self.provedores):
            raise falhas[0]
        return NewsImportResponse(
            imported=[to_admin_response(q) for q in importadas], discarded=descartadas
        )

    def _importar(
        self,
        noticias: list[Noticia],
        cota: int,
        category: Category,
        importadas: list[Question],
        descartadas: list[NewsDiscarded],
        vistas: set[str],
    ) -> None:
        inicio = len(importadas)
        for noticia in noticias:
            if len(importadas) - inicio == cota:
                break
            if self.lado_cheio(noticia, importadas):
                continue
            # Nas checagens o "veículo" é a agência, que não aparece no texto da alegação.
            manchete = normalizar_manchete(
                noticia.titulo, None if noticia.veredito else noticia.veiculo
            )
            descarte = motivo(noticia, manchete)
            if descarte is None and (
                manchete.casefold() in vistas
                or self.questions.exists_by_statement_or_source(manchete, fonte(noticia))
            ):
                descarte = "já importada"
            if descarte:
                descartadas.append(NewsDiscarded(title=noticia.titulo, reason=descarte))
                continue
            vistas.add(manchete.casefold())
            importadas.append(self._rascunho(manchete, noticia, category))

    def lado_cheio(self, noticia: Noticia, importadas: list[Question]) -> bool:
        if self.por_lado is None or noticia.verdadeira is None:
            return False
        lado = sum(q.is_true == noticia.verdadeira for q in importadas)
        return lado >= self.por_lado

    def _rascunho(self, manchete: str, noticia: Noticia, category: Category) -> Question:
        question = Question(
            statement=manchete,
            is_true=bool(noticia.verdadeira),
            reliability_reference=game_rules.default_reliability_reference(
                bool(noticia.verdadeira)
            ),
            explanation=explicacao(noticia),
            source=fonte(noticia),
            category=category,
            status=QuestionStatus.DRAFT,
            origin=QuestionOrigin.NEWS,
        )
        if noticia.veredito:
            question.origin_author = noticia.origem_autor or REDES_SOCIAIS
            question.origin_date = noticia.origem_data
        else:  # manchete: a origem é o próprio veículo, com o link da matéria
            question.origin_author = (noticia.veiculo or "")[:200] or None
            question.origin_link = fonte(noticia)
            question.origin_date = noticia.publicada_em.date() if noticia.publicada_em else None
        question.claim_text = self.afirmacao(manchete)
        question.source_detail = (noticia.descricao or "").strip()[:1000] or None

        if get_settings().noticias_publicar_direto:
            question.status = QuestionStatus.VALIDATED
            question.validated_at = datetime.now(timezone.utc)
        try:
            analise = self.classificador.analisar(
                question.claim_text or manchete, "admin", enunciado=manchete
            )
        except ClassificadorIndisponivel:
            analise = None
        if analise:
            question.model_category = analise.categoria
            question.model_score = analise.nota
            question.model_confidence = analise.confianca
            question.model_version = analise.versao_modelo
        question.model_explanation = self.explicacao_do_jogo(question, noticia)
        return self.questions.add(question)

    def explicacao_do_jogo(self, question: Question, noticia: Noticia | None = None) -> str | None:
        """O "Por quê?" da LLM sobre a avaliação que o jogador vai ver (limiar do jogador)."""
        if self.llm is None:
            return None
        analise = ClassificadorService(self.classificador).analise_do_jogo(
            question.statement, question.claim_text
        )
        if analise is None:
            return None
        return explicacao_didatica(self.llm, dados_da_explicacao(question, analise, noticia))

    def afirmacao(self, manchete: str) -> str | None:
        """A afirmação no formato do treino padronizado, se o modelo publicado foi treinado nele.

        Mesmo prompt da padronização (#20); a primeira afirmação, como no treino. Sem LLM, ou
        com a LLM fora, fica None e o classificador recebe a manchete.
        """
        # No híbrido, a manchete (que não é texto curto de checagem) também vai pela extração.
        if self.llm is None or self.classificador.texto_de_entrada == "original":
            return None
        return afirmacao_extraida(self.llm, manchete)

    def limpar(self, dias: int) -> Limpeza:
        """Apaga as notícias importadas há mais de `dias`; arquiva as que estão em uso."""
        vencidas = self.questions.news_created_before(
            datetime.now(timezone.utc) - timedelta(days=dias)
        )
        ids = {q.id for q in vencidas}
        em_uso = self.questions.ids_in_use(ids)
        for question in vencidas:
            if question.id in em_uso:
                question.status = QuestionStatus.ARCHIVED
        self.questions.db.flush()  # a sessão não grava sozinha (autoflush=False)
        self.questions.delete_ids(ids - em_uso)
        return Limpeza(apagadas=len(ids - em_uso), arquivadas=len(em_uso))
