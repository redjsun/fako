import React from "react";

interface ReliabilityBarProps {
  value: number;
  // Com onChange a barra vira um controle (input range em passos de 5%).
  onChange?: (value: number) => void;
  // Com reference a barra mostra a referência e a faixa de acerto.
  reference?: number;
  tolerance?: number;
  valueLabel?: string;
  referenceLabel?: string;
  caption?: string;
  autoFocus?: boolean;
}

const TICKS = [0, 25, 50, 75, 100];

// Posição de etiquetas sobre a barra sem vazar das pontas: em 0% alinha à esquerda,
// em 100% à direita e no meio fica centralizada.
const pinnedTo = (percent: number): React.CSSProperties => ({
  left: `${percent}%`,
  transform: `translateX(-${percent}%)`,
});

/**
 * Barra de confiabilidade de 0% a 100%: a mesma no tutorial, na pergunta e no feedback.
 */
export const ReliabilityBar: React.FC<ReliabilityBarProps> = ({
  value,
  onChange,
  reference,
  tolerance = 15,
  valueLabel = "Você",
  referenceLabel = "Referência",
  caption,
  autoFocus = false,
}) => {
  const hasReference = reference !== undefined;
  const rangeStart = hasReference ? Math.max(0, reference - tolerance) : 0;
  const rangeEnd = hasReference ? Math.min(100, reference + tolerance) : 0;

  return (
    <div className={`reliability ${hasReference ? "reliability--with-reference" : ""}`}>
      <div className="reliability__ends">
        <div className="reliability__end">
          <span className="reliability__end-badge reliability__end-badge--low" aria-hidden="true">
            !
          </span>
          <span className="reliability__end-text">
            <strong>Nada confiável</strong>
            <small>0%</small>
          </span>
        </div>
        <div className="reliability__end reliability__end--right">
          <span className="reliability__end-text">
            <strong>Totalmente confiável</strong>
            <small>100%</small>
          </span>
          <span className="reliability__end-badge reliability__end-badge--high" aria-hidden="true">
            ✓
          </span>
        </div>
      </div>

      <div className="reliability__area">
        <span className="reliability__tag reliability__tag--value" style={pinnedTo(value)}>
          {valueLabel}: {value}%
        </span>
        <span className="reliability__tag-pin" style={{ left: `${value}%` }} aria-hidden="true" />

        <div className="reliability__track" aria-hidden="true" />

        {hasReference && (
          <>
            <span
              className="reliability__range"
              style={{ left: `${rangeStart}%`, width: `${rangeEnd - rangeStart}%` }}
              aria-hidden="true"
            />
            <span className="reliability__reference" style={{ left: `${reference}%` }} aria-hidden="true" />
          </>
        )}

        <span className="reliability__thumb" style={{ left: `${value}%` }} aria-hidden="true" />

        {onChange && (
          <input
            className="reliability__input"
            type="range"
            min={0}
            max={100}
            step={5}
            value={value}
            onChange={(event) => onChange(Number(event.target.value))}
            aria-label="Quão confiável é esta informação"
            aria-valuetext={`${value}%`}
            autoFocus={autoFocus}
          />
        )}

        <div className="reliability__ticks" aria-hidden="true">
          {TICKS.map((tick) => (
            <span key={tick} className="reliability__tick" style={pinnedTo(tick)}>
              {/* Dentro da etiqueta deslocada, left = tick% cai na posição exata da barra */}
              <span className="reliability__tick-mark" style={{ left: `${tick}%` }} />
              {tick}%
            </span>
          ))}
        </div>

        {hasReference && (
          <span className="reliability__tag reliability__tag--reference" style={pinnedTo(reference)}>
            {referenceLabel}: {reference}%
          </span>
        )}
      </div>

      {caption && <p className="reliability__caption">{caption}</p>}
    </div>
  );
};
