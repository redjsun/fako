import { httpGet } from "./httpClient";
import { Level } from "../types";

// Cópia do seed da API (api/app/seeds/data.py), usada quando ela está fora do ar.
export const LOCAL_LEVELS: Level[] = [
  {
    number: 1, board_size: 16, tick_ms: 160, min_score_to_advance: 30,
    match_seconds: 120, question_seconds: 45, reliability_tolerance: 15,
    wrong_answer_penalty: 0, growth_per_error: 1,
    solid_walls: false, apple_lifetime_seconds: null, rotten_apples: 0,
  },
  {
    number: 2, board_size: 16, tick_ms: 145, min_score_to_advance: 40,
    match_seconds: 120, question_seconds: 40, reliability_tolerance: 15,
    wrong_answer_penalty: 0, growth_per_error: 1,
    solid_walls: false, apple_lifetime_seconds: null, rotten_apples: 0,
  },
  {
    number: 3, board_size: 14, tick_ms: 130, min_score_to_advance: 50,
    match_seconds: 110, question_seconds: 35, reliability_tolerance: 12,
    wrong_answer_penalty: 0, growth_per_error: 2,
    solid_walls: false, apple_lifetime_seconds: null, rotten_apples: 0,
  },
  {
    number: 4, board_size: 14, tick_ms: 125, min_score_to_advance: 50,
    match_seconds: 100, question_seconds: 30, reliability_tolerance: 10,
    wrong_answer_penalty: 5, growth_per_error: 2,
    solid_walls: true, apple_lifetime_seconds: 12, rotten_apples: 0,
  },
  {
    number: 5, board_size: 12, tick_ms: 115, min_score_to_advance: 60,
    match_seconds: 90, question_seconds: 25, reliability_tolerance: 10,
    wrong_answer_penalty: 5, growth_per_error: 2,
    solid_walls: true, apple_lifetime_seconds: 10, rotten_apples: 2,
  },
  {
    number: 6, board_size: 12, tick_ms: 105, min_score_to_advance: 70,
    match_seconds: 90, question_seconds: 20, reliability_tolerance: 8,
    wrong_answer_penalty: 10, growth_per_error: 3,
    solid_walls: true, apple_lifetime_seconds: 8, rotten_apples: 4,
  },
];

export const levelService = {
  async listLevels(): Promise<Level[]> {
    try {
      return await httpGet<Level[]>("/levels");
    } catch {
      return LOCAL_LEVELS;
    }
  },
};
