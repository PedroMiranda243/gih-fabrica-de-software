import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Parceiros from "./Parceiros";

const PERIODO = { id: 2, data_inicio: "2026-03-09", data_fim: "2026-03-15" };

function parceiro(nome, extra = {}, desempenho = {}) {
  return {
    id: nome.length,
    nome,
    categoria: { id: 1, nome: "Padaria", ativa: true },
    origem_categoria: "MANUAL",
    status: "PROSPECCAO",
    contato: null,
    ativo: true,
    criado_em: "2026-03-01T10:00:00Z",
    ...extra,
    desempenho: {
      segmento: "EM_RISCO",
      faturamento: "1000.00",
      pedidos: 20,
      ticket_medio: "50.00",
      variacao_percentual: "-12.50",
      ...desempenho,
    },
  };
}

function pagina(itens, extra = {}) {
  return {
    itens,
    total: itens.length,
    pagina: 1,
    tamanho: 50,
    periodo: PERIODO,
    ...extra,
  };
}

/** Guarda as URLs que a tela pediu, para conferir o que ela mandou à API. */
function simular(corpo, chamadas = []) {
  simularApi({
    "GET /api/categorias": { corpo: [{ id: 1, nome: "Padaria", ativa: true }] },
    "GET /api/parceiros": (url) => {
      chamadas.push(String(url));
      return { corpo };
    },
  });
  return chamadas;
}

function renderizar() {
  return render(
    <MemoryRouter>
      <Parceiros />
    </MemoryRouter>,
  );
}

describe("Parceiros", () => {
  it("mostra o desempenho do período ao lado do cadastro", async () => {
    simular(pagina([parceiro("Casa da Praça")]));

    renderizar();

    const linha = (await screen.findByText("Casa da Praça")).closest("tr");
    expect(within(linha).getByText("R$ 1.000,00")).toBeVisible();
    expect(within(linha).getByText("R$ 50,00")).toBeVisible();
    expect(within(linha).getByText("-12,50%")).toBeVisible();
    expect(within(linha).getByText("Em risco")).toBeVisible();
  });

  it("o status comercial aparece com rótulo, e não com o valor interno", async () => {
    /* A tabela mostrava "PROSPECCAO", em caixa alta e sem acento, como se fosse
       texto para o usuário ler. */
    simular(pagina([parceiro("Casa da Praça")]));

    renderizar();

    const linha = (await screen.findByText("Casa da Praça")).closest("tr");
    expect(within(linha).getByText("Prospecção")).toBeVisible();
    expect(within(linha).queryByText("PROSPECCAO")).not.toBeInTheDocument();
  });

  it("parceiro sem desempenho mostra travessão, e não zero", async () => {
    simular(
      pagina([
        parceiro("Nunca Vendeu", {}, {
          segmento: null,
          faturamento: null,
          pedidos: null,
          ticket_medio: null,
          variacao_percentual: null,
        }),
      ]),
    );

    renderizar();

    const linha = (await screen.findByText("Nunca Vendeu")).closest("tr");
    expect(within(linha).getAllByText("—").length).toBeGreaterThan(0);
    expect(within(linha).queryByText("R$ 0,00")).not.toBeInTheDocument();
  });

  it("clicar numa coluna de número ordena do maior para o menor", async () => {
    /* Pedir dois cliques para ver quem fatura mais é ruído: é a primeira coisa
       que se quer ao clicar em "Faturamento". */
    const chamadas = simular(pagina([parceiro("Alfa")]));
    renderizar();
    await screen.findByText("Alfa");

    await userEvent.click(screen.getByRole("button", { name: /Faturamento/ }));

    await waitFor(() => {
      const ultima = chamadas.at(-1);
      expect(ultima).toContain("ordenar_por=faturamento");
      expect(ultima).toContain("descendente=true");
    });
  });

  it("clicar de novo na mesma coluna inverte o sentido", async () => {
    const chamadas = simular(pagina([parceiro("Alfa")]));
    renderizar();
    await screen.findByText("Alfa");

    await userEvent.click(screen.getByRole("button", { name: /Faturamento/ }));
    await waitFor(() => expect(chamadas.at(-1)).toContain("descendente=true"));
    await userEvent.click(screen.getByRole("button", { name: /Faturamento/ }));

    await waitFor(() => expect(chamadas.at(-1)).not.toContain("descendente=true"));
  });

  it("a coluna ordenada se anuncia para quem usa leitor de tela", async () => {
    /* A seta sozinha é informação visual, e não serve a quem não a vê. */
    simular(pagina([parceiro("Alfa")]));
    renderizar();
    await screen.findByText("Alfa");

    await userEvent.click(screen.getByRole("button", { name: /Pedidos/ }));

    await waitFor(() => {
      const cabecalho = screen.getByRole("button", { name: /Pedidos/ }).closest("th");
      expect(cabecalho).toHaveAttribute("aria-sort", "descending");
    });
  });

  it("filtrar por segmento manda o filtro para a API", async () => {
    const chamadas = simular(pagina([parceiro("Alfa")]));
    renderizar();
    await screen.findByText("Alfa");

    await userEvent.selectOptions(screen.getByLabelText("Segmento"), "EM_RISCO");

    await waitFor(() => expect(chamadas.at(-1)).toContain("segmento=EM_RISCO"));
  });

  it("mudar um filtro volta para a primeira página", async () => {
    /* Quem está na página 7 e filtra veria "nenhum parceiro", e concluiria que
       o filtro não encontrou nada — quando a página é que deixou de existir. */
    const chamadas = simular(pagina([parceiro("Alfa")], { total: 300 }));
    renderizar();
    await screen.findByText("Alfa");

    await userEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() => expect(chamadas.at(-1)).toContain("pagina=2"));
    await userEvent.selectOptions(screen.getByLabelText("Segmento"), "EM_RISCO");

    await waitFor(() => expect(chamadas.at(-1)).not.toContain("pagina=2"));
  });

  it("a paginação diz onde se está e desabilita o que não dá para fazer", async () => {
    simular(pagina([parceiro("Alfa")], { total: 120 }));

    renderizar();

    expect(await screen.findByText("1–50 de 120")).toBeVisible();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Próxima" })).toBeEnabled();
  });

  it("o link de exportar leva exatamente o recorte da tela", async () => {
    /* Exportar um recorte diferente do visível é pior que não exportar. */
    simular(pagina([parceiro("Alfa")]));
    renderizar();
    await screen.findByText("Alfa");

    await userEvent.selectOptions(screen.getByLabelText("Segmento"), "EM_RISCO");
    /* Entre um filtro e o próximo a tabela some, porque a resposta anterior
       deixou de valer. Clicar no cabeçalho antes de ela voltar procura um botão
       que não está na tela. */
    await screen.findByText("Alfa");
    await userEvent.click(screen.getByRole("button", { name: /Pedidos/ }));

    await waitFor(() => {
      const link = screen.getByRole("link", { name: "Exportar CSV" });
      expect(link).toHaveAttribute("href", expect.stringContaining("segmento=EM_RISCO"));
      expect(link).toHaveAttribute("href", expect.stringContaining("ordenar_por=pedidos"));
      expect(link).toHaveAttribute("href", expect.stringContaining("descendente=true"));
    });
  });

  it("base vazia leva à importação, em vez de mostrar tabela em branco", async () => {
    simular(pagina([], { total: 0, periodo: null }));

    renderizar();

    expect(await screen.findByText("Nenhum parceiro cadastrado ainda")).toBeVisible();
    expect(screen.getByRole("link", { name: "Importar um relatório" })).toHaveAttribute(
      "href",
      "/importacao",
    );
  });

  it("categoria só sugerida pelo nome aparece marcada", async () => {
    simular(pagina([parceiro("Pizzaria Bella", { origem_categoria: "INFERIDA" })]));
    renderizar();

    expect(await screen.findByText(/Padaria · sugerida/)).toBeInTheDocument();
  });
});

