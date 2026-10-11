import React, { useState, useEffect, useRef } from "react";
import { Question, AnswerResult } from "../types";
import { soundEffects } from "../services/audioService";

interface QuestionModalProps {
  question: Question;
  isAnswered: boolean;
  result: AnswerResult | null;
  onConfirm: (answer: boolean) => void;
  onResume: () => void;
  isSubmitting?: boolean;
}

export const QuestionModal: React.FC<QuestionModalProps> = ({
  question,
  isAnswered,
  result,
  onConfirm,
  onResume,
  isSubmitting = false,
}) => {
  const QUESTION_DURATION = 45;
  const [selectedAnswer, setSelectedAnswer] = useState<boolean | null>(null);
  const [timeLeft, setTimeLeft] = useState<number>(QUESTION_DURATION);
  const timerRef = useRef<number | null>(null);
  const lastSecondRef = useRef<number>(QUESTION_DURATION);

  // Reiniciar estado da pergunta
  useEffect(() => {
    setSelectedAnswer(null);
    setTimeLeft(QUESTION_DURATION);
    lastSecondRef.current = QUESTION_DURATION;

    const deadline = Date.now() + QUESTION_DURATION * 1000;

    timerRef.current = window.setInterval(() => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setTimeLeft(remaining);

      // Efeito sonoro nos últimos 5 segundos
      if (remaining <= 5 && remaining > 0 && remaining !== lastSecondRef.current) {
        soundEffects.playTick();
        lastSecondRef.current = remaining;
      }

      if (remaining <= 0) {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        // Auto-confirmação: usa a escolha atual ou padrão (true)
        setSelectedAnswer((currentVal) => {
          const finalVal = currentVal ?? true;
          onConfirm(finalVal);
          return finalVal;
        });
      }
    }, 100);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [question, onConfirm]);

  // Se já foi respondido, limpa o cronômetro
  useEffect(() => {
    if (isAnswered && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, [isAnswered]);

  // Teclas de atalho: 1 ou C (Confiável), 2 ou N (Não Confiável), Enter (Confirmar/Continuar)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isAnswered) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onResume();
        }
        return;
      }

      if (e.key === "1" || e.key === "c" || e.key === "C") {
        setSelectedAnswer(true);
      } else if (e.key === "2" || e.key === "n" || e.key === "N") {
        setSelectedAnswer(false);
      } else if (e.key === "ArrowLeft") {
        setSelectedAnswer(true);
      } else if (e.key === "ArrowRight") {
        setSelectedAnswer(false);
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectedAnswer !== null && !isSubmitting) {
          onConfirm(selectedAnswer);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isAnswered, selectedAnswer, isSubmitting, onConfirm, onResume]);

  const statement = question.statement || question.afirmacao || "";
  const category = question.category || question.categoria || "Gerais";

  const getCategoryClass = (cat: string) => {
    const lower = cat.toLowerCase();
    if (lower.includes("saúde") || lower.includes("saude")) return "cat-saude";
    if (lower.includes("tec")) return "cat-tecnologia";
    if (lower.includes("geral") || lower.includes("conhecimento")) return "cat-gerais";
    return "cat-default";
  };

  const isLowTime = timeLeft <= 5 && !isAnswered;

  return (
    <div
      className="bubble-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="question-text"
    >
      <div className="speech-bubble">
        {/* Cabeçalho do balão: Categoria e Cronômetro */}
        <div className="bubble-header">
          <span className={`category-tag ${getCategoryClass(category)}`}>
            {category}
          </span>
          <div className={`countdown-timer ${isLowTime ? "timer-alert" : ""}`}>
            <span className="timer-icon">⏳</span>
            <span className="timer-seconds">
              {isAnswered ? "Finalizado" : `${timeLeft}s`}
            </span>
          </div>
        </div>

        {/* Afirmação para checagem */}
        <p className="statement-text" id="question-text">
          "{statement}"
        </p>

        {/* FASE 1: Seleção de Confiabilidade (Confiável vs Não Confiável) */}
        {!isAnswered ? (
          <div className="semantic-interaction">
            <span className="slider-title">
              Como você classifica a confiabilidade desta informação?
            </span>

            <div className="semantic-buttons-row">
              <button
                type="button"
                className={`semantic-btn btn-confiavel ${
                  selectedAnswer === true ? "active" : ""
                }`}
                onClick={() => setSelectedAnswer(true)}
              >
                <span className="semantic-btn-icon">🛡️</span>
                <span className="semantic-btn-title">Confiável</span>
                <span className="semantic-btn-sub">Informação verídica / segura</span>
                <span className="semantic-btn-key">Atalho: 1 ou C</span>
              </button>

              <button
                type="button"
                className={`semantic-btn btn-nao-confiavel ${
                  selectedAnswer === false ? "active" : ""
                }`}
                onClick={() => setSelectedAnswer(false)}
              >
                <span className="semantic-btn-icon">⚠️</span>
                <span className="semantic-btn-title">Não Confiável</span>
                <span className="semantic-btn-sub">Mito, golpe ou boato falso</span>
                <span className="semantic-btn-key">Atalho: 2 ou N</span>
              </button>
            </div>

            <button
              type="button"
              className="action-button confirm-button"
              disabled={selectedAnswer === null || isSubmitting}
              onClick={() => {
                if (selectedAnswer !== null) {
                  onConfirm(selectedAnswer);
                }
              }}
            >
              {isSubmitting
                ? "Validando resposta..."
                : selectedAnswer === null
                ? "Selecione uma opção acima"
                : "Confirmar Análise (Enter)"}
            </button>
          </div>
        ) : (
          /* FASE 2: Revelação da Resposta e Explicação da API */
          <div className="feedback-reveal">
            {result && (
              <div
                className={`verdict-banner ${
                  result.is_correct ? "verdict-hit" : "verdict-miss"
                }`}
              >
                <div className="verdict-icon">
                  {result.is_correct ? "🎯" : "⚠️"}
                </div>
                <div className="verdict-details">
                  <h3 className="verdict-title">
                    {result.is_correct
                      ? "Mandou bem! Análise correta!"
                      : "Atenção! Análise incorreta!"}
                  </h3>
                  <p className="verdict-points">
                    {result.is_correct
                      ? `+10 pontos! A cobrinha manteve seu tamanho.`
                      : `0 pontos. A cobrinha cresceu +1 bloco!`}
                  </p>
                </div>
              </div>
            )}

            {/* Veredito Oficial do Backend */}
            <div className="official-status-box">
              <span className="official-label">Classificação Oficial:</span>
              <span
                className={`official-badge ${
                  result?.correct_answer ? "badge-confiavel" : "badge-nao-confiavel"
                }`}
              >
                {result?.correct_answer ? "🛡️ Confiável" : "⚠️ Não Confiável"}
              </span>
            </div>

            {/* Explicação pedagógica e fonte da API */}
            <div className="explanation-card">
              <h4 className="explanation-title">💡 Por que essa referência?</h4>
              <p className="explanation-text">{result?.explanation || question.explicacao}</p>
              {(result?.source || question.fonte) && (
                <div className="source-row">
                  <span className="source-label">Fonte de validação:</span>
                  <span className="source-text">{result?.source || question.fonte}</span>
                </div>
              )}
            </div>

            <button
              type="button"
              className="action-button resume-button"
              onClick={onResume}
              autoFocus
            >
              Continuar Jogo (Espaço / Enter) ➔
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
