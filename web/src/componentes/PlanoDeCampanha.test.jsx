import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PlanoDeCampanha from "./PlanoDeCampanha";
import { amostra, montar } from "../testes/montar";

const PLANO = () => amostra("GET_api_otimizacoes_execucao_id");

/* RF30 — o plano de campanha: os pares parceiro-ação escolhidos, o custo e o
   ganho esperado, que é estimativa. */
describe("o plano de campanha (RF30)", () => {
  it("é lacrado com o número, quem calculou e quando", async () => {
    montar(<PlanoDeCampanha execucao={PLANO()} />);

    const lacre = (await screen.findByText("Plano calculado")).closest(".lacre");
    // O número é lido como "número 4"; o "Nº" é só desenho.
    expect(lacre).toHaveTextContent("número 4");
    expect(lacre).toHaveTextContent(/em 05\/10\/2026 às \d{2}:\d{2} por Medição Gestor/);
  });

  it("lista cada ação do plano, com o parceiro, o segmento por nome, o custo e o ganho", async () => {
    montar(<PlanoDeCampanha execucao={PLANO()} />);

    const tabela = await screen.findByRole("region", { name: "Tabela: Ações do plano" });
    const linha = within(tabela).getByText("Ponto Azul 2").closest("tr");
    expect(linha).toHaveTextContent("Em risco");
    expect(linha).toHaveTextContent("Campanha de categoria");
    expect(linha).toHaveTextContent("R$ 480,00");
    expect(linha).toHaveTextContent("R$ 20.258,30");
  });

  it("o ganho esperado é marcado como estimativa, e comparado com o plano guloso", async () => {
    montar(<PlanoDeCampanha execucao={PLANO()} />);

    expect((await screen.findAllByText("Estimativa")).length).toBeGreaterThan(0);
    expect(screen.getByText(/Contra o guloso:/)).toHaveTextContent("R$ 116.299,48");
  });

  it("o nome leva à ficha do parceiro só para quem abre parceiros", async () => {
    montar(<PlanoDeCampanha execucao={PLANO()} />, { perfil: "GESTOR" });
    expect(await screen.findByRole("link", { name: "Ponto Azul 2" })).toHaveAttribute("href", "/parceiros/246");
  });

  it("oferece gerar as mensagens do plano a quem tem a área de mensagens", async () => {
    montar(<PlanoDeCampanha execucao={PLANO()} />, { perfil: "GESTOR" });

    await waitFor(() => expect(screen.getByRole("link", { name: /Gerar mensagens para este plano/ })).toHaveAttribute("href", "/mensagens?plano=4"));
  });

  it("o Administrador, que não gera mensagens, não vê o atalho", async () => {
    montar(<PlanoDeCampanha execucao={PLANO()} />, { perfil: "ADMINISTRADOR" });

    await screen.findByRole("region", { name: "Tabela: Ações do plano" });
    await waitFor(() => expect(screen.queryByRole("link", { name: /Gerar mensagens/ })).not.toBeInTheDocument());
  });

  it("o plano parcial, cortado pelo tempo, avisa que é o melhor viável até ali", async () => {
    montar(<PlanoDeCampanha execucao={{ ...PLANO(), parcial: true }} />);

    expect(await screen.findByText(/O cálculo atingiu o limite de tempo/)).toBeInTheDocument();
  });
});
