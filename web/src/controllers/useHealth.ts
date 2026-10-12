// Camada de controle: orquestra estado e serviços para as views.
import { useEffect, useState } from "react";

import type { Health } from "../models/health";
import { getHealth } from "../services/healthService";

export function useHealth() {
  const [health, setHealth] = useState<Health | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e: Error) => setErro(e.message));
  }, []);

  return { health, erro };
}
