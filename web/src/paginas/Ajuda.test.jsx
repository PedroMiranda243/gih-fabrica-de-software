import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const REGRAS = () => ({ "GET /api/ajuda/regras": { corpo: amostra("GET_api_ajuda_regras") } });

/* RF55 (o significado dos termos, com os segmentos na ordem da RN01) e RNF20
   (em português, operável sem treinamento). */
describe("a ajuda", () => {
  it("lista os segmentos na ordem em que a regra decide (RF55)", async () => {
    abrir("/ajuda", { perfil: "GESTOR", rotas: REGRAS() });

    const segmentos = (await screen.findByRole("heading", { name: "Os segmentos" })).closest("section");
    const ordem = [...segmentos.querySelectorAll("ol > li")].map((li) => li.querySelector(".segmento")?.textContent.trim());
    expect(ordem).toEqual(["Prospecção", "Recém-chegado", "Em risco", "Top", "Em ascensão", "Estável"]);
  });

  it("os limiares vêm da API: com o Top em 10, a ajuda diz 10 (#229)", async () => {
    const regras = amostra("GET_api_ajuda_regras");
    regras.top_n = 10;
    abrir("/ajuda", { perfil: "GESTOR", rotas: { "GET /api/ajuda/regras": { corpo: regras } } });

    expect(await screen.findByText(/Os limiares de agora: Top de 10/)).toBeInTheDocument();
    expect(screen.queryByText(/Top de 15/)).not.toBeInTheDocument();
  });

  it("explica a estimativa e o ganho esperado (RF55)", async () => {
    abrir("/ajuda", { perfil: "GESTOR", rotas: REGRAS() });

    await waitFor(() => expect(document.getElementById("estimativa")).toBeInTheDocument());
    expect(document.getElementById("ganho")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Estimativa" })).toHaveAttribute("href", "#estimativa");
  });

  it("diz quem muda os limiares: o administrador vai à Configuração; os outros, o administrador", async () => {
    abrir("/ajuda", { perfil: "ADMINISTRADOR", rotas: REGRAS() });
    expect(await screen.findByRole("link", { name: "Configuração", hidden: false })).toBeInTheDocument();
  });

  it("o Parceiro lê só sobre o portal dele, e a tela nem pede as regras da rede (RNF20)", async () => {
    const { chamadas } = abrir("/ajuda", { perfil: "PARCEIRO" });

    expect(await screen.findByRole("heading", { name: "O seu portal" })).toBeInTheDocument();
    expect(screen.getByText(/O portal mostra só o seu comércio\./)).toBeInTheDocument();
    expect(chamadas().filter((c) => c.includes("/api/ajuda/regras"))).toEqual([]);
  });
});
