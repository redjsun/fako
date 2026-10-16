import React from "react";
import { Level, UserStats } from "../types";
import { formatMatchDate } from "../utils/formatters";
import { achievementProgress } from "../utils/achievements";
import { describeLevelRules } from "../utils/levelRules";
import { Icon } from "./Icon";

interface JourneyScreenProps {
  levels: Level[];
  currentLevel: number;
  highestLevel: number;
  totalScore: number;
  matchesPlayed: number;
  bestScoreInLevel: number;
  stats: UserStats;
  isGuest: boolean;
  onPlayLevel: (level: number) => void;
}

const LEVEL_DESCRIPTIONS = [
  "Cobra lenta",
  "Um pouco mais rápida",
  "Velocidade média",
  "Rápida",
  "Muito rápida",
  "Desafio final",
];

const MiniBoard: React.FC = () => (
  <span className="mini-board" aria-hidden="true">
    {Array.from({ length: 36 }, (_, index) => (
      <span key={index} className={(Math.floor(index / 6) + index) % 2 === 0 ? "" : "is-dark"} />
    ))}
  </span>
);

/** Jornada: os 6 níveis, totais, conquistas e últimas partidas. */
export const JourneyScreen: React.FC<JourneyScreenProps> = ({
  levels,
  currentLevel,
  highestLevel,
  totalScore,
  matchesPlayed,
  bestScoreInLevel,
  stats,
  isGuest,
  onPlayLevel,
}) => {
  const answered = stats.totalAcertos + stats.totalErros;
  const accuracy = answered > 0 ? `${Math.round((stats.totalAcertos / answered) * 100)}%` : "—";
  const current = levels.find((level) => level.number === currentLevel);
  const goal = current?.min_score_to_advance ?? 0;
  const missing = Math.max(0, goal - bestScoreInLevel);
  const isLastLevel = currentLevel >= levels.length;
  const achievements = achievementProgress(stats);
  const unlockedCount = achievements.filter((achievement) => achievement.unlocked).length;

  return (
    <div className="journey-layout">
      <section className="journey-layout__map" aria-labelledby="journey-heading">
        <header className="page-heading">
          <h1 id="journey-heading">Minha jornada</h1>
          <p>
            {isGuest
              ? "Como visitante, seu progresso fica só neste navegador e some ao sair. Crie uma conta para guardá-lo."
              : "Seu progresso fica salvo na sua conta. Continue de onde parou."}
          </p>
        </header>

        <ol className="level-grid">
          {levels.map((level, index) => {
            const isCurrent = level.number === currentLevel;
            const isUnlocked = level.number <= highestLevel;
            const state = isCurrent ? "current" : isUnlocked ? "done" : "locked";
            return (
              <li key={level.number} className={`level-card is-${state}`}>
                <div className="level-card__top">
                  <span className="level-card__badge" aria-hidden="true">
                    {state === "locked" ? <Icon name="lock" size={22} /> : level.number}
                  </span>
                  <span className="level-card__state">
                    {state === "current" ? "Atual" : state === "done" ? "Liberado" : "Bloqueado"}
                  </span>
                </div>
                <MiniBoard />
                <div className="level-card__text">
                  <h2>Nível {level.number}</h2>
                  <p>
                    {LEVEL_DESCRIPTIONS[index] ?? ""}
                    {isCurrent && ` · meta ${level.min_score_to_advance} pts`}
                  </p>
                  <ul className="level-card__rules" aria-label={`Regras do nível ${level.number}`}>
                    {describeLevelRules(level).map((rule) => (
                      <li key={rule}>{rule}</li>
                    ))}
                  </ul>
                </div>
                <div className="level-card__footer">
                  {state === "locked" ? (
                    <span>Conclua o nível {level.number - 1}</span>
                  ) : (
                    <>
                      <span>
                        {isCurrent ? `${bestScoreInLevel} / ${level.min_score_to_advance} pts` : "Jogar de novo"}
                      </span>
                      <button
                        type="button"
                        className={`button ${isCurrent ? "button--amber button--raised" : "button--subtle"}`}
                        onClick={() => onPlayLevel(level.number)}
                        aria-label={`Jogar o nível ${level.number}`}
                      >
                        Jogar →
                      </button>
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <aside className="journey-layout__summary">
        <div className="stat-grid stat-grid--large">
          <div className="stat-tile">
            <strong>{totalScore}</strong>
            <span>pontos</span>
          </div>
          <div className="stat-tile">
            <strong>{accuracy}</strong>
            <span>acertos</span>
          </div>
          <div className="stat-tile">
            <strong>{matchesPlayed}</strong>
            <span>{matchesPlayed === 1 ? "partida" : "partidas"}</span>
          </div>
        </div>

        <section className="card card--roomy" aria-labelledby="achievements-title">
          <h2 id="achievements-title" className="card__title card__title--large">
            Conquistas · {unlockedCount} de {achievements.length}
          </h2>
          <ul className="achievement-list">
            {achievements.map((achievement) => (
              <li key={achievement.id}>
                <span className="achievement-list__row">
                  <strong>{achievement.title}</strong>
                  <span>{achievement.unlocked ? "Conquistada" : achievement.counter || `${achievement.percent}%`}</span>
                </span>
                <span className="achievement-list__description">{achievement.description}</span>
                <span className="progress-track progress-track--thick" aria-hidden="true">
                  <span style={{ width: `${achievement.percent}%` }} />
                </span>
              </li>
            ))}
          </ul>
          <p className="tip-box">
            <Icon name="bulb" size={18} />
            {isLastLevel
              ? missing > 0
                ? `Faltam ${missing} pontos para vencer o último nível.`
                : "Você venceu o último nível. Tente bater sua melhor pontuação!"
              : `Faltam ${missing} pontos para liberar o nível ${currentLevel + 1}. Uma partida boa já resolve!`}
          </p>
        </section>

        <section className="card card--roomy" aria-labelledby="history-title">
          <h2 id="history-title" className="card__title card__title--large">
            Últimas partidas
          </h2>
          {stats.history.length > 0 && (
            <ul className="history-list">
              {stats.history.slice(0, 5).map((match) => (
                <li key={match.finishedAt}>
                  <span className="history-list__icon" aria-hidden="true">
                    <Icon name="snake" size={18} />
                  </span>
                  <span className="history-list__text">
                    <strong>
                      Nível {match.level} · {match.acertos} de {match.acertos + match.erros} acertos
                    </strong>
                    <span>{formatMatchDate(match.finishedAt)}</span>
                  </span>
                  <span className="history-list__score">{match.score} pts</span>
                </li>
              ))}
            </ul>
          )}
          <p className="empty-text">
            {stats.history.length > 0
              ? "Suas próximas partidas aparecem aqui, com pontos e acertos de cada uma."
              : "Nenhuma partida ainda. Jogue a primeira para ver seu histórico aqui."}
          </p>
        </section>
      </aside>
    </div>
  );
};
