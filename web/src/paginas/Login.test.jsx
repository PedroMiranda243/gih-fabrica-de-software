import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProvedorDeSessao } from "../api/sessao";
import { simularApi } from "../testes/preparar";
import Login from "./Login";

function renderizar() {
  return render(
    <MemoryRouter>
      <ProvedorDeSessao>
        <Login />
      </ProvedorDeSessao>
    </MemoryRouter>,
  );
}

describe("Login", () => {
  it("mostra a recusa do servidor e limpa só a senha", async () => {
    simularApi({
      "GET /api/sessao/atual": { status: 401, corpo: { detail: "Sessão ausente." } },
      "POST /api/sessao": { status: 401, corpo: { detail: "Login ou senha inválidos." } },
    });
    const usuario = userEvent.setup();

    renderizar();
    await usuario.type(await screen.findByLabelText("Login"), "gestora");
    await usuario.type(screen.getByLabelText("Senha"), "senha-errada");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    /* A mensagem é a do servidor — que responde igual para senha errada e
       usuário inexistente (RNF11). A tela não pode ser "prestativa" e
       distinguir os dois. */
    expect(await screen.findByRole("alert")).toHaveTextContent("Login ou senha inválidos.");
    /* Quem errou a senha digita a senha de novo, não o login inteiro. */
    expect(screen.getByLabelText("Login")).toHaveValue("gestora");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
  });

  it("o botão fica desabilitado enquanto faltar campo", async () => {
    simularApi({ "GET /api/sessao/atual": { status: 401, corpo: {} } });

    renderizar();

    expect(await screen.findByRole("button", { name: "Entrar" })).toBeDisabled();
  });

  it("todo campo tem rótulo visível, e não só placeholder", async () => {
    /* Placeholder como rótulo some assim que a pessoa digita. `toBeVisible`
       confere o que a pessoa vê — a armadilha do `[hidden]` está registrada no
       CLAUDE.md: testes que conferiam o atributo passavam com a tela na frente
       do usuário. */
    simularApi({ "GET /api/sessao/atual": { status: 401, corpo: {} } });

    renderizar();

    expect(await screen.findByText("Login")).toBeVisible();
    expect(screen.getByText("Senha")).toBeVisible();
  });
});
