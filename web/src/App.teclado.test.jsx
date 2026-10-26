import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra, endereco } from "./testes/montar";

const PARCEIROS = {
  "GET /api/parceiros": { corpo: amostra("GET_api_parceiros") },
  "GET /api/categorias": { corpo: amostra("GET_api_categorias") },
  "GET /api/painel/recortes": { corpo: amostra("GET_api_painel_recortes") },
};

/*
 * RF02 — encerrar a sessão, invalidando-a no servidor; e a aplicação inteira
 * operável pelo teclado (H96): pular para o conteúdo, o foco no título a cada
 * troca de tela, o menu que abre e fecha.
 */
describe("encerrar a sessão (RF02)", () => {
  it("pelo teclado: invalida a sessão no servidor e volta para a entrada", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/conta", { rotas: { "DELETE /api/sessao": { status: 204 } } });

    const sair = await screen.findByRole("button", { name: "Encerrar sessão" });
    sair.focus();
    await usuario.keyboard("{Enter}");

    await waitFor(() => expect(endereco()).toBe("/entrar"));
    expect(chamadas()).toContain("DELETE /api/sessao");
    // Sair de propósito não é "a sessão terminou".
    expect(screen.queryByText(/A sua sessão terminou/)).not.toBeInTheDocument();
  });

  it("sai mesmo que o servidor não responda: a pessoa pediu para sair", async () => {
    const usuario = userEvent.setup();
    abrir("/conta", { rotas: { "DELETE /api/sessao": { status: 503, corpo: { detail: "Fora do ar." } } } });

    await usuario.click(await screen.findByRole("button", { name: "Encerrar sessão" }));

    await waitFor(() => expect(endereco()).toBe("/entrar"));
  });
});

describe("pelo teclado", () => {
  it("o primeiro Tab chega a 'Pular para o conteúdo', que leva ao conteúdo", async () => {
    const usuario = userEvent.setup();
    abrir("/conta");

    await screen.findByRole("heading", { level: 1, name: "Minha conta" });
    document.body.focus();
    await usuario.tab();
    const pular = screen.getByRole("link", { name: "Pular para o conteúdo" });
    expect(pular).toHaveFocus();
    expect(pular).toHaveAttribute("href", "#conteudo");
    expect(document.getElementById("conteudo").tagName).toBe("MAIN");
  });

  it("ao trocar de tela, o foco vai para o título da tela nova", async () => {
    const usuario = userEvent.setup();
    abrir("/conta", { rotas: PARCEIROS });

    await screen.findByRole("heading", { level: 1, name: "Minha conta" });
    await usuario.click(screen.getByRole("link", { name: /Parceiros/ }));

    const titulo = await screen.findByRole("heading", { level: 1, name: "Parceiros" });
    await waitFor(() => expect(titulo).toHaveFocus());
  });

  it("o item da tela atual é marcado no menu, para quem lê e para quem ouve", async () => {
    abrir("/parceiros", { rotas: PARCEIROS });

    await screen.findByRole("heading", { level: 1, name: "Parceiros" });
    const menu = screen.getByRole("navigation", { name: "Menu principal" });
    const atual = menu.querySelector('[aria-current="page"]');
    expect(atual).toHaveTextContent("Parceiros");
  });

  it("o menu de gaveta abre pelo botão e fecha com Esc, devolvendo o foco", async () => {
    const usuario = userEvent.setup();
    abrir("/conta");

    const abrirMenu = await screen.findByRole("button", { name: "Abrir o menu" });
    await usuario.click(abrirMenu);
    expect(abrirMenu).toHaveAttribute("aria-expanded", "true");
    await usuario.keyboard("{Escape}");
    expect(abrirMenu).toHaveAttribute("aria-expanded", "false");
    expect(abrirMenu).toHaveFocus();
  });
});
