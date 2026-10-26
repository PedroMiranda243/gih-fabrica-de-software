import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { avisariaAoFechar } from "../testes/preparar";
import { abrir, amostra } from "../testes/montar";

const EM_VIGOR = () => amostra("GET_api_configuracao_segmentacao");

/* RF21 — configurar os limiares da segmentação (Top N, tendência, recém-chegado). */
describe("os limiares da segmentação (RF21)", () => {
  it("mostra os valores em vigor, que vêm da API", async () => {
    abrir("/configuracao", { perfil: "ADMINISTRADOR", rotas: { "GET /api/configuracao/segmentacao": { corpo: EM_VIGOR() } } });

    expect(await screen.findByLabelText(/^Tamanho do Top/)).toHaveValue("15");
    expect(screen.getByLabelText(/^Períodos de tendência/)).toHaveValue("2");
    expect(screen.getByLabelText(/^Períodos de recém-chegado/)).toHaveValue("3");
  });

  it("salva só depois de confirmar, e diz o que foi reclassificado", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/configuracao", {
      perfil: "ADMINISTRADOR",
      rotas: {
        "GET /api/configuracao/segmentacao": { corpo: EM_VIGOR() },
        "PUT /api/configuracao/segmentacao": { corpo: { ...EM_VIGOR(), top_n: 10, periodos_reprocessados: 1 } },
      },
    });

    const top = await screen.findByLabelText(/^Tamanho do Top/);
    await usuario.clear(top);
    await usuario.type(top, "10");
    expect(avisariaAoFechar()).toBe(true);
    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));
    const confirmacao = screen.getByText("Salvar os limiares?").closest(".confirmacao");
    await usuario.click(within(confirmacao).getByRole("button", { name: "Salvar limiares" }));

    expect(await screen.findByText(/Limiares salvos\. O período mais recente já foi reclassificado/)).toBeInTheDocument();
    expect(corpoDe("PUT /api/configuracao/segmentacao")).toEqual({ top_n: 10, periodos_tendencia: 2, periodos_novato: 3 });
    expect(top).toHaveValue("10");
  });

  it("o valor que a API recusa volta com a mensagem dela, no campo", async () => {
    const usuario = userEvent.setup();
    abrir("/configuracao", {
      perfil: "ADMINISTRADOR",
      rotas: {
        "GET /api/configuracao/segmentacao": { corpo: EM_VIGOR() },
        "PUT /api/configuracao/segmentacao": {
          status: 422,
          corpo: { erro: "Alguns campos precisam de correção.", campos: [{ campo: "top_n", mensagem: "O Top precisa ter de 1 a 500 parceiros." }] },
        },
      },
    });

    const top = await screen.findByLabelText(/^Tamanho do Top/);
    await usuario.clear(top);
    await usuario.type(top, "0");
    await usuario.click(screen.getByRole("button", { name: "Salvar limiares" }));
    await usuario.click(within(screen.getByText("Salvar os limiares?").closest(".confirmacao")).getByRole("button", { name: "Salvar limiares" }));

    expect((await screen.findAllByText("O Top precisa ter de 1 a 500 parceiros.")).length).toBeGreaterThan(0);
    expect(top).toHaveAttribute("aria-invalid", "true");
  });
});
