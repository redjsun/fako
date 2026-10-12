import { Achievement, AnsweredQuestion, MatchRecord, User, UserStats } from "../types";
import { httpGet, httpPost, setAuthToken, getAuthToken, isApiUnavailable } from "./httpClient";

const SESSION_STORAGE_KEY = "fako_active_session";
const STATS_STORAGE_KEY_PREFIX = "fako_stats_";

const HISTORY_LIMIT = 10;

const DEFAULT_ACHIEVEMENTS: Achievement[] = [
  {
    id: "first_check",
    title: "Primeira Checagem",
    description: "Avaliou a primeira afirmação no FAKO.",
    unlocked: false,
  },
  {
    id: "bullseye",
    title: "Na Mosca!",
    description: "Acertou a referência exata de uma afirmação.",
    unlocked: false,
  },
  {
    id: "level_up",
    title: "Subindo de Nível",
    description: "Alcançou o nível 2.",
    unlocked: false,
  },
  {
    id: "imune",
    title: "Muralha Antifake",
    description: "Acertou 5 afirmações seguidas na mesma partida.",
    unlocked: false,
  },
  {
    id: "master",
    title: "Mestre dos Fatos",
    description: "Chegou ao nível 6.",
    unlocked: false,
  },
];

function defaultStats(): UserStats {
  return {
    highScore: 0,
    maxLevel: 1,
    gamesPlayed: 0,
    totalAcertos: 0,
    totalErros: 0,
    bestStreak: 0,
    hasSeenTutorial: false,
    achievements: DEFAULT_ACHIEVEMENTS.map((achievement) => ({ ...achievement })),
    history: [],
  };
}

// Maior sequência de acertos seguidos numa lista de respostas.
function longestStreak(answers: AnsweredQuestion[]): number {
  let best = 0;
  let current = 0;
  for (const answer of answers) {
    current = answer.isCorrect ? current + 1 : 0;
    best = Math.max(best, current);
  }
  return best;
}

const OFFLINE_ERROR =
  "Servidor indisponível no momento. Entre como visitante para jogar sem conta.";

// Versões anteriores guardavam aqui as contas com a senha em texto puro.
try {
  localStorage.removeItem("fako_local_users");
} catch {
  // Sem armazenamento local, não há o que limpar
}

function authError(error: unknown, fallback: string): string {
  if (isApiUnavailable(error)) return OFFLINE_ERROR;
  return error instanceof Error && error.message ? error.message : fallback;
}

class AuthService {
  private async startSession(): Promise<User> {
    const userResp = await httpGet<User>("/users/me");
    const sessionUser: User = {
      id: userResp.id,
      username: userResp.username,
      is_admin: userResp.is_admin,
      createdAt: Date.now(),
    };
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionUser));
    return sessionUser;
  }

  public async login(
    username: string,
    password: string
  ): Promise<{ success: boolean; error?: string; user?: User }> {
    const cleanUser = username.trim();
    if (!cleanUser || !password) {
      return { success: false, error: "Preencha todos os campos." };
    }

    try {
      const tokenResp = await httpPost<{ access_token: string }>("/auth/login", {
        username: cleanUser,
        password,
      });
      setAuthToken(tokenResp.access_token);
      return { success: true, user: await this.startSession() };
    } catch (error) {
      setAuthToken(null);
      return { success: false, error: authError(error, "Usuário ou senha incorretos.") };
    }
  }

  public async register(
    username: string,
    password: string
  ): Promise<{ success: boolean; error?: string; user?: User }> {
    const cleanUser = username.trim();
    if (cleanUser.length < 3) {
      return { success: false, error: "O nome de usuário deve ter pelo menos 3 caracteres." };
    }
    if (password.length < 6) {
      return { success: false, error: "A senha deve ter pelo menos 6 caracteres." };
    }

    try {
      const tokenResp = await httpPost<{ access_token: string }>("/auth/register", {
        username: cleanUser,
        password,
      });
      setAuthToken(tokenResp.access_token);
      return { success: true, user: await this.startSession() };
    } catch (error) {
      setAuthToken(null);
      return { success: false, error: authError(error, "Não foi possível criar a conta.") };
    }
  }

  public async loginAsGuest(): Promise<{ success: boolean; error?: string; user?: User }> {
    // Modo Visitante é 100% autônomo, instantâneo e offline-first
    const guestNum = Math.floor(1000 + Math.random() * 9000);
    const sessionUser: User = {
      id: guestNum,
      username: `Visitante #${guestNum}`,
      is_admin: false,
      createdAt: Date.now(),
    };

    setAuthToken(`guest-token-${guestNum}`);
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionUser));
    return { success: true, user: sessionUser };
  }

  public getCurrentUser(): User | null {
    try {
      const token = getAuthToken();
      if (!token) return null;
      const session = localStorage.getItem(SESSION_STORAGE_KEY);
      return session ? JSON.parse(session) : null;
    } catch {
      return null;
    }
  }

  public async fetchCurrentUser(): Promise<User | null> {
    try {
      const token = getAuthToken();
      if (!token) return null;
      if (token.startsWith("guest-") || token.startsWith("local-")) {
        return this.getCurrentUser();
      }
      const userResp = await httpGet<User>("/users/me");
      const sessionUser: User = {
        id: userResp.id,
        username: userResp.username,
        is_admin: userResp.is_admin,
        createdAt: Date.now(),
      };
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionUser));
      return sessionUser;
    } catch {
      return this.getCurrentUser();
    }
  }

  public logout(): void {
    setAuthToken(null);
    localStorage.removeItem(SESSION_STORAGE_KEY);
  }

  public getUserStats(username: string): UserStats {
    try {
      const data = localStorage.getItem(STATS_STORAGE_KEY_PREFIX + username.toLowerCase());
      if (data) {
        const saved = JSON.parse(data) as Partial<UserStats>;
        const base = defaultStats();
        // Mantém o estado das conquistas conhecidas e descarta campos antigos (ex.: categorias).
        const achievements = base.achievements.map((achievement) => {
          const stored = saved.achievements?.find((item) => item.id === achievement.id);
          return stored ? { ...achievement, unlocked: stored.unlocked, unlockedAt: stored.unlockedAt } : achievement;
        });
        return {
          ...base,
          highScore: saved.highScore ?? 0,
          maxLevel: saved.maxLevel ?? 1,
          gamesPlayed: saved.gamesPlayed ?? 0,
          totalAcertos: saved.totalAcertos ?? 0,
          totalErros: saved.totalErros ?? 0,
          bestStreak: saved.bestStreak ?? 0,
          hasSeenTutorial: saved.hasSeenTutorial ?? false,
          achievements,
          history: Array.isArray(saved.history) ? saved.history : [],
        };
      }
    } catch {
      // Ignora erro de leitura e segue com os valores iniciais
    }
    return defaultStats();
  }

  public saveUserStats(username: string, stats: UserStats): void {
    try {
      localStorage.setItem(STATS_STORAGE_KEY_PREFIX + username.toLowerCase(), JSON.stringify(stats));
    } catch {
      // Sem armazenamento local, o progresso fica só na API
    }
  }

  // unlockedLevel: nível atual depois da partida (sobe quando o jogador bate a meta).
  public recordMatchFinished(username: string, record: MatchRecord, unlockedLevel: number): UserStats {
    const current = this.getUserStats(username);
    const achievements = current.achievements.map((achievement) => ({ ...achievement }));
    const unlock = (id: string) => {
      const achievement = achievements.find((item) => item.id === id);
      if (achievement && !achievement.unlocked) {
        achievement.unlocked = true;
        achievement.unlockedAt = Date.now();
      }
    };

    const streak = longestStreak(record.answers);
    if (record.answers.length > 0) unlock("first_check");
    if (record.answers.some((answer) => answer.reliability === answer.reference)) unlock("bullseye");
    if (Math.max(record.level, unlockedLevel) >= 2) unlock("level_up");
    if (streak >= 5) unlock("imune");
    if (Math.max(record.level, unlockedLevel) >= 6) unlock("master");

    const updated: UserStats = {
      highScore: Math.max(current.highScore, record.score),
      maxLevel: Math.max(current.maxLevel, record.level, unlockedLevel),
      gamesPlayed: current.gamesPlayed + 1,
      totalAcertos: current.totalAcertos + record.acertos,
      totalErros: current.totalErros + record.erros,
      bestStreak: Math.max(current.bestStreak, streak),
      hasSeenTutorial: true,
      achievements,
      history: [record, ...current.history].slice(0, HISTORY_LIMIT),
    };
    this.saveUserStats(username, updated);
    return updated;
  }

  public hasSeenTutorial(username: string): boolean {
    const stats = this.getUserStats(username);
    return stats.hasSeenTutorial;
  }

  public markTutorialAsSeen(username: string): void {
    const stats = this.getUserStats(username);
    stats.hasSeenTutorial = true;
    this.saveUserStats(username, stats);
  }
}

export const authService = new AuthService();
