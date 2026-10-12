import React from "react";
import { FakoLogo } from "./FakoLogo";
import { Icon } from "./Icon";

export type HeaderTab = "home" | "tutorial" | "journey";

interface AppHeaderProps {
  active: HeaderTab;
  username: string;
  level: number;
  totalScore: number;
  isMuted: boolean;
  theme: "light" | "dark";
  onNavigate: (tab: HeaderTab) => void;
  onToggleTheme: () => void;
  onToggleMute: () => void;
  onLogout: () => void;
}

const TABS: { id: HeaderTab; label: string }[] = [
  { id: "home", label: "Início" },
  { id: "tutorial", label: "Tutorial" },
  { id: "journey", label: "Jornada" },
];

/** Header da Início e da Jornada: logo, abas, jogador e Tema/Som/Sair com rótulo. */
export const AppHeader: React.FC<AppHeaderProps> = ({
  active,
  username,
  level,
  totalScore,
  isMuted,
  theme,
  onNavigate,
  onToggleTheme,
  onToggleMute,
  onLogout,
}) => {
  return (
    <header className="app-header">
      <FakoLogo />

      <div className="app-header__actions">
        <nav className="app-header__nav" aria-label="Navegação principal">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`app-header__tab ${active === tab.id ? "is-active" : ""}`}
              aria-current={active === tab.id ? "page" : undefined}
              onClick={() => onNavigate(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="app-header__user">
          <span className="app-header__avatar" aria-hidden="true">
            {username.charAt(0).toUpperCase()}
          </span>
          <span className="app-header__user-text">
            <strong>{username}</strong>
            <small>
              Nível {level} • {totalScore} pts
            </small>
          </span>
        </div>

        <span className="app-header__divider" aria-hidden="true" />

        <div className="app-header__tools">
          <button
            type="button"
            className="tool-button"
            onClick={onToggleTheme}
            aria-label={`Alternar para tema ${theme === "dark" ? "claro" : "escuro"}`}
          >
            <Icon name="sun" size={16} />
            Tema
          </button>
          <button
            type="button"
            className="tool-button"
            onClick={onToggleMute}
            aria-pressed={isMuted}
            aria-label={isMuted ? "Ativar som" : "Desativar som"}
          >
            <Icon name="volume" size={16} className={isMuted ? "is-muted" : ""} />
            Som
          </button>
          <button type="button" className="tool-button tool-button--danger" onClick={onLogout}>
            <Icon name="logout" size={16} />
            Sair
          </button>
        </div>
      </div>
    </header>
  );
};
