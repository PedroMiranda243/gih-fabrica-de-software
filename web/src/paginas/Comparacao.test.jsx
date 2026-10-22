import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const ROTAS = () => ({ "GET /api/otimizacoes/comparacao": { corpo: amostra("GET_api_otimizacoes_comparacao") } });

/* RF35 — dois planos lado a lado: o que mudou no pedido, no resultado e parceiro
   a parceiro. */
describe("a comparação de dois planos (RF35)", () => {
  it("pede a comparação dos dois planos do endereço", async () => {
    const { chamadas } = abrir("/execucoes/comparar?a=4&b=3", { rotas: ROTAS() });

    expect(await screen.findByRole("heading", { level: 1, name: "Comparação de dois planos" })).toBeInTheDocument();
    expect(chamadas()).toContain("GET /api/otimizacoes/comparacao?a=4&b=3");
  });

  it("mostra os parâmetros lado a lado, com o que mudou", async () => {
    abrir("/execucoes/comparar?a=4&b=3", { rotas: ROTAS() });

    const pedido = (await screen.findByRole("heading", { name: /Parâmetros|pedido/i })).closest("section");
    expect(pedido).toHaveTextContent("Plano A");
    expect(pedido).toHaveTextContent("Plano B");
    expect(pedido).toHaveTextContent("R$ 8.000,00");
  });

  it("parceiro a parceiro, mostra só o que mudou e os iguais a um clique", async () => {
    const usuario = userEvent.setup();
    abrir("/execucoes/comparar?a=4&b=3", { rotas: ROTAS() });

    expect(await screen.findByText("Forno da Serra 2")).toBeInTheDocument();
    const mostrar = screen.getByRole("button", { name: "Mostrar também os 13 que ficaram iguais" });
    expect(mostrar).toHaveAttribute("aria-expanded", "false");
    await usuario.click(mostrar);
    expect(screen.getByRole("button", { name: "Esconder os que ficaram iguais" })).toHaveAttribute("aria-expanded", "true");
  });

  it("sem os dois planos no endereço, não chama a API e diz o que fazer", async () => {
    const { chamadas } = abrir("/execucoes/comparar?a=4", { rotas: ROTAS() });

    await screen.findByRole("heading", { level: 1, name: "Comparação de dois planos" });
    expect(chamadas().filter((c) => c.includes("/comparacao"))).toEqual([]);
  });
});
