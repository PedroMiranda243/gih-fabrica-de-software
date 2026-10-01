import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { simularApi } from "../testes/preparar";
import Painel from "./Painel";

/* O que a API manda em `telas` para cada perfil que abre o painel. */
const GESTOR = ["painel", "painel_decisao", "parceiros", "campanha"];
const ADMINISTRADOR = ["painel", "usuarios"];

const PERIODO = { id: 2, data_inicio: "2026-03-09", data_fim: "2026-03-15" };
const ANTERIOR = { id: 1, data_inicio: "2026-03-02", data_fim: "2026-03-08" };

function renderizar({ endereco = "/", telas = ADMINISTRADOR } = {}) {
  return render(
    <ContextoSessao.Provider value={{ usuario: { nome: "Quem Testa", telas }, sair: () => {} }}>
      <MemoryRouter initialEntries={[endereco]}>
        <Painel />
      </MemoryRouter>
    </ContextoSessao.Provider>,
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

describe("do painel para os outros módulos (H81)", () => {
  it("o nome no ranking leva ao cadastro do parceiro", async () => {
    simularApi(respostas());
    renderizar();

    const link = await screen.findByRole("link", { name: "Comércio Alfa" });
    expect(link).toHaveAttribute("href", "/parceiros/1");
  });

  it("cada segmento da distribuição leva à lista filtrada por ele", async () => {
    simularApi(respostas());
    renderizar();

    const distribuicao = await screen.findByRole("region", { name: "Distribuição por segmento" });
    expect(within(distribuicao).getByRole("link", { name: /Em risco/ })).toHaveAttribute(
      "href",
      "/parceiros?segmento=EM_RISCO",
    );
    expect(within(distribuicao).getByRole("link", { name: /Top 15/ })).toHaveAttribute(
      "href",
      "/parceiros?segmento=TOP",
    );
  });

  it("o indicador de em risco leva a quem está em risco", async () => {
    simularApi(respostas({
      "GET /api/painel/indicadores": { corpo: indicadores({ em_risco: { total: 37, delta: 6 } }) },
    }));
    renderizar();

    const link = await screen.findByRole("link", { name: "Ver quem está em risco" });
    expect(link).toHaveAttribute("href", "/parceiros?segmento=EM_RISCO");
  });

  it("sem segmentação calculada, o indicador não oferece um link para lista vazia", async () => {
    simularApi(respostas());
    renderizar();
    await screen.findByText("Comércio Alfa");

    expect(screen.queryByRole("link", { name: "Ver quem está em risco" })).toBeNull();
  });
});


describe("o recorte do painel (H82)", () => {
  const MAIS_ANTIGO = { id: 1, data_inicio: "2026-03-02", data_fim: "2026-03-08" };
  const PADARIA = { id: 4, nome: "Padaria", ativa: true };
  const RECORTES = {
    periodos: [PERIODO, MAIS_ANTIGO],
    categorias: [{ id: 3, nome: "Mercado", ativa: true }, PADARIA],
  };

  /** As cinco respostas, anotando o que cada pedido levou no endereço. */
  function comPedidos(extra = {}) {
    const pedidos = [];
    const anotando = (corpo) => (url) => {
      pedidos.push(String(url));
      return { corpo };
    };
    simularApi({
      "GET /api/painel/recortes": { corpo: RECORTES },
      "GET /api/painel/indicadores": anotando(indicadores()),
      "GET /api/painel/ranking": anotando(RANKING),
      "GET /api/painel/series": anotando(SERIE),
      "GET /api/painel/segmentos": anotando(SEGMENTOS),
      "GET /api/painel/mobilidade": anotando(MOBILIDADE),
      ...extra,
    });
    return pedidos;
  }

  const de = (pedidos, rota) => pedidos.filter((p) => p.includes(`/api/painel/${rota}`)).at(-1);

  it("oferece os períodos, do mais recente, e as categorias que a API manda", async () => {
    comPedidos();
    renderizar();

    const periodo = await screen.findByLabelText("Período");
    expect(within(periodo).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "09/03/2026 a 15/03/2026",
      "02/03/2026 a 08/03/2026",
    ]);
    expect(periodo).toHaveValue("2");
    const categoria = screen.getByLabelText("Categoria");
    expect(within(categoria).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Rede inteira",
      "Mercado",
      "Padaria",
    ]);
    expect(await screen.findByText("Comparado com 02/03/2026 a 08/03/2026.")).toBeVisible();
  });

  it("escolher a categoria manda o recorte a quatro rotas, e a mobilidade fica na rede", async () => {
    const pedidos = comPedidos();
    const usuario = userEvent.setup();
    renderizar();

    await usuario.selectOptions(await screen.findByLabelText("Categoria"), "4");
    await screen.findByText("Comércio Alfa");

    for (const rota of ["indicadores", "ranking", "series", "segmentos"]) {
      expect(de(pedidos, rota)).toContain("categoria_id=4");
    }
    /* O Top N é da rede inteira (RN02): a mobilidade não leva a categoria. */
    expect(de(pedidos, "mobilidade")).not.toContain("categoria_id");
  });

  it("o recorte do endereço abre o painel já filtrado", async () => {
    const pedidos = comPedidos();
    renderizar({ endereco: "/?periodo=1&categoria=4" });

    await screen.findByText("Comércio Alfa");

    expect(de(pedidos, "indicadores")).toContain("periodo_id=1");
    expect(de(pedidos, "indicadores")).toContain("categoria_id=4");
    expect(de(pedidos, "mobilidade")).toContain("periodo_id=1");
    expect(screen.getByLabelText("Período")).toHaveValue("1");
    expect(screen.getByLabelText("Categoria")).toHaveValue("4");
  });

  it("com categoria, a tela diz o que continua sendo da rede inteira", async () => {
    comPedidos({
      "GET /api/painel/indicadores": { corpo: indicadores({ categoria: PADARIA }) },
      "GET /api/painel/ranking": { corpo: { ...RANKING, categoria: PADARIA } },
      "GET /api/painel/series": { corpo: { ...SERIE, escopo: "categoria", categoria: PADARIA } },
    });
    renderizar({ endereco: "/?categoria=4" });

    expect(await screen.findByText("2 de 2 · posição na rede inteira")).toBeVisible();
    expect(screen.getByText("entraram · 1 saíram · na rede inteira")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Faturamento de Padaria" })).toBeVisible();
    expect(screen.getByText("Comparado com 02/03/2026 a 08/03/2026, na mesma categoria.")).toBeVisible();
  });

  it("os caminhos para a lista levam a categoria do recorte", async () => {
    comPedidos({
      "GET /api/painel/indicadores": {
        corpo: indicadores({ categoria: PADARIA, em_risco: { total: 3, delta: 1 } }),
      },
    });
    renderizar({ endereco: "/?categoria=4" });

    const link = await screen.findByRole("link", { name: "Ver quem está em risco" });
    expect(link).toHaveAttribute("href", "/parceiros?segmento=EM_RISCO&categoria_id=4");
    const distribuicao = screen.getByRole("region", { name: "Distribuição por segmento" });
    expect(within(distribuicao).getByRole("link", { name: /Top 15/ })).toHaveAttribute(
      "href",
      "/parceiros?segmento=TOP&categoria_id=4",
    );
  });

  it("em outro período, o segmento não leva à lista, que é do período mais recente", async () => {
    comPedidos({
      "GET /api/painel/indicadores": {
        corpo: indicadores({
          periodo: MAIS_ANTIGO,
          periodo_anterior: null,
          variacao: null,
          em_risco: { total: 3, delta: null },
        }),
      },
    });
    renderizar({ endereco: "/?periodo=1" });

    const distribuicao = await screen.findByRole("region", { name: "Distribuição por segmento" });
    expect(within(distribuicao).getByText("Top 15")).toBeVisible();
    expect(within(distribuicao).queryByRole("link")).toBeNull();
    expect(screen.queryByRole("link", { name: "Ver quem está em risco" })).toBeNull();
  });

  it("categoria sem movimento no período diz isso no ranking", async () => {
    comPedidos({
      "GET /api/painel/ranking": { corpo: { ...RANKING, categoria: PADARIA, itens: [], total: 0 } },
    });
    renderizar({ endereco: "/?categoria=4" });

    expect(
      await screen.findByText("Nenhum parceiro de Padaria com movimento neste período"),
    ).toBeVisible();
  });

  it("recorte que a API recusa mostra o erro e deixa escolher outro", async () => {
    comPedidos({
      "GET /api/painel/indicadores": {
        status: 404,
        corpo: { detail: "Não existe período com id 77." },
      },
    });
    renderizar({ endereco: "/?periodo=77" });

    expect(await screen.findByRole("alert")).toHaveTextContent("Não existe período com id 77.");
    /* O seletor não finge que está no mais recente enquanto a página mostra o erro. */
    const periodo = screen.getByLabelText("Período");
    expect(within(periodo).getByRole("option", { selected: true })).toHaveTextContent(
      "Escolha um período",
    );
    expect(periodo).toBeEnabled();
  });
});

describe("a previsão e a campanha no painel (H83)", () => {
  const BASE = { id: 2, data_inicio: "2026-03-09", data_fim: "2026-03-15" };
  const DECISAO = {
    categoria: null,
    previsao: {
      disponivel: true,
      motivo: null,
      ajuda: null,
      periodo_base: BASE,
      modelo_versao: "rede-7",
      origem: "MODELO",
      desatualizada: false,
      parceiros: 2,
      faturamento_previsto: "2820.00",
      faturamento_medido: "2900.00",
      variacao_percentual: "-2.76",
      maior_risco: [
        {
          parceiro_id: 9, nome: "Comércio Frágil", categoria: "Padaria",
          probabilidade_queda: 0.81, faturamento: "900.00", faturamento_previsto: "700.00",
        },
        {
          parceiro_id: 5, nome: "Comércio Firme", categoria: null,
          probabilidade_queda: 0.002, faturamento: "2000.00", faturamento_previsto: "2120.00",
        },
      ],
    },
    campanha: {
      plano: {
        execucao_id: 31, concluida_em: "2026-03-16T12:00:00Z",
        aplicacao_inicio: "2026-03-23", aplicacao_fim: "2026-03-29", modelo_versao: "rede-7",
      },
      acoes: 23,
      custo: "4980.00",
      ganho_esperado: "114527.81",
    },
  };

  function comDecisao(decisao = DECISAO, extra = {}) {
    return simularApi(respostas({ "GET /api/painel/decisao": { corpo: decisao }, ...extra }));
  }

  it("mostra o previsto ao lado do medido, marcado como estimativa", async () => {
    comDecisao();
    renderizar({ telas: GESTOR });

    const bloco = await screen.findByRole("region", { name: "Próximo período" });
    expect(within(bloco).getByText("Estimativa")).toBeVisible();
    expect(within(bloco).getByText("R$ 2.820,00")).toBeVisible();
    expect(within(bloco).getByText("R$ 2.900,00")).toBeVisible();
    expect(within(bloco).getByText("-2,76%")).toBeVisible();
    expect(bloco).toHaveTextContent(
      "Soma de 2 parceiros com previsão, pelo modelo rede-7, com dados até 15/03/2026.",
    );
    expect(bloco).toHaveTextContent("e não do escolhido acima");
  });

  it("lista quem tem o maior risco, com o caminho para o cadastro e para a lista", async () => {
    comDecisao();
    renderizar({ telas: GESTOR });

    const bloco = await screen.findByRole("region", { name: "Próximo período" });
    const linhas = within(within(bloco).getByRole("table")).getAllByRole("row");
    expect(linhas[1]).toHaveTextContent("Comércio Frágil");
    expect(linhas[1]).toHaveTextContent("81%");
    /* A chance não finge certeza: 0,002 não vira 0%. */
    expect(linhas[2]).toHaveTextContent("menos de 1%");
    expect(linhas[2]).toHaveTextContent("sem categoria");
    expect(within(bloco).getByRole("link", { name: "Comércio Frágil" })).toHaveAttribute(
      "href",
      "/parceiros/9",
    );
    expect(
      within(bloco).getByRole("link", { name: "Ver todos os parceiros pelo risco" }),
    ).toHaveAttribute("href", "/parceiros?ordenar_por=risco&descendente=true");
  });

  it("resume o último plano e leva a ele", async () => {
    comDecisao();
    renderizar({ telas: GESTOR });

    const bloco = await screen.findByRole("region", { name: "Última campanha" });
    expect(bloco).toHaveTextContent("23");
    expect(within(bloco).getByText("R$ 4.980,00")).toBeVisible();
    expect(within(bloco).getByText("R$ 114.527,81")).toBeVisible();
    expect(bloco).toHaveTextContent("23/03/2026 a 29/03/2026");
    expect(within(bloco).getByRole("link", { name: "Abrir o plano" })).toHaveAttribute(
      "href",
      "/execucoes/31",
    );
  });

  it("sem modelo treinado e sem plano, o bloco diz o que falta", async () => {
    comDecisao({
      categoria: null,
      previsao: {
        disponivel: false,
        motivo: "O modelo ainda não foi treinado.",
        ajuda: "Um administrador ou gestor treina o modelo na tela Modelo.",
        maior_risco: [],
      },
      campanha: { plano: null, acoes: 0, custo: null, ganho_esperado: null },
    });
    renderizar({ telas: GESTOR });

    expect(await screen.findByText("O modelo ainda não foi treinado.")).toBeVisible();
    expect(screen.getByText("Nenhum plano de campanha calculado ainda")).toBeVisible();
    expect(screen.getByRole("link", { name: "Ir para a Campanha" })).toHaveAttribute(
      "href",
      "/campanha",
    );
  });

  it("previsão de antes do último período importado avisa que está desatualizada", async () => {
    comDecisao({ ...DECISAO, previsao: { ...DECISAO.previsao, desatualizada: true } });
    renderizar({ telas: GESTOR });

    expect(await screen.findByText(/Há período importado depois desta estimativa/)).toBeVisible();
  });

  it("com categoria, o pedido e os caminhos levam a categoria", async () => {
    const pedidos = [];
    const padaria = { id: 4, nome: "Padaria", ativa: true };
    comDecisao(DECISAO, {
      "GET /api/painel/decisao": (url) => {
        pedidos.push(String(url));
        return { corpo: { ...DECISAO, categoria: padaria } };
      },
    });
    renderizar({ telas: GESTOR, endereco: "/?categoria=4&periodo=1" });

    const bloco = await screen.findByRole("region", { name: "Próximo período" });
    expect(pedidos.at(-1)).toContain("categoria_id=4");
    /* A previsão não acompanha o período escolhido: o pedido não o leva. */
    expect(pedidos.at(-1)).not.toContain("periodo");
    expect(bloco).toHaveTextContent("com previsão em Padaria");
    expect(
      within(bloco).getByRole("link", { name: "Ver todos os parceiros pelo risco" }),
    ).toHaveAttribute("href", "/parceiros?ordenar_por=risco&descendente=true&categoria_id=4");
    expect(screen.getByRole("region", { name: "Última campanha" })).toHaveTextContent(
      "Só as ações de parceiros de Padaria.",
    );
  });

  it("o administrador não vê o bloco, e a tela nem pede", async () => {
    const chamadas = comDecisao();
    renderizar({ telas: ADMINISTRADOR });

    await screen.findByText("Comércio Alfa");
    expect(screen.queryByRole("region", { name: "Próximo período" })).toBeNull();
    expect(chamadas.mock.calls.some(([url]) => String(url).includes("/api/painel/decisao"))).toBe(
      false,
    );
  });

  it("se o bloco falhar, o painel continua inteiro", async () => {
    simularApi(respostas({ "GET /api/painel/decisao": { status: 500, corpo: { detail: "x" } } }));
    renderizar({ telas: GESTOR });

    expect(await screen.findByText("Comércio Alfa")).toBeVisible();
    expect(screen.queryByRole("region", { name: "Próximo período" })).toBeNull();
  });
});
