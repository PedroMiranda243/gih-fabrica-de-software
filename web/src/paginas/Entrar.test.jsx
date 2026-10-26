import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, endereco, rotasDoPainel, sessaoDe } from "../testes/montar";

/* RF01 — entrar por login e senha, numa sessão que o servidor guarda. */
const PAINEL = rotasDoPainel();

describe("a entrada (RF01)", () => {
  it("tem os rótulos à vista e o botão desligado até os dois campos terem texto", async () => {
    const usuario = userEvent.setup();
    abrir("/entrar", { perfil: null });

    const botao = await screen.findByRole("button", { name: "Entrar" });
    expect(screen.getByLabelText("Login")).toBeVisible();
    expect(screen.getByLabelText("Senha")).toBeVisible();
    expect(botao).toBeDisabled();
    await usuario.type(screen.getByLabelText("Login"), "lab.gestor");
    expect(botao).toBeDisabled();
    await usuario.type(screen.getByLabelText("Senha"), "segredo");
    expect(botao).toBeEnabled();
  });

  it("manda login e senha ao servidor e leva a pessoa para dentro", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/entrar", {
      perfil: null,
      rotas: { "POST /api/sessao": { status: 201, corpo: { usuario: sessaoDe("GESTOR") } }, ...PAINEL },
    });

    await usuario.type(await screen.findByLabelText("Login"), "lab.gestor");
    await usuario.type(screen.getByLabelText("Senha"), "segredo");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    expect(corpoDe("POST /api/sessao")).toEqual({ login: "lab.gestor", senha: "segredo" });
    await waitFor(() => expect(endereco()).toBe("/"));
  });

  it("na recusa, mostra o texto do servidor e apaga só a senha", async () => {
    const usuario = userEvent.setup();
    abrir("/entrar", {
      perfil: null,
      rotas: { "POST /api/sessao": { status: 401, corpo: { detail: "Login ou senha incorretos." } } },
    });

    await usuario.type(await screen.findByLabelText("Login"), "lab.gestor");
    await usuario.type(screen.getByLabelText("Senha"), "errada");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Login ou senha incorretos.");
    expect(screen.getByLabelText("Login")).toHaveValue("lab.gestor");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
    expect(screen.getByLabelText("Senha")).toHaveFocus();
    await waitFor(() => expect(endereco()).toBe("/entrar"));
  });

  it("mostra a senha só quando a pessoa pede, sem enviar o formulário", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/entrar", { perfil: null });

    const senha = await screen.findByLabelText("Senha");
    await usuario.type(senha, "segredo");
    expect(senha).toHaveAttribute("type", "password");
    await usuario.click(screen.getByRole("button", { name: "Mostrar" }));
    expect(senha).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Ocultar" })).toHaveAttribute("aria-pressed", "true");
    expect(chamadas().filter((c) => c.startsWith("POST"))).toEqual([]);
  });

  it("o bloqueio por tentativas (429) chega com o texto do servidor", async () => {
    const usuario = userEvent.setup();
    abrir("/entrar", {
      perfil: null,
      rotas: { "POST /api/sessao": { status: 429, corpo: { detail: "Muitas tentativas. Tente de novo em alguns minutos." } } },
    });

    await usuario.type(await screen.findByLabelText("Login"), "lab.gestor");
    await usuario.type(screen.getByLabelText("Senha"), "errada");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Muitas tentativas. Tente de novo em alguns minutos.");
  });

  it("quem já tem sessão e abre a entrada vai direto para dentro", async () => {
    abrir("/entrar", { perfil: "GESTOR", rotas: PAINEL });

    await waitFor(() => expect(endereco()).toBe("/"));
  });
});
