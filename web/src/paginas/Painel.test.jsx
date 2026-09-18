import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Painel from "./Painel";

const PERIODO = { id: 2, data_inicio: "2026-03-09", data_fim: "2026-03-15" };
const ANTERIOR = { id: 1, data_inicio: "2026-03-02", data_fim: "2026-03-08" };

function renderizar() {
  return render(
    <MemoryRouter>
      <Painel />
    </MemoryRouter>,
  );
}

function indicadores(extra = {}) {
  return {
    periodo: PERIODO,
    periodo_anterior: ANTERIOR,
    faturamento: "3000.00",
    pedidos: 25,
    ticket_medio: "120.00",
    parceiros_ativos: 2,
    variacao: { faturamento: "50.00", pedidos: "-10.00", ticket_medio: null, parceiros_ativos: "0.00" },
    ...extra,
  };
}

const SERIE = {
  escopo: "rede",
  parceiro_id: null,
  parceiro_nome: null,
  pontos: [
    { periodo: ANTERIOR, faturamento: "2000.00", pedidos: 20, ticket_medio: "100.00" },
    { periodo: PERIODO, faturamento: "3000.00", pedidos: 25, ticket_medio: "120.00" },
  ],
};

const RANKING = {
  periodo: PERIODO,
  periodo_anterior: ANTERIOR,
  total: 2,
  pagina: 1,
  tamanho: 25,
  itens: [
    {
      parceiro_id: 1, nome: "Comércio Alfa", categoria: "Lanches", posicao: 1, posicao_anterior: 2,
      faturamento: "2000.00", pedidos: 20, ticket_medio: "100.00", variacao_percentual: "33.33",
      estreante: false,
    },
    {
      parceiro_id: 2, nome: "Comércio Novo", categoria: null, posicao: 2, posicao_anterior: null,
      faturamento: "1000.00", pedidos: 5, ticket_medio: "200.00", variacao_percentual: null,
      estreante: true,
    },
  ],
};

describe("Painel", () => {
  it("base vazia leva à importação, em vez de mostrar tela em branco", async () => {
    /* UC05, A1 — tela vazia sem explicação é defeito (docs/09, seção 6). */
    simularApi({
      "GET /api/painel/indicadores": { corpo: indicadores({ periodo: null, periodo_anterior: null, variacao: null }) },
      "GET /api/painel/ranking": { corpo: { ...RANKING, periodo: null, itens: [], total: 0 } },
      "GET /api/painel/series": { corpo: { ...SERIE, pontos: [] } },
    });

    renderizar();

    expect(await screen.findByText("Nenhum dado importado ainda")).toBeVisible();
    expect(screen.getByRole("link", { name: "Importar um relatório" })).toHaveAttribute(
      "href",
      "/importacao",
    );
  });

  it("período único avisa que variação exige histórico", async () => {
    /* UC05, A2 — sem o aviso, os travessões seriam lidos como defeito. */
    simularApi({
      "GET /api/painel/indicadores": { corpo: indicadores({ periodo_anterior: null, variacao: null }) },
      "GET /api/painel/ranking": { corpo: RANKING },
      "GET /api/painel/series": { corpo: SERIE },
    });

    renderizar();

    expect(await screen.findByText(/variação e tendência exigem histórico/)).toBeVisible();
  });

  it("variação nula aparece como travessão, e nunca como 0%", async () => {
    simularApi({
      "GET /api/painel/indicadores": { corpo: indicadores() },
      "GET /api/painel/ranking": { corpo: RANKING },
      "GET /api/painel/series": { corpo: SERIE },
    });

    renderizar();

    await screen.findByText("Comércio Alfa");
    /* Ticket médio veio com variação nula; parceiros ativos, com zero de
       verdade. Os dois precisam aparecer diferentes. */
    expect(screen.getByText(/sem variação calculável/)).toBeInTheDocument();
    expect(screen.getByText("0,00%")).toBeInTheDocument();
  });

  it("estreante é marcado como novo, e não como queda", async () => {
    simularApi({
      "GET /api/painel/indicadores": { corpo: indicadores() },
      "GET /api/painel/ranking": { corpo: RANKING },
      "GET /api/painel/series": { corpo: SERIE },
    });

    renderizar();

    expect(await screen.findByText("· novo")).toBeVisible();
  });

  it("o erro do servidor aparece com a ajuda que ele mandou", async () => {
    /* A API explica o que fazer. Reescrever a mensagem na tela perderia isso. */
    simularApi({
      "GET /api/painel/indicadores": {
        status: 404,
        corpo: { detail: { erro: "Não existe período com id 9.", ajuda: "Escolha outro período." } },
      },
      "GET /api/painel/ranking": { corpo: RANKING },
      "GET /api/painel/series": { corpo: SERIE },
    });

    renderizar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Não existe período com id 9.");
    expect(screen.getByText("Escolha outro período.")).toBeVisible();
  });
});
