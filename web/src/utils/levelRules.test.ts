import { describe, expect, it } from "vitest";
import { LOCAL_LEVELS } from "../services/levelService";
import { describeLevelRules } from "./levelRules";

describe("describeLevelRules", () => {
  it("no primeiro nível só lista as regras básicas", () => {
    expect(describeLevelRules(LOCAL_LEVELS[0])).toEqual([
      "Tabuleiro 16×16",
      "45s por pergunta · acerto até 15 pts da referência",
      "Erro cresce 1 bloco",
      "Paredes atravessáveis",
    ]);
  });

  it("no último nível lista todos os modificadores", () => {
    expect(describeLevelRules(LOCAL_LEVELS[5])).toEqual([
      "Tabuleiro 12×12",
      "20s por pergunta · acerto até 8 pts da referência",
      "Erro tira 10 pts e cresce 3 blocos",
      "Paredes sólidas",
      "A maçã muda de lugar a cada 8s",
      "4 maçãs podres: evite, elas fazem a cobra crescer",
    ]);
  });
});
