// Camada de serviço: conversa com a API e devolve modelos do domínio.
import type { Health } from "../models/health";
import { httpGet } from "./httpClient";

export function getHealth(): Promise<Health> {
  return httpGet<Health>("/health");
}
