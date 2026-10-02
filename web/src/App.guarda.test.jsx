import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "./api/contextoSessao";
import App from "./App";
import { simularApi } from "./testes/preparar";

/**
 * A guarda das rotas pelo perfil — H94.
 *
 * As telas de cada perfil são as que o servidor manda na sessão. O que se
 * confere aqui é a interface: o endereço de uma tela que o perfil não tem
 * mostra a página "Sem acesso", **sem pedir nada à API**; e o que o menu
 * oferece, o endereço abre. A recusa de verdade é da API, e tem o teste dela.
 */
const ANALISTA = {
  nome: "Ana de Exemplo",
  perfil: "ANALISTA",
  telas: ["painel", "importar", "historico_importacoes", "parceiros", "campanha", "execucoes", "execucao",
    "mensagens", "aprovacao", "relatorios", "assistente"],
};
const ADMINISTRADOR = {
  nome: "Administração",
  perfil: "ADMINISTRADOR",
  telas: ["painel", "historico_importacoes", "usuarios", "auditoria", "configuracao", "modelo", "execucoes",
    "benchmark", "relatorio_operacoes"],
};
const PARCEIRO = { nome: "Comércio do Vale", perfil: "PARCEIRO", telas: ["meu_desempenho"] };

function abrir(usuario, endereco) {
  const espia = simularApi({});
  render(
    <ContextoSessao.Provider value={{ usuario, conferindo: false, sair: () => {} }}>
      <MemoryRouter initialEntries={[endereco]}>
        <App />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
  return espia;
}

const semAcesso = () => screen.queryByText("O seu perfil não abre esta tela");

describe("a guarda das rotas pelo perfil", () => {
  it("a tela que o perfil não tem diz isso, com o perfil e a volta, e não pede nada à API", async () => {
    const espia = abrir(ANALISTA, "/auditoria");

    const pagina = screen.getByRole("region", { name: "Sem acesso" });
    expect(pagina).toHaveTextContent("O perfil Analista não tem acesso a /auditoria");
    expect(within(pagina).getByRole("link", { name: "Ir para o início" })).toHaveAttribute("href", "/");
    // O menu continua ao lado, com o que a pessoa abre.
    expect(screen.getByRole("navigation", { name: "Seções do sistema" })).toHaveTextContent("Parceiros");
    await waitFor(() => expect(document.title).toBe("Sem acesso · Auditoria · GIH"));
    expect(espia).not.toHaveBeenCalled();
  });

  it.each([
    ["o analista", ANALISTA, "/usuarios"],
    ["o analista", ANALISTA, "/usuarios/7"],
    ["o analista", ANALISTA, "/configuracao"],
    ["o analista", ANALISTA, "/relatorios/operacoes"],
    ["o analista", ANALISTA, "/modelo"],
    ["o administrador", ADMINISTRADOR, "/parceiros"],
    ["o administrador", ADMINISTRADOR, "/campanha"],
    ["o administrador", ADMINISTRADOR, "/relatorios/risco"],
    ["o parceiro", PARCEIRO, "/parceiros/3"],
    ["o parceiro", PARCEIRO, "/execucoes"],
  ])("%s não abre %s", (_quem, usuario, endereco) => {
    const espia = abrir(usuario, endereco);

    expect(semAcesso()).toBeInTheDocument();
    expect(espia).not.toHaveBeenCalled();
  });

  it("o administrador tem o histórico das execuções, mas não o plano de uma delas (RF34)", () => {
    abrir(ADMINISTRADOR, "/execucoes/12");
    expect(semAcesso()).toBeInTheDocument();
  });

  it.each([
    ["o administrador", ADMINISTRADOR, "/execucoes"],
    ["o administrador", ADMINISTRADOR, "/importacao"],
    ["o analista", ANALISTA, "/relatorios/desempenho"],
    ["o parceiro", PARCEIRO, "/meu-desempenho"],
    ["o parceiro", PARCEIRO, "/"],
  ])("%s abre %s", (_quem, usuario, endereco) => {
    abrir(usuario, endereco);
    expect(semAcesso()).not.toBeInTheDocument();
  });

  it("a Minha conta é de todos os perfis", () => {
    abrir(PARCEIRO, "/conta");

    expect(semAcesso()).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Trocar a senha" })).toBeInTheDocument();
  });

  it("a Ajuda é de todos os perfis, e a do parceiro não pede nada à API", () => {
    const espia = abrir(PARCEIRO, "/ajuda");

    expect(semAcesso()).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Ajuda" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "O seu portal" })).toBeInTheDocument();
    expect(espia).not.toHaveBeenCalled();
  });

  it.each([
    ["do analista", ANALISTA],
    ["do administrador", ADMINISTRADOR],
    ["do parceiro", PARCEIRO],
  ])("todo item do menu %s leva a uma tela que ele abre", (_de, usuario) => {
    abrir(usuario, "/conta");
    const enderecos = within(screen.getByRole("navigation", { name: "Seções do sistema" }))
      .getAllByRole("link")
      .map((a) => a.getAttribute("href"));
    expect(enderecos.length).toBeGreaterThan(0);

    for (const endereco of enderecos) {
      document.body.innerHTML = "";
      abrir(usuario, endereco);
      expect(semAcesso(), endereco).not.toBeInTheDocument();
    }
  });

  it("sessão sem a lista de telas deixa a API responder, em vez de adivinhar", () => {
    abrir({ nome: "Sessão Antiga", perfil: "GESTOR" }, "/auditoria");
    expect(semAcesso()).not.toBeInTheDocument();
  });
});
