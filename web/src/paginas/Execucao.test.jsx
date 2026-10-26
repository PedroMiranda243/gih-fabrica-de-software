import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const EXECUCAO = () => amostra("GET_api_otimizacoes_execucao_id");
const ROTAS = (corpo = EXECUCAO()) => ({ "GET /api/otimizacoes/:id": { corpo } });

/* RF34 (a execução registrada), RF53 (o plano em CSV) e o caminho para as
   mensagens do plano (RF36): a tela de uma execução do otimizador. */
describe("uma execução do otimizador", () => {
  it("abre a execução do endereço, com o título e o caminho de volta", async () => {
    const { chamadas } = abrir("/execucoes/4", { rotas: ROTAS() });

    expect(await screen.findByRole("heading", { level: 1, name: /^Execução de / })).toBeInTheDocument();
    expect(chamadas()).toContain("GET /api/otimizacoes/4");
    expect(screen.getAllByRole("link", { name: "Execuções" }).some((l) => l.getAttribute("href") === "/execucoes")).toBe(true);
  });

  it("o plano com ações traz o CSV dele e o caminho para gerar as mensagens (RF53, RF36)", async () => {
    abrir("/execucoes/4", { rotas: ROTAS() });

    expect(await screen.findByRole("link", { name: /Exportar CSV/ })).toHaveAttribute("href", "/api/otimizacoes/4/exportacao.csv");
    expect(screen.getByRole("link", { name: /Gerar mensagens para este plano/ })).toHaveAttribute("href", "/mensagens?plano=4");
    expect(screen.getByText("Ponto Azul 2")).toBeInTheDocument();
  });

  it("sem solução viável, não oferece CSV e diz por quê (RN07)", async () => {
    const motivo = "As cotas mínimas exigem pelo menos R$ 720,00, acima do orçamento de R$ 100,00: faltam R$ 620,00.";
    abrir("/execucoes/4", { rotas: ROTAS({ ...EXECUCAO(), viavel: false, restricao_violada: "orcamento", motivo, acoes: 0, itens: [] }) });

    expect(await screen.findByText(motivo)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Exportar CSV/ })).not.toBeInTheDocument();
  });

  it("endereço de uma execução que não existe diz isso e leva de volta à lista", async () => {
    abrir("/execucoes/999", { rotas: { "GET /api/otimizacoes/:id": { status: 404, corpo: { erro: "Execução não encontrada." } } } });

    const aviso = (await screen.findByText("Execução não encontrada", { selector: "p, h2, h3, strong" })).closest("div");
    expect(within(aviso.parentElement).getByRole("link", { name: "Voltar para as execuções" })).toHaveAttribute("href", "/execucoes");
  });
});
