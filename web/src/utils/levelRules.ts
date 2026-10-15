import { Level } from "../types";

/** O que o nível muda no jogo, em frases curtas para a jornada e o "Como jogar". */
export function describeLevelRules(level: Level): string[] {
  const blocks = level.growth_per_error === 1 ? "1 bloco" : `${level.growth_per_error} blocos`;
  const rules = [
    `Tabuleiro ${level.board_size}×${level.board_size}`,
    `${level.question_seconds}s por pergunta · acerto até ${level.reliability_tolerance} pts da referência`,
    level.wrong_answer_penalty > 0
      ? `Erro tira ${level.wrong_answer_penalty} pts e cresce ${blocks}`
      : `Erro cresce ${blocks}`,
    level.solid_walls ? "Paredes sólidas" : "Paredes atravessáveis",
  ];
  if (level.apple_lifetime_seconds) {
    rules.push(`A maçã muda de lugar a cada ${level.apple_lifetime_seconds}s`);
  }
  if (level.rotten_apples === 1) rules.push("1 maçã podre: evite, ela faz a cobra crescer");
  else if (level.rotten_apples > 1) {
    rules.push(`${level.rotten_apples} maçãs podres: evite, elas fazem a cobra crescer`);
  }
  return rules;
}
