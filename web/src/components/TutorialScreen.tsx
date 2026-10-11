import React, { useState } from "react";

interface TutorialScreenProps {
  onComplete: () => void;
  onSkip: () => void;
}

interface TutorialStep {
  id: number;
  badge: string;
  icon?: string;
  iconSvg?: React.ReactNode;
  title: string;
  headline?: React.ReactNode;
  subtitle?: string;
  description: React.ReactNode;
  visualSnippet?: React.ReactNode;
}

/**
 * Ilustração visual do Passo 1:
 * Reproduz o mini-tabuleiro com grade suave, a maçã oficial e
 * a COBRINHA IDÊNTICA À DO TABULEIRO DO JOGO (GameBoard.tsx):
 * - Segmentos arredondados com cores oficiais (--snake-head e --snake-body)
 * - Brilho superior em cada bloco do corpo
 * - Olhos expressivos com esclera, pupila voltada para a frente e ponto de luz
 * - Maçã com sombra, brilho elíptico, cabinho de madeira e folha verde
 * - Linha pontilhada de aproximação
 */
const BoardSnakeTutorialVisual: React.FC = () => {
  return (
    <div className="tutorial-board-visual">
      <svg
        viewBox="0 0 360 100"
        className="tutorial-board-svg"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Cobrinha do FAKO em direção à maçã no tabuleiro"
      >
        <defs>
          <pattern
            id="tutorialBoardGrid"
            width="20"
            height="20"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 20 0 L 0 0 0 20"
              fill="none"
              stroke="rgba(47, 107, 58, 0.14)"
              strokeWidth="1"
            />
          </pattern>
        </defs>

        {/* Fundo do Mini-Tabuleiro em tom suave */}
        <rect width="360" height="100" rx="14" fill="#eaf3e8" />
        <rect width="360" height="100" rx="14" fill="url(#tutorialBoardGrid)" />
        <rect
          width="360"
          height="100"
          rx="14"
          fill="none"
          stroke="#c7dec4"
          strokeWidth="1.5"
        />

        {/* 1. CORPO DA COBRINHA (Idêntico ao GameBoard.tsx: #2f6b3a com cantos arredondados) */}
        {[24, 48, 72, 96, 120].map((x, i) => (
          <g key={i}>
            <rect
              x={x}
              y={39}
              width={22}
              height={22}
              rx={5.5}
              fill="#2f6b3a"
            />
            {/* Brilho orgânico suave no topo de cada bloco */}
            <rect
              x={x + 2}
              y={41}
              width={18}
              height={7}
              rx={3}
              fill="rgba(255, 255, 255, 0.12)"
            />
          </g>
        ))}

        {/* 2. CABEÇA DA COBRINHA (Idêntico ao GameBoard.tsx: #1d4a27 com cantos arredondados) */}
        <rect
          x={144}
          y={39}
          width={23}
          height={22}
          rx={7}
          fill="#1d4a27"
        />

        {/* 3. OLHOS EXPRESSIVOS (Idênticos ao GameBoard.tsx: esclera branca, pupila preta voltada para a direita, ponto de luz) */}
        {/* Olho Superior */}
        <circle cx={158} cy={44.5} r={3.3} fill="#ffffff" />
        <circle cx={159.2} cy={44.5} r={1.65} fill="#111a13" />
        <circle cx={158.7} cy={44.0} r={0.65} fill="#ffffff" />

        {/* Olho Inferior */}
        <circle cx={158} cy={55.5} r={3.3} fill="#ffffff" />
        <circle cx={159.2} cy={55.5} r={1.65} fill="#111a13" />
        <circle cx={158.7} cy={55.0} r={0.65} fill="#ffffff" />

        {/* 4. TRAJETÓRIA PONTILHADA VERDE ATÉ A MAÇÃ */}
        {[178, 194, 210, 226, 242, 258, 274].map((dotX, idx) => (
          <rect
            key={idx}
            x={dotX}
            y={48}
            width={4.5}
            height={4.5}
            rx={1}
            fill="#257a3e"
          />
        ))}

        {/* 5. MAÇÃ OFICIAL DO JOGO (Idêntica ao GameBoard.tsx) */}
        {/* Sombra da Maçã */}
        <ellipse
          cx={304}
          cy={65}
          rx={13}
          ry={3.5}
          fill="rgba(0, 0, 0, 0.12)"
        />
        {/* Corpo Vermelho */}
        <circle cx={304} cy={52} r={13.5} fill="#dc3545" />
        {/* Brilho da Maçã */}
        <ellipse
          cx={299.5}
          cy={47.5}
          rx={4.2}
          ry={2.4}
          transform="rotate(-35 299.5 47.5)"
          fill="rgba(255, 255, 255, 0.42)"
        />
        {/* Cabinho de Madeira */}
        <path
          d="M 304 39 C 303 33, 302 30, 307 27"
          fill="none"
          stroke="#5a3d28"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        {/* Folha Verde */}
        <ellipse
          cx={310.5}
          cy={29}
          rx={4.2}
          ry={2.2}
          transform="rotate(25 310.5 29)"
          fill="#2f6b3a"
        />
      </svg>
    </div>
  );
};

/**
 * Ilustração visual do Passo 2 (Figma):
 * Divide a caixa em:
 * 1. Controles direcionais (D-pad em cruz com 4 botões verdes e setas brancas)
 * 2. Linha divisória vertical
 * 3. Mini-grade com a COBRINHA e MAÇÃ OFICIAIS DO TABULEIRO (GameBoard.tsx)
 */
const ControlsSnakeTutorialVisual: React.FC = () => {
  return (
    <div className="tutorial-controls-visual">
      {/* Lado Esquerdo: D-pad em Cruz */}
      <div className="tutorial-dpad-col">
        <div className="tutorial-dpad-grid">
          <div className="dpad-cell" />
          <div className="dpad-btn btn-up" aria-label="Cima">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </div>
          <div className="dpad-cell" />

          <div className="dpad-btn btn-left" aria-label="Esquerda">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </div>
          <div className="dpad-center-spacer" />
          <div className="dpad-btn btn-right" aria-label="Direita">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </div>

          <div className="dpad-cell" />
          <div className="dpad-btn btn-down" aria-label="Baixo">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M19 12l-7 7-7-7" />
            </svg>
          </div>
          <div className="dpad-cell" />
        </div>
      </div>

      {/* Divisória Vertical */}
      <div className="tutorial-visual-divider" aria-hidden="true" />

      {/* Lado Direito: Mini-Tabuleiro com a Cobrinha e Maçã Oficiais */}
      <div className="tutorial-mini-board-col">
        <svg
          viewBox="0 0 210 90"
          className="tutorial-sub-board-svg"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="Cobrinha do tabuleiro guiada para a maçã"
        >
          <defs>
            <pattern
              id="subBoardGrid"
              width="16"
              height="16"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 16 0 L 0 0 0 16"
                fill="none"
                stroke="rgba(47, 107, 58, 0.13)"
                strokeWidth="1"
              />
            </pattern>
          </defs>

          {/* Fundo do Grid com bordas suaves */}
          <rect width="210" height="90" rx="10" fill="#eaf3e8" />
          <rect width="210" height="90" rx="10" fill="url(#subBoardGrid)" />
          <rect
            width="210"
            height="90"
            rx="10"
            fill="none"
            stroke="#c7dec4"
            strokeWidth="1.2"
          />

          {/* Cobrinha Oficial do Tabuleiro (GameBoard.tsx) */}
          {/* Segmentos do Corpo: #2f6b3a com cantos arredondados e brilho orgânico */}
          {[16, 34, 52].map((x, i) => (
            <g key={i}>
              <rect
                x={x}
                y={36}
                width={17}
                height={17}
                rx={4.5}
                fill="#2f6b3a"
              />
              <rect
                x={x + 1.5}
                y={37.5}
                width={14}
                height={5.5}
                rx={2.5}
                fill="rgba(255, 255, 255, 0.12)"
              />
            </g>
          ))}

          {/* Cabeça da Cobrinha: #1d4a27 */}
          <rect
            x={70}
            y={36}
            width={18}
            height={17}
            rx={5.5}
            fill="#1d4a27"
          />

          {/* Olhos Oficiais (olhando para a direita) */}
          <circle cx={81} cy={40.5} r={2.6} fill="#ffffff" />
          <circle cx={82} cy={40.5} r={1.3} fill="#111a13" />
          <circle cx={81.6} cy={40.1} r={0.5} fill="#ffffff" />

          <circle cx={81} cy={48.5} r={2.6} fill="#ffffff" />
          <circle cx={82} cy={48.5} r={1.3} fill="#111a13" />
          <circle cx={81.6} cy={48.1} r={0.5} fill="#ffffff" />

          {/* Trajetória Pontilhada Verde */}
          {[96, 110, 124, 138, 152].map((dotX, idx) => (
            <rect
              key={idx}
              x={dotX}
              y={43}
              width={3.8}
              height={3.8}
              rx={0.8}
              fill="#257a3e"
            />
          ))}

          {/* Maçã Oficial do Tabuleiro */}
          <ellipse
            cx={176}
            cy={55}
            rx={10.5}
            ry={2.8}
            fill="rgba(0, 0, 0, 0.12)"
          />
          <circle cx={176} cy={45} r={11} fill="#dc3545" />
          <ellipse
            cx={172.5}
            cy={41.5}
            rx={3.5}
            ry={2}
            transform="rotate(-35 172.5 41.5)"
            fill="rgba(255, 255, 255, 0.42)"
          />
          <path
            d="M 176 34.5 C 175 29.5, 174 27, 178 24.5"
            fill="none"
            stroke="#5a3d28"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <ellipse
            cx={181}
            cy={26}
            rx={3.5}
            ry={1.8}
            transform="rotate(25 181 26)"
            fill="#2f6b3a"
          />
        </svg>
      </div>
    </div>
  );
};

/**
 * Ilustração visual do Passo 3 (Figma):
 * 1. Colete a maçã (Cobrinha oficial indo em direção à maçã)
 * 2. A cobra pausa (Cobrinha oficial tocando a maçã com partículas/brilho)
 * 3. Surge a afirmação (Balão com pergunta + badge do cronômetro 60s)
 */
const AppleAffirmationTutorialVisual: React.FC = () => {
  return (
    <div className="tutorial-step3-container">
      <div className="step3-flow-row">
        {/* Etapa 1: Colete a maçã */}
        <div className="step3-flow-item">
          <div className="step3-flow-box">
            <svg
              viewBox="0 0 100 68"
              className="step3-sub-svg"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="Passo 1: Colete a maçã"
            >
              <defs>
                <pattern
                  id="gridStep3_1"
                  width="12"
                  height="12"
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d="M 12 0 L 0 0 0 12"
                    fill="none"
                    stroke="rgba(47, 107, 58, 0.12)"
                    strokeWidth="1"
                  />
                </pattern>
              </defs>
              <rect width="100" height="68" rx="8" fill="#eaf3e8" />
              <rect width="100" height="68" rx="8" fill="url(#gridStep3_1)" />
              <rect width="100" height="68" rx="8" fill="none" stroke="#c7dec4" strokeWidth="1" />

              {/* Cobrinha oficial */}
              {[6, 19, 32].map((x, i) => (
                <g key={i}>
                  <rect x={x} y={26} width={12} height={12} rx={3.2} fill="#2f6b3a" />
                  <rect x={x + 1} y={27} width={10} height={4} rx={1.8} fill="rgba(255,255,255,0.12)" />
                </g>
              ))}
              {/* Cabeça */}
              <rect x={45} y={26} width={13} height={12} rx={4} fill="#1d4a27" />
              <circle cx={53} cy={29.5} r={2} fill="#ffffff" />
              <circle cx={53.8} cy={29.5} r={1} fill="#111a13" />
              <circle cx={53} cy={34.5} r={2} fill="#ffffff" />
              <circle cx={53.8} cy={34.5} r={1} fill="#111a13" />

              {/* Trajetória pontilhada */}
              {[62, 70, 78].map((dotX, idx) => (
                <rect key={idx} x={dotX} y={30.5} width={3} height={3} rx={0.6} fill="#257a3e" />
              ))}

              {/* Maçã oficial */}
              <ellipse cx={88} cy={39} rx={6.5} ry={1.8} fill="rgba(0,0,0,0.12)" />
              <circle cx={88} cy={32} r={7.5} fill="#dc3545" />
              <ellipse cx={85.5} cy={29.5} rx={2.4} ry={1.4} transform="rotate(-35 85.5 29.5)" fill="rgba(255,255,255,0.42)" />
              <path d="M 88 24.5 C 87.5 21, 87 19.5, 89.5 18" fill="none" stroke="#5a3d28" strokeWidth="1.3" strokeLinecap="round" />
              <ellipse cx={91} cy={19.5} rx={2.4} ry={1.2} transform="rotate(25 91 19.5)" fill="#2f6b3a" />
            </svg>
          </div>
          <span className="step3-flow-label">1. Colete a maçã</span>
        </div>

        {/* Seta 1 */}
        <span className="step3-flow-arrow" aria-hidden="true">→</span>

        {/* Etapa 2: A cobra pausa */}
        <div className="step3-flow-item">
          <div className="step3-flow-box">
            <svg
              viewBox="0 0 100 68"
              className="step3-sub-svg"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="Passo 2: A cobra pausa"
            >
              <defs>
                <pattern
                  id="gridStep3_2"
                  width="12"
                  height="12"
                  patternUnits="userSpaceOnUse"
                >
                  <path
                    d="M 12 0 L 0 0 0 12"
                    fill="none"
                    stroke="rgba(47, 107, 58, 0.12)"
                    strokeWidth="1"
                  />
                </pattern>
              </defs>
              <rect width="100" height="68" rx="8" fill="#eaf3e8" />
              <rect width="100" height="68" rx="8" fill="url(#gridStep3_2)" />
              <rect width="100" height="68" rx="8" fill="none" stroke="#c7dec4" strokeWidth="1" />

              {/* Linhas de impacto / pausa no topo */}
              <path d="M 67 18 L 64 14 M 72 17 L 72 12 M 77 18 L 80 14" stroke="#257a3e" strokeWidth="1.6" strokeLinecap="round" />

              {/* Cobrinha oficial */}
              {[15, 28, 41].map((x, i) => (
                <g key={i}>
                  <rect x={x} y={26} width={12} height={12} rx={3.2} fill="#2f6b3a" />
                  <rect x={x + 1} y={27} width={10} height={4} rx={1.8} fill="rgba(255,255,255,0.12)" />
                </g>
              ))}
              {/* Cabeça encostando na fruta */}
              <rect x={54} y={26} width={13} height={12} rx={4} fill="#1d4a27" />
              <circle cx={62} cy={29.5} r={2} fill="#ffffff" />
              <circle cx={62.8} cy={29.5} r={1} fill="#111a13" />
              <circle cx={62} cy={34.5} r={2} fill="#ffffff" />
              <circle cx={62.8} cy={34.5} r={1} fill="#111a13" />

              {/* Maçã oficial tocando a boca */}
              <ellipse cx={73} cy={39} rx={6.5} ry={1.8} fill="rgba(0,0,0,0.12)" />
              <circle cx={73} cy={32} r={7.5} fill="#dc3545" />
              <ellipse cx={70.5} cy={29.5} rx={2.4} ry={1.4} transform="rotate(-35 70.5 29.5)" fill="rgba(255,255,255,0.42)" />
              <path d="M 73 24.5 C 72.5 21, 72 19.5, 74.5 18" fill="none" stroke="#5a3d28" strokeWidth="1.3" strokeLinecap="round" />
              <ellipse cx={76} cy={19.5} rx={2.4} ry={1.2} transform="rotate(25 76 19.5)" fill="#2f6b3a" />
            </svg>
          </div>
          <span className="step3-flow-label">2. A cobra pausa</span>
        </div>

        {/* Seta 2 */}
        <span className="step3-flow-arrow" aria-hidden="true">→</span>

        {/* Etapa 3: Surge a afirmação */}
        <div className="step3-flow-item">
          <div className="step3-flow-box step3-question-box">
            <div className="step3-speech-bubble">
              <p>“Tomar vitamina C previne resfriado?”</p>
              <div className="bubble-tail" aria-hidden="true" />
            </div>
            <div className="step3-timer-pill">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              <span>60s</span>
            </div>
          </div>
          <span className="step3-flow-label">3. Surge a afirmação</span>
        </div>

        {/* Seta final à direita */}
        <span className="step3-flow-arrow" aria-hidden="true">→</span>
      </div>
    </div>
  );
};

/**
 * Ilustração visual do Passo 4 (Figma):
 * 1. Balão com afirmação
 * 2. Barra de gradiente (0% a 100%) com marcadores "Você (45%)" e "Ref (50%)"
 * 3. Chave de margem de 15 pontos de acerto
 * 4. Cards laterais: dica científica e legenda dos marcadores
 */
const ReliabilitySliderTutorialVisual: React.FC = () => {
  return (
    <div className="tutorial-step4-container">
      {/* Coluna da Esquerda: Barra Interativa com Balão e Marcadores */}
      <div className="step4-slider-col">
        {/* Balão da Pergunta */}
        <div className="step4-speech-bubble">
          <p>
            “Tomar vitamina C<br />
            previne resfriado?”
          </p>
          <div className="bubble-tail" aria-hidden="true" />
        </div>

        {/* Linha com Não Confiável, Marcadores e Confiável */}
        <div className="step4-labels-row">
          <div className="step4-tag tag-unreliable">
            <span className="tag-circle-icon icon-alert" aria-hidden="true">!</span>
            <div className="tag-text">
              <span>Não confiável</span>
              <small>(0%)</small>
            </div>
          </div>

          <div className="step4-markers-pair">
            {/* Marcador Você */}
            <div className="step4-marker marker-you">
              <span>Você (45%)</span>
              <span className="marker-arrow arrow-you" aria-hidden="true" />
            </div>
            {/* Marcador Ref */}
            <div className="step4-marker marker-ref">
              <span>Ref (50%)</span>
              <span className="marker-arrow arrow-ref" aria-hidden="true" />
            </div>
          </div>

          <div className="step4-tag tag-reliable">
            <div className="tag-text text-right">
              <span>Confiável</span>
              <small>(100%)</small>
            </div>
            <span className="tag-circle-icon icon-check" aria-hidden="true">✓</span>
          </div>
        </div>

        {/* A Barra Gradiente com os Marcadores */}
        <div className="step4-track-container">
          <div className="step4-gradient-track">
            {/* Thumb Você (45%) */}
            <div className="step4-thumb-you" style={{ left: "45%" }}>
              <span className="thumb-dot" />
            </div>
            {/* Marcador Ref (50%) */}
            <div className="step4-bar-ref" style={{ left: "50%" }} />
          </div>

          {/* Ticks e Escala com alinhamento exato */}
          <div className="step4-ticks-track">
            <div className="tick-mark tick-0">
              <span className="tick-pin" />
              <span className="tick-val">0%</span>
            </div>
            <div className="tick-mark tick-25">
              <span className="tick-pin" />
            </div>
            <div className="tick-mark tick-50">
              <span className="tick-pin" />
              <span className="tick-val">50%</span>
            </div>
            <div className="tick-mark tick-75">
              <span className="tick-pin" />
            </div>
            <div className="tick-mark tick-100">
              <span className="tick-pin" />
              <span className="tick-val">100%</span>
            </div>
          </div>

          {/* Chave de Margem de 15 pontos */}
          <div className="step4-bracket-container">
            <div className="step4-bracket-span">
              <span className="bracket-edge left" />
              <span className="bracket-dashed-bar" />
              <span className="bracket-edge right" />
            </div>
            <div className="bracket-caption">
              <span className="bracket-caption-title">15 pontos de margem</span>
              <span className="bracket-caption-sub">(acerto)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Divisória Vertical */}
      <div className="step4-vertical-divider" aria-hidden="true" />

      {/* Coluna da Direita: Dica e Legenda */}
      <div className="step4-side-col">
        {/* Card de Dica Informativa */}
        <div className="step4-info-card">
          <div className="step4-info-icon" aria-hidden="true">i</div>
          <p className="step4-info-text">
            Quanto mais próximo da referência científica, maiores são seus pontos!
          </p>
        </div>

        {/* Card de Legenda */}
        <div className="step4-legend-card">
          <div className="step4-legend-row">
            <span className="step4-legend-circle circle-you" />
            <span className="step4-legend-name">Você (45%)</span>
          </div>
          <div className="step4-legend-row">
            <span className="step4-legend-circle circle-ref" />
            <span className="step4-legend-name">Ref (50%)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export const TutorialScreen: React.FC<TutorialScreenProps> = ({ onComplete, onSkip }) => {
  const [currentStep, setCurrentStep] = useState(0);

  const steps: TutorialStep[] = [
    {
      id: 1,
      badge: "PASSO 1 DE 5",
      iconSvg: (
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="tutorial-target-icon"
        >
          <circle cx="12" cy="12" r="10" />
          <circle cx="12" cy="12" r="6" />
          <circle cx="12" cy="12" r="2" fill="currentColor" />
          <path d="M19 5l-5 5" />
        </svg>
      ),
      title: "Objetivo do jogo",
      headline: (
        <>
          Jogue. Analise.
          <br />
          Aprenda.
        </>
      ),
      description: "Encontre afirmações, avalie sua confiabilidade e acumule pontos.",
      visualSnippet: <BoardSnakeTutorialVisual />,
    },
    {
      id: 2,
      badge: "PASSO 2 DE 5",
      iconSvg: (
        <svg
          width="34"
          height="26"
          viewBox="0 0 34 26"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="tutorial-gamepad-icon"
          aria-hidden="true"
        >
          <path
            d="M 6 4 C 11 3, 23 3, 28 4 C 32 4.8, 33 8, 33 12 C 33 16, 31 22, 27 23 C 24 23.8, 22 20, 20.5 17.5 C 19.5 16, 18 15, 17 15 C 16 15, 14.5 16, 13.5 17.5 C 12 20, 10 23.8, 7 23 C 3 22, 1 16, 1 12 C 1 8, 2 4.8, 6 4 Z"
            fill="#17532a"
          />
          {/* D-Pad na esquerda */}
          <rect x="7.5" y="8.5" width="2" height="6" rx="0.8" fill="#ffffff" />
          <rect x="5.5" y="10.5" width="6" height="2" rx="0.8" fill="#ffffff" />
          {/* Botões de ação na direita */}
          <circle cx="24.5" cy="9.5" r="1.1" fill="#ffffff" />
          <circle cx="27.5" cy="11.5" r="1.1" fill="#ffffff" />
          <circle cx="24.5" cy="13.5" r="1.1" fill="#ffffff" />
          <circle cx="21.5" cy="11.5" r="1.1" fill="#ffffff" />
        </svg>
      ),
      title: "Controle a cobrinha",
      description: (
        <>
          Use as setas para movimentar a cobrinha.
          <br />
          Colete as maçãs e avance pelo jogo.
        </>
      ),
      visualSnippet: <ControlsSnakeTutorialVisual />,
    },
    {
      id: 3,
      badge: "PASSO 3 DE 5",
      iconSvg: (
        <svg
          width="32"
          height="32"
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="tutorial-apple-heading-icon"
          aria-hidden="true"
        >
          <ellipse cx="16" cy="27" rx="10" ry="2.8" fill="rgba(0,0,0,0.12)" />
          <circle cx="16" cy="18" r="11" fill="#dc3545" />
          <ellipse cx="12.5" cy="14" rx="3.5" ry="2" transform="rotate(-35 12.5 14)" fill="rgba(255,255,255,0.42)" />
          <path d="M 16 7 C 15.2 2.5, 14.5 1, 18.5 -0.5" fill="none" stroke="#5a3d28" strokeWidth="2.2" strokeLinecap="round" />
          <ellipse cx="20.5" cy="1.5" rx="3.5" ry="1.8" transform="rotate(25 20.5 1.5)" fill="#2f6b3a" />
        </svg>
      ),
      title: "A Maçã Abre a Afirmação",
      headline: "Colete a fruta e avalie o fato.",
      description: (
        <>
          Ao comer a fruta, a cobrinha pausa e surge uma afirmação sobre o tabuleiro. Você terá{" "}
          <span className="tutorial-highlight-pill">60 segundos</span> para ler e posicionar seu palpite na{" "}
          <strong>barra de confiabilidade</strong>.
        </>
      ),
      visualSnippet: <AppleAffirmationTutorialVisual />,
    },
    {
      id: 4,
      badge: "PASSO 4 DE 5",
      iconSvg: (
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="tutorial-target-icon"
          aria-hidden="true"
        >
          <line x1="4" y1="21" x2="4" y2="14" />
          <line x1="4" y1="10" x2="4" y2="3" />
          <line x1="12" y1="21" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12" y2="3" />
          <line x1="20" y1="21" x2="20" y2="16" />
          <line x1="20" y1="12" x2="20" y2="3" />
          <line x1="1" y1="14" x2="7" y2="14" />
          <line x1="9" y1="8" x2="15" y2="8" />
          <line x1="17" y1="16" x2="23" y2="16" />
        </svg>
      ),
      title: "Barra de Confiabilidade",
      headline: "De 0% a 100% com margem de 15 pontos.",
      description: (
        <>
          Ajuste o cursor de 0% (“Nada confiável”) a 100% (“Totalmente confiável”).
          <br />
          Palpites com até <strong>15 pontos de distância</strong> da referência oficial contam como acerto{" "}
          <strong>(+100 pontos)!</strong>
        </>
      ),
      visualSnippet: <ReliabilitySliderTutorialVisual />,
    },
    {
      id: 5,
      badge: "PASSO 5 DE 5",
      icon: "🐍",
      title: "A Cobra Só Cresce no Erro!",
      headline: "Acertos mantêm seu tamanho seguro.",
      description:
        "Ao contrário de outros jogos, a cobra NÃO cresce ao comer a maçã! Ela só cresce 1 bloco quando você erra a pergunta (> 15 pontos da referência). Complete 6 níveis para vencer!",
      visualSnippet: (
        <div className="tutorial-visual-box visual-step-5">
          <div className="growth-preview">
            <span className="growth-tag tag-success">Acerto: Cobra não cresce ✅</span>
            <span className="growth-tag tag-danger">Erro: Cobra cresce +1 ⚠️</span>
          </div>
        </div>
      ),
    },
  ];

  const step = steps[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === steps.length - 1;

  const handleNext = () => {
    if (isLast) {
      onComplete();
    } else {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (!isFirst) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  return (
    <div className="tutorial-page">
      <div className="tutorial-card">
        {/* 1. BARRA SUPERIOR UNIFICADA (Pill com dots dinâmicos + Pular Tutorial) */}
        <div className="tutorial-topbar">
          <div className="tutorial-step-pill">
            <div className="pill-dots" aria-hidden="true">
              {steps.map((_, idx) => (
                <span
                  key={idx}
                  className={`dot ${idx <= currentStep ? "dot-active" : "dot-inactive"}`}
                />
              ))}
            </div>
            <span className="pill-text">{step.badge}</span>
          </div>

          <button
            type="button"
            className="tutorial-skip-btn"
            onClick={onSkip}
            title="Pular para o jogo"
          >
            Pular Tutorial <span className="close-x" aria-hidden="true">✕</span>
          </button>
        </div>

        {/* 2. CABEÇALHO DO PASSO: Ícone + Título */}
        <div className="tutorial-header-row">
          {step.iconSvg ? (
            <span className="tutorial-icon-wrap" aria-hidden="true">
              {step.iconSvg}
            </span>
          ) : (
            <span className="tutorial-icon-emoji" aria-hidden="true">
              {step.icon}
            </span>
          )}
          <h2 className="tutorial-title">{step.title}</h2>
        </div>
        {step.headline && <h1 className="tutorial-headline">{step.headline}</h1>}

        {/* 4. SUBTÍTULO / DESCRIÇÃO */}
        <p className="tutorial-lead-desc">{step.description}</p>

        {/* 5. VISUAL CENTRAL (Mini-tabuleiro com Cobrinha do Jogo ou Preview) */}
        {step.visualSnippet}

        {/* 6. BOTÕES DE AÇÃO INFERIORES EM PÍLULA */}
        <div className="tutorial-actions">
          <button
            type="button"
            className="tutorial-btn-outline"
            onClick={handlePrev}
            disabled={isFirst}
          >
            ← Anterior
          </button>

          <button
            type="button"
            className="tutorial-btn-solid"
            onClick={handleNext}
            autoFocus
          >
            {isLast ? "Começar a Jogar 🚀" : "Próximo Passo →"}
          </button>
        </div>
      </div>
    </div>
  );
};
