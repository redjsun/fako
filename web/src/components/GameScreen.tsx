import React from "react";
import { Direction, GameStatus, Position } from "../types";
import { GameBoard } from "./GameBoard";
import { Icon } from "./Icon";
import { PausedOverlay, ResumeCountdown } from "./BoardOverlays";

interface GameScreenProps {
  status: GameStatus;
  level: number;
  score: number;
  minScoreToAdvance: number;
  isLastLevel: boolean;
  gridSize: number;
  rottenApples: Position[];
  isAppleFading: boolean;
  solidWalls: boolean;
  snake: Position[];
  direction: Direction;
  apple: Position | null;
  blocksFromErrors: number;
  countdownLeft: number;
  countdownTotal: number;
  onDirection: (direction: Direction) => void;
  onTogglePause: () => void;
  onHowToPlay: () => void;
}

const ARROW_KEYS: { direction: Direction; icon: "up" | "left" | "down" | "right"; label: string }[] = [
  { direction: "LEFT", icon: "left", label: "Esquerda" },
  { direction: "DOWN", icon: "down", label: "Baixo" },
  { direction: "RIGHT", icon: "right", label: "Direita" },
];

/**
 * Área da partida abaixo do HUD: progresso e cobrinha à esquerda, tabuleiro no centro,
 * pausa, ajuda e controles à direita.
 */
export const GameScreen: React.FC<GameScreenProps> = ({
  status,
  level,
  score,
  minScoreToAdvance,
  isLastLevel,
  gridSize,
  rottenApples,
  isAppleFading,
  solidWalls,
  snake,
  direction,
  apple,
  blocksFromErrors,
  countdownLeft,
  countdownTotal,
  onDirection,
  onTogglePause,
  onHowToPlay,
}) => {
  const goalPercent = minScoreToAdvance > 0 ? Math.min(100, (score / minScoreToAdvance) * 100) : 0;
  const isPaused = status === "PAUSED";
  const canSteer = status === "PLAYING";

  return (
    <div className="game-layout">
      <aside className="game-layout__side game-layout__side--left">
        <section className="side-card">
          <h2 className="side-card__eyebrow">
            <Icon name="apple" size={14} />
            Progresso
          </h2>
          <div className="side-card__progress">
            <span>
              <span>{isLastLevel ? `Meta do nível ${level}` : `Meta p/ o nível ${level + 1}`}</span>
              <span>
                {score} / {minScoreToAdvance} pts
              </span>
            </span>
            <span className="progress-track" aria-hidden="true">
              <span style={{ width: `${goalPercent}%` }} />
            </span>
          </div>
        </section>

        <section className="side-card">
          <h2 className="side-card__title">
            <Icon name="snake" size={17} />
            Sua cobrinha
          </h2>
          <dl className="side-card__rows">
            <div>
              <dt>Tamanho atual</dt>
              <dd>
                {snake.length} {snake.length === 1 ? "bloco" : "blocos"}
              </dd>
            </div>
            <div>
              <dt>Blocos ganhos por erro</dt>
              <dd>+{blocksFromErrors}</dd>
            </div>
          </dl>
          <p className="side-card__note">Ela só cresce quando você erra. Cuidado para não se morder!</p>
        </section>
      </aside>

      <section className="game-layout__board" aria-label="Tabuleiro">
        <div className={solidWalls ? "board-frame board-frame--solid" : "board-frame"}>
          <GameBoard
            gridSize={gridSize}
            rottenApples={rottenApples}
            isAppleFading={isAppleFading}
            snake={snake}
            direction={direction}
            apple={apple}
            onSwipe={onDirection}
          />
          {status === "COUNTDOWN" && (
            <ResumeCountdown secondsLeft={countdownLeft} total={countdownTotal} direction={direction} />
          )}
          {isPaused && <PausedOverlay onResume={onTogglePause} />}
        </div>
      </section>

      <aside className="game-layout__side game-layout__side--right">
        <section className="side-card">
          <button
            type="button"
            className="button button--primary button--block"
            onClick={onTogglePause}
            disabled={status !== "PLAYING" && !isPaused}
          >
            <Icon name="pause" size={17} />
            {isPaused ? "Continuar (Esc)" : "Pausar (Esc)"}
          </button>
          <button type="button" className="button button--subtle button--block" onClick={onHowToPlay}>
            <Icon name="book" size={17} />
            Como jogar
          </button>
          <p className="side-card__note">Para encerrar, use “Sair” no topo. Sua pontuação é salva.</p>
        </section>

        <section className="side-card side-card--controls">
          <h2 className="side-card__label">Controles</h2>
          <div className="key-pad">
            <button
              type="button"
              className="key-cap"
              aria-label="Cima"
              disabled={!canSteer}
              onPointerDown={() => onDirection("UP")}
              // Enter/Espaço no botão (o toque e o mouse já viraram no onPointerDown)
              onClick={(event) => event.detail === 0 && onDirection("UP")}
            >
              <Icon name="up" size={18} />
            </button>
            <div className="key-pad__row">
              {ARROW_KEYS.map((key) => (
                <button
                  key={key.direction}
                  type="button"
                  className="key-cap"
                  aria-label={key.label}
                  disabled={!canSteer}
                  onPointerDown={() => onDirection(key.direction)}
                  onClick={(event) => event.detail === 0 && onDirection(key.direction)}
                >
                  <Icon name={key.icon} size={18} />
                </button>
              ))}
            </div>
          </div>
          <div className="key-legend">
            <kbd className="key-cap key-cap--text">Esc</kbd>
            Pausar partida
          </div>
          <p className="side-card__note side-card__note--muted">
            Também funciona com W A S D ou deslizando o dedo no tabuleiro.
          </p>
        </section>
      </aside>
    </div>
  );
};
