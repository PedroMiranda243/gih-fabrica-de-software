import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

/* RF26 — o Parceiro vê exclusivamente o próprio desempenho, período a período. */
describe("Meu desempenho (RF26)", () => {
  it("mostra os números do próprio comércio, comparados com o período anterior", async () => {
    abrir("/meu-desempenho", { perfil: "PARCEIRO", rotas: { "GET /api/meu-desempenho": { corpo: amostra("GET_api_meu_desempenho") } } });

    expect(await screen.findByRole("heading", { level: 1, name: "Meu desempenho" })).toBeInTheDocument();
    const indicadores = await waitFor(() => {
      const s = document.querySelector('[aria-labelledby="titulo-meus-indicadores"]');
      expect(s).toHaveTextContent("79.410");
      return s;
    });
    expect(indicadores).toHaveTextContent("1.070");
    expect(indicadores).toHaveTextContent("−15,06%");
    expect(screen.getByText(/Ponto Azul 2/)).toBeInTheDocument();
  });

  it("chama só a consulta do próprio parceiro, e nenhuma da rede", async () => {
    const { chamadas } = abrir("/meu-desempenho", { perfil: "PARCEIRO", rotas: { "GET /api/meu-desempenho": { corpo: amostra("GET_api_meu_desempenho") } } });

    await screen.findByRole("heading", { level: 1, name: "Meu desempenho" });
    await waitFor(() => expect(chamadas()).toContain("GET /api/meu-desempenho"));
    expect(chamadas().filter((c) => /\/api\/(parceiros|painel|relatorios)/.test(c))).toEqual([]);
  });

  it("o menu do Parceiro tem só o portal dele", async () => {
    abrir("/meu-desempenho", { perfil: "PARCEIRO", rotas: { "GET /api/meu-desempenho": { corpo: amostra("GET_api_meu_desempenho") } } });

    const menu = await screen.findByRole("navigation", { name: "Menu principal" });
    const itens = [...menu.querySelectorAll(".menu__rotulo")].map((e) => e.textContent);
    expect(itens).toEqual(["Meu desempenho"]);
  });

  it("antes do primeiro relatório com o comércio, diz que os números ainda não chegaram", async () => {
    const vazio = { ...amostra("GET_api_meu_desempenho"), atual: null, anterior: null, variacao: null, pontos: [] };
    abrir("/meu-desempenho", { perfil: "PARCEIRO", rotas: { "GET /api/meu-desempenho": { corpo: vazio } } });

    expect(await screen.findByText("Ponto Azul 2: seus números ainda não chegaram.")).toBeInTheDocument();
  });
});
