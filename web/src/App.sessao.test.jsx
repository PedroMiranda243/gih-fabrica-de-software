import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra, endereco, sessaoDe } from "./testes/montar";

/*
 * H96 — a sessão que termina no meio do trabalho. Sem aviso, a tela de entrada
 * no meio do trabalho parece defeito; e depois de entrar de novo, a pessoa volta
 * para onde estava, com os filtros.
 */
describe("a sessão que termina no meio", () => {
  it("leva à entrada com o aviso e, depois de entrar, devolve ao mesmo endereço", async () => {
    const usuario = userEvent.setup();
    let expirada = true;
    abrir("/parceiros?segmento=TOP", {
      perfil: "GESTOR",
      rotas: {
        "GET /api/parceiros": () => (expirada ? { status: 401, corpo: { detail: "Sessão expirada." } } : { corpo: amostra("GET_api_parceiros") }),
        "GET /api/categorias": { corpo: amostra("GET_api_categorias") },
        "GET /api/painel/recortes": { corpo: amostra("GET_api_painel_recortes") },
        "POST /api/sessao": () => {
          expirada = false;
          return { status: 201, corpo: { usuario: sessaoDe("GESTOR") } };
        },
      },
    });

    expect(await screen.findByText("A sua sessão terminou. Entre de novo para continuar de onde parou.")).toBeInTheDocument();
    expect(endereco()).toBe("/entrar");

    await usuario.type(screen.getByLabelText("Login"), "lab.gestor");
    await usuario.type(screen.getByLabelText("Senha"), "segredo");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => expect(endereco()).toBe("/parceiros?segmento=TOP"));
    expect(await screen.findByRole("heading", { level: 1, name: "Parceiros" })).toBeInTheDocument();
  });

  it("quem abre o sistema sem sessão não vê o aviso de sessão terminada", async () => {
    abrir("/parceiros", { perfil: null });

    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByText(/A sua sessão terminou/)).not.toBeInTheDocument();
  });
});
