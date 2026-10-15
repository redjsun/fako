import { Achievement, MatchRecord, UserStats } from "../types";

// Catálogo das conquistas (tabela em doc/jogo/conquistas.md).
// `value` mede o progresso: a conquista é liberada quando chega a `target`. `match` é a partida
// que acabou de terminar; na Jornada ele não existe, e as conquistas de uma partida só mostram 0 ou 100%.
export interface AchievementRule {
  id: string;
  title: string;
  description: string;
  target: number;
  unit?: string;
  value: (stats: UserStats, match?: MatchRecord) => number;
}

const answered = (stats: UserStats) => stats.totalAcertos + stats.totalErros;

export const ACHIEVEMENT_RULES: AchievementRule[] = [
  {
    id: "first_check",
    title: "Primeira Checagem",
    description: "Avaliou a primeira afirmação no FAKO.",
    target: 1,
    value: answered,
  },
  {
    id: "bullseye",
    title: "Na Mosca!",
    description: "Acertou a referência exata de uma afirmação.",
    target: 1,
    value: (_, match) =>
      match?.answers.some((answer) => answer.reliability === answer.reference) ? 1 : 0,
  },
  {
    id: "level_up",
    title: "Subindo de Nível",
    description: "Alcançou o nível 2.",
    target: 1,
    value: (stats) => stats.maxLevel - 1,
  },
  {
    id: "imune",
    title: "Muralha Antifake",
    description: "Acertou 5 afirmações seguidas na mesma partida.",
    target: 5,
    unit: "seguidas",
    value: (stats) => stats.bestStreak,
  },
  {
    id: "perfect",
    title: "Partida Perfeita",
    description: "Terminou uma partida com pelo menos 5 respostas e nenhum erro.",
    target: 1,
    value: (_, match) =>
      match && match.answers.length >= 5 && match.answers.every((answer) => answer.isCorrect) ? 1 : 0,
  },
  {
    id: "regular",
    title: "Checador Assíduo",
    description: "Jogou 10 partidas.",
    target: 10,
    unit: "partidas",
    value: (stats) => stats.gamesPlayed,
  },
  {
    id: "hundred",
    title: "Cem Checagens",
    description: "Avaliou 100 afirmações.",
    target: 100,
    unit: "afirmações",
    value: answered,
  },
  {
    id: "master",
    title: "Mestre dos Fatos",
    description: "Chegou ao nível 6.",
    target: 6,
    unit: "níveis",
    value: (stats) => stats.maxLevel,
  },
];

export function defaultAchievements(): Achievement[] {
  return ACHIEVEMENT_RULES.map(({ id, title, description }) => ({ id, title, description, unlocked: false }));
}

// Libera as conquistas que a partida (ou o acumulado até ela) alcançou. Não tira nenhuma já liberada.
export function unlockAchievements(stats: UserStats, match: MatchRecord, now = Date.now()): Achievement[] {
  return stats.achievements.map((achievement) => {
    const rule = ACHIEVEMENT_RULES.find((item) => item.id === achievement.id);
    if (achievement.unlocked || !rule || rule.value(stats, match) < rule.target) return achievement;
    return { ...achievement, unlocked: true, unlockedAt: now };
  });
}

export interface AchievementProgress {
  id: string;
  title: string;
  description: string;
  unlocked: boolean;
  percent: number;
  // "3 / 5 seguidas"; vazio nas conquistas de sim ou não.
  counter: string;
}

export function achievementProgress(stats: UserStats): AchievementProgress[] {
  return ACHIEVEMENT_RULES.map((rule) => {
    const unlocked = stats.achievements.find((item) => item.id === rule.id)?.unlocked ?? false;
    const current = Math.max(0, Math.min(rule.target, rule.value(stats)));
    return {
      id: rule.id,
      title: rule.title,
      description: rule.description,
      unlocked,
      percent: unlocked ? 100 : Math.round((current / rule.target) * 100),
      counter: rule.target > 1 && !unlocked ? `${current} / ${rule.target} ${rule.unit ?? ""}`.trim() : "",
    };
  });
}
