// Guarda a sessão (token e usuário) no localStorage quando o jogador pede "Lembrar de mim" e
// no sessionStorage (some ao fechar o navegador) quando não pede. Sem armazenamento, nada fica salvo.

function stores(): Storage[] {
  const available: Storage[] = [];
  try {
    available.push(window.sessionStorage);
  } catch {
    // sessionStorage bloqueado
  }
  try {
    available.push(window.localStorage);
  } catch {
    // localStorage bloqueado
  }
  return available;
}

export function readSession(key: string): string | null {
  for (const store of stores()) {
    try {
      const value = store.getItem(key);
      if (value !== null) return value;
    } catch {
      // Segue para o próximo armazenamento
    }
  }
  return null;
}

// Grava no armazenamento escolhido e apaga a cópia do outro, para não sobrar sessão antiga.
export function writeSession(key: string, value: string, remember: boolean): void {
  removeSession(key);
  try {
    (remember ? window.localStorage : window.sessionStorage).setItem(key, value);
  } catch {
    // Sem armazenamento: a sessão vale só até recarregar a página
  }
}

export function removeSession(key: string): void {
  for (const store of stores()) {
    try {
      store.removeItem(key);
    } catch {
      // Nada a apagar
    }
  }
}
