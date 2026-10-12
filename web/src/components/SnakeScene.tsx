import React from "react";

interface SnakeSceneProps {
  // Quantidade de blocos do corpo, sem contar a cabeça.
  bodyLength?: number;
  // Quantidade de pontos do caminho até a maçã.
  trailLength?: number;
  label: string;
  className?: string;
}

const CELL = 22;
const GAP = 2;
const HEIGHT = 64;

/**
 * Cobrinha andando até a maçã, no mesmo desenho do tabuleiro do jogo.
 * As cores vêm dos tokens do tabuleiro (classes `snake-scene__*` no CSS).
 */
export const SnakeScene: React.FC<SnakeSceneProps> = ({
  bodyLength = 4,
  trailLength = 6,
  label,
  className = "",
}) => {
  const top = (HEIGHT - CELL) / 2;
  const headX = 8 + bodyLength * (CELL + GAP);
  const trailStart = headX + CELL + 10;
  const appleX = trailStart + trailLength * 14 + 14;
  const width = appleX + 24;

  return (
    <svg
      className={`snake-scene ${className}`}
      viewBox={`0 0 ${width} ${HEIGHT}`}
      role="img"
      aria-label={label}
    >
      {Array.from({ length: bodyLength }, (_, index) => {
        const x = 8 + index * (CELL + GAP);
        return (
          <g key={index}>
            <rect className="snake-scene__body" x={x} y={top} width={CELL} height={CELL} rx={6} />
            <rect className="snake-scene__shine" x={x + 2} y={top + 2} width={CELL - 4} height={7} rx={3} />
          </g>
        );
      })}

      <rect className="snake-scene__head" x={headX} y={top} width={CELL} height={CELL} rx={7} />
      {[top + 6, top + CELL - 6].map((eyeY) => (
        <g key={eyeY}>
          <circle className="snake-scene__eye" cx={headX + 14} cy={eyeY} r={3.3} />
          <circle className="snake-scene__pupil" cx={headX + 15.2} cy={eyeY} r={1.7} />
        </g>
      ))}

      {Array.from({ length: trailLength }, (_, index) => (
        <rect
          key={index}
          className="snake-scene__trail"
          x={trailStart + index * 14}
          y={HEIGHT / 2 - 2.25}
          width={4.5}
          height={4.5}
          rx={1}
        />
      ))}

      <ellipse className="snake-scene__apple-shadow" cx={appleX} cy={HEIGHT / 2 + 13} rx={12} ry={3.2} />
      <circle className="snake-scene__apple" cx={appleX} cy={HEIGHT / 2} r={12.5} />
      <ellipse
        className="snake-scene__apple-shine"
        cx={appleX - 4.5}
        cy={HEIGHT / 2 - 4.5}
        rx={4}
        ry={2.3}
        transform={`rotate(-35 ${appleX - 4.5} ${HEIGHT / 2 - 4.5})`}
      />
      <path
        className="snake-scene__stem"
        d={`M ${appleX} ${HEIGHT / 2 - 12} C ${appleX - 1} ${HEIGHT / 2 - 18}, ${appleX - 2} ${HEIGHT / 2 - 21}, ${appleX + 3} ${HEIGHT / 2 - 24}`}
      />
      <ellipse
        className="snake-scene__leaf"
        cx={appleX + 6.5}
        cy={HEIGHT / 2 - 22}
        rx={4}
        ry={2.1}
        transform={`rotate(25 ${appleX + 6.5} ${HEIGHT / 2 - 22})`}
      />
    </svg>
  );
};
