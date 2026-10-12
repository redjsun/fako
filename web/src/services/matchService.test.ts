import { afterEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "./httpClient";
import { matchService } from "./matchService";

const apiMatch = {
  id: 7,
  level: { number: 1, board_size: 7, tick_ms: 400, min_score_to_advance: 30 },
  score: 0,
  status: "in_progress",
  duration_seconds: 120,
  started_at: "2026-10-12T00:00:00Z",
  ended_at: null,
};

describe("matchService", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("na partida da API, questões esgotadas sobem como 404 em vez de virar pergunta local", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(apiMatch), { status: 201 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Não há mais questões disponíveis" }), { status: 404 })
      );
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

    expect(question.id).toBeLessThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(1); // só a tentativa de criar a partida
    expect(result.explanation).toBeTruthy();
  });
});
