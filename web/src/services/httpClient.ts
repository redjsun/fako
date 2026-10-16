import { readSession, removeSession, writeSession } from "./sessionStore";

// Camada de infraestrutura: único ponto de acesso HTTP da aplicação.
const BASE_URL = "/api";
const TOKEN_KEY = "fako_token";
const GUEST_TOKEN_PREFIX = "guest-";

export function getAuthToken(): string | null {
  return readSession(TOKEN_KEY);
}

// remember: guarda no localStorage ("Lembrar de mim"); senão, só até fechar o navegador.
export function setAuthToken(token: string | null, remember = true): void {
  if (token) writeSession(TOKEN_KEY, token, remember);
  else removeSession(TOKEN_KEY);
}

export function guestToken(id: number): string {
  return `${GUEST_TOKEN_PREFIX}token-${id}`;
}

// Visitantes usam um token só do front: ele nunca vai para a API.
export function isGuestSession(): boolean {
  return getAuthToken()?.startsWith(GUEST_TOKEN_PREFIX) ?? false;
}

// Resposta da API com status de erro; falha de rede chega como TypeError do fetch.
export class HttpError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
  }
}

// API fora do ar: sem resposta, ou erro do proxy/servidor (5xx).
export function isApiUnavailable(error: unknown): boolean {
  return !(error instanceof HttpError) || error.status >= 500;
}

let unauthorizedHandler: (() => void) | null = null;

// Chamado quando a API recusa um token de conta (expirado ou inválido).
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

// Mensagem do erro para o jogador. A validação do Pydantic (422 com lista) vem em inglês.
function errorMessage(status: number, data: unknown): string {
  const detail = data && typeof data === "object" ? (data as { detail?: unknown }).detail : undefined;
  if (typeof detail === "string" && detail) return detail;
  if (status === 429) return "Muitas tentativas seguidas. Aguarde um pouco e tente de novo.";
  if (status === 422) return "Alguns dados enviados são inválidos. Confira e tente de novo.";
  return `Falha na requisição: ${status}`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const token = getAuthToken();
  const isAccountToken = !!token && !token.startsWith(GUEST_TOKEN_PREFIX);
  if (isAccountToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && isAccountToken && !path.startsWith("/auth/")) {
    unauthorizedHandler?.();
  }

  if (!response.ok) {
    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      // Resposta sem JSON
    }
    throw new HttpError(errorMessage(response.status, data), response.status);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return (await response.json()) as T;
}

export async function httpGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export async function httpPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}
