import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError, guestToken, setAuthToken } from "./httpClient";
import { advancesLevel, matchService, shuffled } from "./matchService";

const apiMatch = {
  id: 7,
  level: { number: 1, board_size: 7, tick_ms: 400, min_score_to_advance: 30 },
  score: 0,
  status: "in_progress",
  duration_seconds: 120,
  started_at: "2026-10-12T00:00:00Z",
  ended_at: null,
};

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), { status });
}

describe("matchService", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    setAuthToken("jwt-da-conta");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("na partida da API, questões esgotadas sobem como 404 em vez de virar pergunta local", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(apiMatch, 201))
      .mockResolvedValueOnce(jsonResponse({ detail: "Não há mais questões disponíveis" }, 404));
    vi.stubGlobal("fetch", fetchMock);

    const match = await matchService.startMatch(1);
    const error = await matchService.getNextQuestion(match.id).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(HttpError);
    expect((error as HttpError).status).toBe(404);
  });

  it("com a API fora do ar, a partida e as perguntas são locais e corrigidas no front", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const match = await matchService.startMatch(1);
    const question = await matchService.getNextQuestion(match.id);
    const result = await matchService.answerQuestion(match.id, question.id, 50);

    expect(matchService.isLocalMatch(match.id)).toBe(true);
    expect(question.id).toBeLessThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(1); // só a tentativa de criar a partida
    expect(result.explanation).toBeTruthy();
  });

  it("um erro de regra da API (ex.: nível bloqueado) sobe em vez de virar partida local", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Nível ainda não liberado" }, 422))
    );

    await expect(matchService.startMatch(4)).rejects.toThrow("Nível ainda não liberado");
  });

  it("o visitante joga a partida local sem chamar a API", async () => {
    setAuthToken(guestToken(1234), false);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const match = await matchService.startMatch(1);

    expect(matchService.isLocalMatch(match.id)).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("na partida local cada afirmação aparece uma vez e depois vem o 404 de questões esgotadas", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const match = await matchService.startMatch(1);

    const ids = new Set<number>();
    let error: unknown = null;
    for (let index = 0; index < 50 && !error; index++) {
      try {
        ids.add((await matchService.getNextQuestion(match.id)).id);
      } catch (caught) {
        error = caught;
      }
    }

    expect(ids.size).toBeGreaterThan(0);
    expect(error).toBeInstanceOf(HttpError);
    expect((error as HttpError).status).toBe(404);
  });

  it("a falha ao encerrar uma partida da API sobe, sem inventar resultado", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(apiMatch, 201))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const match = await matchService.startMatch(1);

    await expect(matchService.finishMatch(match.id, 1)).rejects.toBeInstanceOf(TypeError);
  });

  it("a partida local acima do nível atual não libera nível", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const match = await matchService.startMatch(1);

    const result = await matchService.finishMatch(match.id, 3);

    expect(result.advanced).toBe(false);
    expect(result.current_level).toBe(3);
  });
});

describe("advancesLevel", () => {
  const base = { matchLevel: 2, currentLevel: 2, score: 40, minScoreToAdvance: 40, maxLevel: 6 };

  it("avança quem bate a meta jogando o nível atual", () => {
    expect(advancesLevel(base)).toBe(true);
  });

  it("não avança abaixo da meta, rejogando um nível antigo ou no último nível", () => {
    expect(advancesLevel({ ...base, score: 39 })).toBe(false);
    expect(advancesLevel({ ...base, matchLevel: 1 })).toBe(false);
    expect(advancesLevel({ ...base, matchLevel: 6, currentLevel: 6 })).toBe(false);
  });
});

describe("shuffled", () => {
  it("mantém os mesmos itens sem alterar a lista original", () => {
    const original = [1, 2, 3, 4, 5];
    const result = shuffled(original, () => 0);

    expect([...result].sort()).toEqual(original);
    expect(original).toEqual([1, 2, 3, 4, 5]);
    expect(result).not.toEqual(original);
  });
});
