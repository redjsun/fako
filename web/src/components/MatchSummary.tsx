import React from "react";
import { AnsweredQuestion, MatchEndReason } from "../types";
import { formatClock } from "../utils/formatters";
import { Icon } from "./Icon";

interface MatchSummaryProps {
  username: string;
  endReason: MatchEndReason;
  score: number;
  level: number;
  maxLevel: number;
  minScoreToAdvance: number;
  advanced: boolean;
  answers: AnsweredQuestion[];
  snakeLength: number;
  secondsPlayed: number;
  pointsPerCorrect: number;
  onPlayAgain: () => void;
  onGoHome: () => void;
  onOpenJourney: () => void;
}

const END_REASON_TEXT: Record<MatchEndReason, string> = {
  TIMEOUT: "Tempo esgotado · Partida encerrada",
  GAMEOVER: "A cobrinha se mordeu · Partida encerrada",
  EXIT: "Você saiu · Partida encerrada",
};

/** Fim da partida: pontuação, números da rodada, próximo objetivo e o que foi analisado. */
export const MatchSummary: React.FC<MatchSummaryProps> = ({
  username,
  endReason,
  score,
  level,
  maxLevel,
  minScoreToAdvance,
  advanced,
  answers,
  snakeLength,
  secondsPlayed,
  pointsPerCorrect,
  onPlayAgain,
  onGoHome,
  onOpenJourney,
}) => {
  const acertos = answers.filter((answer) => answer.isCorrect).length;
  const accuracy = answers.length > 0 ? Math.round((acertos / answers.length) * 100) : 0;
  const isLastLevel = level >= maxLevel;
  const missing = Math.max(0, minScoreToAdvance - score);
  const goalPercent = minScoreToAdvance > 0 ? Math.min(100, (score / minScoreToAdvance) * 100) : 100;

  let goalTitle: string;
  let goalText: string;
  if (advanced) {
    goalTitle = `Nível ${level + 1} liberado!`;
    goalText = `Você fez ${score} de ${minScoreToAdvance} pts. A próxima partida já começa no nível ${level + 1}.`;
  } else if (isLastLevel && missing === 0) {
    goalTitle = "Você venceu o último nível!";
    goalText = `${score} de ${minScoreToAdvance} pts no nível ${level}.`;
  } else {
    const points = missing === 1 ? "ponto" : "pontos";
    goalTitle = isLastLevel
      ? `Faltam ${missing} ${points} para vencer o nível ${level}`
      : `Faltam ${missing} ${points} para o nível ${level + 1}`;
    goalText = `${score} de ${minScoreToAdvance} pts · Dica: ficar a até 15 pontos da referência vale +${pointsPerCorrect}.`;
  }

  return (
    <div className="match-summary">
      <section className="match-summary__score" aria-labelledby="summary-title">
        <span className="match-summary__reason">
          <Icon name="timer" size={16} />
          {END_REASON_TEXT[endReason]}
        </span>

        <div className="match-summary__greeting">
          <p id="summary-title">
            {advanced ? `Mandou bem, ${username}!` : `Boa tentativa, ${username}!`}
          </p>
          <span>Você fez</span>
        </div>

        <p className="match-summary__points">
          <strong>{score}</strong>
          <span>pontos</span>
        </p>

        <dl className="match-summary__numbers">
          <div>
            <dd>
              {acertos}/{answers.length}
            </dd>
            <dt>acertos</dt>
          </div>
          <div>
            <dd>{accuracy}%</dd>
            <dt>precisão</dt>
          </div>
          <div>
            <dd>{snakeLength}</dd>
            <dt>blocos de cobra</dt>
          </div>
          <div>
            <dd>{formatClock(secondsPlayed)}</dd>
            <dt>jogados</dt>
          </div>
        </dl>

        <div className="match-summary__goal">
          <span className="match-summary__goal-level" aria-hidden="true">
            {isLastLevel ? level : level + 1}
          </span>
          <div className="match-summary__goal-text">
            <strong>{goalTitle}</strong>
            <span className="match-summary__goal-track" aria-hidden="true">
              <span style={{ width: `${goalPercent}%` }} />
            </span>
            <small>{goalText}</small>
          </div>
        </div>

        <div className="match-summary__actions">
          <button type="button" className="button button--vivid button--large" onClick={onPlayAgain} autoFocus>
            <Icon name="replay" size={18} />
            Jogar novamente (Enter)
          </button>
          <button type="button" className="button button--ghost-light button--large" onClick={onGoHome}>
            <Icon name="home" size={18} />
            Ir para o Início
          </button>
        </div>
      </section>

      <section className="match-summary__answers" aria-labelledby="answers-title">
        <header>
          <h2 id="answers-title">O que você analisou</h2>
          <span>
            {answers.length} {answers.length === 1 ? "afirmação" : "afirmações"}
          </span>
        </header>

        {answers.length === 0 ? (
          <p className="empty-text">
            Nenhuma maçã coletada nesta partida. Na próxima, guie a cobrinha até a maçã para ver uma
            afirmação.
          </p>
        ) : (
          <ul className="answer-list">
            {answers.map((answer, index) => (
              <li key={index} className="answer-list__item">
                <span
                  className={`answer-list__icon ${answer.isCorrect ? "is-correct" : "is-wrong"}`}
                  aria-hidden="true"
                >
                  <Icon name={answer.isCorrect ? "check" : "x"} size={18} />
                </span>
                <div>
                  <p>{answer.statement}</p>
                  <span className="answer-list__meta">
                    <span className={`tag ${answer.isCorrect ? "tag--success" : "tag--danger"}`}>
                      {answer.isCorrect ? `Acertou · +${pointsPerCorrect}` : "Errou · +1 bloco"}
                    </span>
                    Você: {answer.reliability}% · Referência: {answer.reference}%
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}

        <button type="button" className="link-button match-summary__journey" onClick={onOpenJourney}>
          Ver minha jornada completa →
        </button>
      </section>
    </div>
  );
};
