import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Usuarios from "./Usuarios";

const USUARIOS = [
  { id: 1, login: "admin", nome: "Administração", perfil: "ADMINISTRADOR", ativo: true, parceiro_id: null, criado_em: "2026-09-01T10:00:00Z" },
  { id: 2, login: "antiga", nome: "Conta Antiga", perfil: "ANALISTA", ativo: false, parceiro_id: null, criado_em: "2026-09-02T10:00:00Z" },
];

function renderizar(endereco = "/usuarios") {
  return render(
    <MemoryRouter initialEntries={[endereco]}>
      <Usuarios />
    </MemoryRouter>,
  );
}

describe("lista de usuários", () => {
  it("mostra nome, login, perfil e situação — e os desativados continuam na lista", async () => {
    simularApi({ "GET /api/usuarios": { corpo: USUARIOS } });
    renderizar();

    const tabela = await screen.findByRole("table");
    const [, primeira, segunda] = within(tabela).getAllByRole("row");
    expect(primeira).toHaveTextContent("Administração");
    expect(primeira).toHaveTextContent("Administrador");
    expect(segunda).toHaveTextContent("Desativado");
    expect(within(segunda).getByRole("link", { name: "Conta Antiga" })).toHaveAttribute("href", "/usuarios/2");
  });

  it("o filtro vai para o servidor pelo endereço", async () => {
    const pedidos = [];
    simularApi({
      "GET /api/usuarios": (url) => {
        pedidos.push(String(url));
        return { corpo: USUARIOS.slice(1) };
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("table");

    await usuario.selectOptions(screen.getByLabelText("Situação"), "false");

    await screen.findByText("1 encontrados");
    expect(pedidos.at(-1)).toContain("ativo=false");
  });

  it("recorte sem ninguém diz o que fazer", async () => {
    simularApi({ "GET /api/usuarios": { corpo: [] } });
    renderizar("/usuarios?perfil=PARCEIRO");

    expect(await screen.findByText("Nenhum usuário neste recorte")).toBeInTheDocument();
  });

  it("abre nos ativos, e 'Todas' tira o filtro sem voltar ao padrão", async () => {
    const pedidos = [];
    simularApi({
      "GET /api/usuarios": (url) => {
        pedidos.push(String(url));
        return { corpo: USUARIOS };
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("table");
    expect(pedidos.at(-1)).toContain("ativo=true");

    await usuario.selectOptions(screen.getByLabelText("Situação"), "todas");

    await screen.findByText("2 encontrados");
    expect(pedidos.at(-1)).not.toContain("ativo=");
    expect(screen.getByLabelText("Situação")).toHaveValue("todas");
  });
});
