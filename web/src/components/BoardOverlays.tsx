import React from "react";
import { Direction } from "../types";
import { Icon, IconName } from "./Icon";

const DIRECTION_TEXT: Record<Direction, { label: string; icon: IconName }> = {
  UP: { label: "para cima", icon: "up" },
  DOWN: { label: "para baixo", icon: "down" },
  LEFT: { label: "para a esquerda", icon: "left" },
  RIGHT: { label: "para a direita", icon: "right" },
};

interface ResumeCountdownProps {
  secondsLeft: number;
  total: number;
  direction: Direction;
}

/** Contagem antes de a cobra voltar a andar, com o tabuleiro e a direção visíveis. */
export const ResumeCountdown: React.FC<ResumeCountdownProps> = ({ secondsLeft, total, direction }) => {
  const directionText = DIRECTION_TEXT[direction];
  const steps = Array.from({ length: total }, (_, index) => total - index);

  return (
    <div className="board-overlay" role="status" aria-live="assertive">
      <div className="countdown-ring" aria-hidden="true">
        <span>{secondsLeft}</span>
      </div>
      <p className="board-overlay__title">Prepare-se!</p>
      <p className="board-overlay__subtitle">
        A cobrinha segue {directionText.label}
        <Icon name={directionText.icon} size={18} />
      </p>
      <div className="countdown-steps" aria-hidden="true">
        {steps.map((step) => (
          <span key={step} className={step === secondsLeft ? "is-current" : ""}>
            {step}
          </span>
        ))}
      </div>
      <p className="board-overlay__hint">Use as setas assim que o jogo voltar.</p>
    </div>
  );
};

interface PausedOverlayProps {
  onResume: () => void;
}

export const PausedOverlay: React.FC<PausedOverlayProps> = ({ onResume }) => {
  return (
    <div className="board-overlay">
      <div className="countdown-ring countdown-ring--icon" aria-hidden="true">
        <Icon name="pause" size={56} />
      </div>
      <p className="board-overlay__title">Jogo pausado</p>
      <p className="board-overlay__subtitle">O cronômetro está parado.</p>
      <button type="button" className="button button--amber" onClick={onResume} autoFocus>
        Continuar (Esc)
      </button>
    </div>
  );
};
