import { httpGet, httpPost } from "./httpClient";
import { LOCAL_LEVELS } from "./levelService";
import { AnswerResult, Match, MatchResult, Question } from "../types";

// Mesmas regras da API (api/app/services/game_rules.py), usadas quando ela está fora do ar.
const RELIABILITY_TOLERANCE = 15;
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

function answerLocally(questionId: number, reliability: number): AnswerResult {
  const question = LOCAL_QUESTIONS.find((item) => item.id === questionId) || LOCAL_QUESTIONS[0];
  const distance = Math.abs(reliability - question.reliability_reference);
  const isCorrect = distance <= RELIABILITY_TOLERANCE;

  if (activeLocalMatch && isCorrect) {
    activeLocalMatch.match.score += POINTS_PER_CORRECT_ANSWER;
  }

  return {
    is_correct: isCorrect,
    correct_answer: question.is_true,
    reliability,
    reliability_reference: question.reliability_reference,
    tolerance: RELIABILITY_TOLERANCE,
    distance,
    explanation: question.explanation,
    source: question.source,
    score: activeLocalMatch ? activeLocalMatch.match.score : isCorrect ? POINTS_PER_CORRECT_ANSWER : 0,
  };
}

export const matchService = {
  async startMatch(level?: number): Promise<Match> {
    try {
      const match = await httpPost<Match>("/matches", { level });
      activeLocalMatch = null;
      return match;
    } catch {
      // Fallback local caso o backend esteja offline
      const lvlNum = level && level >= 1 && level <= 6 ? level : 1;
      const lvlConfig = LOCAL_LEVELS.find((l) => l.number === lvlNum) || LOCAL_LEVELS[0];

      const mockMatch: Match = {
        id: Date.now(),
        level: lvlConfig,
        score: 0,
        status: "in_progress",
        duration_seconds: 120,
        started_at: new Date().toISOString(),
        ended_at: null,
      };

      const indices = LOCAL_QUESTIONS.map((_, i) => i).sort(() => Math.random() - 0.5);
      activeLocalMatch = {
        match: mockMatch,
        questionIndices: indices,
        cursor: 0,
      };

      return mockMatch;
    }
  },

  async getMatch(matchId: number): Promise<Match> {
    try {
      return await httpGet<Match>(`/matches/${matchId}`);
    } catch {
      if (activeLocalMatch && activeLocalMatch.match.id === matchId) {
        return activeLocalMatch.match;
      }
      return {
        id: matchId,
        level: LOCAL_LEVELS[0],
        score: 0,
        status: "in_progress",
        duration_seconds: 120,
        started_at: new Date().toISOString(),
        ended_at: null,
      };
    }
  },

  async getNextQuestion(matchId: number): Promise<Question> {
    try {
      return await httpGet<Question>(`/matches/${matchId}/next-question`);
    } catch {
      let question: LocalQuestionSeed;
      if (activeLocalMatch) {
        const { questionIndices, cursor } = activeLocalMatch;
        question = LOCAL_QUESTIONS[questionIndices[cursor % questionIndices.length]];
        activeLocalMatch.cursor += 1;
      } else {
        question = LOCAL_QUESTIONS[Math.floor(Math.random() * LOCAL_QUESTIONS.length)];
      }
      return { id: question.id, statement: question.statement };
    }
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

  async finishMatch(matchId: number): Promise<MatchResult> {
    try {
      return await httpPost<MatchResult>(`/matches/${matchId}/finish`);
    } catch {
      const currentScore = activeLocalMatch ? activeLocalMatch.match.score : 0;
      const currentLvl = activeLocalMatch ? activeLocalMatch.match.level.number : 1;
      const minScore = activeLocalMatch
        ? activeLocalMatch.match.level.min_score_to_advance
        : 30;
      const advanced = currentScore >= minScore;
      const nextLvl = advanced ? Math.min(6, currentLvl + 1) : currentLvl;

      const finishedMatch: Match = activeLocalMatch
        ? {
            ...activeLocalMatch.match,
            score: currentScore,
            status: "finished",
            ended_at: new Date().toISOString(),
          }
        : {
            id: matchId,
            level: LOCAL_LEVELS[0],
            score: currentScore,
            status: "finished",
            duration_seconds: 120,
            started_at: new Date().toISOString(),
            ended_at: new Date().toISOString(),
          };

      return {
        match: finishedMatch,
        advanced,
        current_level: nextLvl,
      };
    }
  },
};
