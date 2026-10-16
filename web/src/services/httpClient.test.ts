import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  HttpError,
  getAuthToken,
  guestToken,
  httpGet,
  httpPost,
  setAuthToken,
  setUnauthorizedHandler,
} from "./httpClient";

function respondWith(status: number, body: unknown = { detail: "Não autenticado" }) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status }))
  );
}

describe("httpClient com token recusado (401)", () => {
  const handler = vi.fn();

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    handler.mockReset();
    setUnauthorizedHandler(handler);
  });

  afterEach(() => {
    setUnauthorizedHandler(null);
    vi.unstubAllGlobals();
  });

  it("avisa a sessão expirada quando o token é de conta", async () => {
    setAuthToken("jwt-da-conta");
    respondWith(401);

    await expect(httpGet("/progress/me")).rejects.toBeInstanceOf(HttpError);
    expect(handler).toHaveBeenCalledOnce();
  });

  it("não avisa para o token de visitante, que a API sempre recusa", async () => {
    setAuthToken("guest-token-1234");
    respondWith(401);

    await expect(httpGet("/progress/me")).rejects.toThrow();
    expect(handler).not.toHaveBeenCalled();
  });

  it("não avisa no login com senha errada", async () => {
    setAuthToken("jwt-antigo");
    respondWith(401, { detail: "Usuário ou senha inválidos" });

    await expect(httpPost("/auth/login", {})).rejects.toThrow("Usuário ou senha inválidos");
    expect(handler).not.toHaveBeenCalled();
  });
});

describe("httpClient", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("não manda o token do visitante para a API", async () => {
    setAuthToken(guestToken(42), false);
    const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await httpGet("/levels");

    const headers = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].headers as Headers;
    expect(headers.has("Authorization")).toBe(false);
  });

  it("traduz o 429 e a validação do Pydantic para o jogador", async () => {
    respondWith(429, {});
    await expect(httpPost("/auth/login", {})).rejects.toThrow("Muitas tentativas");

    respondWith(422, { detail: [{ msg: "String should have at least 8 characters" }] });
    await expect(httpPost("/auth/register", {})).rejects.toThrow("dados enviados são inválidos");
  });

  it("sem 'Lembrar de mim' o token fica só no sessionStorage", () => {
    setAuthToken("jwt", false);
    expect(sessionStorage.getItem("fako_token")).toBe("jwt");
    expect(localStorage.getItem("fako_token")).toBeNull();

    setAuthToken("jwt-2", true);
    expect(localStorage.getItem("fako_token")).toBe("jwt-2");
    expect(sessionStorage.getItem("fako_token")).toBeNull();
    expect(getAuthToken()).toBe("jwt-2");
  });
});
