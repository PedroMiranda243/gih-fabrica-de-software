import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

/* O jsdom não implementa `matchMedia`. Sem isto o hook de tema quebraria em
   todo teste que renderiza a casca. */
if (!window.matchMedia) {
  window.matchMedia = () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  });
}

/**
 * Responde às chamadas da API a partir de uma tabela de rotas.
 *
 * Simula no nível do `fetch`, e não do módulo `cliente.js`: assim o teste passa
 * pelo mesmo caminho que a aplicação — credenciais, tratamento de 401, leitura
 * do erro — em vez de pular exatamente a parte que costuma quebrar.
 */
export function simularApi(rotas) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url, opcoes = {}) => {
    const metodo = opcoes.method ?? "GET";
    const caminho = String(url).split("?")[0];
    const chave = `${metodo} ${caminho}`;
    const resposta = rotas[chave];

    if (!resposta) {
      return new Response(JSON.stringify({ detail: `rota não simulada: ${chave}` }), {
        status: 404,
      });
    }

    const { status = 200, corpo = null } = typeof resposta === "function" ? resposta(url, opcoes) : resposta;
    return new Response(status === 204 ? null : JSON.stringify(corpo), { status });
  });
}
