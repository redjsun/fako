import React from "react";

export interface FakoLogoProps {
  size?: "medium" | "large";
  // "inverse" para fundos escuros (painel do login).
  variant?: "default" | "inverse";
  className?: string;
}

/** Logo do FAKO: três blocos da cobrinha, a maçã e o nome. */
export const FakoLogo: React.FC<FakoLogoProps> = ({
  size = "medium",
  variant = "default",
  className = "",
}) => {
  return (
    <div className={`fako-logo fako-logo--${size} fako-logo--${variant} ${className}`} aria-label="FAKO">
      <span className="fako-logo__blocks" aria-hidden="true">
        <span className="fako-logo__block" />
        <span className="fako-logo__block" />
        <span className="fako-logo__block fako-logo__block--head" />
        <span className="fako-logo__apple" />
      </span>
      <span className="fako-logo__text">FAKO</span>
    </div>
  );
};
