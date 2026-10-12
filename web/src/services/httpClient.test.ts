import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError, httpGet, httpPost, setAuthToken, setUnauthorizedHandler } from "./httpClient";

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
