import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Auditoria from "./Auditoria";

const ACOES = [
  { acao: "LOGIN_FALHA", rotulo: "Entrada recusada" },
  { acao: "PERFIL_ALTERADO", rotulo: "Perfil de usuário alterado" },
];

const USUARIOS = [
  { id: 1, login: "chefia", nome: "Chefia", perfil: "ADMINISTRADOR", ativo: true },
  { id: 2, login: "ana", nome: "Ana", perfil: "ANALISTA", ativo: true },
];

const ALTERACAO = {
  id: 11,
  usuario_id: 1,
  autor: "Chefia",
  autor_login: "chefia",
  acao: "PERFIL_ALTERADO",
  rotulo: "Perfil de usuário alterado",
  resumo: "ana: de ANALISTA para GESTOR",
  detalhes: { alvo: 2, login: "ana", de: "ANALISTA", para: "GESTOR" },
  origem: "172.18.0.1",
  ocorrido_em: "2026-10-01T12:30:00Z",
};

const RECUSA = {
  id: 10,
  usuario_id: null,
  autor: null,
  autor_login: null,
  acao: "LOGIN_FALHA",
  rotulo: "Entrada recusada",
  resumo: "login tentado: fantasma",
  detalhes: { login: "fantasma" },
  origem: "172.18.0.1",
  ocorrido_em: "2026-10-01T12:00:00Z",
};

function pagina(itens, total = itens.length) {
  return { itens, total, pagina: 1, tamanho: 50 };
}

function rotas(extra = {}) {
  return {
    "GET /api/auditoria/acoes": { corpo: ACOES },
    "GET /api/usuarios": { corpo: USUARIOS },
    "GET /api/auditoria": { corpo: pagina([ALTERACAO, RECUSA]) },
    ...extra,
  };
}

function renderizar(endereco = "/auditoria") {
  return render(
    <MemoryRouter initialEntries={[endereco]}>
      <Auditoria />
    </MemoryRouter>,
  );
}

describe("trilha de auditoria", () => {
  it("mostra quando, quem, a ação em português e o que aconteceu", async () => {
    simularApi(rotas());
    renderizar();

    const tabela = await screen.findByRole("table");
    const [, primeira] = within(tabela).getAllByRole("row");
    expect(primeira).toHaveTextContent("Chefia");
    expect(primeira).toHaveTextContent("chefia");
    expect(primeira).toHaveTextContent("Perfil de usuário alterado");
    expect(primeira).toHaveTextContent("ana: de ANALISTA para GESTOR");
    expect(primeira).toHaveTextContent("172.18.0.1");
    // O código da ação não aparece: a frase vem da API.
    expect(primeira).not.toHaveTextContent("PERFIL_ALTERADO");
    expect(screen.getByText("2 registros")).toBeInTheDocument();
  });

  it("evento sem usuário diz isso, e o login tentado está no resumo", async () => {
    simularApi(rotas());
    renderizar();

    const tabela = await screen.findByRole("table");
    const segunda = within(tabela).getAllByRole("row")[2];
    expect(segunda).toHaveTextContent("sem usuário");
    expect(segunda).toHaveTextContent("login tentado: fantasma");
  });

  it("a linha abre o que foi gravado, para quem investiga", async () => {
    simularApi(rotas());
    const usuario = userEvent.setup();
    renderizar();

    const tabela = await screen.findByRole("table");
    const primeira = within(tabela).getAllByRole("row")[1];
    await usuario.click(within(primeira).getByText("O que foi gravado"));

    expect(within(primeira).getByText(/"para": "GESTOR"/)).toBeVisible();
  });

  it("os filtros e a busca vão para o servidor, e a página volta à primeira", async () => {
    const pedidos = [];
    simularApi(
      rotas({
        "GET /api/auditoria": (url) => {
          pedidos.push(String(url));
          return { corpo: pagina([ALTERACAO]) };
        },
      }),
    );
    const usuario = userEvent.setup();
    renderizar("/auditoria?pagina=3");
    await screen.findByRole("table");

    await usuario.selectOptions(await screen.findByLabelText("Ação"), "PERFIL_ALTERADO");
    await usuario.selectOptions(screen.getByLabelText("Quem fez"), "1");
    await usuario.type(screen.getByLabelText("Buscar na trilha"), "ana");

    await screen.findByText("1 registro");
    const ultimo = pedidos.at(-1);
    expect(ultimo).toContain("acao=PERFIL_ALTERADO");
    expect(ultimo).toContain("autor=1");
    expect(ultimo).toContain("busca=ana");
    expect(ultimo).toContain("pagina=1");
  });

  it("o filtro de ação oferece os rótulos que a API manda", async () => {
    simularApi(rotas());
    renderizar();

    const acao = await screen.findByLabelText("Ação");
    expect(await within(acao).findByRole("option", { name: "Entrada recusada" })).toHaveValue("LOGIN_FALHA");
    expect(within(acao).getByRole("option", { name: "Todas as ações" })).toHaveValue("");
  });

  it("o link de exportar leva exatamente o recorte da tela", async () => {
    simularApi(rotas());
    renderizar("/auditoria?acao=LOGIN_FALHA&de=2026-10-01&busca=fantasma");
    await screen.findByRole("table");

    const exportar = screen.getByRole("link", { name: "Exportar CSV" });
    const destino = new URL(exportar.getAttribute("href"), "http://local");
    expect(destino.pathname).toBe("/api/auditoria/exportacao.csv");
    expect(Object.fromEntries(destino.searchParams)).toEqual({
      acao: "LOGIN_FALHA",
      de: "2026-10-01",
      busca: "fantasma",
    });
  });

  it("recorte sem registro diz isso, em vez de mostrar tabela vazia", async () => {
    simularApi(rotas({ "GET /api/auditoria": { corpo: pagina([]) } }));
    renderizar("/auditoria?acao=LOGIN_FALHA");

    expect(await screen.findByText("Nenhum registro nesse recorte")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("a paginação diz onde se está e desabilita o que não dá para fazer", async () => {
    simularApi(rotas({ "GET /api/auditoria": { corpo: pagina([ALTERACAO, RECUSA], 120) } }));
    renderizar();
    await screen.findByRole("table");

    expect(screen.getByText("1–50 de 120")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Próxima" })).toBeEnabled();
  });

  it("o erro do servidor aparece com a ajuda que ele mandou", async () => {
    simularApi(
      rotas({
        "GET /api/auditoria": {
          status: 403,
          corpo: { detail: { erro: "Seu perfil não permite esta operação.", ajuda: "Fale com o administrador." } },
        },
      }),
    );
    renderizar();

    expect(await screen.findByText("Seu perfil não permite esta operação.")).toBeInTheDocument();
    expect(screen.getByText("Fale com o administrador.")).toBeInTheDocument();
  });
});
