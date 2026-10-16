export interface Question {
  id: number;
  statement: string;
  category?: string;
}

// Resultado da resposta na barra de confiabilidade (0 a 100).
// Palpite do classificador sobre a afirmação (CLASSIFICADOR_NO_JOGO), só depois da resposta.
export interface ModelGuess {
  category: "falso" | "enganoso" | "confere" | "incerto";
  score: number | null; // 0 a 100; sem nota quando incerto
  confidence: number;
  model_version: string;
}

// Onde a afirmação circulou (alegação checada) ou foi publicada (manchete de veículo).
export interface ClaimOrigin {
  kind: "alegacao" | "materia";
  author: string;
  when: string | null; // AAAA-MM-DD
  link: string | null;
}

export interface AnswerResult {
  is_correct: boolean;
  correct_answer: boolean;
  reliability: number;
  reliability_reference: number;
  tolerance: number;
  distance: number;
  explanation: string;
  source: string;
  score: number;
  // A API conta como erro a resposta que chega depois do tempo da pergunta (com folga).
  timed_out?: boolean;
  // Palpite do classificador sobre a afirmação; ausente quando ele está desligado.
  model_guess?: ModelGuess | null;
  claim_origin?: ClaimOrigin | null;
}

// Afirmação já respondida, para o feedback, o resumo da partida e o histórico.
export interface AnsweredQuestion {
  statement: string;
  reliability: number;
  reference: number;
  isCorrect: boolean;
}

// Regras de um nível da jornada (api/app/models/level.py; tabela em doc/jogo/niveis.md).
export interface Level {
  number: number;
  board_size: number;
  tick_ms: number;
  min_score_to_advance: number;
  match_seconds: number;
  question_seconds: number;
  reliability_tolerance: number;
  wrong_answer_penalty: number;
  growth_per_error: number;
  solid_walls: boolean;
  apple_lifetime_seconds: number | null;
  rotten_apples: number;
}

export interface Match {
  id: number;
  level: Level;
  score: number;
  status: "in_progress" | "finished" | "abandoned";
  duration_seconds: number;
  started_at: string;
  ended_at: string | null;
}

export interface MatchResult {
  match: Match;
  advanced: boolean;
  current_level: number;
}

export interface UserProgress {
  current_level: number;
  highest_level: number;
  total_score: number;
  matches_played: number;
}

export type Direction = "UP" | "DOWN" | "LEFT" | "RIGHT";

export interface Position {
  x: number;
  y: number;
}

/**
 * Estados da partida:
 * PLAYING (cobra andando), PAUSED (Esc ou modal de sair), QUESTION (popup da afirmação),
 * FEEDBACK (popup do resultado), COUNTDOWN (3 s antes de retomar) e FINISHED.
 */
export type GameStatus = "PLAYING" | "PAUSED" | "QUESTION" | "FEEDBACK" | "COUNTDOWN" | "FINISHED";

// EXIT: o jogador saiu pelo "Sair e salvar".
// NO_QUESTIONS: o banco não tem mais afirmações inéditas para esta partida.
// GOAL: o placar alcançou a meta do nível.
export type MatchEndReason = "TIMEOUT" | "GAMEOVER" | "EXIT" | "NO_QUESTIONS" | "GOAL";

// Partida encerrada, guardada no histórico local do jogador.
export interface MatchRecord {
  finishedAt: number;
  level: number;
  score: number;
  acertos: number;
  erros: number;
  snakeLength: number;
  secondsPlayed: number;
  endReason: MatchEndReason;
  answers: AnsweredQuestion[];
}

export type AppScreen = "login" | "home" | "tutorial" | "journey" | "game";

export interface User {
  id?: number;
  username: string;
  is_admin?: boolean;
  createdAt?: number;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  unlocked: boolean;
  unlockedAt?: number;
}

export interface UserStats {
  highScore: number;
  // Soma dos pontos de todas as partidas, como o total_score da API.
  totalScore: number;
  maxLevel: number;
  gamesPlayed: number;
  totalAcertos: number;
  totalErros: number;
  bestStreak: number;
  hasSeenTutorial: boolean;
  achievements: Achievement[];
  history: MatchRecord[];
}
