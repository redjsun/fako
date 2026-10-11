import { httpGet } from "./httpClient";
import { UserProgress } from "../types";
import { authService } from "./authService";

export const progressService = {
  async getMyProgress(): Promise<UserProgress> {
    try {
      return await httpGet<UserProgress>("/progress/me");
    } catch {
      const user = authService.getCurrentUser();
      const stats = user ? authService.getUserStats(user.username) : null;
      return {
        current_level: stats?.maxLevel || 1,
        highest_level: stats?.maxLevel || 1,
        total_score: stats?.highScore || 0,
        matches_played: stats?.gamesPlayed || 0,
      };
    }
  },
};
