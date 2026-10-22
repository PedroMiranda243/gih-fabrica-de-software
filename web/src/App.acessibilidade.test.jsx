import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { violacoesDaAplicacao } from "./testes/acessibilidade";
import { abrir, amostra, rotasDoPainel } from "./testes/montar";

/*
 * A aplicação inteira, com a casca, conferida pelo axe com as regras da página
 * — o `main`, o título de nível 1, o conteúdo fora de região, os nomes únicos
 * das regiões. A conferência de todo teste as desliga, porque a página
 * renderizada sozinha não tem a casca; aqui ela tem. Foi a falta disto que
 * deixou passar as regiões de nome repetido (landmark-unique) que o laboratório
 * pegou no navegador.
 */
const ENTRADAS = [
  ["GESTOR", "/", "Painel", rotasDoPainel()],
  ["ANALISTA", "/importacao", "Importação", { "GET /api/importacoes": { corpo: amostra("GET_api_importacoes") } }],
  [
    "ADMINISTRADOR",
    "/usuarios",
    "Usuários",
    { "GET /api/usuarios": { corpo: amostra("GET_api_usuarios") } },
  ],
  ["PARCEIRO", "/meu-desempenho", "Meu desempenho", { "GET /api/meu-desempenho": { corpo: amostra("GET_api_meu_desempenho") } }],
];

describe("a aplicação com a casca, pelo axe", () => {
  it.each(ENTRADAS)("o %s, em %s, sem violação", async (perfil, rota, titulo, rotas) => {
    abrir(rota, { perfil, rotas });
    expect(await screen.findByRole("heading", { level: 1, name: titulo })).toBeInTheDocument();
    await screen.findByRole("main");
    expect(await violacoesDaAplicacao(document.body)).toEqual([]);
  });

  it("a entrada, sem sessão, sem violação", async () => {
    abrir("/entrar", { perfil: null });
    await screen.findByRole("button", { name: "Entrar" });
    expect(await violacoesDaAplicacao(document.body)).toEqual([]);
  });
});
