import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
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

const QUEM_IMPORTA = ["painel", "importar", "historico_importacoes", "parceiros"];
const ADMINISTRADOR = ["painel", "historico_importacoes", "usuarios", "configuracao"];

const HISTORICO_VAZIO = { itens: [], total: 0, pagina: 1, tamanho: 10 };

function importacao(id, extra = {}) {
  return {
    id,
    periodo: { id, data_inicio: "2026-09-07", data_fim: "2026-09-13" },
    autor: { id: 1, nome: "Analista de Exemplo" },
    origem: "TEXTO",
    total_gravado: 3,
    total_rejeitado: 1,
    enviado_em: "2026-09-14T13:05:00Z",
    metricas_vigentes: 3,
    ...extra,
  };
}

function renderizar(telas = QUEM_IMPORTA) {
  return render(
    <ContextoSessao.Provider value={{ usuario: { nome: "Quem Testa", telas } }}>
      <MemoryRouter>
        <Importacao />
      </MemoryRouter>
    </ContextoSessao.Provider>,
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
      "GET /api/importacoes": { corpo: HISTORICO_VAZIO },
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
      "GET /api/importacoes": { corpo: HISTORICO_VAZIO },
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

  it("o histórico lista as importações, e diz qual foi substituída", async () => {
    simularApi({
      "GET /api/importacoes": {
        corpo: {
          itens: [importacao(2), importacao(1, { metricas_vigentes: 0 })],
          total: 2,
          pagina: 1,
          tamanho: 10,
        },
      },
    });
    renderizar();

    const historico = await screen.findByRole("table", { name: /Importações anteriores/ });
    const [, maisNova, maisAntiga] = within(historico).getAllByRole("row");
    expect(maisNova).toHaveTextContent("07/09/2026 a 13/09/2026");
    expect(maisNova).toHaveTextContent("Analista de Exemplo");
    expect(maisNova).toHaveTextContent("Texto colado");
    expect(maisAntiga).toHaveTextContent("substituída");
    expect(screen.getByText("2 no total")).toBeInTheDocument();
  });

  it("quem só lê o histórico não vê o formulário de importar", async () => {
    simularApi({ "GET /api/importacoes": { corpo: HISTORICO_VAZIO } });
    renderizar(ADMINISTRADOR);

    expect(await screen.findByText("Nenhuma importação ainda")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ver a prévia" })).not.toBeInTheDocument();
  });

  it("depois de gravar, o histórico é lido de novo", async () => {
    let leituras = 0;
    simularApi({
      "GET /api/importacoes": () => {
        leituras += 1;
        return { corpo: HISTORICO_VAZIO };
      },
      "POST /api/importacoes/previa": { corpo: PREVIA },
      "POST /api/importacoes": {
        status: 201,
        corpo: { id: 9, periodo: PERIODO, total_gravado: 1, total_rejeitado: 0 },
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("Nenhuma importação ainda");
    const antes = leituras;

    await ateAPrevia(usuario);
    await usuario.click(screen.getByRole("button", { name: "Gravar 1 registros" }));
    await screen.findByRole("status");

    await screen.findByText("Nenhuma importação ainda");
    expect(leituras).toBeGreaterThan(antes);
  });
});
