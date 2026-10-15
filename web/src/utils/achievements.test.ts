import { describe, expect, it } from "vitest";
import type { AnsweredQuestion, MatchRecord, UserStats } from "../types";
import { ACHIEVEMENT_RULES, achievementProgress, defaultAchievements, unlockAchievements } from "./achievements";

function makeStats(overrides: Partial<UserStats> = {}): UserStats {
  return {
    highScore: 0,
    maxLevel: 1,
    gamesPlayed: 0,
    totalAcertos: 0,
    totalErros: 0,
    bestStreak: 0,
    hasSeenTutorial: false,
    achievements: defaultAchievements(),
    history: [],
    ...overrides,
  };
}

function makeMatch(answers: AnsweredQuestion[]): MatchRecord {
  return {
    finishedAt: 0,
    level: 1,
    score: 0,
    acertos: answers.filter((answer) => answer.isCorrect).length,
    erros: answers.filter((answer) => !answer.isCorrect).length,
    snakeLength: 3,
    secondsPlayed: 60,
    endReason: "TIMEOUT",
    answers,
  };
}

function answer(isCorrect: boolean, reliability = 40, reference = 50): AnsweredQuestion {
  return { statement: "x", reliability, reference, isCorrect };
}

const unlockedIds = (stats: UserStats, match: MatchRecord) =>
  unlockAchievements(stats, match)
    .filter((achievement) => achievement.unlocked)
    .map((achievement) => achievement.id);

describe("catálogo de conquistas", () => {
  it("tem ids únicos e uma conquista padrão para cada regra", () => {
    const ids = ACHIEVEMENT_RULES.map((rule) => rule.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(defaultAchievements().map((achievement) => achievement.id)).toEqual(ids);
  });
});

describe("unlockAchievements", () => {
  it("libera Na Mosca! só quando a resposta bate a referência exata", () => {
    const stats = makeStats({ totalAcertos: 1 });
    expect(unlockedIds(stats, makeMatch([answer(true, 50, 50)]))).toContain("bullseye");
    expect(unlockedIds(stats, makeMatch([answer(true, 45, 50)]))).not.toContain("bullseye");
  });

  it("libera Partida Perfeita com 5 respostas sem erro, e não com menos", () => {
    const stats = makeStats({ totalAcertos: 5 });
    expect(unlockedIds(stats, makeMatch(Array.from({ length: 5 }, () => answer(true))))).toContain("perfect");
    expect(unlockedIds(stats, makeMatch(Array.from({ length: 4 }, () => answer(true))))).not.toContain("perfect");
    const comErro = [true, true, true, true, true, false].map((ok) => answer(ok));
    expect(unlockedIds(stats, makeMatch(comErro))).not.toContain("perfect");
  });

  it("libera as conquistas acumuladas ao bater a meta", () => {
    const stats = makeStats({ gamesPlayed: 10, totalAcertos: 70, totalErros: 30, maxLevel: 6 });
    expect(unlockedIds(stats, makeMatch([]))).toEqual(
      expect.arrayContaining(["first_check", "level_up", "regular", "hundred", "master"])
    );
  });

  it("não tira uma conquista já liberada nem muda a data dela", () => {
    const achievements = defaultAchievements().map((achievement) =>
      achievement.id === "bullseye" ? { ...achievement, unlocked: true, unlockedAt: 123 } : achievement
    );
    const result = unlockAchievements(makeStats({ achievements }), makeMatch([]), 999);
    expect(result.find((achievement) => achievement.id === "bullseye")).toMatchObject({
      unlocked: true,
      unlockedAt: 123,
    });
  });
});

describe("achievementProgress", () => {
  it("mostra contador e percentual das metas com mais de um passo", () => {
    const progress = achievementProgress(makeStats({ bestStreak: 3, maxLevel: 3 }));
    expect(progress.find((item) => item.id === "imune")).toMatchObject({ percent: 60, counter: "3 / 5 seguidas" });
    expect(progress.find((item) => item.id === "master")).toMatchObject({ percent: 50, counter: "3 / 6 níveis" });
  });

  it("mostra 100% e sem contador quando a conquista já foi liberada", () => {
    const achievements = defaultAchievements().map((achievement) => ({ ...achievement, unlocked: true }));
    const progress = achievementProgress(makeStats({ achievements }));
    expect(progress.every((item) => item.percent === 100 && item.counter === "")).toBe(true);
  });
});
