import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra, endereco, rotasDoPainel } from "../testes/montar";

/* O endereço que não existe: diz qual foi pedido e oferece o caminho de volta,
   sem redirecionar em silêncio (CT-N07 do docs/12). */
describe("a página de endereço inexistente", () => {
  it("mostra o endereço pedido, com o título da página", async () => {
    const { chamadas } = abrir("/relatorio-que-nao-existe");

    expect(await screen.findByRole("heading", { level: 1, name: "Página não encontrada" })).toBeInTheDocument();
    expect(screen.getByText("/relatorio-que-nao-existe", { selector: "code" })).toBeInTheDocument();
    expect(chamadas().filter((c) => !c.startsWith("GET /api/sessao"))).toEqual([]);
  });

  it("'Ir para o início' leva ao painel", async () => {
    const usuario = userEvent.setup();
    abrir("/relatorio-que-nao-existe", { rotas: rotasDoPainel() });

    await usuario.click(await screen.findByRole("link", { name: "Ir para o início" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Painel" })).toBeInTheDocument();
    expect(endereco()).toBe("/");
  });

  it("um endereço dentro de uma área que existe também não redireciona", async () => {
    abrir("/parceiros/novo/coisa", { rotas: { "GET /api/parceiros": { corpo: amostra("GET_api_parceiros") } } });

    expect(await screen.findByRole("heading", { level: 1, name: "Página não encontrada" })).toBeInTheDocument();
    expect(screen.getByText("/parceiros/novo/coisa", { selector: "code" })).toBeInTheDocument();
  });
});
