import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra, endereco } from "../testes/montar";

const GESTORA = () => amostra("GET_api_usuarios_usuario_id");
const ROTAS = (extra = {}) => ({
  "GET /api/usuarios/:id": { corpo: GESTORA() },
  "GET /api/usuarios/parceiros": { corpo: amostra("GET_api_usuarios_parceiros") },
  ...extra,
});

/* RF03 (cadastrar, editar, desativar), RF04 (um perfil por conta), RF54
   (redefinir a senha de outro) e RF56 (achar o parceiro da conta Parceiro). */
describe("a conta de um usuário", () => {
  it("cria a conta com login, nome, senha inicial e um perfil (RF03, RF04)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/usuarios/novo", {
      perfil: "ADMINISTRADOR",
      rotas: ROTAS({ "POST /api/usuarios": { status: 201, corpo: { ...GESTORA(), id: 9, login: "nova.gestora", nome: "Nova Gestora" } } }),
    });

    await usuario.type(await screen.findByLabelText(/^Login/), "nova.gestora");
    await usuario.type(screen.getByLabelText(/^Nome/), "Nova Gestora");
    await usuario.type(screen.getByLabelText(/^Senha inicial/), "forte-e-longa-123");
    await usuario.selectOptions(screen.getByLabelText(/^Perfil/), "GESTOR");
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(corpoDe("POST /api/usuarios")).toEqual({ login: "nova.gestora", nome: "Nova Gestora", senha: "forte-e-longa-123", perfil: "GESTOR", parceiro_id: null });
    await waitFor(() => expect(endereco()).toBe("/usuarios/9"));
    expect(await screen.findByText("Usuário criado. Nova Gestora já pode entrar com o login nova.gestora.")).toBeInTheDocument();
  });

  it("a conta Parceiro pede o parceiro dela, achado pelo nome — e a busca mostra só o nome (RF56)", async () => {
    const usuario = userEvent.setup();
    const { chamadas, corpoDe } = abrir("/usuarios/novo", {
      perfil: "ADMINISTRADOR",
      rotas: ROTAS({ "POST /api/usuarios": { status: 201, corpo: { ...GESTORA(), id: 10, perfil: "PARCEIRO", parceiro_id: 246 } } }),
    });

    await usuario.selectOptions(await screen.findByLabelText(/^Perfil/), "PARCEIRO");
    await usuario.type(screen.getByLabelText("Buscar pelo nome do parceiro"), "Ponto");
    await usuario.click(await screen.findByRole("button", { name: "Ponto Azul 2" }));
    expect(screen.getByText(/A conta vê só o desempenho de/)).toHaveTextContent("Ponto Azul 2");

    await usuario.type(screen.getByLabelText(/^Login/), "ponto.azul");
    await usuario.type(screen.getByLabelText(/^Nome/), "Dono do Ponto Azul");
    await usuario.type(screen.getByLabelText(/^Senha inicial/), "forte-e-longa-123");
    await usuario.click(screen.getByRole("button", { name: "Criar usuário" }));

    expect(chamadas().some((c) => c.startsWith("GET /api/usuarios/parceiros") && c.includes("busca=Ponto"))).toBe(true);
    await waitFor(() => expect(corpoDe("POST /api/usuarios")).toMatchObject({ perfil: "PARCEIRO", parceiro_id: 246 }));
  });

  it("muda o perfil mandando só o que mudou (RF04)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/usuarios/3", {
      perfil: "ADMINISTRADOR",
      rotas: ROTAS({ "PATCH /api/usuarios/:id": { corpo: { ...GESTORA(), perfil: "ANALISTA" } } }),
    });

    await usuario.selectOptions(await screen.findByLabelText(/^Perfil/), "ANALISTA");
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText(/Alterações salvas\./)).toBeInTheDocument();
    expect(corpoDe("PATCH /api/usuarios/3")).toEqual({ perfil: "ANALISTA" });
  });

  it("redefine a senha de outra pessoa, com confirmação, sem a senha voltar na tela (RF54)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/usuarios/3", { perfil: "ADMINISTRADOR", rotas: ROTAS({ "POST /api/usuarios/:id/senha": { status: 204 } }) });

    await usuario.type(await screen.findByLabelText(/^Senha nova/), "outra-forte-456");
    await usuario.click(screen.getByRole("button", { name: "Redefinir a senha" }));
    expect(screen.getByText(/Redefinir a senha de Gestora do Laboratório\?/)).toBeInTheDocument();
    await usuario.click(screen.getAllByRole("button", { name: "Redefinir a senha" }).at(-1));

    expect(await screen.findByText(/Senha redefinida\. A senha não volta na resposta/)).toBeInTheDocument();
    expect(corpoDe("POST /api/usuarios/3/senha")).toEqual({ senha_nova: "outra-forte-456" });
  });

  it("na própria conta, a senha se troca em Minha conta, que pede a atual", async () => {
    const admin = amostra("sessao_de_cada_perfil").ADMINISTRADOR;
    abrir(`/usuarios/${admin.id}`, { perfil: "ADMINISTRADOR", rotas: ROTAS({ "GET /api/usuarios/:id": { corpo: { ...admin, parceiro: null } } }) });

    expect(await screen.findByText(/Esta é a sua conta: a sua senha se troca em/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Minha conta" })).toHaveAttribute("href", "/conta");
    expect(screen.queryByLabelText(/^Senha nova/)).not.toBeInTheDocument();
  });

  it("desativa com confirmação, que diz o que acontece com as sessões (RF03)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/usuarios/3", { perfil: "ADMINISTRADOR", rotas: ROTAS({ "PATCH /api/usuarios/:id": { corpo: { ...GESTORA(), ativo: false } } }) });

    await usuario.click(await screen.findByRole("button", { name: "Desativar" }));
    expect(screen.getByText("Desativar a conta de Gestora do Laboratório? As sessões abertas são encerradas agora.")).toBeInTheDocument();
    await usuario.click(screen.getAllByRole("button", { name: "Desativar" }).at(-1));

    await waitFor(() => expect(corpoDe("PATCH /api/usuarios/3")).toEqual({ ativo: false }));
  });
});
