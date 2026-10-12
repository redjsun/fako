import React from "react";
import { UserStats } from "../types";
import { Icon, IconName } from "./Icon";
import { SnakeScene } from "./SnakeScene";

interface HomeScreenProps {
  username: string;
  currentLevel: number;
  maxLevels: number;
  missingPoints: number;
  matchSeconds: number;
  stats: UserStats;
  matchesPlayed: number;
  onPlay: () => void;
  onTutorial: () => void;
}

const HOW_IT_WORKS: { icon: IconName; title: string; text: string }[] = [
  { icon: "apple", title: "1. Colete as maçãs", text: "Guie a cobrinha com as setas. Cada maçã traz uma afirmação." },
  { icon: "sliders", title: "2. Avalie de 0% a 100%", text: "Arraste a barra para dizer o quanto a informação é confiável." },
  { icon: "bulb", title: "3. Aprenda com a resposta", text: "Veja a referência oficial, a explicação e a fonte." },
];

/** Início: chamada para jogar, como funciona, jornada e última partida. */
export const HomeScreen: React.FC<HomeScreenProps> = ({
  username,
  currentLevel,
  maxLevels,
  missingPoints,
  matchSeconds,
  stats,
  matchesPlayed,
  onPlay,
  onTutorial,
}) => {
  const answered = stats.totalAcertos + stats.totalErros;
  const accuracy = answered > 0 ? `${Math.round((stats.totalAcertos / answered) * 100)}%` : "—";
  const lastMatch = stats.history[0];
  const isLastLevel = currentLevel >= maxLevels;

  return (
    <div className="home-grid">
      <div className="home-grid__main">
        <section className="hero-card" aria-labelledby="hero-title">
          <div className="hero-card__text">
            <span className="hero-card__hello">Olá, {username}!</span>
            <h1 id="hero-title">Pronto para caçar algumas fakes hoje?</h1>
            <p>
              Partidas de {matchSeconds} segundos. Cada maçã traz uma afirmação: marque de 0% a 100% o
              quanto ela é confiável.
            </p>
            <div className="hero-card__actions">
              <button type="button" className="button button--amber" onClick={onPlay}>
                Jogar agora →
              </button>
              <button type="button" className="button button--outline-light" onClick={onTutorial}>
                Como jogar
              </button>
            </div>
          </div>
          <div className="hero-card__board" aria-hidden="true">
            <SnakeScene bodyLength={3} trailLength={4} label="Cobrinha do FAKO no tabuleiro" />
          </div>
        </section>

        <section className="home-steps" aria-labelledby="steps-title">
          <header className="section-header">
            <h2 id="steps-title">Como funciona</h2>
            <span>Aprenda em menos de 1 minuto</span>
          </header>
          <div className="home-steps__grid">
            {HOW_IT_WORKS.map((step) => (
              <article key={step.title} className="step-card">
                <span className="step-card__icon" aria-hidden="true">
                  <Icon name={step.icon} size={22} />
                </span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </article>
            ))}
          </div>
        </section>
      </div>

      <aside className="home-grid__side">
        <section className="card" aria-labelledby="journey-title">
          <header className="card__header">
            <h2 id="journey-title">Sua jornada</h2>
            <span className="tag tag--success">
              Nível {currentLevel} de {maxLevels}
            </span>
          </header>
          <ol className="level-dots" aria-label="Progresso nos níveis">
            {Array.from({ length: maxLevels }, (_, index) => {
              const number = index + 1;
              const state = number < currentLevel ? "done" : number === currentLevel ? "current" : "locked";
              return (
                <li key={number} className={`level-dots__item is-${state}`} aria-current={state === "current" ? "step" : undefined}>
                  {number}
                </li>
              );
            })}
          </ol>
          <p className="journey-hint">
            <Icon name="check" size={14} />
            {isLastLevel
              ? missingPoints > 0
                ? `Faltam ${missingPoints} pts para vencer o nível ${currentLevel}`
                : "Você chegou ao último nível!"
              : `Faltam ${missingPoints} pts para o nível ${currentLevel + 1}`}
          </p>
        </section>

        <div className="stat-grid">
          <div className="stat-tile">
            <strong>{stats.highScore}</strong>
            <span>Melhor pontuação</span>
          </div>
          <div className="stat-tile">
            <strong>{accuracy}</strong>
            <span>Taxa de acertos</span>
          </div>
          <div className="stat-tile">
            <strong>{matchesPlayed}</strong>
            <span>Partidas jogadas</span>
          </div>
        </div>

        <section className="card" aria-labelledby="last-match-title">
          <h2 id="last-match-title" className="card__title">
            Sua última partida
          </h2>
          {lastMatch && lastMatch.answers.length > 0 ? (
            <ul className="last-answers">
              {lastMatch.answers.slice(0, 3).map((answer, index) => (
                <li key={index} className="last-answers__item">
                  <span className={`mini-status ${answer.isCorrect ? "is-correct" : "is-wrong"}`} aria-hidden="true">
                    <Icon name={answer.isCorrect ? "check" : "x"} size={12} />
                  </span>
                  <div className="last-answers__text">
                    <strong>{answer.statement}</strong>
                    <span>
                      Você: {answer.reliability}% · Referência: {answer.reference}%
                    </span>
                  </div>
                  <span className={`tag ${answer.isCorrect ? "tag--success" : "tag--danger"}`}>
                    {answer.isCorrect ? "Acertou" : "Errou"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-text">
              Suas respostas aparecem aqui depois da primeira partida, com a sua avaliação e a
              referência oficial.
            </p>
          )}
        </section>
      </aside>
    </div>
  );
};
