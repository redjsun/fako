import { httpGet, httpPost } from "./httpClient";
import { AnswerResult, Match, MatchResult, Question } from "../types";

// Partidas, perguntas e correção vêm só da API: sem ela não há jogo. Um erro (inclusive o
// 404 de questões esgotadas) sobe para o jogo, que avisa o jogador.
export const matchService = {
  startMatch(level?: number): Promise<Match> {
    return httpPost<Match>("/matches", { level });
  },

  getMatch(matchId: number): Promise<Match> {
    return httpGet<Match>(`/matches/${matchId}`);
  },

  getNextQuestion(matchId: number): Promise<Question> {
    return httpGet<Question>(`/matches/${matchId}/next-question`);
  },

  answerQuestion(matchId: number, questionId: number, reliability: number): Promise<AnswerResult> {
    return httpPost<AnswerResult>(`/matches/${matchId}/answers`, {
      question_id: questionId,
      reliability,
    });
  },

  finishMatch(matchId: number): Promise<MatchResult> {
    return httpPost<MatchResult>(`/matches/${matchId}/finish`);
  },
};
