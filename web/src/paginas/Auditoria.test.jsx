import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const ROTAS = () => ({
  "GET /api/auditoria": { corpo: amostra("GET_api_auditoria") },
  "GET /api/auditoria/acoes": { corpo: amostra("GET_api_auditoria_acoes") },
  "GET /api/usuarios": { corpo: amostra("GET_api_usuarios") },
});
const ultima = (chamadas) => chamadas().filter((c) => c.startsWith("GET /api/auditoria?")).at(-1) ?? "";

/* RF08 (consultar a trilha com filtros) e RF49 (buscar por texto e exportar o recorte). */
describe("a trilha de auditoria", () => {
  it("mostra quem fez o quê, quando e de onde (RF08)", async () => {
    abrir("/auditoria", { perfil: "ADMINISTRADOR", rotas: ROTAS() });

    const trilha = await screen.findByRole("region", { name: "Tabela: Trilha de auditoria" });
    const primeiro = amostra("GET_api_auditoria").itens[0];
    expect(trilha).toHaveTextContent(primeiro.rotulo);
    expect(trilha).toHaveTextContent(primeiro.autor);
    expect(trilha).toHaveTextContent(primeiro.origem);
  });

  it("filtra por ação, por pessoa e por datas (RF08)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/auditoria", { perfil: "ADMINISTRADOR", rotas: ROTAS() });

    await screen.findByRole("option", { name: "Entrada recusada" });
    await screen.findByRole("option", { name: /lab\.gestor/ });
    await usuario.selectOptions(screen.getByLabelText("Ação"), "LOGIN_FALHA");
    await waitFor(() => expect(ultima(chamadas)).toContain("acao=LOGIN_FALHA"));
    await usuario.selectOptions(screen.getByLabelText("Quem fez"), "3");
    await waitFor(() => expect(ultima(chamadas)).toContain("autor=3"));
    await usuario.type(screen.getByLabelText("De"), "2026-10-01");
    await waitFor(() => expect(ultima(chamadas)).toContain("de=2026-10-01"));
  });

  it("busca por texto e exporta exatamente o recorte (RF49)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/auditoria?acao=LOGIN_FALHA", { perfil: "ADMINISTRADOR", rotas: ROTAS() });

    await usuario.type(await screen.findByLabelText("Buscar na trilha"), "lab.gestor");
    await waitFor(() => expect(ultima(chamadas)).toContain("busca=lab.gestor"));
    const csv = screen.getByRole("link", { name: /Exportar CSV/ });
    expect(csv.getAttribute("href")).toMatch(/^\/api\/auditoria\/exportacao\.csv\?/);
    expect(csv.getAttribute("href")).toContain("acao=LOGIN_FALHA");
    expect(csv.getAttribute("href")).toContain("busca=lab.gestor");
  });

  it("recorte vazio diz isso", async () => {
    abrir("/auditoria?busca=nada", {
      perfil: "ADMINISTRADOR",
      rotas: { ...ROTAS(), "GET /api/auditoria": { corpo: { itens: [], total: 0, pagina: 1, tamanho: 50 } } },
    });

    expect(await screen.findByText("Nenhum registro nesse recorte")).toBeInTheDocument();
  });
});
