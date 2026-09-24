import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { simularApi } from "../testes/preparar";
import Usuario from "./Usuario";

const EU = { id: 1, login: "admin", nome: "Administração", perfil: "ADMINISTRADOR", ativo: true };
const OUTRA = {
  id: 2,
  login: "gestora",
  nome: "Gestora de Exemplo",
  perfil: "GESTOR",
  ativo: true,
  parceiro_id: null,
  criado_em: "2026-09-02T10:00:00Z",
};

function renderizar(endereco) {
  return render(
    <ContextoSessao.Provider value={{ usuario: EU }}>
      <MemoryRouter initialEntries={[endereco]}>
        <Routes>
          <Route path="/usuarios/novo" element={<Usuario />} />
          <Route path="/usuarios/:id" element={<Usuario />} />
        </Routes>
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

async function preencherNovo(usuario, { login = "nova.pessoa", nome = "Nova Pessoa", senha = "senha-bem-longa" } = {}) {
  await usuario.type(screen.getByLabelText(/^Login/), login);
  await usuario.type(screen.getByLabelText(/^Nome/), nome);
  await usuario.type(screen.getByLabelText(/^Senha inicial/), senha);
}

describe("conta de usuário", () => {
  it("criar leva à conta criada, com a confirmação", async () => {
    simularApi({
      "POST /api/usuarios": { status: 201, corpo: { ...OUTRA, id: 7, login: "nova.pessoa", nome: "Nova Pessoa" } },
      "GET /api/usuarios/7": { corpo: { ...OUTRA, id: 7, login: "nova.pessoa", nome: "Nova Pessoa" } },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario);
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Nova Pessoa já pode entrar com o login nova.pessoa",
    );
    expect(await screen.findByRole("heading", { name: "Situação" })).toBeInTheDocument();
  });

  it("o perfil Parceiro não é oferecido, e a tela diz por quê", () => {
    renderizar("/usuarios/novo");

    const perfis = within(screen.getByLabelText(/^Perfil/)).getAllByRole("option").map((o) => o.textContent);
    expect(perfis).toEqual(["Administrador", "Gestor", "Analista"]);
    expect(screen.getByText(/depende do portal do parceiro/)).toBeInTheDocument();
  });

  it("login repetido aponta a conta que já o usa", async () => {
    simularApi({
      "POST /api/usuarios": {
        status: 409,
        corpo: {
          detail: {
            erro: "Já existe um usuário com o login 'antiga'.",
            ajuda: "Escolha outro login. Se a conta é da mesma pessoa e está desativada, reative-a em vez de criar outra.",
            existente: { id: 2, login: "antiga", nome: "Conta Antiga", ativo: false },
          },
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario, { login: "antiga" });
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("reative-a");
    expect(within(alerta).getByRole("link", { name: "Abrir a conta de Conta Antiga (desativada)" })).toHaveAttribute(
      "href",
      "/usuarios/2",
    );
  });

  it("senha fraca aparece embaixo do campo, com o foco nele", async () => {
    simularApi({
      "POST /api/usuarios": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "senha", mensagem: "A senha precisa ter pelo menos 12 caracteres." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/novo");

    await preencherNovo(usuario, { senha: "curta" });
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(await screen.findByText("A senha precisa ter pelo menos 12 caracteres.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Senha inicial/)).toHaveFocus();
  });

  it("trocar o perfil manda só o que mudou", async () => {
    const enviados = [];
    simularApi({
      "GET /api/usuarios/2": { corpo: OUTRA },
      "PATCH /api/usuarios/2": (_url, opcoes) => {
        enviados.push(JSON.parse(opcoes.body));
        return { corpo: { ...OUTRA, perfil: "ANALISTA" } };
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/2");

    await usuario.selectOptions(await screen.findByLabelText(/^Perfil/), "ANALISTA");
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByRole("status")).toHaveTextContent("O perfil novo vale já");
    expect(enviados[0]).toEqual({ nome: "Gestora de Exemplo", perfil: "ANALISTA" });
  });

  it("o último administrador não cai, e a recusa aparece na própria seção", async () => {
    simularApi({
      "GET /api/usuarios/1": { corpo: { ...OUTRA, ...EU } },
      "PATCH /api/usuarios/1": {
        status: 409,
        corpo: {
          detail: {
            erro: "Este é o último administrador ativo.",
            ajuda: "Sem ele, ninguém mais conseguiria gerenciar usuários. Promova outro usuário a Administrador antes.",
          },
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar("/usuarios/1");

    await usuario.click(await screen.findByRole("button", { name: "Desativar" }));
    // A própria conta: a confirmação avisa que a sessão cai junto.
    const confirmacao = screen.getByRole("group", { name: "Confirmação" });
    expect(confirmacao).toHaveTextContent("Esta é a sua conta");
    await usuario.click(within(confirmacao).getByRole("button", { name: "Desativar" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Este é o último administrador ativo.");
    expect(alerta).toHaveTextContent("Promova outro usuário");
  });

  it("conta inexistente oferece a volta para a lista", async () => {
    simularApi({ "GET /api/usuarios/99": { status: 404, corpo: { detail: "Usuário não encontrado." } } });
    renderizar("/usuarios/99");

    expect(await screen.findByText("Usuário não encontrado")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para os usuários" })).toHaveAttribute("href", "/usuarios");
  });
});
