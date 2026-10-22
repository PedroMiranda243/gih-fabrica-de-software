import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra, endereco } from "../testes/montar";

const ROTAS = () => ({
  "GET /api/parceiros": { corpo: amostra("GET_api_parceiros") },
  "GET /api/categorias": { corpo: amostra("GET_api_categorias") },
});

const ultimaLista = (chamadas) => chamadas().filter((c) => c.startsWith("GET /api/parceiros?")).at(-1) ?? "";

/* RF23 (filtrar e ordenar), RF24 (buscar por nome) e RF25 (exportar a visão filtrada). */
describe("a lista de parceiros", () => {
  it("lista os parceiros da API, com o segmento por nome e a estimativa marcada", async () => {
    abrir("/parceiros", { rotas: ROTAS() });

    const primeiro = amostra("GET_api_parceiros").itens[0];
    expect(await screen.findByText(primeiro.nome)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tabela: Parceiros" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Risco de queda/ })).toBeInTheDocument();
  });

  it("busca por nome com correspondência parcial, depois que a digitação para (RF24)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/parceiros", { rotas: ROTAS() });

    await usuario.type(await screen.findByLabelText("Buscar por nome"), "canti");

    await waitFor(() => expect(ultimaLista(chamadas)).toContain("busca=canti"));
    expect(endereco()).toContain("busca=canti");
  });

  it("filtra por segmento e categoria: o filtro vai para o endereço e para a API (RF23)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/parceiros", { rotas: ROTAS() });

    await usuario.selectOptions(await screen.findByLabelText("Segmento"), "EM_RISCO");
    await waitFor(() => expect(ultimaLista(chamadas)).toContain("segmento=EM_RISCO"));
    const categoria = amostra("GET_api_categorias")[0];
    await usuario.selectOptions(screen.getByLabelText("Categoria"), String(categoria.id));
    await waitFor(() => expect(ultimaLista(chamadas)).toContain(`categoria_id=${categoria.id}`));
    expect(endereco()).toContain("segmento=EM_RISCO");
  });

  it("ordena pela coluna: número do maior para o menor no primeiro clique (RF23)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/parceiros", { rotas: ROTAS() });

    await screen.findByText(amostra("GET_api_parceiros").itens[0].nome);
    await usuario.click(screen.getByRole("button", { name: /Faturamento/ }));

    await waitFor(() => expect(ultimaLista(chamadas)).toContain("ordenar_por=faturamento"));
    expect(ultimaLista(chamadas)).toContain("descendente=true");
    expect(screen.getByRole("columnheader", { name: /Faturamento/ })).toHaveAttribute("aria-sort", "descending");
  });

  it("exporta em CSV a visão filtrada, como link (RF25)", async () => {
    abrir("/parceiros?segmento=TOP&ordenar_por=pedidos&descendente=true", { rotas: ROTAS() });

    const link = await screen.findByRole("link", { name: /Exportar CSV/ });
    expect(link.getAttribute("href")).toBe("/api/parceiros/exportacao.csv?segmento=TOP&ordenar_por=pedidos&descendente=true");
  });

  it("recorte sem resultado explica por quê", async () => {
    abrir("/parceiros?busca=zzz", { rotas: { ...ROTAS(), "GET /api/parceiros": { corpo: { itens: [], total: 0, pagina: 1, tamanho: 25 } } } });

    expect(await screen.findByText("Nenhum parceiro com esse recorte")).toBeInTheDocument();
  });

  it("'Novo parceiro' leva ao cadastro", async () => {
    abrir("/parceiros", { rotas: ROTAS() });

    expect(await screen.findByRole("link", { name: /Novo parceiro/ })).toHaveAttribute("href", "/parceiros/novo");
  });
});
