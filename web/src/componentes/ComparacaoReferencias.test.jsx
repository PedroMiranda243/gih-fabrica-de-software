import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ComparacaoReferencias from "./ComparacaoReferencias";

function barras() {
  return [
    { rotulo: "Rede", valor: 0.09, destaque: true },
    { rotulo: "Média móvel", valor: 0.1 },
    { rotulo: "Sem medida", valor: null },
  ];
}

describe("comparação com as referências", () => {
  it("cada barra tem nome e valor em texto, e a maior ocupa o trilho", () => {
    render(
      <ComparacaoReferencias titulo="Erro" barras={barras()} formatar={(x) => `${x * 100}%`} />,
    );
    const figura = screen.getByRole("figure", { name: "Erro" });
    const linhas = within(figura).getAllByRole("listitem");

    // Valor nulo não vira barra de tamanho zero, que leria como "erro zero".
    expect(linhas).toHaveLength(2);
    expect(linhas[0]).toHaveTextContent("Rede9%");
    expect(linhas[0]).toHaveAttribute("title", "Rede: 9%");

    const [menor, maior] = linhas.map(
      (l) => l.querySelector(".comparacao__barra").dataset.proporcao,
    );
    expect(maior).toBe("1.0000");
    expect(menor).toBe("0.9000");
  });

  it("a barra começa no zero: 9% contra 10% é quase do mesmo tamanho", () => {
    render(<ComparacaoReferencias titulo="Erro" barras={barras()} formatar={String} />);
    const larguras = screen
      .getAllByRole("listitem")
      .map((l) => Number(l.querySelector(".comparacao__barra").dataset.proporcao));
    expect(larguras[0] / larguras[1]).toBeCloseTo(0.9);
  });
});
