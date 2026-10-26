import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir } from "../testes/montar";

/* RF07 — trocar a própria senha, exigindo a atual. */
describe("Minha conta (RF07)", () => {
  it("mostra os dados da conta, só para leitura", async () => {
    abrir("/conta", { perfil: "ANALISTA" });

    expect(await screen.findByRole("heading", { level: 1, name: "Minha conta" })).toBeInTheDocument();
    expect(screen.getByText("Quem muda o nome e o perfil é o administrador.")).toBeInTheDocument();
    expect(screen.getByText("Analista", { selector: "dd" })).toBeInTheDocument();
  });

  it("troca a senha mandando a atual e a nova", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/conta", { perfil: "GESTOR", rotas: { "POST /api/sessao/senha": { status: 204 } } });

    await usuario.type(await screen.findByLabelText(/^Senha atual/), "antiga-123");
    await usuario.type(screen.getByLabelText(/^Senha nova(?!, de novo)/), "nova-e-forte-456");
    await usuario.type(screen.getByLabelText(/^Senha nova, de novo/), "nova-e-forte-456");
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    expect(await screen.findByText(/Senha trocada\./)).toBeInTheDocument();
    expect(corpoDe("POST /api/sessao/senha")).toEqual({ senha_atual: "antiga-123", senha_nova: "nova-e-forte-456" });
    expect(screen.getByLabelText(/^Senha atual/)).toHaveValue("");
  });

  it("pega o erro de digitação antes de mandar ao servidor", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/conta", { perfil: "GESTOR" });

    await usuario.type(await screen.findByLabelText(/^Senha atual/), "antiga-123");
    await usuario.type(screen.getByLabelText(/^Senha nova(?!, de novo)/), "nova-e-forte-456");
    await usuario.type(screen.getByLabelText(/^Senha nova, de novo/), "nova-e-forte-465");
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    expect(screen.getByText("As duas digitações da senha nova não são iguais.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Senha nova, de novo/)).toHaveFocus();
    expect(chamadas().filter((c) => c.startsWith("POST"))).toEqual([]);
  });

  it("a senha atual errada volta com o texto do servidor, ao lado do campo", async () => {
    const usuario = userEvent.setup();
    abrir("/conta", {
      perfil: "GESTOR",
      rotas: {
        "POST /api/sessao/senha": {
          status: 422,
          corpo: { erro: "Alguns campos precisam de correção.", campos: [{ campo: "senha_atual", mensagem: "A senha atual não confere." }] },
        },
      },
    });

    await usuario.type(await screen.findByLabelText(/^Senha atual/), "errada");
    await usuario.type(screen.getByLabelText(/^Senha nova(?!, de novo)/), "nova-e-forte-456");
    await usuario.type(screen.getByLabelText(/^Senha nova, de novo/), "nova-e-forte-456");
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    expect((await screen.findAllByText("A senha atual não confere.")).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/^Senha atual/)).toHaveAttribute("aria-invalid", "true");
  });
});
