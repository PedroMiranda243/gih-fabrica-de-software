import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SerieHistorica from "./SerieHistorica";

function periodo(dia) {
  return { id: dia, data_inicio: `2026-03-${String(dia).padStart(2, "0")}`, data_fim: "2026-03-31" };
}

describe("Série histórica", () => {
  it("a lacuna interrompe a linha em vez de ligar os vizinhos", () => {
    /* A API devolve o período sem medição com os valores nulos. Ligar os
       vizinhos desenharia uma tendência que ninguém mediu. */
    const { container } = render(
      <SerieHistorica
        pontos={[
          { periodo: periodo(2), faturamento: "100.00", pedidos: 1, ticket_medio: "100.00" },
          { periodo: periodo(9), faturamento: "150.00", pedidos: 2, ticket_medio: "75.00" },
          { periodo: periodo(16), faturamento: null, pedidos: null, ticket_medio: null },
          { periodo: periodo(23), faturamento: "300.00", pedidos: 3, ticket_medio: "100.00" },
          { periodo: periodo(30), faturamento: "320.00", pedidos: 3, ticket_medio: "106.67" },
        ]}
      />,
    );

    /* Dois trechos contínuos: dois caminhos de linha, não um. */
    expect(container.querySelectorAll(".grafico__linha")).toHaveLength(2);
    /* Quatro medições, quatro marcadores — a lacuna não ganha ponto. */
    expect(container.querySelectorAll(".grafico__ponto")).toHaveLength(4);
    expect(container.textContent).toContain("A linha se interrompe");
  });

  it("série sem lacuna é uma linha só e não mostra o aviso", () => {
    const { container } = render(
      <SerieHistorica
        pontos={[
          { periodo: periodo(2), faturamento: "100.00", pedidos: 1, ticket_medio: "100.00" },
          { periodo: periodo(9), faturamento: "200.00", pedidos: 2, ticket_medio: "100.00" },
        ]}
      />,
    );

    expect(container.querySelectorAll(".grafico__linha")).toHaveLength(1);
    expect(container.textContent).not.toContain("A linha se interrompe");
  });

  it("ponto isolado entre duas lacunas continua visível", () => {
    /* Um trecho de um ponto só não desenha linha — sem o marcador, o período
       sumiria do gráfico, e ele existiu. */
    const { container } = render(
      <SerieHistorica
        pontos={[
          { periodo: periodo(2), faturamento: null, pedidos: null, ticket_medio: null },
          { periodo: periodo(9), faturamento: "200.00", pedidos: 2, ticket_medio: "100.00" },
          { periodo: periodo(16), faturamento: null, pedidos: null, ticket_medio: null },
        ]}
      />,
    );

    expect(container.querySelectorAll(".grafico__ponto")).toHaveLength(1);
  });

  it("a estimativa do próximo período é tracejada, tem legenda e entra na tabela", () => {
    /* H44: a previsão se distingue do medido por mais que a cor — traço,
       marcador vazado e a legenda dizendo qual é qual. */
    const { container, getByRole, getByText } = render(
      <SerieHistorica
        pontos={[
          { periodo: periodo(2), faturamento: "100.00", pedidos: 1, ticket_medio: "100.00" },
          { periodo: periodo(9), faturamento: "200.00", pedidos: 2, ticket_medio: "100.00" },
        ]}
        previsao={{ valor: "180.00" }}
      />,
    );

    expect(container.querySelectorAll(".grafico__linha--prevista")).toHaveLength(2); // traço e legenda
    expect(container.querySelectorAll(".grafico__ponto--previsto")).toHaveLength(1);
    expect(getByText(/estimativa do modelo para o próximo período/)).toBeInTheDocument();
    expect(getByRole("img").getAttribute("aria-label")).toContain("estimativa do próximo");
    expect(container.textContent).toContain("próximo");

    fireEvent.click(getByRole("button", { name: "Ver os números" }));
    expect(getByText("Próximo período (estimativa)")).toBeInTheDocument();
  });

  it("sem estimativa, nada tracejado", () => {
    const { container } = render(
      <SerieHistorica
        pontos={[{ periodo: periodo(2), faturamento: "100.00", pedidos: 1, ticket_medio: "100.00" }]}
      />,
    );
    expect(container.querySelectorAll(".grafico__linha--prevista")).toHaveLength(0);
  });
});
