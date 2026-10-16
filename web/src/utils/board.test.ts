import { describe, expect, it } from "vitest";
import { hitsBody, includesCell, nextHead, randomFreeCell } from "./board";

describe("nextHead", () => {
  it("anda uma célula na direção", () => {
    expect(nextHead({ x: 3, y: 3 }, "UP", 8, false)).toEqual({ x: 3, y: 2 });
    expect(nextHead({ x: 3, y: 3 }, "RIGHT", 8, true)).toEqual({ x: 4, y: 3 });
  });

  it("com paredes atravessáveis volta pelo lado oposto", () => {
    expect(nextHead({ x: 7, y: 2 }, "RIGHT", 8, false)).toEqual({ x: 0, y: 2 });
    expect(nextHead({ x: 2, y: 0 }, "UP", 8, false)).toEqual({ x: 2, y: 7 });
  });

  it("com paredes sólidas sair do tabuleiro é batida", () => {
    expect(nextHead({ x: 7, y: 2 }, "RIGHT", 8, true)).toBeNull();
    expect(nextHead({ x: 2, y: 0 }, "UP", 8, true)).toBeNull();
  });
});

describe("randomFreeCell", () => {
  it("nunca devolve célula ocupada", () => {
    const occupied = [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 0, y: 1 },
    ];
    for (let i = 0; i < 20; i++) {
      expect(includesCell(occupied, randomFreeCell(2, occupied)!)).toBe(false);
    }
  });

  it("devolve null com o tabuleiro cheio", () => {
    expect(randomFreeCell(1, [{ x: 0, y: 0 }])).toBeNull();
  });
});

describe("hitsBody", () => {
  // Cobra em quadrado: a cabeça em (1,0) e a cauda em (0,0), logo à esquerda dela.
  const snake = [
    { x: 1, y: 0 },
    { x: 1, y: 1 },
    { x: 0, y: 1 },
    { x: 0, y: 0 },
  ];

  it("ir para a célula da cauda sem crescer não é mordida", () => {
    expect(hitsBody(snake, { x: 0, y: 0 }, false)).toBe(false);
  });

  it("ir para a célula da cauda crescendo é mordida", () => {
    expect(hitsBody(snake, { x: 0, y: 0 }, true)).toBe(true);
  });

  it("bater no meio do corpo é sempre mordida", () => {
    expect(hitsBody(snake, { x: 1, y: 1 }, false)).toBe(true);
  });
});
