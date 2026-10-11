import React from "react";
import { soundEffects } from "../services/audioService";
import { FakoLogo } from "./FakoLogo";

interface HeaderProps {
  score: number;
  level: number;
  applesInLevel: number;
  maxApplesPerLevel: number;
  maxLevels: number;
  matchTimeLeft?: number;
  isMuted: boolean;
  onToggleMute: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onGoHome?: () => void;
  username?: string;
}

export const Header: React.FC<HeaderProps> = ({
  score,
  level,
  applesInLevel,
  maxApplesPerLevel,
  maxLevels,
  matchTimeLeft,
  isMuted,
  onToggleMute,
  theme,
  onToggleTheme,
  onGoHome,
  username,
}) => {
  const progressPercent = Math.min(100, Math.round((applesInLevel / maxApplesPerLevel) * 100));

  return (
    <header className="fako-header">
      <div className="header-top">
        <div className="logo-group">
          <FakoLogo
            size="small"
            subtitle={username ? `Jogador: ${username}` : "Checador da Cobrinha"}
          />
        </div>

        <div className="header-actions">
          {onGoHome && (
            <button
              type="button"
              className="icon-button home-nav-btn"
              onClick={onGoHome}
              title="Voltar para a tela inicial"
              aria-label="Voltar para a tela inicial"
            >
              🏠
            </button>
          )}

          <button
            type="button"
            className="icon-button"
            onClick={onToggleMute}
            title={isMuted ? "Ativar efeitos sonoros" : "Mutar sons"}
            aria-label={isMuted ? "Ativar sons" : "Mutar sons"}
          >
            {isMuted ? "🔇" : "🔊"}
          </button>

          <button
            type="button"
            className="icon-button"
            onClick={onToggleTheme}
            title={`Tema atual: ${theme === "dark" ? "Escuro" : "Claro"} (Clique para alternar)`}
            aria-label="Alternar tema visual"
          >
            {theme === "dark" ? "🌙" : "☀️"}
          </button>
        </div>
      </div>

      <div className="stats-bar">
        {matchTimeLeft !== undefined && (
          <div className={`stat-pill time-pill ${matchTimeLeft <= 20 ? "pill-time-alert" : ""}`}>
            <span className="stat-label">Tempo</span>
            <span className="stat-value">{matchTimeLeft}s</span>
          </div>
        )}

        <div className="stat-pill score-pill">
          <span className="stat-label">Pontos</span>
          <span className="stat-value" id="score-display">{score}</span>
        </div>

        <div className="stat-pill level-pill">
          <span className="stat-label">Nível</span>
          <span className="stat-value">
            {level}<span className="stat-total">/{maxLevels}</span>
          </span>
        </div>

        <div className="stat-pill apples-pill">
          <div className="apples-info">
            <span className="stat-label">Maçãs</span>
            <span className="stat-value">
              {applesInLevel}<span className="stat-total">/{maxApplesPerLevel}</span>
            </span>
          </div>
          <div className="progress-track" title={`${applesInLevel} de ${maxApplesPerLevel} maçãs no nível`}>
            <div
              className="progress-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>
    </header>
  );
};
