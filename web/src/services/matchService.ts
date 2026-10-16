import { HttpError, httpGet, httpPost, isApiUnavailable, isGuestSession } from "./httpClient";
import { LOCAL_LEVELS } from "./levelService";
import { AnswerResult, Match, MatchResult, Question } from "../types";

// Mesmas regras da API (api/app/services/game_rules.py e o nível da partida), usadas quando
// ela está fora do ar.
const POINTS_PER_CORRECT_ANSWER = 10;

interface LocalQuestionSeed {
  id: number;
  statement: string;
  is_true: boolean;
  reliability_reference: number;
  explanation: string;
  source: string;
}

// Ids negativos: nunca coincidem com os do banco, então uma pergunta local nunca é
// respondida na API (que corrigiria contra outra questão).
const LOCAL_QUESTIONS: LocalQuestionSeed[] = [
  {
    id: -1,
    statement: "Vacinas causam autismo.",
    is_true: false,
    reliability_reference: 5,
    explanation:
      "O estudo de 1998 que sugeriu essa relação foi retratado por fraude, e pesquisas com milhões de crianças não encontraram ligação entre vacinas e autismo.",
    source: "Organização Mundial da Saúde (OMS)",
  },
  {
    id: -2,
    statement: "Lavar as mãos com água e sabão reduz a transmissão de doenças infecciosas.",
    is_true: true,
    reliability_reference: 95,
    explanation:
      "A higiene das mãos remove microrganismos e é uma das medidas mais eficazes para prevenir infecções.",
    source: "Organização Mundial da Saúde (OMS)",
  },
  {
    id: -3,
    statement: "O modo anônimo do navegador impede que o provedor de internet veja os sites acessados.",
    is_true: false,
    reliability_reference: 10,
    explanation:
      "O modo anônimo apenas não salva histórico e cookies no aparelho; o provedor, a rede da escola ou do trabalho e os próprios sites ainda podem ver o acesso.",
    source: "Central de Ajuda do Google Chrome",
  },
  {
    id: -4,
    statement: "Senhas longas são mais difíceis de descobrir por tentativa e erro do que senhas curtas.",
    is_true: true,
    reliability_reference: 90,
    explanation:
      "Cada caractere a mais multiplica o número de combinações possíveis, por isso o comprimento é um dos fatores mais importantes de uma senha forte.",
    source: "NIST SP 800-63B — Digital Identity Guidelines",
  },
  {
    id: -5,
    statement: "A Grande Muralha da China pode ser vista a olho nu da Lua.",
    is_true: false,
    reliability_reference: 5,
    explanation:
      "A muralha é longa, mas estreita demais para ser vista da Lua; nem da órbita baixa da Terra ela é facilmente visível sem auxílio.",
    source: "NASA",
  },
  {
    id: -6,
    statement: "O Brasil é o maior país da América do Sul em área territorial.",
    is_true: true,
    reliability_reference: 100,
    explanation:
      "Com cerca de 8,5 milhões de km², o Brasil ocupa quase metade do território da América do Sul.",
    source: "IBGE",
  },
  {
    id: -7,
    statement: "Chá de boldo cura qualquer infecção viral imediatamente.",
    is_true: false,
    reliability_reference: 5,
    explanation:
      "Embora ervas tenham propriedades digestivas, não há comprovação científica de que o boldo elimine infecções virais sistêmicas.",
    source: "Ministério da Saúde",
  },
  {
    id: -8,
    statement: "Autenticação em dois fatores (2FA) adiciona uma camada extra de proteção mesmo se sua senha vazar.",
    is_true: true,
    reliability_reference: 90,
    explanation:
      "Mesmo que criminosos tenham a senha, eles ainda precisarão do segundo fator (código gerado no celular ou chave física) para acessar a conta.",
    source: "CERT.br / CGI.br",
  },
  {
    id: -9,
    statement: "Checar a data de publicação de uma notícia ajuda a evitar o compartilhamento de fatos descontextualizados.",
    is_true: true,
    reliability_reference: 90,
    explanation:
      "Muitos boatos reutilizam notícias antigas fora de contexto para criar alarmismo ou desinformação sobre eventos atuais.",
    source: "Projeto Comprova",
  },
  {
    id: -10,
    statement: "Antibióticos são eficazes contra infecções virais comuns como a gripe.",
    is_true: false,
    reliability_reference: 5,
    explanation:
      "Antibióticos atuam exclusivamente contra bactérias. Seu uso indevido contra vírus não cura a doença e pode selecionar bactérias resistentes.",
    source: "ANVISA / OMS",
  },
  {
    id: -11,
    statement: "Mensagens com tom de urgência e links encurtados costumam ser táticas de phishing para roubo de dados.",
    is_true: true,
    reliability_reference: 85,
    explanation:
      "Criminosos usam o senso de urgência (bloqueio de conta, prêmios imediatos) para levar a vítima a clicar sem verificar a autenticidade.",
    source: "FEBRABAN",
  },
];

interface LocalMatchSession {
  match: Match;
  questionIndices: number[];
  cursor: number;
}

let activeLocalMatch: LocalMatchSession | null = null;

// Embaralhamento de Fisher–Yates (o sort com Math.random() favorece algumas ordens).
export function shuffled<T>(items: readonly T[], random: () => number = Math.random): T[] {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index--) {
    const other = Math.floor(random() * (index + 1));
    [result[index], result[other]] = [result[other], result[index]];
  }
  return result;
}

// Mesma regra da API (match_service.finish): avança quem bate a meta jogando o nível atual,
// enquanto houver nível acima.
export function advancesLevel(options: {
  matchLevel: number;
  currentLevel: number;
  score: number;
  minScoreToAdvance: number;
  maxLevel: number;
}): boolean {
  const { matchLevel, currentLevel, score, minScoreToAdvance, maxLevel } = options;
  return matchLevel === currentLevel && score >= minScoreToAdvance && currentLevel < maxLevel;
}

function startLocalMatch(level?: number): Match {
  const lvlConfig = LOCAL_LEVELS.find((item) => item.number === level) ?? LOCAL_LEVELS[0];
  const match: Match = {
    id: Date.now(),
    level: lvlConfig,
    score: 0,
    status: "in_progress",
    duration_seconds: lvlConfig.match_seconds,
    started_at: new Date().toISOString(),
    ended_at: null,
  };
  activeLocalMatch = {
    match,
    questionIndices: shuffled(LOCAL_QUESTIONS.map((_, index) => index)),
    cursor: 0,
  };
  return match;
}

function answerLocally(questionId: number, reliability: number): AnswerResult {
  const question = LOCAL_QUESTIONS.find((item) => item.id === questionId) || LOCAL_QUESTIONS[0];
  const rules = activeLocalMatch?.match.level ?? LOCAL_LEVELS[0];
  const distance = Math.abs(reliability - question.reliability_reference);
  const isCorrect = distance <= rules.reliability_tolerance;

  if (activeLocalMatch) {
    const score = activeLocalMatch.match.score;
    activeLocalMatch.match.score = isCorrect
      ? score + POINTS_PER_CORRECT_ANSWER
      : Math.max(0, score - rules.wrong_answer_penalty);
  }

  return {
    is_correct: isCorrect,
    correct_answer: question.is_true,
    reliability,
    reliability_reference: question.reliability_reference,
    tolerance: rules.reliability_tolerance,
    distance,
    explanation: question.explanation,
    source: question.source,
    score: activeLocalMatch ? activeLocalMatch.match.score : isCorrect ? POINTS_PER_CORRECT_ANSWER : 0,
  };
}

export const matchService = {
  async startMatch(level?: number): Promise<Match> {
    if (isGuestSession()) return startLocalMatch(level);
    try {
      const match = await httpPost<Match>("/matches", { level });
      activeLocalMatch = null;
      return match;
    } catch (error) {
      // Partida local só com a API fora do ar. Um erro de regra (ex.: nível ainda não
      // liberado) sobe para o jogo: virar partida local esconderia que nada é salvo.
      if (!isApiUnavailable(error)) throw error;
      return startLocalMatch(level);
    }
  },

  // A partida em andamento é a local (visitante ou API fora do ar)?
  isLocalMatch(matchId: number): boolean {
    return activeLocalMatch?.match.id === matchId;
  },

  async getNextQuestion(matchId: number): Promise<Question> {
    if (activeLocalMatch && activeLocalMatch.match.id === matchId) {
      const { questionIndices, cursor } = activeLocalMatch;
      // Cada afirmação local aparece uma vez por partida, como no banco da API.
      if (cursor >= questionIndices.length) {
        throw new HttpError("Não há mais questões disponíveis", 404);
      }
      const question = LOCAL_QUESTIONS[questionIndices[cursor]];
      activeLocalMatch.cursor += 1;
      return { id: question.id, statement: question.statement };
    }
    // Partida da API: as perguntas e o placar são só os dela; um erro (inclusive o 404 de
    // questões esgotadas) sobe para o jogo.
    return httpGet<Question>(`/matches/${matchId}/next-question`);
  },

  async answerQuestion(
    matchId: number,
    questionId: number,
    reliability: number
  ): Promise<AnswerResult> {
    if (questionId < 0) return answerLocally(questionId, reliability);
    // Questão do banco: só a API sabe a referência; uma falha aqui sobe para o jogo.
    return httpPost<AnswerResult>(`/matches/${matchId}/answers`, {
      question_id: questionId,
      reliability,
    });
  },

  // currentLevel: nível atual do jogador, usado só para decidir o avanço na partida local.
  async finishMatch(matchId: number, currentLevel: number): Promise<MatchResult> {
    const local = activeLocalMatch;
    if (!local || local.match.id !== matchId) {
      // Partida da API: uma falha sobe para o jogo avisar que o resultado não foi salvo.
      return httpPost<MatchResult>(`/matches/${matchId}/finish`);
    }

    activeLocalMatch = null;
    const advanced = advancesLevel({
      matchLevel: local.match.level.number,
      currentLevel,
      score: local.match.score,
      minScoreToAdvance: local.match.level.min_score_to_advance,
      maxLevel: LOCAL_LEVELS.length,
    });
    return {
      match: { ...local.match, status: "finished", ended_at: new Date().toISOString() },
      advanced,
      current_level: advanced ? currentLevel + 1 : currentLevel,
    };
  },
};
