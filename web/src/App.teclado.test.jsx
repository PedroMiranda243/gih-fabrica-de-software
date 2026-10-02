import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "./api/contextoSessao";
import { ProvedorDeSessao } from "./api/sessao";
import App from "./App";
import { simularApi } from "./testes/preparar";

/**
 * O teclado e a sessão, na aplicação inteira — H96.
 *
 * O que só existe com a casca e as rotas juntas: o link que pula o menu, o foco
 * que acompanha a troca de tela, e o aviso de que a sessão terminou.
 */
const ADMINISTRADOR = {
  id: 1,
  login: "admin",
  nome: "Administração",
  perfil: "ADMINISTRADOR",
  telas: ["painel", "usuarios", "auditoria", "configuracao"],
};

function abrir(usuario, endereco) {
  return render(
    <ContextoSessao.Provider value={{ usuario, conferindo: false, sair: () => {} }}>
      <MemoryRouter initialEntries={[endereco]}>
        <App />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

describe("o teclado", () => {
  it("o primeiro Tab da página chega em 'Pular para o conteúdo', que leva ao conteúdo", async () => {
    simularApi({});
    const usuario = userEvent.setup();
    abrir(ADMINISTRADOR, "/conta");

    await usuario.tab();

    const pular = screen.getByRole("link", { name: "Pular para o conteúdo" });
    expect(pular).toHaveFocus();
    expect(pular).toHaveAttribute("href", "#conteudo");
    // O destino existe e aceita o foco: é o `main`, que não é um controle.
    expect(screen.getByRole("main")).toHaveAttribute("id", "conteudo");
    expect(screen.getByRole("main")).toHaveAttribute("tabindex", "-1");
  });

  it("trocar de tela pelo menu leva o foco ao título da tela nova", async () => {
    simularApi({ "GET /api/usuarios": { corpo: [] } });
    const usuario = userEvent.setup();
    abrir(ADMINISTRADOR, "/conta");

    await usuario.click(
      within(screen.getByRole("navigation", { name: "Seções do sistema" })).getByRole("link", { name: "Usuários" }),
    );

    await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "Usuários" })).toHaveFocus());
  });

  it("mudar um filtro não tira o foco do campo: a consulta mudou, a tela não", async () => {
    simularApi({ "GET /api/usuarios": { corpo: [] } });
    const usuario = userEvent.setup();
    abrir(ADMINISTRADOR, "/usuarios");

    const busca = await screen.findByLabelText("Buscar por nome ou login");
    await usuario.type(busca, "ana");
    // A busca vai para o endereço depois de a digitação parar.
    await new Promise((r) => setTimeout(r, 400));

    expect(busca).toHaveFocus();
    expect(busca).toHaveValue("ana");
  });

  it("ao abrir a aplicação, o foco não é tomado: só a troca de tela o move", () => {
    simularApi({});
    abrir(ADMINISTRADOR, "/conta");

    expect(screen.getByRole("heading", { level: 1, name: "Minha conta" })).not.toHaveFocus();
  });
});

describe("a sessão que termina com a tela aberta", () => {
  function comProvedor(endereco) {
    return render(
      <MemoryRouter initialEntries={[endereco]}>
        <ProvedorDeSessao>
          <App />
        </ProvedorDeSessao>
      </MemoryRouter>,
    );
  }

  it("leva ao login dizendo que a sessão terminou, e depois de entrar volta para onde a pessoa estava", async () => {
    let dentro = true;
    simularApi({
      "GET /api/sessao/atual": () => (dentro ? { corpo: ADMINISTRADOR } : { status: 401, corpo: {} }),
      // A sessão expirou no servidor: a próxima requisição é recusada.
      "POST /api/sessao/senha": { status: 401, corpo: { detail: "Sessão inválida ou expirada." } },
      "POST /api/sessao": { status: 201, corpo: { usuario: ADMINISTRADOR } },
    });
    const usuario = userEvent.setup();
    comProvedor("/conta");

    await usuario.type(await screen.findByLabelText(/^Senha atual/), "senha-de-agora");
    await usuario.type(screen.getByLabelText(/^Senha nova \*/), "senha-nova-bem-longa");
    await usuario.type(screen.getByLabelText(/^Senha nova, de novo/), "senha-nova-bem-longa");
    dentro = false;
    await usuario.click(screen.getByRole("button", { name: "Trocar a senha" }));

    const aviso = await screen.findByRole("status");
    expect(aviso).toHaveTextContent("A sua sessão terminou.");
    expect(aviso).toHaveTextContent("Entre de novo para continuar de onde parou.");

    await usuario.type(screen.getByLabelText("Login"), "admin");
    await usuario.type(screen.getByLabelText("Senha"), "senha-de-agora");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    // De volta à tela em que estava, e não ao painel.
    expect(await screen.findByRole("heading", { level: 1, name: "Minha conta" })).toBeInTheDocument();
  });

  it("quem ainda não entrou não vê o aviso: o 401 da primeira conferência não é sessão terminada", async () => {
    simularApi({ "GET /api/sessao/atual": { status: 401, corpo: {} } });
    comProvedor("/conta");

    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByText("A sua sessão terminou.")).not.toBeInTheDocument();
  });

  it("sair de propósito não é sessão terminada", async () => {
    simularApi({
      "GET /api/sessao/atual": { corpo: ADMINISTRADOR },
      "DELETE /api/sessao": { status: 204 },
    });
    const usuario = userEvent.setup();
    comProvedor("/conta");

    await usuario.click(await screen.findByRole("button", { name: "Encerrar sessão" }));

    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByText("A sua sessão terminou.")).not.toBeInTheDocument();
  });
});
