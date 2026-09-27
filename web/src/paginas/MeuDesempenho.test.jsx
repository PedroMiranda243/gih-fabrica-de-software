import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import App from "../App";
import { simularApi } from "../testes/preparar";
import MeuDesempenho from "./MeuDesempenho";

function ponto(inicio, fim, faturamento, pedidos, ticket) {
  return {
    periodo: { id: 1, data_inicio: inicio, data_fim: fim },
    faturamento,
    pedidos,
    ticket_medio: ticket,
  };
}

const PONTOS = [
  ponto("2026-08-10", "2026-08-16", "1000.00", 20, "50.00"),
  ponto("2026-08-17", "2026-08-23", null, null, null),
  ponto("2026-08-24", "2026-08-30", "1250.00", 25, "50.00"),
  ponto("2026-08-31", "2026-09-06", "1500.00", 25, "60.00"),
];

function desempenho(extra = {}) {
  return {
    parceiro: "Mercearia Boa Vista",
    categoria: "Mercado",
    atual: PONTOS[3],
    anterior: PONTOS[2].periodo,
    variacao: { faturamento: "20.00", pedidos: "0.00", ticket_medio: "20.00" },
    pontos: PONTOS,
    ...extra,
  };
}

function renderizar() {
  return render(
    <MemoryRouter>
      <MeuDesempenho />
    </MemoryRouter>,
  );
}

describe("meu desempenho (portal do Parceiro)", () => {
  it("mostra só os números dele: o período, os três indicadores e a série", async () => {
    const chamadas = simularApi({ "GET /api/meu-desempenho": { corpo: desempenho() } });
    renderizar();

    expect(await screen.findByRole("heading", { name: "Mercearia Boa Vista · Mercado" })).toBeInTheDocument();
    expect(screen.getByText(/Período de 31\/08\/2026 a 06\/09\/2026, comparado com 24\/08\/2026 a 30\/08\/2026/)).toBeInTheDocument();
    const indicadores = screen.getByRole("region", { name: "Os seus indicadores do período" });
    expect(within(indicadores).getByText("R$ 1.500,00")).toBeInTheDocument();
    // O faturamento e o ticket subiram 20%; os pedidos ficaram iguais.
    expect(within(indicadores).getAllByText("+20,00%", { selector: "span" })).toHaveLength(2);
    expect(within(indicadores).getByText("25")).toBeInTheDocument();
    expect(screen.getByRole("img").getAttribute("aria-label")).toMatch(/^Faturamento por período\. 4 períodos/);
    // Nada de ranking, posição ou rede.
    expect(screen.queryByText(/ranking|posição|rede/i)).not.toBeInTheDocument();
    // A tela não manda identificador de parceiro: quem diz de quem é, é a sessão.
    expect(String(chamadas.mock.calls[0][0])).toBe("/api/meu-desempenho");
  });

  it("o relatório mais recente sem o comércio dele: indicadores vazios, e o aviso", async () => {
    simularApi({
      "GET /api/meu-desempenho": {
        corpo: desempenho({
          atual: ponto("2026-09-07", "2026-09-13", null, null, null),
          variacao: { faturamento: null, pedidos: null, ticket_medio: null },
        }),
      },
    });
    renderizar();
    expect(await screen.findByText("O último relatório não trouxe o seu comércio.")).toBeInTheDocument();
    expect(screen.getAllByText("sem dados neste período")).toHaveLength(3);
  });

  it("o primeiro período com os números dele diz que não há com que comparar", async () => {
    simularApi({
      "GET /api/meu-desempenho": {
        corpo: desempenho({ atual: PONTOS[0], anterior: null, variacao: null, pontos: [PONTOS[0]] }),
      },
    });
    renderizar();
    expect(await screen.findByText(/o primeiro com os seus números/)).toBeInTheDocument();
  });

  it("sem histórico ainda, explica quando os números chegam (UC13-A1)", async () => {
    simularApi({
      "GET /api/meu-desempenho": {
        corpo: desempenho({ atual: null, anterior: null, variacao: null, pontos: [] }),
      },
    });
    renderizar();
    expect(await screen.findByText("Mercearia Boa Vista: seus números ainda não chegaram.")).toBeInTheDocument();
    expect(screen.getByText(/depois da primeira importação de relatório que incluir o seu comércio/)).toBeInTheDocument();
  });

  it("o parceiro que entra pela raiz vai direto ao portal dele", async () => {
    simularApi({ "GET /api/meu-desempenho": { corpo: desempenho() } });
    render(
      <ContextoSessao.Provider
        value={{
          usuario: { nome: "Dona da Mercearia", perfil: "PARCEIRO", telas: ["meu_desempenho"] },
          conferindo: false,
          sair: () => {},
        }}
      >
        <MemoryRouter initialEntries={["/"]}>
          <App />
        </MemoryRouter>
      </ContextoSessao.Provider>,
    );
    expect(await screen.findByRole("heading", { name: "Mercearia Boa Vista · Mercado" })).toBeInTheDocument();
    const trilho = screen.getByRole("navigation", { name: "Seções do sistema" });
    expect(within(trilho).getAllByRole("link").map((a) => a.textContent.trim())).toEqual(["Meu desempenho"]);
  });
});
