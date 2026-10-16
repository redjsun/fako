/** Segundos no formato do cronômetro: 118 → "01:58". */
export function formatClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

/** Leitura em palavras da barra de confiabilidade (70% → "Provavelmente confiável"). */
export function reliabilityLabel(value: number): string {
  if (value <= 10) return "Nada confiável";
  if (value <= 35) return "Pouco confiável";
  if (value < 65) return "Incerto";
  if (value < 90) return "Provavelmente confiável";
  return "Totalmente confiável";
}

/** Efeito de um erro no nível: "+2 blocos" ou "+2 blocos · −5 pts". */
export function wrongAnswerEffect(growthPerError: number, wrongAnswerPenalty: number): string {
  const blocks = `+${growthPerError} ${growthPerError === 1 ? "bloco" : "blocos"}`;
  return wrongAnswerPenalty > 0 ? `${blocks} · −${wrongAnswerPenalty} pts` : blocks;
}

export function clampReliability(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value / 5) * 5));
}

/** Data do histórico: "Hoje, 14:32", "Ontem, 09:10" ou "03/10, 18:05". */
export function formatMatchDate(timestamp: number): string {
  const date = new Date(timestamp);
  const time = date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return `Hoje, ${time}`;
  if (date.toDateString() === yesterday.toDateString()) return `Ontem, ${time}`;
  const day = date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  return `${day}, ${time}`;
}
