import React from "react";
import { GameStatus } from "../types";
import { formatClock } from "../utils/formatters";
import { FakoLogo } from "./FakoLogo";
import { Icon } from "./Icon";

interface MatchHudProps {
  level: number;
  boardSize: number;
  status: GameStatus;
  timeLeft: number;
  duration: number;
  score: number;
  // Enquanto a resposta vai para a API, sair agora deixaria o resultado sem dono.
  exitDisabled?: boolean;
  onExit: () => void;
}

// O cronômetro fica vermelho nos últimos segundos.
const TIME_WARNING_SECONDS = 20;

const STATUS_TEXT: Record<GameStatus, { label: string; tone: "active" | "paused" | "ended" }> = {
  PLAYING: { label: "Em andamento", tone: "active" },
  PAUSED: { label: "Pausado", tone: "paused" },
  QUESTION: { label: "Pausado · pergunta", tone: "paused" },
  FEEDBACK: { label: "Pausado · resultado", tone: "paused" },
  COUNTDOWN: { label: "Retomando", tone: "paused" },
  FINISHED: { label: "Partida encerrada", tone: "ended" },
};

/** HUD da partida: Sair e logo, nível, status, cronômetro com barra e pontos. */
export const MatchHud: React.FC<MatchHudProps> = ({
  level,
  boardSize,
  status,
  timeLeft,
  duration,
  score,
  exitDisabled = false,
  onExit,
}) => {
  const statusText = STATUS_TEXT[status];
  const isEnding = timeLeft <= TIME_WARNING_SECONDS;
  const timePercent = duration > 0 ? (timeLeft / duration) * 100 : 0;

  return (
    <header className="match-hud">
      <div className="match-hud__group">
        <button
          type="button"
          className="match-hud__exit"
          onClick={onExit}
          disabled={status === "FINISHED" || exitDisabled}
        >
          <Icon name="logout" size={16} />
          Sair
        </button>
        <FakoLogo />
      </div>

      <div className="match-hud__group">
        <span className="match-hud__level">
          <strong>NÍVEL {level}</strong>
          <span>
            · Tabuleiro {boardSize}×{boardSize}
          </span>
        </span>
        <span className={`match-hud__status match-hud__status--${statusText.tone}`} role="status">
          <span className="match-hud__status-dot" aria-hidden="true" />
          {statusText.label}
        </span>
      </div>

      <div className="match-hud__group">
        <div
          className={`match-hud__timer ${isEnding ? "is-ending" : ""}`}
          aria-label={`Tempo restante: ${formatClock(timeLeft)} de ${formatClock(duration)}`}
        >
          <span className="match-hud__timer-row">
            <Icon name="timer" size={16} />
            <strong>{formatClock(timeLeft)}</strong>
            <small>/ {formatClock(duration)}</small>
          </span>
          <span className="match-hud__timer-track" aria-hidden="true">
            <span className="match-hud__timer-fill" style={{ width: `${timePercent}%` }} />
          </span>
        </div>
        <div className="match-hud__score" aria-label={`${score} pontos`}>
          <Icon name="star" size={18} />
          <strong>{score}</strong>
          <small>pts</small>
        </div>
      </div>
    </header>
  );
};
