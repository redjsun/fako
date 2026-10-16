import React from "react";
import { Level } from "../types";
import { formatClock } from "../utils/formatters";
import { describeLevelRules } from "../utils/levelRules";
import { Icon } from "./Icon";

interface ExitMatchDialogProps {
  score: number;
  acertos: number;
  answered: number;
  timeLeft: number;
  onContinue: () => void;
  onExit: () => void;
}

/** Confirmação de "Sair": explica a consequência e mostra o que fica salvo. */
export const ExitMatchDialog: React.FC<ExitMatchDialogProps> = ({
  score,
  acertos,
  answered,
  timeLeft,
  onContinue,
  onExit,
}) => {
  return (
    <div className="popup-scrim popup-scrim--strong">
      <section
        className="popup-card dialog-card"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="exit-title"
        aria-describedby="exit-description"
      >
        <span className="dialog-card__icon dialog-card__icon--danger" aria-hidden="true">
          <Icon name="logout" size={28} />
        </span>
        <h2 id="exit-title">Sair da partida?</h2>
        <p id="exit-description">
          A partida termina agora e não dá para voltar a ela. Seus pontos e acertos desta rodada
          ficam salvos na sua Jornada.
        </p>

        <dl className="dialog-card__summary">
          <div>
            <dt>Pontos</dt>
            <dd>{score} pts</dd>
          </div>
          <div>
            <dt>Acertos</dt>
            <dd>
              {acertos} / {answered}
            </dd>
          </div>
          <div>
            <dt>Tempo restante</dt>
            <dd>{formatClock(timeLeft)}</dd>
          </div>
        </dl>

        <div className="dialog-card__actions">
          <button type="button" className="button button--primary button--block" onClick={onContinue} autoFocus>
            Continuar jogando (Esc)
          </button>
          <button type="button" className="button button--danger-outline button--block" onClick={onExit}>
            <Icon name="logout" size={18} />
            Sair e salvar
          </button>
        </div>
        <p className="dialog-card__hint">Dica: o jogo fica pausado enquanto esta janela estiver aberta.</p>
      </section>
    </div>
  );
};

interface HowToPlayDialogProps {
  rules: Level;
  pointsPerCorrect: number;
  onClose: () => void;
}

/** "Como jogar" durante a partida, sem sair do jogo. */
export const HowToPlayDialog: React.FC<HowToPlayDialogProps> = ({
  rules,
  pointsPerCorrect,
  onClose,
}) => {
  const blocks = rules.growth_per_error === 1 ? "1 bloco" : `${rules.growth_per_error} blocos`;
  const penalty = rules.wrong_answer_penalty > 0 ? ` e perde ${rules.wrong_answer_penalty} pts` : "";
  const steps = [
    { icon: "apple" as const, title: "Colete as maçãs", text: "Guie a cobrinha com as setas. Cada maçã traz uma afirmação." },
    {
      icon: "sliders" as const,
      title: "Avalie de 0% a 100%",
      text: `Você tem ${rules.question_seconds}s para marcar na barra o quanto a informação é confiável.`,
    },
    {
      icon: "target" as const,
      title: "Fique perto da referência",
      text: `Até ${rules.reliability_tolerance} pontos de distância vale +${pointsPerCorrect} pts. Mais longe, a cobrinha cresce ${blocks}${penalty}.`,
    },
    {
      icon: "flag" as const,
      title: `Regras do nível ${rules.number}`,
      text: describeLevelRules(rules).join(" · "),
    },
  ];

  return (
    <div className="popup-scrim popup-scrim--strong">
      <section className="popup-card dialog-card" role="dialog" aria-modal="true" aria-labelledby="howto-title">
        <span className="dialog-card__icon" aria-hidden="true">
          <Icon name="book" size={28} />
        </span>
        <h2 id="howto-title">Como jogar</h2>
        <ol className="howto-list">
          {steps.map((step) => (
            <li key={step.title}>
              <span className="howto-list__icon" aria-hidden="true">
                <Icon name={step.icon} size={20} />
              </span>
              <span>
                <strong>{step.title}</strong>
                {step.text}
              </span>
            </li>
          ))}
        </ol>
        <button type="button" className="button button--primary button--block" onClick={onClose} autoFocus>
          Voltar ao jogo (Esc)
        </button>
      </section>
    </div>
  );
};
