import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Configuracao from "./Configuracao";

const ATUAL = {
  top_n: 15,
  periodos_tendencia: 2,
  periodos_novato: 3,
  atualizado_em: "2026-09-20T18:00:00Z",
  atualizado_por: "Administração",
  periodos_reprocessados: 0,
};

function renderizar() {
  return render(
    <MemoryRouter>
      <Configuracao />
    </MemoryRouter>,
  );
}

describe("limiares da segmentação", () => {
  it("mostra os valores em vigor e quem os mudou por último", async () => {
    simularApi({ "GET /api/configuracao/segmentacao": { corpo: ATUAL } });
    renderizar();

    expect(await screen.findByLabelText(/Tamanho do Top/)).toHaveValue(15);
    expect(screen.getByLabelText(/Períodos de tendência/)).toHaveValue(2);
    expect(screen.getByText(/Alterados por Administração/)).toBeInTheDocument();
  });

  it("sem mudança, não há o que salvar", async () => {
    simularApi({ "GET /api/configuracao/segmentacao": { corpo: ATUAL } });
    renderizar();

    expect(await screen.findByRole("button", { name: "Salvar limiares" })).toBeDisabled();
  });

  it("salvar pede confirmação, e depois diz o que foi reclassificado", async () => {
    const enviados = [];
    simularApi({
      "GET /api/configuracao/segmentacao": { corpo: ATUAL },
      "PUT /api/configuracao/segmentacao": (_url, opcoes) => {
        enviados.push(JSON.parse(opcoes.body));
        return { corpo: { ...ATUAL, top_n: 10, periodos_reprocessados: 1 } };
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    const top = await screen.findByLabelText(/Tamanho do Top/);
    await usuario.clear(top);
    await usuario.type(top, "10");
    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));

    // Ainda nada foi gravado: a confirmação vem antes, dizendo o alcance.
    expect(enviados).toHaveLength(0);
    const confirmacao = screen.getByRole("group", { name: "Confirmação" });
    expect(confirmacao).toHaveTextContent("período mais recente");

    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));

    expect(await screen.findByRole("status")).toHaveTextContent("já foi reclassificado");
    expect(screen.getByText(/reprocessar-segmentos/)).toBeInTheDocument();
    expect(enviados[0]).toMatchObject({ top_n: "10", periodos_tendencia: "2" });
  });

  it("o erro do servidor aparece embaixo do campo, e o foco vai para ele", async () => {
    simularApi({
      "GET /api/configuracao/segmentacao": { corpo: ATUAL },
      "PUT /api/configuracao/segmentacao": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "top_n", mensagem: "Use um valor a partir de 1." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    const top = await screen.findByLabelText(/Tamanho do Top/);
    await usuario.clear(top);
    await usuario.type(top, "0");
    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));
    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));

    expect(await screen.findByText("Use um valor a partir de 1.")).toBeInTheDocument();
    expect(top).toHaveAttribute("aria-invalid", "true");
    expect(top).toHaveFocus();
  });

  it("sem período importado, diz que não havia o que reclassificar", async () => {
    simularApi({
      "GET /api/configuracao/segmentacao": { corpo: { ...ATUAL, atualizado_por: null } },
      "PUT /api/configuracao/segmentacao": { corpo: { ...ATUAL, top_n: 20, periodos_reprocessados: 0 } },
    });
    const usuario = userEvent.setup();
    renderizar();

    expect(await screen.findByText(/Valores de fábrica/)).toBeInTheDocument();
    const top = screen.getByLabelText(/Tamanho do Top/);
    await usuario.clear(top);
    await usuario.type(top, "20");
    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));
    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));

    expect(await screen.findByRole("status")).toHaveTextContent("não há período importado");
    expect(screen.queryByText(/reprocessar-segmentos/)).not.toBeInTheDocument();
  });
});
