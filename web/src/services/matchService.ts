import { httpGet, httpPost } from "./httpClient";
import { Match, Question, AnswerResult, MatchResult, Level } from "../types";

const LOCAL_LEVELS: Level[] = [
  { number: 1, board_size: 16, tick_ms: 160, min_score_to_advance: 30 },
  { number: 2, board_size: 16, tick_ms: 146, min_score_to_advance: 40 },
  { number: 3, board_size: 16, tick_ms: 132, min_score_to_advance: 50 },
  { number: 4, board_size: 16, tick_ms: 118, min_score_to_advance: 50 },
  { number: 5, board_size: 16, tick_ms: 104, min_score_to_advance: 60 },
  { number: 6, board_size: 16, tick_ms: 90, min_score_to_advance: 70 },
];

interface LocalQuestionSeed {
  id: number;
  category: string;
  statement: string;
  is_true: boolean;
  explanation: string;
  source: string;
}

const LOCAL_QUESTIONS: LocalQuestionSeed[] = [
  {
    id: 1,
    category: "Saúde",
    statement: "Vacinas causam autismo.",
    is_true: false,
    explanation:
      "O estudo de 1998 que sugeriu essa relação foi retratado por fraude, e pesquisas com milhões de crianças não encontraram ligação entre vacinas e autismo.",
    source: "Organização Mundial da Saúde (OMS)",
  },
  {
    id: 2,
    category: "Saúde",
    statement: "Lavar as mãos com água e sabão reduz a transmissão de doenças infecciosas.",
    is_true: true,
    explanation:
      "A higiene das mãos remove microrganismos e é uma das medidas mais eficazes para prevenir infecções.",
    source: "Organização Mundial da Saúde (OMS)",
  },
  {
    id: 3,
    category: "Tecnologia",
    statement: "O modo anônimo do navegador impede que o provedor de internet veja os sites acessados.",
    is_true: false,
    explanation:
      "O modo anônimo apenas não salva histórico e cookies no aparelho; o provedor, a rede da escola ou do trabalho e os próprios sites ainda podem ver o acesso.",
    source: "Central de Ajuda do Google Chrome",
  },
  {
    id: 4,
    category: "Tecnologia",
    statement: "Senhas longas são mais difíceis de descobrir por tentativa e erro do que senhas curtas.",
    is_true: true,
    explanation:
      "Cada caractere a mais multiplica o número de combinações possíveis, por isso o comprimento é um dos fatores mais importantes de uma senha forte.",
    source: "NIST SP 800-63B — Digital Identity Guidelines",
  },
  {
    id: 5,
    category: "Conhecimentos Gerais",
    statement: "A Grande Muralha da China pode ser vista a olho nu da Lua.",
    is_true: false,
    explanation:
      "A muralha é longa, mas estreita demais para ser vista da Lua; nem da órbita baixa da Terra ela é facilmente visível sem auxílio.",
    source: "NASA",
  },
  {
    id: 6,
    category: "Conhecimentos Gerais",
    statement: "O Brasil é o maior país da América do Sul em área territorial.",
    is_true: true,
    explanation:
      "Com cerca de 8,5 milhões de km², o Brasil ocupa quase metade do território da América do Sul.",
    source: "IBGE",
  },
  {
    id: 7,
    category: "Saúde",
    statement: "Chá de boldo cura qualquer infecção viral imediatamente.",
    is_true: false,
    explanation:
      "Embora ervas tenham propriedades digestivas, não há comprovação científica de que o boldo elimine infecções virais sistêmicas.",
    source: "Ministério da Saúde",
  },
  {
    id: 8,
    category: "Tecnologia",
    statement: "Autenticação em dois fatores (2FA) adiciona uma camada extra de proteção mesmo se sua senha vazar.",
    is_true: true,
    explanation:
      "Mesmo que criminosos tenham a senha, eles ainda precisarão do segundo fator (código gerado no celular ou chave física) para acessar a conta.",
    source: "CERT.br / CGI.br",
  },
  {
    id: 9,
    category: "Conhecimentos Gerais",
    statement: "Checar a data de publicação de uma notícia ajuda a evitar o compartilhamento de fatos descontextualizados.",
    is_true: true,
    explanation:
      "Muitos boatos reutilizam notícias antigas fora de contexto para criar alarmismo ou desinformação sobre eventos atuais.",
    source: "Projeto Comprova",
  },
  {
    id: 10,
    category: "Saúde",
    statement: "Antibióticos são eficazes contra infecções virais comuns como a gripe.",
    is_true: false,
    explanation:
      "Antibióticos atuam exclusivamente contra bactérias. Seu uso indevido contra vírus não cura a doença e pode selecionar bactérias resistentes.",
    source: "ANVISA / OMS",
  },
  {
    id: 11,
    category: "Tecnologia",
    statement: "Mensagens com tom de urgência e links encurtados costumam ser táticas de phishing para roubo de dados.",
    is_true: true,
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

export const matchService = {
  async startMatch(level?: number): Promise<Match> {
    try {
      return await httpPost<Match>("/matches", { level });
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
      if (activeLocalMatch) {
        const idx = activeLocalMatch.questionIndices[activeLocalMatch.cursor % activeLocalMatch.questionIndices.length];
        activeLocalMatch.cursor += 1;
        const q = LOCAL_QUESTIONS[idx];
        return {
          id: q.id,
          statement: q.statement,
          category: q.category,
          afirmacao: q.statement,
          categoria: q.category as any,
          explicacao: q.explanation,
          fonte: q.source,
        };
      }

      const randomIdx = Math.floor(Math.random() * LOCAL_QUESTIONS.length);
      const fallbackQ = LOCAL_QUESTIONS[randomIdx];
      return {
        id: fallbackQ.id,
        statement: fallbackQ.statement,
        category: fallbackQ.category,
        afirmacao: fallbackQ.statement,
        categoria: fallbackQ.category as any,
        explicacao: fallbackQ.explanation,
        fonte: fallbackQ.source,
      };
    }
  },

  async answerQuestion(
    matchId: number,
    questionId: number | string,
    answer: boolean
  ): Promise<AnswerResult> {
    try {
      return await httpPost<AnswerResult>(`/matches/${matchId}/answers`, {
        question_id: Number(questionId),
        answer,
      });
    } catch {
      const q =
        LOCAL_QUESTIONS.find((item) => item.id === Number(questionId)) ||
        LOCAL_QUESTIONS[0];
      const isCorrect = answer === q.is_true;

      if (activeLocalMatch) {
        if (isCorrect) {
          activeLocalMatch.match.score += 10;
        }
      }

      return {
        is_correct: isCorrect,
        correct_answer: q.is_true,
        explanation: q.explanation,
        source: q.source,
        score: activeLocalMatch ? activeLocalMatch.match.score : isCorrect ? 10 : 0,
      };
    }
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
