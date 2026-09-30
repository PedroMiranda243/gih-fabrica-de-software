import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import App from "../App";
import { violacoesDaAplicacao } from "../testes/acessibilidade";

/**
 * O endereço que não existe — H79.
 *
 * Até a Sprint 06 ele ia para o painel sem aviso. Aqui a aplicação inteira
 * roda, com a casca e as rotas de verdade, e o endereço inválido tem de dizer o
 * que aconteceu, manter o menu e oferecer a volta.
 */
function sessao(usuario) {
  return { usuario, conferindo: false, sair: () => {} };
}

const GESTORA = {
  nome: "Gestora",
  perfil: "GESTOR",
  telas: ["painel", "importar", "historico_importacoes", "parceiros"],
};

function abrir(caminho, usuario = GESTORA) {
  render(
    <ContextoSessao.Provider value={sessao(usuario)}>
      <MemoryRouter initialEntries={[caminho]}>
        <App />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

describe("endereço que não leva a tela nenhuma", () => {
  it("diz que a página não existe, mostra o endereço pedido e oferece a volta", () => {
    abrir("/relatorios/antigos?periodo=3");

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Página não encontrada");
    expect(screen.getByText("Este endereço não leva a nenhuma tela")).toBeInTheDocument();
    expect(screen.getByText(/Não existe tela em \/relatorios\/antigos\?periodo=3\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para o início" })).toHaveAttribute("href", "/");
  });

  it("não cai mais no painel sem aviso — e o menu continua ali", () => {
    abrir("/pagina-que-nao-existe");

    expect(screen.queryByRole("heading", { level: 1, name: "Painel" })).toBeNull();
    expect(screen.getByRole("navigation", { name: "Seções do sistema" })).toBeInTheDocument();
    expect(document.title).toBe("Página não encontrada · GIH");
  });

  it("sem sessão, o portão leva à entrada antes, como em qualquer tela", () => {
    abrir("/pagina-que-nao-existe", null);

    expect(screen.getByLabelText("Login")).toBeInTheDocument();
    expect(screen.queryByText("Este endereço não leva a nenhuma tela")).toBeNull();
  });

  it("a página inteira, com a casca, passa pela conferência de acessibilidade", async () => {
    abrir("/pagina-que-nao-existe");

    expect(await violacoesDaAplicacao(document.body)).toEqual([]);
  });
});
