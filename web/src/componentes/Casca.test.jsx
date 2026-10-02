import { fireEvent, render, screen, within } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import Casca from "./Casca";
import { useTituloDaAba } from "./tituloDaAba";

function menu(usuario) {
  render(
    <ContextoSessao.Provider value={{ usuario, sair: () => {} }}>
      <MemoryRouter>
        <Casca titulo="Painel" />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
  const trilho = screen.getByRole("navigation", { name: "Seções do sistema" });
  return within(trilho)
    .getAllByRole("link")
    .map((a) => a.textContent.trim());
}

describe("cabeçalho", () => {
  it("o nome de quem está usando leva à conta dele, em qualquer perfil (H92)", () => {
    menu({ nome: "Comércio do Vale", perfil: "PARCEIRO", telas: ["meu_desempenho"] });

    const conta = screen.getByRole("link", { name: "Minha conta: Comércio do Vale PARCEIRO" });
    expect(conta).toHaveAttribute("href", "/conta");
  });

  it("a ajuda fica no cabeçalho, em qualquer perfil, e não no menu (H95)", () => {
    const itens = menu({ nome: "Comércio do Vale", perfil: "PARCEIRO", telas: ["meu_desempenho"] });

    expect(screen.getByRole("link", { name: "Ajuda" })).toHaveAttribute("href", "/ajuda");
    expect(itens).not.toContain("Ajuda");
  });
});

describe("menu lateral", () => {
  it("os relatórios da rede ficam na Análise, e o de operações, ao lado da Auditoria (UC15)", () => {
    const daGestora = menu({
      nome: "Gestora",
      perfil: "GESTOR",
      telas: ["painel", "parceiros", "relatorios"],
    });
    expect(daGestora).toEqual(["Painel", "Parceiros", "Relatórios"]);
  });

  it("o Administrador não vê os relatórios da rede, e vê o de operações", () => {
    const doAdmin = menu({
      nome: "Admin",
      perfil: "ADMINISTRADOR",
      telas: ["painel", "usuarios", "auditoria", "relatorio_operacoes", "configuracao"],
    });
    expect(doAdmin).toEqual(["Painel", "Usuários", "Auditoria", "Operações", "Configuração"]);
  });

  it("o Administrador vê usuários e configuração, e não Parceiros, que a rota lhe recusa", () => {
    const itens = menu({
      nome: "Admin",
      perfil: "ADMINISTRADOR",
      telas: ["painel", "historico_importacoes", "usuarios", "configuracao"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Usuários", "Configuração"]);
  });

  it("quem importa vê as três telas de sempre", () => {
    const itens = menu({
      nome: "Gestora",
      perfil: "GESTOR",
      telas: ["painel", "importar", "historico_importacoes", "parceiros"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros"]);
  });

  it("o Gestor vê o modelo, que o UC07 lhe dá — com as telas que o servidor mandou", () => {
    const itens = menu({
      nome: "Gestora",
      perfil: "GESTOR",
      telas: ["painel", "importar", "historico_importacoes", "parceiros", "modelo"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros", "Modelo"]);
  });

  it("o Administrador vê as execuções do otimizador sem a Campanha (RF34, H58), depois do Modelo", () => {
    /* Na ordem do fluxo (H79): a previsão alimenta a otimização, e não o contrário. */
    const itens = menu({
      nome: "Admin",
      perfil: "ADMINISTRADOR",
      telas: ["painel", "historico_importacoes", "modelo", "execucoes", "usuarios", "configuracao"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Modelo", "Execuções", "Usuários", "Configuração"]);
  });

  it("o Analista vê as mensagens, que o UC10 lhe dá, depois das execuções (H60)", () => {
    const itens = menu({
      nome: "Analista",
      perfil: "ANALISTA",
      telas: ["painel", "importar", "historico_importacoes", "parceiros", "campanha", "execucoes", "mensagens"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros", "Campanha", "Execuções", "Mensagens"]);
  });

  it("a fila de aprovação aparece depois das mensagens, para quem a abre (H61)", () => {
    const itens = menu({
      nome: "Gestora",
      perfil: "GESTOR",
      telas: ["painel", "importar", "historico_importacoes", "parceiros", "mensagens", "aprovacao", "decidir_mensagens"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros", "Mensagens", "Aprovação"]);
  });

  it("o assistente fica junto das consultas, para quem o UC12 dá (H65)", () => {
    const itens = menu({
      nome: "Analista",
      perfil: "ANALISTA",
      telas: ["painel", "importar", "historico_importacoes", "parceiros", "assistente", "campanha"],
    });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros", "Assistente", "Campanha"]);
  });

  it("sessão de antes da atualização, sem telas, mantém o menu anterior", () => {
    /* Uma aba aberta durante a atualização não pode ficar com o trilho vazio. */
    const itens = menu({ nome: "Antiga", perfil: "GESTOR" });

    expect(itens).toEqual(["Painel", "Importação", "Parceiros"]);
  });
});

function comMenu(usuario) {
  render(
    <ContextoSessao.Provider value={{ usuario, sair: () => {} }}>
      <MemoryRouter>
        <Casca titulo="Painel" />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
  return screen.getByRole("navigation", { name: "Seções do sistema" });
}

const GESTORA = {
  nome: "Gestora",
  perfil: "GESTOR",
  telas: [
    "painel", "importar", "historico_importacoes", "parceiros", "assistente", "modelo",
    "campanha", "execucoes", "execucao", "benchmark", "mensagens", "aprovacao",
  ],
};

describe("o menu por módulo (H79)", () => {
  it("os grupos seguem o fluxo do produto, e cada um é uma região com o nome dele", () => {
    const trilho = comMenu(GESTORA);

    const grupos = within(trilho).getAllByRole("group").map((g) => g.getAttribute("aria-labelledby"));
    expect(grupos.map((id) => document.getElementById(id).textContent)).toEqual([
      "Análise",
      "Previsão",
      "Otimização",
      "Comunicação",
    ]);
    const otimizacao = within(trilho).getByRole("group", { name: "Otimização" });
    expect(within(otimizacao).getAllByRole("link").map((a) => a.textContent.trim())).toEqual([
      "Campanha",
      "Execuções",
      "Benchmark",
    ]);
  });

  it("grupo sem tela que o perfil abre não aparece — o Gestor não vê a Administração", () => {
    const trilho = comMenu(GESTORA);

    expect(within(trilho).queryByRole("group", { name: "Administração" })).toBeNull();
  });

  it("o Administrador vê a Administração por último, separada do resto", () => {
    const trilho = comMenu({
      nome: "Admin",
      perfil: "ADMINISTRADOR",
      telas: ["painel", "historico_importacoes", "modelo", "execucoes", "usuarios", "configuracao"],
    });

    const nomes = within(trilho).getAllByRole("group").map((g) => g.getAttribute("aria-labelledby"));
    expect(nomes.at(-1)).toBe("grupo-administracao");
    const administracao = within(trilho).getByRole("group", { name: "Administração" });
    expect(within(administracao).getAllByRole("link").map((a) => a.textContent.trim())).toEqual([
      "Usuários",
      "Configuração",
    ]);
  });

  it("a Auditoria entra na Administração, para quem o servidor a dá (UC14, H89)", () => {
    const trilho = comMenu({
      nome: "Admin",
      perfil: "ADMINISTRADOR",
      telas: ["painel", "usuarios", "auditoria", "configuracao"],
    });

    const administracao = within(trilho).getByRole("group", { name: "Administração" });
    expect(within(administracao).getAllByRole("link").map((a) => a.textContent.trim())).toEqual([
      "Usuários",
      "Auditoria",
      "Configuração",
    ]);
    expect(within(administracao).getByRole("link", { name: "Auditoria" })).toHaveAttribute(
      "href",
      "/auditoria",
    );
  });

  it("o Parceiro vê só o próprio desempenho, sem os módulos da rede (RF26)", () => {
    const trilho = comMenu({ nome: "Parceiro", perfil: "PARCEIRO", telas: ["meu_desempenho"] });

    expect(within(trilho).getAllByRole("group")).toHaveLength(1);
    expect(within(trilho).getAllByRole("link").map((a) => a.textContent.trim())).toEqual([
      "Meu desempenho",
    ]);
  });
});

function Detalhe() {
  useTituloDaAba("Ponto Azul 2");
  return <Link to="/parceiros">Parceiros</Link>;
}

function naRota(caminho) {
  render(
    <ContextoSessao.Provider value={{ usuario: GESTORA, sair: () => {} }}>
      <MemoryRouter initialEntries={[caminho]}>
        <Routes>
          <Route element={<Casca titulo="Parceiros" />}>
            <Route path="/parceiros" element={<p>A lista</p>} />
            <Route path="/parceiros/:id" element={<Detalhe />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

describe("o título da aba (H79)", () => {
  it("diz a tela e o produto, e não mais o mesmo nome em toda aba", () => {
    naRota("/parceiros");

    expect(document.title).toBe("Parceiros · GIH");
  });

  it("na tela de detalhe, o item aberto vem primeiro", () => {
    naRota("/parceiros/246");

    expect(document.title).toBe("Ponto Azul 2 · Parceiros · GIH");
  });

  it("de volta à lista, na mesma casca, o título volta a ser o da tela", () => {
    naRota("/parceiros/246");
    /* O link da página, e não o do menu, que também se chama Parceiros. */
    fireEvent.click(within(screen.getByRole("main")).getByRole("link", { name: "Parceiros" }));

    expect(screen.getByText("A lista")).toBeInTheDocument();
    expect(document.title).toBe("Parceiros · GIH");
  });
});
