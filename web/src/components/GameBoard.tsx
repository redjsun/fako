import React, { useRef, useEffect } from "react";
import { Direction, Position } from "../types";

interface GameBoardProps {
  gridSize: number;
  rottenApples: Position[];
  /** A maçã está para mudar de lugar: desenhada mais apagada. */
  isAppleFading: boolean;
  snake: Position[];
  direction: Direction;
  apple: Position | null;
  onSwipe: (dir: Direction) => void;
}

export const GameBoard: React.FC<GameBoardProps> = ({
  gridSize,
  rottenApples,
  isAppleFading,
  snake,
  direction,
  apple,
  onSwipe,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Tela de alta densidade (Retina)
    const dpr = window.devicePixelRatio || 1;
    const displaySize = 620;
    canvas.width = displaySize * dpr;
    canvas.height = displaySize * dpr;
    ctx.scale(dpr, dpr);

    const cellSize = displaySize / gridSize;

    // Cores dos tokens do tabuleiro (index.css)
    const styles = getComputedStyle(document.documentElement);
    const cellA = styles.getPropertyValue("--board-cell-a").trim() || "#dfe8c8";
    const cellB = styles.getPropertyValue("--board-cell-b").trim() || "#d3dfb8";
    const headColor = styles.getPropertyValue("--snake-head").trim() || "#1d4a27";
    const bodyColor = styles.getPropertyValue("--snake-body").trim() || "#2f6b3a";
    const appleColor = styles.getPropertyValue("--apple-body").trim() || "#dc3545";
    const leafColor = styles.getPropertyValue("--apple-leaf").trim() || "#2f6b3a";
    const rottenColor = styles.getPropertyValue("--apple-rotten").trim() || "#6b4a2b";

    // 1. Xadrez do tabuleiro
    for (let x = 0; x < gridSize; x++) {
      for (let y = 0; y < gridSize; y++) {
        ctx.fillStyle = (x + y) % 2 === 0 ? cellA : cellB;
        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
      }
    }

    // 2. Maçãs com brilho, cabinho e folha; a podre é marrom, com manchas e sem folha
    const drawApple = (position: Position, rotten: boolean, alpha: number) => {
      const ax = position.x * cellSize;
      const ay = position.y * cellSize;
      const cx = ax + cellSize / 2;
      const cy = ay + cellSize * 0.54;
      const radius = cellSize * 0.36;
      ctx.save();
      ctx.globalAlpha = alpha;

      // Sombra suave da maçã
      ctx.fillStyle = "rgba(0, 0, 0, 0.12)";
      ctx.beginPath();
      ctx.ellipse(cx, ay + cellSize * 0.88, radius * 0.9, radius * 0.28, 0, 0, Math.PI * 2);
      ctx.fill();

      // Corpo da maçã
      ctx.fillStyle = rotten ? rottenColor : appleColor;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      if (rotten) {
        // Manchas da maçã podre
        ctx.fillStyle = "rgba(0, 0, 0, 0.35)";
        [
          [-0.3, -0.1, 0.16],
          [0.25, 0.2, 0.12],
          [0.05, -0.4, 0.09],
        ].forEach(([dx, dy, size]) => {
          ctx.beginPath();
          ctx.arc(cx + dx * radius, cy + dy * radius, size * cellSize, 0, Math.PI * 2);
          ctx.fill();
        });
      } else {
        // Brilho da maçã
        ctx.fillStyle = "rgba(255, 255, 255, 0.35)";
        ctx.beginPath();
        ctx.ellipse(cx - radius * 0.35, cy - radius * 0.35, radius * 0.28, radius * 0.18, -Math.PI / 4, 0, Math.PI * 2);
        ctx.fill();
      }

      // Cabinho de madeira
      ctx.strokeStyle = "#5a3d28";
      ctx.lineWidth = Math.max(2, cellSize * 0.08);
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(cx, cy - radius * 0.8);
      ctx.quadraticCurveTo(cx - 2, cy - radius * 1.35, cx + 4, cy - radius * 1.45);
      ctx.stroke();

      if (!rotten) {
        // Folha verde
        ctx.fillStyle = leafColor;
        ctx.beginPath();
        ctx.ellipse(cx + 6, cy - radius * 1.25, cellSize * 0.14, cellSize * 0.08, Math.PI / 6, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    };

    if (apple) drawApple(apple, false, isAppleFading ? 0.45 : 1);
    rottenApples.forEach((rotten) => drawApple(rotten, true, 1));

    // 3. Desenhar a Cobrinha (corpo com cantos arredondados)
    const padding = cellSize * 0.06;
    const innerSize = cellSize - padding * 2;
    const cornerRadius = cellSize * 0.26;

    snake.forEach((segment, index) => {
      const sx = segment.x * cellSize + padding;
      const sy = segment.y * cellSize + padding;
      const isHead = index === 0;

      ctx.fillStyle = isHead ? headColor : bodyColor;

      ctx.beginPath();
      if (typeof ctx.roundRect === "function") {
        ctx.roundRect(sx, sy, innerSize, innerSize, isHead ? cornerRadius * 1.2 : cornerRadius);
      } else {
        ctx.rect(sx, sy, innerSize, innerSize);
      }
      ctx.fill();

      // Marcação suave no corpo para textura orgânica
      if (!isHead) {
        ctx.fillStyle = "rgba(255, 255, 255, 0.09)";
        ctx.beginPath();
        if (typeof ctx.roundRect === "function") {
          ctx.roundRect(sx + 2, sy + 2, innerSize - 4, innerSize * 0.4, cornerRadius * 0.8);
        }
        ctx.fill();
      }
    });

    // 4. Olhos da Cobrinha que acompanham a direção do movimento
    if (snake.length > 0) {
      const head = snake[0];
      const cx = (head.x + 0.5) * cellSize;
      const cy = (head.y + 0.5) * cellSize;

      let dx = 0;
      let dy = 0;
      switch (direction) {
        case "UP":
          dy = -1;
          break;
        case "DOWN":
          dy = 1;
          break;
        case "LEFT":
          dx = -1;
          break;
        case "RIGHT":
          dx = 1;
          break;
      }

      // Vetor perpendicular para os dois olhos
      const px = -dy;
      const py = dx;

      const eyeOffsetForward = cellSize * 0.16;
      const eyeOffsetSide = cellSize * 0.22;
      const eyeRadius = cellSize * 0.13;
      const pupilRadius = cellSize * 0.065;
      const pupilShift = cellSize * 0.045;

      [-1, 1].forEach((side) => {
        const eyeX = cx + dx * eyeOffsetForward + px * side * eyeOffsetSide;
        const eyeY = cy + dy * eyeOffsetForward + py * side * eyeOffsetSide;

        // Esclera branca
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(eyeX, eyeY, eyeRadius, 0, Math.PI * 2);
        ctx.fill();

        // Pupila preta olhando na direção do movimento
        ctx.fillStyle = "#111a13";
        ctx.beginPath();
        ctx.arc(eyeX + dx * pupilShift, eyeY + dy * pupilShift, pupilRadius, 0, Math.PI * 2);
        ctx.fill();

        // Ponto de luz na pupila
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(eyeX + dx * pupilShift - 1, eyeY + dy * pupilShift - 1, pupilRadius * 0.4, 0, Math.PI * 2);
        ctx.fill();
      });
    }
  }, [gridSize, rottenApples, isAppleFading, snake, direction, apple]);

  // Gestos de Touch (Swipe)
  const handleTouchStart = (e: React.TouchEvent<HTMLCanvasElement>) => {
    const touch = e.touches[0];
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTouchEnd = (e: React.TouchEvent<HTMLCanvasElement>) => {
    if (!touchStartRef.current) return;
    const touch = e.changedTouches[0];
    const dx = touch.clientX - touchStartRef.current.x;
    const dy = touch.clientY - touchStartRef.current.y;
    touchStartRef.current = null;

    const minSwipeDistance = 24;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < minSwipeDistance) return;

    if (Math.abs(dx) > Math.abs(dy)) {
      onSwipe(dx > 0 ? "RIGHT" : "LEFT");
    } else {
      onSwipe(dy > 0 ? "DOWN" : "UP");
    }
  };

  return (
    <div className="canvas-wrapper">
      <canvas
        ref={canvasRef}
        className="game-canvas"
        style={{ width: "100%", height: "auto", aspectRatio: "1" }}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        aria-label="Grade do jogo da cobrinha FAKO"
      />
    </div>
  );
};
