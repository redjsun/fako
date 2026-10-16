import { httpGet, isGuestSession } from "./httpClient";
import { UserProgress } from "../types";
import { authService } from "./authService";

// Progresso guardado no navegador: o do visitante, ou o da conta com a API fora do ar.
function localProgress(): UserProgress {
  const user = authService.getCurrentUser();
  const stats = user ? authService.getUserStats(user.username) : null;
  return {
    current_level: stats?.maxLevel || 1,
    highest_level: stats?.maxLevel || 1,
    total_score: stats?.totalScore || 0,
    matches_played: stats?.gamesPlayed || 0,
  };
}

export const progressService = {
  async getMyProgress(): Promise<UserProgress> {
    if (isGuestSession()) return localProgress();
    try {
      return await httpGet<UserProgress>("/progress/me");
    } catch {
      return localProgress();
    }
  },
};
