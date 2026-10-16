import { AnsweredQuestion, MatchRecord, User, UserStats } from "../types";
import { defaultAchievements, unlockAchievements } from "../utils/achievements";
import {
  guestToken,
  httpGet,
  httpPost,
  setAuthToken,
  getAuthToken,
  isApiUnavailable,
  setUnauthorizedHandler,
} from "./httpClient";
import { readSession, removeSession, writeSession } from "./sessionStore";

const SESSION_STORAGE_KEY = "fako_active_session";
const STATS_STORAGE_KEY_PREFIX = "fako_stats_";

const HISTORY_LIMIT = 10;

function defaultStats(): UserStats {
  return {
    highScore: 0,
    totalScore: 0,
    maxLevel: 1,
    gamesPlayed: 0,
    totalAcertos: 0,
    totalErros: 0,
    bestStreak: 0,
    hasSeenTutorial: false,
    achievements: defaultAchievements(),
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

// Limites do cadastro na API (api/app/schemas/auth_schema.py). A senha conta bytes: o bcrypt
// só usa os primeiros 72.
export const USERNAME_MIN = 3;
export const USERNAME_MAX = 50;
export const PASSWORD_MIN = 8;
const PASSWORD_MAX_BYTES = 72;
const USERNAME_PATTERN = /^[A-Za-z0-9._-]+$/;

function passwordBytes(password: string): number {
  return new TextEncoder().encode(password).length;
}

// Mensagem do primeiro problema do cadastro, ou null quando está tudo certo.
export function registrationError(username: string, password: string): string | null {
  const cleanUser = username.trim();
  if (cleanUser.length < USERNAME_MIN || cleanUser.length > USERNAME_MAX || !USERNAME_PATTERN.test(cleanUser)) {
    return `O usuário precisa ter de ${USERNAME_MIN} a ${USERNAME_MAX} caracteres: letras, números, . - _`;
  }
  if (password.length < PASSWORD_MIN) {
    return `A senha deve ter pelo menos ${PASSWORD_MIN} caracteres.`;
  }
  if (passwordBytes(password) > PASSWORD_MAX_BYTES) {
    return `A senha pode ter no máximo ${PASSWORD_MAX_BYTES} caracteres (acentos e emojis contam mais).`;
  }
  return null;
}

function authError(error: unknown, fallback: string): string {
  if (isApiUnavailable(error)) return OFFLINE_ERROR;
  return error instanceof Error && error.message ? error.message : fallback;
}

class AuthService {
  private async startSession(remember: boolean): Promise<User> {
    const userResp = await httpGet<User>("/users/me");
    const sessionUser: User = {
      id: userResp.id,
      username: userResp.username,
      is_admin: userResp.is_admin,
      createdAt: Date.now(),
    };
    writeSession(SESSION_STORAGE_KEY, JSON.stringify(sessionUser), remember);
    return sessionUser;
  }

  // remember: "Lembrar de mim"; sem ele, a sessão some ao fechar o navegador.
  public async login(
    username: string,
    password: string,
    remember = false
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
      setAuthToken(tokenResp.access_token, remember);
      return { success: true, user: await this.startSession(remember) };
    } catch (error) {
      setAuthToken(null);
      return { success: false, error: authError(error, "Usuário ou senha incorretos.") };
    }
  }

  public async register(
    username: string,
    password: string,
    remember = false
  ): Promise<{ success: boolean; error?: string; user?: User }> {
    const cleanUser = username.trim();
    const invalid = registrationError(cleanUser, password);
    if (invalid) return { success: false, error: invalid };

    try {
      const tokenResp = await httpPost<{ access_token: string }>("/auth/register", {
        username: cleanUser,
        password,
      });
      setAuthToken(tokenResp.access_token, remember);
      return { success: true, user: await this.startSession(remember) };
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

    // A sessão do visitante vale só até fechar o navegador.
    setAuthToken(guestToken(guestNum), false);
    writeSession(SESSION_STORAGE_KEY, JSON.stringify(sessionUser), false);
    return { success: true, user: sessionUser };
  }

  public getCurrentUser(): User | null {
    try {
      const token = getAuthToken();
      if (!token) return null;
      const session = readSession(SESSION_STORAGE_KEY);
      return session ? JSON.parse(session) : null;
    } catch {
      return null;
    }
  }

  // Encerra a sessão e avisa quando a API recusa o token da conta.
  public onSessionExpired(callback: () => void): () => void {
    setUnauthorizedHandler(() => {
      this.logout();
      callback();
    });
    return () => setUnauthorizedHandler(null);
  }

  public logout(): void {
    setAuthToken(null);
    removeSession(SESSION_STORAGE_KEY);
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
          totalScore: saved.totalScore ?? 0,
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
    const streak = longestStreak(record.answers);

    const updated: UserStats = {
      highScore: Math.max(current.highScore, record.score),
      totalScore: current.totalScore + record.score,
      maxLevel: Math.max(current.maxLevel, record.level, unlockedLevel),
      gamesPlayed: current.gamesPlayed + 1,
      totalAcertos: current.totalAcertos + record.acertos,
      totalErros: current.totalErros + record.erros,
      bestStreak: Math.max(current.bestStreak, streak),
      hasSeenTutorial: true,
      achievements: current.achievements,
      history: [record, ...current.history].slice(0, HISTORY_LIMIT),
    };
    updated.achievements = unlockAchievements(updated, record);
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
