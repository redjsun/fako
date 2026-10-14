import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ResultPopup } from "./QuestionModal";
import { AnswerResult } from "../types";

const base: AnswerResult = {
  is_correct: false,
  correct_answer: false,
  reliability: 80,
  reliability_reference: 10,
  tolerance: 15,
  distance: 70,
  explanation: "Circulou no WhatsApp em 30/09/2026. Aos Fatos checou e concluiu que é falsa.",
  source: "https://www.aosfatos.org/noticias/vacina-chip/",
  score: 0,
};

function renderizar(result: AnswerResult) {
  render(<ResultPopup statement="Vacina tem chip" result={result} pointsPerCorrect={10} onContinue={() => {}} />);
}

describe("ResultPopup", () => {
  afterEach(cleanup);

  it("destaca onde a alegação circulou e deixa a checagem como apoio", () => {
    renderizar({
      ...base,
      claim_origin: { kind: "alegacao", author: "WhatsApp", when: "2026-09-30", link: null },
    });
    expect(screen.getByText("Onde circulou")).toBeInTheDocument();
    expect(screen.getByText("WhatsApp")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "aosfatos.org" })).toHaveAttribute("href", base.source);
    expect(screen.queryByText(base.source)).not.toBeInTheDocument();
  });

  it("na manchete, mostra o veículo com o link da matéria", () => {
    renderizar({
      ...base,
      correct_answer: true,
      explanation: "Manchete publicada por G1 em 14/10/2026.",
      source: "https://g1.globo.com/x",
      claim_origin: { kind: "materia", author: "G1", when: "2026-10-14", link: "https://g1.globo.com/x" },
    });
    expect(screen.getByText("Onde foi publicada")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ler a matéria" })).toHaveAttribute("href", "https://g1.globo.com/x");
  });

  it("sem origem, mostra só a fonte", () => {
    renderizar({ ...base, source: "Organização Mundial da Saúde (OMS)" });
    expect(screen.queryByText("Onde circulou")).not.toBeInTheDocument();
    expect(screen.getByText(/Organização Mundial da Saúde/)).toBeInTheDocument();
  });
});
