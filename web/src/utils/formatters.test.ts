import { describe, expect, it } from "vitest";
import {
  clampReliability,
  formatClock,
  formatMatchDate,
  reliabilityLabel,
  wrongAnswerEffect,
} from "./formatters";

describe("formatClock", () => {
  it("formata minutos e segundos com dois dígitos", () => {
    expect(formatClock(118)).toBe("01:58");
  });

  it("nunca fica negativo", () => {
    expect(formatClock(-5)).toBe("00:00");
  });

  it("arredonda fracções de segundo", () => {
    expect(formatClock(59.6)).toBe("01:00");
  });
});

describe("reliabilityLabel", () => {
  const casos: Array<[number, string]> = [
    [0, "Nada confiável"],
    [10, "Nada confiável"],
    [35, "Pouco confiável"],
    [50, "Incerto"],
    [89, "Provavelmente confiável"],
    [100, "Totalmente confiável"],
  ];

  for (const [value, label] of casos) {
    it(`classifica ${value}% como "${label}"`, () => {
      expect(reliabilityLabel(value)).toBe(label);
    });
  }
});

describe("clampReliability", () => {
  it("arredonda para o múltiplo de 5 mais próximo", () => {
    expect(clampReliability(42)).toBe(40);
    expect(clampReliability(43)).toBe(45);
  });

  it("limita entre 0 e 100", () => {
    expect(clampReliability(-10)).toBe(0);
    expect(clampReliability(1000)).toBe(100);
  });
});

describe("formatMatchDate", () => {
  it("marca o dia de hoje", () => {
    const now = Date.now();
    expect(formatMatchDate(now)).toMatch(/^Hoje, \d{2}:\d{2}$/);
  });

  it("marca ontem", () => {
    const yesterday = Date.now() - 24 * 60 * 60 * 1000;
    expect(formatMatchDate(yesterday)).toMatch(/^Ontem, \d{2}:\d{2}$/);
  });

  it("usa dia/mês para datas mais antigas", () => {
    const oldDate = new Date("2024-03-10T18:05:00");
    expect(formatMatchDate(oldDate.getTime())).toMatch(/^10\/03, \d{2}:\d{2}$/);
  });
});

describe("wrongAnswerEffect", () => {
  it("mostra os blocos do nível e a perda de pontos quando há", () => {
    expect(wrongAnswerEffect(1, 0)).toBe("+1 bloco");
    expect(wrongAnswerEffect(3, 10)).toBe("+3 blocos · −10 pts");
  });
});
