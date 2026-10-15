import React, { useState } from "react";
import { Icon, IconName } from "./Icon";
import { ReliabilityBar } from "./ReliabilityBar";
import { SnakeScene } from "./SnakeScene";

interface TutorialScreenProps {
  questionSeconds: number;
  pointsPerCorrect: number;
  completeLabel: string;
  onComplete: () => void;
  onSkip: () => void;
}

interface TutorialStep {
  icon: IconName;
  title: string;
  headline?: string;
  description: React.ReactNode;
  visual: React.ReactNode;
  wide?: boolean;
}

const ControlsVisual: React.FC = () => (
  <div className="tutorial-visual tutorial-visual--controls">
    <div className="tutorial-dpad" aria-hidden="true">
      <span className="tutorial-dpad__key tutorial-dpad__key--up">
        <Icon name="up" size={15} />
      </span>
      <span className="tutorial-dpad__key tutorial-dpad__key--left">
        <Icon name="left" size={15} />
      </span>
      <span className="tutorial-dpad__key tutorial-dpad__key--right">
        <Icon name="right" size={15} />
      </span>
      <span className="tutorial-dpad__key tutorial-dpad__key--down">
        <Icon name="down" size={15} />
      </span>
    </div>
    <span className="tutorial-visual__divider" aria-hidden="true" />
    <div className="tutorial-visual__board">
      <SnakeScene bodyLength={3} trailLength={5} label="Cobrinha do tabuleiro guiada para a maçã" />
    </div>
  </div>
);

const AppleFlowVisual: React.FC<{ questionSeconds: number }> = ({ questionSeconds }) => (
  <div className="tutorial-visual tutorial-visual--flow">
    <figure className="tutorial-flow__item">
      <div className="tutorial-flow__box">
        <SnakeScene bodyLength={3} trailLength={2} label="Passo 1: colete a maçã" />
      </div>
      <figcaption>1. Colete a maçã</figcaption>
    </figure>
    <span className="tutorial-flow__arrow" aria-hidden="true">→</span>
    <figure className="tutorial-flow__item">
      <div className="tutorial-flow__box tutorial-flow__box--impact">
        <SnakeScene bodyLength={3} trailLength={0} label="Passo 2: a cobra pausa" />
      </div>
      <figcaption>2. A cobra pausa</figcaption>
    </figure>
    <span className="tutorial-flow__arrow" aria-hidden="true">→</span>
    <figure className="tutorial-flow__item">
      <div className="tutorial-flow__box tutorial-flow__box--question">
        <p className="tutorial-bubble">“Tomar vitamina C previne resfriado?”</p>
        <span className="pill pill--soft pill--small">
          <Icon name="timer" size={12} />
          {questionSeconds}s
        </span>
      </div>
      <figcaption>3. Surge a afirmação</figcaption>
    </figure>
  </div>
);

const ReliabilityVisual: React.FC = () => (
  <div className="tutorial-visual tutorial-visual--reliability">
    <div className="tutorial-reliability__bar">
      <p className="tutorial-bubble tutorial-bubble--large">“Tomar vitamina C previne resfriado?”</p>
      <ReliabilityBar
        value={45}
        reference={50}
        caption="A área tracejada é a faixa de acerto: até 15 pontos da referência."
      />
    </div>
    <span className="tutorial-visual__divider tutorial-visual__divider--tall" aria-hidden="true" />
    <div className="tutorial-reliability__side">
      <p className="tutorial-note">
        <span className="tutorial-note__icon" aria-hidden="true">i</span>
        Quanto mais próximo da referência científica, maiores são seus pontos!
      </p>
      <ul className="tutorial-legend">
        <li>
          <span className="tutorial-legend__dot tutorial-legend__dot--you" aria-hidden="true" />
          Você (45%)
        </li>
        <li>
          <span className="tutorial-legend__dot tutorial-legend__dot--reference" aria-hidden="true" />
          Referência (50%)
        </li>
      </ul>
    </div>
  </div>
);

const GrowthVisual: React.FC = () => (
  <div className="tutorial-visual tutorial-visual--growth">
    <span className="growth-row growth-row--success">
      <Icon name="check" size={16} />
      Acerto: Cobra não cresce
    </span>
    <span className="growth-row growth-row--danger">
      <Icon name="alert" size={16} />
      Erro: Cobra cresce +1
    </span>
  </div>
);

/** Tutorial em 5 passos, alinhado às regras da partida (tempo por pergunta e pontos). */
export const TutorialScreen: React.FC<TutorialScreenProps> = ({
  questionSeconds,
  pointsPerCorrect,
  completeLabel,
  onComplete,
  onSkip,
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  const steps: TutorialStep[] = [
    {
      icon: "target",
      title: "Objetivo do jogo",
      headline: "Jogue. Analise. Aprenda.",
      description: "Colete maçãs, avalie de 0% a 100% o quanto cada afirmação é confiável e acumule pontos.",
      visual: (
        <div className="tutorial-visual tutorial-visual--board">
          <SnakeScene bodyLength={5} trailLength={7} label="Cobrinha do FAKO em direção à maçã no tabuleiro" />
        </div>
      ),
    },
    {
      icon: "snake",
      title: "Controle a cobrinha",
      description: (
        <>
          Use as setas para movimentar a cobrinha.
          <br />
          Colete as maçãs e avance pelo jogo.
        </>
      ),
      visual: <ControlsVisual />,
    },
    {
      icon: "apple",
      title: "A Maçã Abre a Afirmação",
      headline: "Colete a fruta e avalie o fato.",
      description: (
        <>
          Ao comer a fruta, a cobrinha pausa e surge uma afirmação sobre o tabuleiro. Você tem{" "}
          <strong>{questionSeconds} segundos</strong> para ler e posicionar seu palpite na barra de
          confiabilidade.
        </>
      ),
      visual: <AppleFlowVisual questionSeconds={questionSeconds} />,
      wide: true,
    },
    {
      icon: "sliders",
      title: "Barra de Confiabilidade",
      headline: "De 0% a 100% com margem de 15 pontos.",
      description: (
        <>
          Ajuste o cursor de 0% (“Nada confiável”) a 100% (“Totalmente confiável”).
          <br />
          Palpites com até <strong>15 pontos de distância</strong> da referência oficial contam como
          acerto <strong>(+{pointsPerCorrect} pontos)!</strong>
        </>
      ),
      visual: <ReliabilityVisual />,
      wide: true,
    },
    {
      icon: "snake",
      title: "A Cobra Só Cresce no Erro!",
      headline: "Acertos mantêm seu tamanho seguro.",
      description:
        "Ao contrário de outros jogos, a cobra NÃO cresce ao comer a maçã! Ela só cresce 1 bloco quando você erra a pergunta (> 15 pontos da referência). Complete 6 níveis para vencer!",
      visual: <GrowthVisual />,
      wide: true,
    },
  ];

  const step = steps[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === steps.length - 1;

  return (
    <main className="tutorial-page">
      <section
        className={`tutorial-card ${step.wide ? "tutorial-card--wide" : ""}`}
        aria-labelledby="tutorial-title"
      >
        <div className="tutorial-card__top">
          <span className="tutorial-progress">
            <span className="tutorial-progress__dots" aria-hidden="true">
              {steps.map((_, index) => (
                <span key={index} className={index <= currentStep ? "is-done" : ""} />
              ))}
            </span>
            Passo {currentStep + 1} de {steps.length}
          </span>
          <button type="button" className="tutorial-skip" onClick={onSkip}>
            Pular Tutorial
            <Icon name="x" size={16} />
          </button>
        </div>

        <h2 id="tutorial-title" className="tutorial-card__title">
          <Icon name={step.icon} size={28} />
          {step.title}
        </h2>
        {step.headline && <p className="tutorial-card__headline">{step.headline}</p>}
        <p className="tutorial-card__description">{step.description}</p>

        {step.visual}

        <div className="tutorial-card__actions">
          <button
            type="button"
            className="button button--outline-strong button--pill"
            onClick={() => setCurrentStep((previous) => previous - 1)}
            disabled={isFirst}
          >
            ← Anterior
          </button>
          <button
            type="button"
            className="button button--strong button--pill"
            onClick={() => (isLast ? onComplete() : setCurrentStep((previous) => previous + 1))}
            autoFocus
          >
            {isLast ? completeLabel : "Próximo Passo →"}
          </button>
        </div>
      </section>
    </main>
  );
};
