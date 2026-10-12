import { beforeEach, describe, expect, it } from "vitest";
import { authService } from "./authService";
import type { AnsweredQuestion, MatchRecord } from "../types";

function makeRecord(overrides: Partial<MatchRecord> = {}): MatchRecord {
  return {
    finishedAt: Date.now(),
    level: 1,
    score: 100,
    acertos: 3,
    erros: 1,
    snakeLength: 5,
    secondsPlayed: 42,
    endReason: "TIMEOUT",
    answers: [],
    ...overrides,
  };
}

function answer(isCorrect: boolean): AnsweredQuestion {
  return { statement: "x", reliability: 50, reference: 50, isCorrect };
}

describe("authService.getUserStats", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("retorna estatísticas zeradas para um usuário novo", () => {
    const stats = authService.getUserStats("novo_usuario");
    expect(stats.highScore).toBe(0);
    expect(stats.gamesPlayed).toBe(0);
    expect(stats.achievements.every((achievement) => !achievement.unlocked)).toBe(true);
  });
});

describe("authService.recordMatchFinished", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("acumula pontuação, partidas e acertos/erros entre partidas", () => {
    authService.recordMatchFinished("jogador", makeRecord({ score: 100, acertos: 3, erros: 1 }), 1);
    const stats = authService.recordMatchFinished(
      "jogador",
      makeRecord({ score: 80, acertos: 2, erros: 0 }),
      1
    );

    expect(stats.gamesPlayed).toBe(2);
    expect(stats.highScore).toBe(100);
    expect(stats.totalAcertos).toBe(5);
    expect(stats.totalErros).toBe(1);
  });

  it("desbloqueia a conquista da primeira checagem ao responder qualquer afirmação", () => {
    const stats = authService.recordMatchFinished(
      "jogador",
      makeRecord({ answers: [answer(true)] }),
      1
    );
    expect(stats.achievements.find((achievement) => achievement.id === "first_check")?.unlocked).toBe(
      true
    );
  });

  it("desbloqueia a muralha antifake com 5 acertos seguidos", () => {
    const answers = [true, true, true, true, true, false].map(answer);
    const stats = authService.recordMatchFinished("jogador", makeRecord({ answers }), 1);
    expect(stats.achievements.find((achievement) => achievement.id === "imune")?.unlocked).toBe(true);
  });

  it("não desbloqueia a muralha antifake sem 5 acertos seguidos", () => {
    const answers = [true, true, false, true, true].map(answer);
    const stats = authService.recordMatchFinished("jogador", makeRecord({ answers }), 1);
    expect(stats.achievements.find((achievement) => achievement.id === "imune")?.unlocked).toBe(false);
  });

  it("desbloqueia o nível 2 quando o jogador avança para lá", () => {
    const stats = authService.recordMatchFinished("jogador", makeRecord({ level: 1 }), 2);
    expect(stats.achievements.find((achievement) => achievement.id === "level_up")?.unlocked).toBe(true);
  });

  it("mantém o histórico limitado às últimas 10 partidas", () => {
    let stats = authService.getUserStats("jogador");
    for (let i = 0; i < 12; i += 1) {
      stats = authService.recordMatchFinished("jogador", makeRecord({ finishedAt: i }), 1);
    }
    expect(stats.history).toHaveLength(10);
    expect(stats.history[0].finishedAt).toBe(11);
  });
});
