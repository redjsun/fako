export type QuestionCategory = "Saúde" | "Tecnologia" | "Conhecimentos Gerais";
export type CategoryFilter = QuestionCategory | "Misto";

export interface Question {
  id: number | string;
  statement?: string;
  category?: string;
  // Campos opcionais de compatibilidade
  afirmacao?: string;
  categoria?: QuestionCategory;
  confiabilidade_referencia?: number;
  explicacao?: string;
  fonte?: string;
}

export interface AnswerResult {
  is_correct: boolean;
  correct_answer: boolean;
  explanation: string;
  source: string;
  score: number;
}

export interface QuestionResult {
  question: Question;
  isCorrect: boolean;
  correctAnswer: boolean;
  explanation: string;
  source: string;
  points: number;
}

export interface Level {
  number: number;
  board_size: number;
  tick_ms: number;
  min_score_to_advance: number;
}

export type MatchStatus = "in_progress" | "finished";

export interface Match {
  id: number;
  level: Level;
  score: number;
  status: MatchStatus;
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

export type GameStatus =
  | "START"
  | "PLAYING"
  | "QUESTION"
  | "FEEDBACK"
  | "GAMEOVER"
  | "VICTORY"
  | "TIMEOUT";

export interface GameStats {
  score: number;
  level: number;
  applesInLevel: number;
  totalApples: number;
  acertos: number;
  erros: number;
  category: CategoryFilter;
  advanced?: boolean;
}

export type AppScreen = "login" | "home" | "categories" | "tutorial" | "journey" | "game";

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
  icon: string;
  unlocked: boolean;
  unlockedAt?: number;
}

export interface UserStats {
  highScore: number;
  maxLevel: number;
  gamesPlayed: number;
  totalAcertos: number;
  totalErros: number;
  streakDays: number;
  hasSeenTutorial: boolean;
  categoryStats: {
    saude: { acertos: number; total: number };
    tecnologia: { acertos: number; total: number };
    gerais: { acertos: number; total: number };
  };
  achievements: Achievement[];
}
