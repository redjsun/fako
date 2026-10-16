import { Direction, Position } from "../types";

// Regras do tabuleiro da cobrinha, sem estado: posições, colisões e sorteio de células.

const DIRECTION_DELTAS: Record<Direction, [number, number]> = {
  UP: [0, -1],
  DOWN: [0, 1],
  LEFT: [-1, 0],
  RIGHT: [1, 0],
};

export function sameCell(a: Position, b: Position): boolean {
  return a.x === b.x && a.y === b.y;
}

export function includesCell(cells: Position[], cell: Position): boolean {
  return cells.some((item) => sameCell(item, cell));
}

/**
 * A cabeça nova bate no corpo? Sem crescer, a ponta da cauda sai do lugar no mesmo passo,
 * então ir para a célula dela não é mordida.
 */
export function hitsBody(snake: Position[], head: Position, growing: boolean): boolean {
  const body = growing ? snake : snake.slice(0, -1);
  return includesCell(body, head);
}

/** Cobra de 3 blocos no meio do tabuleiro, virada para a direita. */
export function initialSnake(boardSize: number): Position[] {
  const middle = Math.floor(boardSize / 2);
  return [
    { x: middle, y: middle },
    { x: middle - 1, y: middle },
    { x: middle - 2, y: middle },
  ];
}

/**
 * Próxima posição da cabeça. Com paredes atravessáveis a cobra volta pelo lado oposto;
 * com paredes sólidas, sair do tabuleiro devolve null (a cobra bateu).
 */
export function nextHead(
  head: Position,
  direction: Direction,
  boardSize: number,
  solidWalls: boolean
): Position | null {
  const [dx, dy] = DIRECTION_DELTAS[direction];
  const x = head.x + dx;
  const y = head.y + dy;
  if (solidWalls) {
    return x < 0 || y < 0 || x >= boardSize || y >= boardSize ? null : { x, y };
  }
  return { x: (x + boardSize) % boardSize, y: (y + boardSize) % boardSize };
}

/** Célula livre sorteada, fora de `occupied`; null quando o tabuleiro está cheio. */
export function randomFreeCell(
  boardSize: number,
  occupied: Position[],
  random: () => number = Math.random
): Position | null {
  const freeCells: Position[] = [];
  for (let x = 0; x < boardSize; x++) {
    for (let y = 0; y < boardSize; y++) {
      if (!includesCell(occupied, { x, y })) freeCells.push({ x, y });
    }
  }
  return freeCells.length > 0 ? freeCells[Math.floor(random() * freeCells.length)] : null;
}

