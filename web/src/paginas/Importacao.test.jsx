import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Importacao from "./Importacao";

const PERIODO = { id: 3, data_inicio: "2026-03-16", data_fim: "2026-03-22" };

const PREVIA = {
  periodo: PERIODO,
  reconhecidos: [{ linha: 2, nome: "Comércio Alfa", faturamento: "12500.40", pedidos: 312 }],
  rejeitados: [],
  parceiros_novos: [],
  total_reconhecido: 1,
  total_rejeitado: 0,
};

function renderizar() {
  return render(
    <MemoryRouter>
      <Importacao />
    </MemoryRouter>,
  );
}

/** Período e texto preenchidos, prévia aberta: o ponto em que se decide gravar. */
async function ateAPrevia(usuario) {
  await usuario.type(screen.getByLabelText("Início do período"), "2026-03-16");
  await usuario.type(screen.getByLabelText("Fim do período"), "2026-03-22");
  await usuario.type(screen.getByLabelText("Colar o relatório"), "Comércio Alfa;12500,40;312");
  await usuario.click(screen.getByRole("button", { name: "Ver a prévia" }));
  await screen.findByRole("heading", { name: "Prévia" });
}

describe("Importação", () => {
  it("depois de gravar, leva ao painel", async () => {
    simularApi({
      "POST /api/importacoes/previa": { corpo: PREVIA },
      "POST /api/importacoes": {
        status: 201,
        corpo: { id: 9, periodo: PERIODO, total_gravado: 1, total_rejeitado: 0 },
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await ateAPrevia(usuario);
    await usuario.click(screen.getByRole("button", { name: "Gravar 1 registros" }));

    const aviso = await screen.findByRole("status");
    expect(aviso).toHaveTextContent("Importação concluída — 1 registros gravados.");
    expect(screen.getByRole("link", { name: "Ver no painel" })).toHaveAttribute("href", "/");
  });

  it("período já importado: diz quanto seria apagado antes de oferecer a substituição", async () => {
    simularApi({
      "POST /api/importacoes/previa": { corpo: PREVIA },
      "POST /api/importacoes": {
        status: 409,
        corpo: {
          detail: {
            erro: "Este período já foi importado.",
            ajuda: "O padrão é cancelar, para não duplicar nem apagar dados sem querer.",
            ja_existe: {
              importacao: 4,
              autor: "Analista de Exemplo",
              enviado_em: "2026-03-23T09:00:00",
              metricas_que_serao_apagadas: 480,
            },
          },
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await ateAPrevia(usuario);
    await usuario.click(screen.getByRole("button", { name: "Gravar 1 registros" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Este período já foi importado.");
    expect(alerta).toHaveTextContent("Já existem 480 registros neste período, trazidos por Analista de Exemplo.");
    expect(screen.getByRole("button", { name: "Substituir mesmo assim" })).toBeEnabled();
    expect(screen.queryByRole("link", { name: "Ver no painel" })).not.toBeInTheDocument();
  });
});
