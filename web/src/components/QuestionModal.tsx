import React from "react";
import { AnswerResult, ModelGuess, Question } from "../types";
import { reliabilityLabel } from "../utils/formatters";
import { Icon } from "./Icon";
import { ReliabilityBar } from "./ReliabilityBar";

const SHORTCUTS = [0, 25, 50, 75, 100];

interface QuestionPopupProps {
  question: Question | null;
  reliability: number;
  secondsLeft: number;
  isSubmitting: boolean;
  onChangeReliability: (value: number) => void;
  onConfirm: () => void;
}

/** Popup da afirmação: a partida pausa e o jogador marca de 0% a 100% na barra. */
export const QuestionPopup: React.FC<QuestionPopupProps> = ({
  question,
  reliability,
  secondsLeft,
  isSubmitting,
  onChangeReliability,
  onConfirm,
}) => {
  return (
    <div className="popup-scrim popup-scrim--below-hud">
      <section
        className="popup-card question-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="question-statement"
      >
        <div className="question-card__pills">
          <span className="pill pill--muted">
            <Icon name="pause" size={14} />
            Tempo pausado
          </span>
          <span className={`pill pill--amber ${secondsLeft <= 10 ? "is-ending" : ""}`} role="timer">
            <Icon name="hourglass" size={14} />
            {secondsLeft}s para responder
          </span>
        </div>

        {question ? (
          <>
            <h2 id="question-statement" className="question-card__statement">
              “{question.statement}”
            </h2>
            <p className="question-card__prompt">Quão confiável é esta informação?</p>

            <div className="question-card__reading" aria-live="polite">
              <strong>{reliability}%</strong>
              <span>{reliabilityLabel(reliability)}</span>
            </div>

            <ReliabilityBar
              value={reliability}
              onChange={onChangeReliability}
              valueLabel="Sua resposta"
              autoFocus
            />

            <div className="question-card__shortcuts" role="group" aria-label="Valores rápidos">
              {SHORTCUTS.map((shortcut) => (
                <button
                  key={shortcut}
                  type="button"
                  className={`chip-button ${reliability === shortcut ? "is-active" : ""}`}
                  onClick={() => onChangeReliability(shortcut)}
                >
                  {shortcut}%
                </button>
              ))}
            </div>

            <button
              type="button"
              className="button button--dark button--block button--large"
              onClick={onConfirm}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Enviando resposta…" : "Confirmar resposta (Enter)"}
              <Icon name="right" size={20} />
            </button>

            <p className="question-card__help">
              Atalhos: ← → ajusta 5% · Enter confirma
              <br />
              Você acerta se ficar a até 15 pontos da referência oficial.
            </p>
          </>
        ) : (
          <p className="question-card__loading" role="status">
            Carregando a afirmação…
          </p>
        )}
      </section>
    </div>
  );
};

interface ResultPopupProps {
  statement: string;
  result: AnswerResult;
  pointsPerCorrect: number;
  onContinue: () => void;
}

function distanceMessage(result: AnswerResult): string {
  if (result.distance === 0) return "Cravou a referência. Na mosca!";
  const points = result.distance === 1 ? "ponto" : "pontos";
  return result.is_correct
    ? `Ficou a ${result.distance} ${points} da referência. Boa análise!`
    : `Ficou a ${result.distance} ${points} da referência. Leia o porquê abaixo.`;
}

/** Popup do resultado: sua resposta × referência, explicação, fonte e efeito na cobrinha. */
const GUESS_LABELS: Record<ModelGuess["category"], string> = {
  falso: "Falso",
  enganoso: "Enganoso",
  confere: "Confere",
  incerto: "Incerto",
};

// O que o classificador achou da afirmação; não muda a correção, que vem da checagem.
const ModelGuessCard: React.FC<{ guess: ModelGuess }> = ({ guess }) => (
  <div className="result-card__why result-card__model">
    <h3>
      <Icon name="bulb" size={18} />
      O que o classificador achou
    </h3>
    <p>
      <strong>{GUESS_LABELS[guess.category] ?? guess.category}</strong>
      {guess.category === "incerto"
        ? " — o modelo não tem certeza sobre esta afirmação."
        : ` — nota ${Math.round(guess.score ?? 0)} de 100, com ${Math.round(
            guess.confidence * 100
          )}% de confiança.`}
    </p>
    <p className="result-card__source">Modelo: {guess.model_version}</p>
  </div>
);

export const ResultPopup: React.FC<ResultPopupProps> = ({
  statement,
  result,
  pointsPerCorrect,
  onContinue,
}) => {
  const tone = result.is_correct ? "success" : "danger";

  return (
    <div className="popup-scrim popup-scrim--below-hud">
      <section
        className={`popup-card result-card result-card--${tone}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="result-title"
      >
        <header className="result-card__header">
          <span className="result-card__icon" aria-hidden="true">
            <Icon name={result.is_correct ? "check" : "x"} size={30} />
          </span>
          <div className="result-card__heading">
            <h2 id="result-title">{result.is_correct ? "Você acertou!" : "Não foi dessa vez"}</h2>
            <p>{distanceMessage(result)}</p>
          </div>
          <span className="result-card__badge">
            {result.is_correct ? `+${pointsPerCorrect} pts` : "+1 bloco"}
          </span>
        </header>

        <div className="result-card__body">
          <blockquote className="result-card__statement">“{statement}”</blockquote>

          <div className="result-card__comparison">
            <h3>Sua resposta × referência oficial</h3>
            <ReliabilityBar
              value={result.reliability}
              reference={result.reliability_reference}
              tolerance={result.tolerance}
              caption={`A área tracejada é a faixa de acerto: até ${result.tolerance} pontos da referência.`}
            />
          </div>

          <div className="result-card__why">
            <h3>
              <Icon name="bulb" size={18} />
              Por quê?
            </h3>
            <p>{result.explanation}</p>
            {result.source && (
              <p className="result-card__source">
                <Icon name="book" size={14} />
                Fonte: {result.source}
              </p>
            )}
          </div>

          {result.model_guess && <ModelGuessCard guess={result.model_guess} />}

          <div className="result-card__snake">
            <span className="result-card__snake-blocks" aria-hidden="true">
              <span />
              <span />
              <span />
              {!result.is_correct && <span className="is-new" />}
            </span>
            {result.is_correct
              ? "A cobrinha não cresceu. Continue assim!"
              : "A cobrinha cresceu +1 bloco. Leia com calma!"}
          </div>

          <button
            type="button"
            className="button button--dark button--block button--large"
            onClick={onContinue}
            autoFocus
          >
            Continuar jogando (Enter)
            <Icon name="right" size={20} />
          </button>
        </div>
      </section>
    </div>
  );
};
