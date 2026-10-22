import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { abrir, amostra } from "../testes/montar";

const DESEMPENHO = () => ({
  "GET /api/painel/recortes": { corpo: amostra("GET_api_painel_recortes") },
  "GET /api/relatorios/desempenho": { corpo: amostra("GET_api_relatorios_desempenho") },
});
const RISCO = () => ({
  "GET /api/categorias": { corpo: amostra("GET_api_categorias") },
  "GET /api/relatorios/risco": { corpo: amostra("GET_api_relatorios_risco") },
});
const CAMPANHA = () => ({
  "GET /api/relatorios/campanha/planos": { corpo: amostra("GET_api_relatorios_campanha_planos") },
  "GET /api/relatorios/campanha": { corpo: amostra("GET_api_relatorios_campanha") },
});
const OPERACOES = () => ({
  "GET /api/usuarios": { corpo: amostra("GET_api_usuarios") },
  "GET /api/auditoria/acoes": { corpo: amostra("GET_api_auditoria_acoes") },
  "GET /api/relatorios/operacoes": { corpo: amostra("GET_api_relatorios_operacoes") },
});
const csv = () => screen.getByRole("link", { name: /Exportar CSV/ }).getAttribute("href");
const ultima = (chamadas, caminho) => chamadas().filter((c) => c.startsWith(`GET ${caminho}`)).at(-1) ?? "";

/* RF44 a RF48 — os quatro relatórios, cada um com o recorte escrito na folha, o
   CSV do mesmo recorte e a impressão em PDF. */
describe("os relatórios", () => {
  it("a lista mostra só os relatórios do perfil", async () => {
    abrir("/relatorios", { perfil: "GESTOR" });

    expect(await screen.findByRole("link", { name: "Abrir o relatório Desempenho por período" })).toHaveAttribute("href", "/relatorios/desempenho");
    expect(screen.getByRole("link", { name: /Abrir o relatório Parceiros em risco/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Operações/ })).not.toBeInTheDocument();
  });

  it("desempenho do período, por categoria e por segmento, com o recorte na folha e no CSV (RF44, RF48)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/relatorios/desempenho", { rotas: DESEMPENHO() });

    expect(await screen.findByRole("heading", { level: 2, name: "Desempenho por período" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("article")).toHaveTextContent("28/09/2026 a 04/10/2026"));
    await usuario.selectOptions(screen.getByLabelText("Segmento"), "TOP");
    await waitFor(() => expect(ultima(chamadas, "/api/relatorios/desempenho")).toContain("segmento=TOP"));
    await waitFor(() => expect(csv()).toBe("/api/relatorios/desempenho/exportacao.csv?segmento=TOP"));
  });

  it("parceiros em risco: a chance mínima vai para a API em fração, e fica no endereço em percentual (RF45)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/relatorios/risco", { rotas: RISCO() });

    const minimo = await screen.findByLabelText("Chance de queda a partir de (%)");
    await usuario.type(minimo, "14");
    await waitFor(() => expect(ultima(chamadas, "/api/relatorios/risco")).toContain("risco_minimo=0.1400"));
    expect(csv()).toContain("risco_minimo=0.1400");
  });

  it("parceiros em risco aberto por um link antigo, com o percentual no endereço, manda a fração à API", async () => {
    const { chamadas } = abrir("/relatorios/risco?risco_minimo=14", { rotas: RISCO() });

    expect(await screen.findByLabelText("Chance de queda a partir de (%)")).toHaveValue("14");
    await waitFor(() => expect(ultima(chamadas, "/api/relatorios/risco")).toContain("risco_minimo=0.1400"));
  });

  it("o relatório de risco marca o que é estimativa (RF45)", async () => {
    abrir("/relatorios/risco", { rotas: RISCO() });

    await screen.findByRole("heading", { level: 2, name: "Parceiros em risco" });
    expect((await screen.findAllByText("Estimativa")).length).toBeGreaterThan(0);
  });

  it("campanha: escolhe o plano, e o CSV é o do plano escolhido (RF46)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/relatorios/campanha", { rotas: CAMPANHA() });

    await screen.findByRole("heading", { level: 2, name: "Campanha" });
    await waitFor(() => expect(csv()).toBe("/api/relatorios/campanha/exportacao.csv?execucao_id=4"));
    const plano = screen.getByRole("combobox");
    await usuario.selectOptions(plano, "3");
    await waitFor(() => expect(ultima(chamadas, "/api/relatorios/campanha")).toContain("execucao_id=3"));
  });

  it("operações do sistema, por tipo de ação, num intervalo de datas — do Administrador (RF47)", async () => {
    abrir("/relatorios/operacoes", { perfil: "ADMINISTRADOR", rotas: OPERACOES() });

    expect(await screen.findByRole("heading", { level: 2, name: "Operações do sistema" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("article")).toHaveTextContent("Acesso negado"));
    expect(screen.getByRole("article")).toHaveTextContent("211");
  });

  it("imprime pelo navegador, com quem emitiu e quando na folha (RF48)", async () => {
    const usuario = userEvent.setup();
    const imprimir = vi.spyOn(window, "print").mockImplementation(() => {});
    abrir("/relatorios/desempenho", { rotas: DESEMPENHO() });

    await usuario.click(await screen.findByRole("button", { name: /Imprimir ou salvar em PDF/ }));

    expect(imprimir).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/^Emitido em .* por Gestora do Laboratório\.$/)).toHaveClass("so-impressao");
  });

  it("o Analista abre os relatórios da rede, mas não o de operações", async () => {
    const { chamadas } = abrir("/relatorios/operacoes", { perfil: "ANALISTA" });

    expect(await screen.findByRole("heading", { level: 1, name: "Sem acesso" })).toBeInTheDocument();
    expect(chamadas().filter((c) => c.includes("/api/relatorios/operacoes"))).toEqual([]);
  });
});
