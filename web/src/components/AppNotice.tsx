import React from "react";
import { Icon } from "./Icon";

interface AppNoticeProps {
  message: string;
  onClose: () => void;
}

/** Aviso do app ao jogador (ex.: partida não salva no servidor), com botão para fechar. */
export const AppNotice: React.FC<AppNoticeProps> = ({ message, onClose }) => (
  <div className="app-notice" role="alert">
    <Icon name="bulb" size={18} />
    <span>{message}</span>
    <button type="button" className="app-notice__close" onClick={onClose} aria-label="Fechar aviso">
      <Icon name="x" size={16} />
    </button>
  </div>
);
