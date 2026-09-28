import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "./api/contextoSessao";
import App from "./App";
import { violacoesDaAplicacao } from "./testes/acessibilidade";
import { simularApi } from "./testes/preparar";

/**
 * A aplicação inteira, com a casca — H76.
 *
 * A conferência de todo teste roda sobre a página sozinha, sem as regras que
 * dependem da página inteira: um `main` só, um título de nível 1, todo conteúdo
 * dentro de uma região. Aqui elas valem, com a casca em volta de uma página e na
 * tela de entrada, que não tem casca.
 */
function sessao(usuario) {
  return { usuario, conferindo: false, sair: () => {} };
}

const GESTORA = {
  nome: "Gestora",
  perfil: "GESTOR",
  telas: ["painel", "importar", "historico_importacoes", "parceiros", "assistente", "campanha", "mensagens"],
};

describe("a aplicação inteira", () => {
  it("a casca com uma página tem um main, um título de nível 1 e tudo dentro de regiões", async () => {
    simularApi({
      "GET /api/assistente": {
        corpo: {
          assistente: { disponivel: true, modelo: "qwen2.5:7b", motivo: null },
          exemplos: [
            { tipo: "resumo_do_periodo", descricao: "O resumo da rede.", exemplo: "Como foi a rede?" },
          ],
          tamanho_maximo: 1000,
        },
      },
    });
    render(
      <ContextoSessao.Provider value={sessao(GESTORA)}>
        <MemoryRouter initialEntries={["/assistente"]}>
          <App />
        </MemoryRouter>
      </ContextoSessao.Provider>,
    );
    await screen.findByRole("heading", { name: "Pergunte sobre os dados" });

    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Assistente");
    expect(await violacoesDaAplicacao(document.body)).toEqual([]);
  });

  it("a tela de entrada, sem casca, também", async () => {
    render(
      <ContextoSessao.Provider value={sessao(null)}>
        <MemoryRouter initialEntries={["/entrar"]}>
          <App />
        </MemoryRouter>
      </ContextoSessao.Provider>,
    );
    await screen.findByLabelText(/login/i);

    expect(await violacoesDaAplicacao(document.body)).toEqual([]);
  });
});
