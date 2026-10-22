import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const ultima = (chamadas) => chamadas().filter((c) => c.startsWith("GET /api/usuarios")).at(-1) ?? "";

/* RF03 (listar usuários) e RF52 (buscar por nome ou login). */
describe("a lista de usuários", () => {
  it("lista as contas, com o perfil por extenso (RF03)", async () => {
    abrir("/usuarios", { perfil: "ADMINISTRADOR", rotas: { "GET /api/usuarios": { corpo: amostra("GET_api_usuarios") } } });

    const tabela = await screen.findByRole("region", { name: "Tabela: Usuários" });
    expect(tabela).toHaveTextContent("Administrador");
    expect(tabela).toHaveTextContent("lab.gestor");
    expect(screen.getByRole("link", { name: /Novo usuário/ })).toHaveAttribute("href", "/usuarios/novo");
  });

  it("busca por um trecho do nome ou do login, e filtra por perfil (RF52)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/usuarios", { perfil: "ADMINISTRADOR", rotas: { "GET /api/usuarios": { corpo: amostra("GET_api_usuarios") } } });

    await usuario.type(await screen.findByLabelText("Buscar por nome ou login"), "gest");
    await waitFor(() => expect(ultima(chamadas)).toContain("busca=gest"));
    await usuario.selectOptions(screen.getByLabelText("Perfil"), "ANALISTA");
    await waitFor(() => expect(ultima(chamadas)).toContain("perfil=ANALISTA"));
  });

  it("recorte sem ninguém diz isso", async () => {
    abrir("/usuarios?busca=ninguem", { perfil: "ADMINISTRADOR", rotas: { "GET /api/usuarios": { corpo: [] } } });

    expect(await screen.findByText("Nenhum usuário neste recorte")).toBeInTheDocument();
  });
});
