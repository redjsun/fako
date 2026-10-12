import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReliabilityBar } from "./ReliabilityBar";

describe("ReliabilityBar", () => {
  it("mostra o valor atual", () => {
    render(<ReliabilityBar value={70} />);
    expect(screen.getByText("Você: 70%")).toBeInTheDocument();
  });

  it("sem onChange, não renderiza o controle de arraste", () => {
    render(<ReliabilityBar value={50} />);
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  });

  it("com onChange, chama o callback ao mover o controle", () => {
    const onChange = vi.fn();
    render(<ReliabilityBar value={50} onChange={onChange} />);
    fireEvent.change(screen.getByRole("slider"), { target: { value: "75" } });
    expect(onChange).toHaveBeenCalledWith(75);
  });

  it("com reference, mostra a etiqueta de referência", () => {
    render(<ReliabilityBar value={50} reference={80} />);
    expect(screen.getByText("Referência: 80%")).toBeInTheDocument();
  });
});
