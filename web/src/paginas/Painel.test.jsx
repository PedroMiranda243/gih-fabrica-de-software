import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Painel from "./Painel";

const PERIODO = { id: 2, data_inicio: "2026-03-09", data_fim: "2026-03-15" };
const ANTERIOR = { id: 1, data_inicio: "2026-03-02", data_fim: "2026-03-08" };

function renderizar() {
  return render(
    <MemoryRouter>
      <Painel />
    </MemoryRouter>,
  );
}

function indicadores(extra = {}) {
  return {
    periodo: PERIODO,
    periodo_anterior: ANTERIOR,
    faturamento: "3000.00",
    pedidos: 25,
    ticket_medio: "120.00",
    parceiros_ativos: 2,
    variacao: { faturamento: "50.00", pedidos: "-10.00", ticket_medio: null, parceiros_ativos: "0.00" },
    ...extra,
  };
}

const SERIE = {
  escopo: "rede",
  parceiro_id: null,
  parceiro_nome: null,
  pontos: [
    { periodo: ANTERIOR, faturamento: "2000.00", pedidos: 20, ticket_medio: "100.00" },
    { periodo: PERIODO, faturamento: "3000.00", pedidos: 25, ticket_medio: "120.00" },
  ],
};

const RANKING = {
  periodo: PERIODO,
  periodo_anterior: ANTERIOR,
  total: 2,
  pagina: 1,
  tamanho: 25,
  itens: [
    {
      parceiro_id: 1, nome: "Comércio Alfa", categoria: "Lanches", posicao: 1, posicao_anterior: 2,
      faturamento: "2000.00", pedidos: 20, ticket_medio: "100.00", variacao_percentual: "33.33",
      estreante: false,
    },
    {
      parceiro_id: 2, nome: "Comércio Novo", categoria: null, posicao: 2, posicao_anterior: null,
      faturamento: "1000.00", pedidos: 5, ticket_medio: "200.00", variacao_percentual: null,
      estreante: true,
    },
  ],
};

const SEGMENTOS = {
  periodo: PERIODO,
  total: 2,
  itens: [
    { segmento: "TOP", total: 1 },
    { segmento: "EM_RISCO", total: 1 },
  ],
};

const MOBILIDADE = {
  periodo: PERIODO,
  periodo_anterior: ANTERIOR,
  top_n: 15,
  entradas: [{ parceiro_id: 2, nome: "Comércio Novo", posicao: 2, posicao_anterior: null }],
  saidas: [{ parceiro_id: 3, nome: "Comércio Velho", posicao: null, posicao_anterior: 2 }],
};

/* A tela pede cinco respostas de uma vez. Simular três deixaria o `Promise.all`
   pendurado, e o teste reprovaria por tela vazia — dizendo "não achei o texto"
   sobre uma tela que nem chegou a renderizar. */
function respostas(extra = {}) {
  return {
    "GET /api/painel/indicadores": { corpo: indicadores() },
    "GET /api/painel/ranking": { corpo: RANKING },
    "GET /api/painel/series": { corpo: SERIE },
    "GET /api/painel/segmentos": { corpo: SEGMENTOS },
    "GET /api/painel/mobilidade": { corpo: MOBILIDADE },
    ...extra,
  };
}

describe("Painel", () => {
  it("base vazia leva à importação, em vez de mostrar tela em branco", async () => {
    /* UC05, A1 — tela vazia sem explicação é defeito (docs/09, seção 6). */
    simularApi(
      respostas({
        "GET /api/painel/indicadores": {
          corpo: indicadores({ periodo: null, periodo_anterior: null, variacao: null }),
        },
        "GET /api/painel/ranking": { corpo: { ...RANKING, periodo: null, itens: [], total: 0 } },
        "GET /api/painel/series": { corpo: { ...SERIE, pontos: [] } },
        "GET /api/painel/segmentos": { corpo: { periodo: null, total: 0, itens: [] } },
        "GET /api/painel/mobilidade": {
          corpo: { ...MOBILIDADE, periodo: null, periodo_anterior: null, entradas: [], saidas: [] },
        },
      }),
    );

    renderizar();

    expect(await screen.findByText("Nenhum dado importado ainda")).toBeVisible();
    expect(screen.getByRole("link", { name: "Importar um relatório" })).toHaveAttribute(
      "href",
      "/importacao",
    );
  });

  it("período único avisa que variação exige histórico", async () => {
    /* UC05, A2 — sem o aviso, os travessões seriam lidos como defeito. */
    simularApi(
      respostas({
        "GET /api/painel/indicadores": {
          corpo: indicadores({ periodo_anterior: null, variacao: null }),
        },
        "GET /api/painel/mobilidade": {
          corpo: { ...MOBILIDADE, periodo_anterior: null, entradas: [], saidas: [] },
        },
      }),
    );

    renderizar();

    expect(await screen.findByText(/variação e tendência exigem histórico/)).toBeVisible();
  });

  it("variação nula aparece como travessão, e nunca como 0%", async () => {
    simularApi(respostas());

    renderizar();

    await screen.findByText("Comércio Alfa");
    /* Ticket médio veio com variação nula; parceiros ativos, com zero de
       verdade. Os dois precisam aparecer diferentes. */
    expect(screen.getByText(/sem variação calculável/)).toBeInTheDocument();
    expect(screen.getByText("0,00%")).toBeInTheDocument();
  });

  it("estreante é marcado como novo, e não como queda", async () => {
    simularApi(respostas());

    renderizar();

    expect(await screen.findByText("· novo")).toBeVisible();
  });

  it("a distribuição por segmento desenha uma barra por segmento, com o número ao lado", async () => {
    simularApi(respostas());

    renderizar();

    await screen.findByText("Distribuição por segmento");
    const distribuicao = screen.getByRole("list");
    const linhas = within(distribuicao).getAllByRole("listitem");
    expect(linhas).toHaveLength(2);
    /* O número ao lado é o que cumpre a RNF22: nada aqui depende só de cor. */
    expect(within(linhas[0]).getByText("Top 15")).toBeVisible();
    expect(within(linhas[0]).getByText(/^1$/)).toBeVisible();
  });

  it("sem segmentação calculada, a distribuição explica em vez de ficar vazia", async () => {
    simularApi(
      respostas({ "GET /api/painel/segmentos": { corpo: { periodo: PERIODO, total: 0, itens: [] } } }),
    );

    renderizar();

    expect(await screen.findByText("Segmentação ainda não calculada")).toBeVisible();
  });

  it("em risco sobe com a cor de risco, e não com a de crescimento", async () => {
    /* A seta continua apontando para cima, porque o número subiu. O que muda é
       a cor: mais parceiros em risco é a única notícia ruim da fileira, e
       pintá-la de verde diria o contrário do que aconteceu. */
    simularApi(respostas({
      "GET /api/painel/indicadores": { corpo: indicadores({ em_risco: { total: 37, delta: 6 } }) },
    }));

    renderizar();

    const texto = await screen.findByText("6 a mais");
    expect(texto.closest("span")).toHaveClass("indicador__variacao--cai");
  });

  it("em risco nulo diz que a segmentação não rodou, em vez de mostrar zero", async () => {
    simularApi(respostas({
      "GET /api/painel/indicadores": { corpo: indicadores({ em_risco: null }) },
    }));

    renderizar();

    expect(await screen.findByText(/Segmentação ainda não calculada para este período/)).toBeVisible();
  });

  it("a mobilidade conta entradas e saídas do Top N", async () => {
    simularApi(respostas());

    renderizar();

    expect(await screen.findByText("Mobilidade Top 15")).toBeVisible();
    expect(screen.getByText("entraram · 1 saíram")).toBeVisible();
  });

  it("sem período anterior, a mobilidade não inventa movimento", async () => {
    simularApi(respostas({
      "GET /api/painel/mobilidade": {
        corpo: { ...MOBILIDADE, periodo_anterior: null, entradas: [], saidas: [] },
      },
    }));

    renderizar();

    expect(await screen.findByText(/exige um período anterior/)).toBeVisible();
  });

  it("o ranking mostra o segmento, e travessão quando ele não existe", async () => {
    simularApi(respostas({
      "GET /api/painel/ranking": {
        corpo: {
          ...RANKING,
          itens: [
            { ...RANKING.itens[0], segmento: "EM_RISCO" },
            { ...RANKING.itens[1], segmento: null },
          ],
        },
      },
    }));

    renderizar();

    const linha = (await screen.findByText("Comércio Alfa")).closest("tr");
    /* O rótulo é texto neutro; a cor mora no ponto ao lado. */
    expect(within(linha).getByText("Em risco")).toBeVisible();

    const novo = screen.getByText("Comércio Novo").closest("tr");
    expect(within(novo).getByTitle("Segmentação ainda não calculada")).toBeVisible();
  });

  it("o erro do servidor aparece com a ajuda que ele mandou", async () => {
    /* A API explica o que fazer. Reescrever a mensagem na tela perderia isso. */
    simularApi(
      respostas({
        "GET /api/painel/indicadores": {
          status: 404,
          corpo: { detail: { erro: "Não existe período com id 9.", ajuda: "Escolha outro período." } },
        },
      }),
    );

    renderizar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Não existe período com id 9.");
    expect(screen.getByText("Escolha outro período.")).toBeVisible();
  });
});
