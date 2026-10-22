import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Ausente, Delta, Estimativa, Segmento, Variacao } from "./Dados";

/*
 * Como um número aparece. A cor nunca é o único sinal (RNF22): a variação tem
 * seta e sinal, o segmento tem o nome ao lado da cor, a estimativa tem etiqueta.
 * E nulo é travessão com a razão para quem ouve — nulo não é zero.
 */
describe("os dados na tela", () => {
  it("o ausente é travessão para quem lê e a razão para quem ouve", () => {
    const { container } = render(<Ausente porque="sem medição no período" />);
    expect(container).toHaveTextContent("—sem medição no período");
    expect(screen.getByText("—")).toHaveAttribute("aria-hidden", "true");
  });

  it("variação nula diz que não há base; zero diz que mediu e não mudou", () => {
    const { container: nula } = render(<Variacao valor={null} />);
    expect(nula).toHaveTextContent("Sem base de comparação neste período");
    const { container: zero } = render(<Variacao valor="0.00" />);
    expect(zero).toHaveTextContent("estável (mediu e não mudou)");
  });

  it("variação tem sinal e seta, e a cor só reforça", () => {
    const { container } = render(<Variacao valor="-15.06" />);
    expect(container).toHaveTextContent("−15,06%");
    expect(container.querySelector(".variacao--ruim svg, .variacao--ruim .icone")).not.toBeNull();
  });

  it("no risco, subir é ruim: a cor inverte, a seta e o sinal não", () => {
    const { container } = render(<Variacao valor="8" ruimQuandoSobe />);
    expect(container.querySelector(".variacao--ruim")).not.toBeNull();
    expect(container).toHaveTextContent("+8,00%");
  });

  it("a diferença de contagem é escrita em palavras", () => {
    const { container } = render(<Delta valor={-2} />);
    expect(container).toHaveTextContent("2 a menos");
  });

  it("o segmento tem o nome ao lado da cor, e o Top não leva número", () => {
    render(<Segmento codigo="TOP" />);
    expect(screen.getByText("Top")).toBeInTheDocument();
    const { container } = render(<Segmento codigo="EM_RISCO" />);
    expect(container.querySelector(".segmento--em-risco")).toHaveTextContent("Em risco");
  });

  it("segmento ainda não calculado é ausente, e não 'Estável'", () => {
    const { container } = render(<Segmento codigo={null} />);
    expect(container).toHaveTextContent("Segmentação ainda não calculada para este período");
    expect(container).not.toHaveTextContent("Estável");
  });

  it("a estimativa leva etiqueta", () => {
    render(<Estimativa />);
    expect(screen.getByText("Estimativa")).toBeInTheDocument();
  });
});
