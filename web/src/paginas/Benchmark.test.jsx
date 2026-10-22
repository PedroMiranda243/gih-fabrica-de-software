import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const ROTAS = (extra = {}) => ({
  "GET /api/benchmark": { corpo: amostra("GET_api_benchmark") },
  "GET /api/benchmarks": { corpo: amostra("GET_api_benchmarks") },
  "GET /api/benchmarks/:id": { corpo: amostra("GET_api_benchmarks_execucao_id") },
  ...extra,
});

/* RF33 — o benchmark entre os modos: tempo, ganho sobre a base serial e o mesmo
   plano em todos. O ganho se lê contra o Python (RNF02) e contra o C++ serial,
   que é onde o paralelismo aparece (CLAUDE.md, armadilhas de desempenho). */
describe("o benchmark (RF33)", () => {
  it("compara os quatro modos com tempo, desvio e o ganho contra as duas bases", async () => {
    abrir("/benchmark", { rotas: ROTAS() });

    const tabela = await screen.findByRole("region", { name: "Tabela: Comparativo dos modos de execução" });
    const cabecalhos = within(tabela).getAllByRole("columnheader").map((c) => c.textContent);
    expect(cabecalhos.join(" | ")).toMatch(/Python/);
    expect(cabecalhos.join(" | ")).toMatch(/GPU/);
    expect(tabela).toHaveTextContent("Ganho sobre o Python");
    expect(tabela).toHaveTextContent("Ganho sobre o C++ serial");
    expect(tabela).toHaveTextContent("83,9x");
    expect(tabela).toHaveTextContent("5,5x");
  });

  it("cada modo diz o que tem nesta máquina, e o que falta diz por quê", async () => {
    const estado = amostra("GET_api_benchmark");
    estado.colunas = estado.colunas.map((c) => (c.coluna === "GPU" ? { ...c, disponivel: false, motivo: "Nenhuma placa compatível." } : c));
    abrir("/benchmark", { rotas: ROTAS({ "GET /api/benchmark": { corpo: estado } }) });

    const modos = (await screen.findByRole("heading", { name: "Modos nesta máquina" })).closest("section");
    expect(modos).toHaveTextContent("OpenMP · 8 threads");
    expect(modos).toHaveTextContent("Indisponível: Nenhuma placa compatível.");
  });

  it("roda um cenário novo e mostra o andamento enquanto mede", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/benchmark", {
      rotas: ROTAS({
        "POST /api/benchmarks": { status: 202, corpo: { ...amostra("GET_api_benchmarks_execucao_id"), id: 9, situacao: "EM_ANDAMENTO" } },
        "GET /api/benchmarks/:id": { corpo: { ...amostra("GET_api_benchmarks_execucao_id"), id: 9, situacao: "EM_ANDAMENTO", progresso: { passo: 2, total: 12 } } },
      }),
    });

    const parceiros = await screen.findByLabelText("Parceiros");
    await usuario.clear(parceiros);
    await usuario.type(parceiros, "500");
    await usuario.click(screen.getByRole("button", { name: /Rodar benchmark/ }));

    expect(await screen.findByRole("button", { name: /Benchmark em andamento…/ })).toBeDisabled();
    expect(corpoDe("POST /api/benchmarks")).toMatchObject({ parceiros: 500 });
    expect((await screen.findAllByText(/passo 2 de 12/)).length).toBeGreaterThan(0);
  });

  it("o gráfico de escala logarítmica tem a descrição em texto e a tabela dos números a um clique", async () => {
    const usuario = userEvent.setup();
    abrir("/benchmark", { rotas: ROTAS() });

    const grafico = await screen.findByRole("img", { name: /./ });
    expect(grafico).toHaveAccessibleName();
    await usuario.click(screen.getByRole("button", { name: "Ver os números" }));
    expect(screen.getByRole("button", { name: "Ocultar os números" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("table").length).toBeGreaterThan(1);
  });
});
