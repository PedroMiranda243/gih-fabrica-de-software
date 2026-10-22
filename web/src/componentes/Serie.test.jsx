import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import Serie from "./Serie";

const P = (id, inicio, fim, faturamento, pedidos = 100) => ({ periodo: { id, data_inicio: inicio, data_fim: fim }, faturamento, pedidos });
const PONTOS = [
  P(1, "2026-09-07", "2026-09-13", "1000.00"),
  P(2, "2026-09-14", "2026-09-20", "1200.00"),
  P(3, "2026-09-21", "2026-09-27", null, null),
  P(4, "2026-09-28", "2026-10-04", "1500.00"),
];

/* RF19 — a série histórica, da rede ou de um parceiro: um ponto por período, a
   lacuna como lacuna (nulo não é zero) e a estimativa do modelo em tracejado. */
describe("a série histórica (RF19)", () => {
  it("descreve o gráfico em texto: períodos, mínimo, máximo e o último medido", () => {
    render(<Serie pontos={PONTOS} rotulo="Faturamento da rede" />);

    const grafico = screen.getByRole("img");
    expect(grafico).toHaveAccessibleName(/Faturamento da rede: 4 períodos, de 07\/09\/2026 a 04\/10\/2026/);
    expect(grafico).toHaveAccessibleName(/no último período medido, R\$ 1\.500,00/);
  });

  it("o período sem medição interrompe a linha, e não vira zero", () => {
    const { container } = render(<Serie pontos={PONTOS} rotulo="Faturamento da rede" />);

    expect(container.querySelectorAll("polyline.grafico__linha")).toHaveLength(2);
    expect(container.querySelector(".grafico__lacuna")).not.toBeNull();
    expect(screen.getByRole("img")).toHaveAccessibleName(/Há período sem medição, e a linha se interrompe nele\./);
  });

  it("a estimativa entra tracejada, com marcador próprio, e dita como estimativa", () => {
    const { container } = render(<Serie pontos={PONTOS} rotulo="Faturamento da rede" estimativa={{ valor: "1600.00" }} />);

    expect(container.querySelector("line.grafico__linha-est")).not.toBeNull();
    expect(container.querySelector("circle.grafico__estacao-est")).not.toBeNull();
    expect(screen.getByRole("img")).toHaveAccessibleName(/Estimativa do modelo para o próximo período: R\$ 1\.600,00\./);
  });

  it("os números do gráfico ficam a um clique, numa tabela, com a lacuna como travessão", async () => {
    const usuario = userEvent.setup();
    render(<Serie pontos={PONTOS} rotulo="Faturamento da rede" estimativa={{ valor: "1600.00" }} />);

    await usuario.click(screen.getByRole("button", { name: "Ver os números" }));

    const tabela = screen.getByRole("table", { name: "Faturamento da rede, período a período" });
    expect(tabela).toHaveTextContent("21/09/2026 a 27/09/2026—");
    expect(tabela).toHaveTextContent("Próximo período (estimativa do modelo)R$ 1.600,00");
  });

  it("com um período só, não desenha linha: diz que a série vem com mais períodos", () => {
    render(<Serie pontos={[PONTOS[0]]} rotulo="Faturamento da rede" />);

    expect(screen.getByText("Sem série para mostrar")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
