import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { simularApi } from "../testes/preparar";
import RelatorioCampanha from "./RelatorioCampanha";
import RelatorioDesempenho from "./RelatorioDesempenho";
import RelatorioOperacoes from "./RelatorioOperacoes";
import RelatorioRisco from "./RelatorioRisco";
import Relatorios from "./Relatorios";

/* O que a API manda em `telas` para cada perfil. */
const GESTOR = { nome: "Gestora", perfil: "GESTOR", telas: ["painel", "parceiros", "relatorios"] };
const ADMINISTRADOR = {
  nome: "Chefia",
  perfil: "ADMINISTRADOR",
  telas: ["painel", "auditoria", "relatorio_operacoes"],
};

function renderizar(endereco, usuario = GESTOR) {
  return render(
    <ContextoSessao.Provider value={{ usuario, sair: () => {} }}>
      <MemoryRouter initialEntries={[endereco]}>
        <Routes>
          <Route path="/relatorios" element={<Relatorios />} />
          <Route path="/relatorios/desempenho" element={<RelatorioDesempenho />} />
          <Route path="/relatorios/risco" element={<RelatorioRisco />} />
          <Route path="/relatorios/campanha" element={<RelatorioCampanha />} />
          <Route path="/relatorios/operacoes" element={<RelatorioOperacoes />} />
        </Routes>
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

/** As rotas dadas, anotando o endereço de cada pedido. */
function comPedidos(rotas) {
  const pedidos = [];
  simularApi(
    Object.fromEntries(
      Object.entries(rotas).map(([chave, corpo]) => [
        chave,
        (url) => {
          pedidos.push(String(url));
          return typeof corpo === "function" ? corpo(url) : { corpo };
        },
      ]),
    ),
  );
  return pedidos;
}

const ultimo = (pedidos, trecho) => pedidos.filter((p) => p.includes(trecho)).at(-1);

const PERIODO = { id: 2, data_inicio: "2026-03-09", data_fim: "2026-03-15" };
const ANTERIOR = { id: 1, data_inicio: "2026-03-02", data_fim: "2026-03-08" };
const PADARIA = { id: 4, nome: "Padaria", ativa: true };
const RECORTES = { periodos: [PERIODO, ANTERIOR], categorias: [PADARIA] };

// ============================================================ a lista
describe("a lista de relatórios", () => {
  it("o gestor vê os três relatórios da rede, com o caminho de cada um", () => {
    renderizar("/relatorios");

    const itens = screen.getAllByRole("listitem");
    expect(itens.map((i) => within(i).getByRole("heading").textContent)).toEqual([
      "Desempenho por período",
      "Parceiros em risco",
      "Campanha",
    ]);
    expect(
      within(itens[1]).getByRole("link", { name: "Abrir o relatório Parceiros em risco" }),
    ).toHaveAttribute("href", "/relatorios/risco");
  });

  it("o administrador vê só o de operações, que é o que a API lhe dá", () => {
    renderizar("/relatorios", ADMINISTRADOR);

    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "Operações do sistema" })).toBeVisible();
  });

  it("perfil sem relatório nenhum recebe a explicação, e não uma lista vazia", () => {
    renderizar("/relatorios", { nome: "Parceiro", perfil: "PARCEIRO", telas: ["meu_desempenho"] });

    expect(screen.getByText("Nenhum relatório para o seu perfil")).toBeVisible();
    expect(screen.queryByRole("list")).toBeNull();
  });
});

// ======================================================== desempenho (H84)
const linha = (chave, rotulo, extra = {}) => ({
  chave,
  rotulo,
  parceiros: 2,
  faturamento: "1500.00",
  pedidos: 16,
  ticket_medio: "93.75",
  variacao_percentual: "25.00",
  ...extra,
});

const DESEMPENHO = {
  periodo: PERIODO,
  periodo_anterior: ANTERIOR,
  categoria: null,
  segmento: null,
  mesmos_parceiros: false,
  segmentado: true,
  total: linha(null, "Total", {
    parceiros: 5, faturamento: "2700.00", pedidos: 30, ticket_medio: "90.00",
    variacao_percentual: "-3.57",
  }),
  por_categoria: [
    linha("4", "Padaria"),
    linha(null, "Sem categoria", { faturamento: "1200.00", variacao_percentual: null }),
  ],
  por_segmento: [
    linha("EM_RISCO", "Em risco", { variacao_percentual: "-11.11" }),
    linha("TOP", "Top", { faturamento: "1200.00" }),
  ],
};

describe("relatório de desempenho (H84)", () => {
  function comDesempenho(dados = DESEMPENHO) {
    return comPedidos({
      "GET /api/painel/recortes": RECORTES,
      "GET /api/relatorios/desempenho": dados,
    });
  }

  it("mostra o total, as categorias e os segmentos com o que a API mandou", async () => {
    comDesempenho();
    renderizar("/relatorios/desempenho");

    const total = await screen.findByRole("region", { name: "Total do recorte" });
    expect(within(total).getByText("R$ 2.700,00")).toBeVisible();
    expect(within(total).getByText("-3,57%")).toBeVisible();
    expect(within(total).getByText("5 parceiros com movimento")).toBeVisible();

    const categorias = screen.getByRole("region", { name: "Por categoria" });
    const linhas = within(categorias).getAllByRole("row");
    expect(linhas[1]).toHaveTextContent("Padaria");
    expect(linhas[1]).toHaveTextContent("R$ 1.500,00");
    expect(linhas[1]).toHaveTextContent("+25,00%");
    /* Grupo sem com o que comparar: travessão, e nunca 0%. */
    expect(within(linhas[2]).getByText(/sem variação calculável/)).toBeInTheDocument();
    expect(linhas.at(-1)).toHaveTextContent("Total");
    expect(linhas.at(-1)).toHaveTextContent("R$ 2.700,00");

    const segmentos = screen.getByRole("region", { name: "Por segmento" });
    expect(within(segmentos).getByText("Em risco")).toBeVisible();
    expect(within(segmentos).getByText("-11,11%")).toBeVisible();
  });

  it("diz de que grupo é cada variação", async () => {
    comDesempenho();
    renderizar("/relatorios/desempenho");

    const categorias = await screen.findByRole("region", { name: "Por categoria" });
    expect(categorias).toHaveTextContent("contra o dela mesma no período anterior, como no painel");
    const segmentos = screen.getByRole("region", { name: "Por segmento" });
    expect(segmentos).toHaveTextContent("A variação é a dos mesmos parceiros");
    expect(segmentos).toHaveTextContent("não é a soma destas");
  });

  it("com filtro de segmento, o total e as categorias também são dos mesmos parceiros", async () => {
    comDesempenho({ ...DESEMPENHO, segmento: "EM_RISCO", mesmos_parceiros: true });
    renderizar("/relatorios/desempenho?segmento=EM_RISCO");

    const total = await screen.findByRole("region", { name: "Total do recorte" });
    expect(total).toHaveTextContent("A variação é a dos mesmos parceiros");
    expect(screen.getByRole("region", { name: "Por categoria" })).not.toHaveTextContent(
      "como no painel",
    );
  });

  it("o recorte da folha é o que a API devolveu", async () => {
    comDesempenho({ ...DESEMPENHO, categoria: PADARIA, segmento: "EM_RISCO", mesmos_parceiros: true });
    renderizar("/relatorios/desempenho?categoria=4&segmento=EM_RISCO");

    await screen.findByRole("region", { name: "Total do recorte" });
    expect(
      screen.getByText(
        "Período de 09/03/2026 a 15/03/2026 · comparado com 02/03/2026 a 08/03/2026 · categoria Padaria · segmento Em risco",
      ),
    ).toBeVisible();
  });

  it("os filtros vão para a API e para o CSV, que é a mesma consulta", async () => {
    const pedidos = comDesempenho();
    const usuario = userEvent.setup();
    renderizar("/relatorios/desempenho");

    await usuario.selectOptions(await screen.findByLabelText("Categoria"), "4");
    await usuario.selectOptions(screen.getByLabelText("Segmento"), "EM_RISCO");
    await usuario.selectOptions(screen.getByLabelText("Período"), "1");
    await screen.findByRole("region", { name: "Total do recorte" });

    const consulta = new URL(ultimo(pedidos, "/api/relatorios/desempenho"), "http://local");
    expect(Object.fromEntries(consulta.searchParams)).toEqual({
      periodo_id: "1",
      categoria_id: "4",
      segmento: "EM_RISCO",
    });
    const csv = new URL(screen.getByRole("link", { name: "Exportar CSV" }).getAttribute("href"), "http://local");
    expect(csv.pathname).toBe("/api/relatorios/desempenho/exportacao.csv");
    expect(Object.fromEntries(csv.searchParams)).toEqual(Object.fromEntries(consulta.searchParams));
  });

  it("período sem segmentação diz isso, em vez de uma tabela vazia", async () => {
    comDesempenho({ ...DESEMPENHO, segmentado: false, por_segmento: [] });
    renderizar("/relatorios/desempenho");

    const segmentos = await screen.findByRole("region", { name: "Por segmento" });
    expect(
      within(segmentos).getByText("Segmentação ainda não calculada para este período"),
    ).toBeVisible();
    expect(within(segmentos).queryByRole("table")).toBeNull();
  });

  it("recorte sem movimento diz isso, e base vazia leva à importação", async () => {
    comDesempenho({
      ...DESEMPENHO,
      total: linha(null, "Total", { parceiros: 0, faturamento: "0.00", pedidos: 0, ticket_medio: null }),
      por_categoria: [],
      por_segmento: [],
    });
    const { unmount } = renderizar("/relatorios/desempenho?categoria=4");
    expect(await screen.findByText("Nenhum parceiro com movimento nesse recorte")).toBeVisible();
    unmount();

    comDesempenho({ ...DESEMPENHO, periodo: null, periodo_anterior: null, total: null, por_categoria: [], por_segmento: [] });
    renderizar("/relatorios/desempenho");
    expect(await screen.findByRole("link", { name: "Importar um relatório" })).toHaveAttribute(
      "href",
      "/importacao",
    );
    /* Sem relatório, não há o que exportar. */
    expect(screen.queryByRole("link", { name: "Exportar CSV" })).toBeNull();
  });

  it("o erro da API aparece com a ajuda que ela mandou", async () => {
    comPedidos({
      "GET /api/painel/recortes": RECORTES,
      "GET /api/relatorios/desempenho": () => ({
        status: 404,
        corpo: { detail: { erro: "Não existe período com id 77.", ajuda: "Escolha um dos períodos importados." } },
      }),
    });
    renderizar("/relatorios/desempenho?periodo=77");

    expect(await screen.findByRole("alert")).toHaveTextContent("Não existe período com id 77.");
    expect(screen.getByText("Escolha um dos períodos importados.")).toBeVisible();
  });
});

// ======================================================= a moldura (H88)
describe("a moldura do relatório (H88)", () => {
  it("imprimir chama a impressão do navegador, e a folha diz quando e por quem", async () => {
    comPedidos({
      "GET /api/painel/recortes": RECORTES,
      "GET /api/relatorios/desempenho": DESEMPENHO,
    });
    const imprimir = vi.spyOn(window, "print").mockImplementation(() => {});
    const usuario = userEvent.setup();
    renderizar("/relatorios/desempenho");
    await screen.findByRole("region", { name: "Total do recorte" });

    await usuario.click(screen.getByRole("button", { name: "Imprimir ou salvar em PDF" }));

    expect(imprimir).toHaveBeenCalledTimes(1);
    const emissao = screen.getByText(/^Gerado em/);
    expect(emissao).toHaveTextContent(/Gerado em \d{2}\/\d{2}\/\d{4} às \d{2}:\d{2} por Gestora \(Gestor\)/);
    /* Só na folha: na tela, a linha de emissão não aparece. */
    expect(emissao).toHaveClass("so-impressao");
  });

  it("o que é da tela não vai para a folha: a trilha, os filtros e os botões", async () => {
    comPedidos({
      "GET /api/painel/recortes": RECORTES,
      "GET /api/relatorios/desempenho": DESEMPENHO,
    });
    renderizar("/relatorios/desempenho");
    await screen.findByRole("region", { name: "Total do recorte" });

    expect(screen.getByRole("navigation", { name: "Você está em" })).toHaveClass("nao-imprime");
    expect(screen.getByRole("region", { name: "Filtros do relatório" })).toHaveClass("nao-imprime");
    expect(screen.getByRole("button", { name: "Imprimir ou salvar em PDF" }).parentElement).toHaveClass(
      "nao-imprime",
    );
    expect(screen.getByRole("link", { name: "Relatórios" })).toHaveAttribute("href", "/relatorios");
  });
});

// ============================================================ risco (H85)
const RISCO = {
  disponivel: true,
  motivo: null,
  ajuda: null,
  periodo_base: PERIODO,
  modelo_versao: "rede-7",
  origem: "MODELO",
  desatualizada: false,
  categoria: null,
  segmento: null,
  risco_minimo: null,
  plano: {
    execucao_id: 31, concluida_em: "2026-03-16T12:00:00Z",
    aplicacao_inicio: "2026-03-23", aplicacao_fim: "2026-03-29", modelo_versao: "rede-7",
  },
  total: 2,
  com_previsao: 1,
  faturamento_medido: "900.00",
  faturamento_previsto: "700.00",
  no_plano: 1,
  pagina: 1,
  tamanho: 50,
  itens: [
    {
      parceiro_id: 9, nome: "Comércio Frágil", categoria: "Padaria", segmento: "EM_RISCO",
      faturamento: "900.00", variacao_percentual: "-10.00", faturamento_previsto: "700.00",
      probabilidade_queda: 0.998, sem_previsao: null, acao: "Visita de relacionamento", custo: "90.00",
    },
    {
      parceiro_id: 5, nome: "Comércio Novo", categoria: null, segmento: "RECEM_CHEGADO",
      faturamento: "300.00", variacao_percentual: null, faturamento_previsto: null,
      probabilidade_queda: null,
      sem_previsao: "Com 2 períodos de histórico, ainda não há previsão: são necessários 4.",
      acao: null, custo: null,
    },
  ],
};

describe("relatório de parceiros em risco (H85)", () => {
  function comRisco(dados = RISCO) {
    return comPedidos({
      "GET /api/painel/recortes": RECORTES,
      "GET /api/relatorios/risco": dados,
    });
  }

  it("marca como estimativa e diz de que modelo, com dados até quando", async () => {
    comRisco();
    renderizar("/relatorios/risco");

    const resumo = await screen.findByRole("region", { name: "Resumo do recorte" });
    expect(within(resumo).getByText("Estimativa")).toBeVisible();
    expect(resumo).toHaveTextContent("estimativa do modelo rede-7, com dados até 15/03/2026");
    expect(within(resumo).getByText("R$ 700,00")).toBeVisible();
    expect(within(resumo).getByText("R$ 900,00")).toBeVisible();
  });

  it("a chance não finge certeza, e quem não tem previsão aparece com o motivo", async () => {
    comRisco();
    renderizar("/relatorios/risco");

    const tabela = await screen.findByRole("table");
    const [, fragil, novo] = within(tabela).getAllByRole("row");
    expect(fragil).toHaveTextContent("mais de 99%");
    expect(fragil).toHaveTextContent("Visita de relacionamento");
    expect(fragil).toHaveTextContent("R$ 90,00");
    /* RN09: o motivo no lugar dos dois números, e não zero. */
    expect(novo).toHaveTextContent("Com 2 períodos de histórico, ainda não há previsão");
    expect(novo).not.toHaveTextContent("0%");
    expect(within(novo).getByText(/fora do último plano/)).toBeInTheDocument();
  });

  it("o nome leva ao cadastro, que volta para o relatório", async () => {
    comRisco();
    renderizar("/relatorios/risco?segmento=EM_RISCO");

    const link = await screen.findByRole("link", { name: "Comércio Frágil" });
    expect(link).toHaveAttribute("href", "/parceiros/9");
  });

  it("a porcentagem digitada vai como fração, para a tela e para o CSV", async () => {
    const pedidos = comRisco({ ...RISCO, risco_minimo: 0.4 });
    const usuario = userEvent.setup();
    renderizar("/relatorios/risco?pagina=3");

    await usuario.type(await screen.findByLabelText("Chance de queda a partir de (%)"), "40");
    await screen.findByText(/chance de queda a partir de 40%/);

    const consulta = new URL(ultimo(pedidos, "/api/relatorios/risco"), "http://local");
    expect(consulta.searchParams.get("risco_minimo")).toBe("0.4000");
    /* Mudar o filtro volta para a primeira página. */
    expect(consulta.searchParams.get("pagina")).toBe("1");
    const csv = new URL(screen.getByRole("link", { name: "Exportar CSV" }).getAttribute("href"), "http://local");
    expect(csv.pathname).toBe("/api/relatorios/risco/exportacao.csv");
    expect(csv.searchParams.get("risco_minimo")).toBe("0.4000");
    /* O arquivo é o recorte inteiro: não leva a página. */
    expect(csv.searchParams.has("pagina")).toBe(false);
  });

  it("com mais de uma página, a folha diz que o CSV traz todos", async () => {
    comRisco({ ...RISCO, total: 120 });
    renderizar("/relatorios/risco");

    await screen.findByRole("table");
    expect(screen.getByText(/parceiros 1 a 50 de 120 — o arquivo CSV traz todos/)).toBeVisible();
    expect(screen.getByText("1–50 de 120")).toBeVisible();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Próxima" })).toBeEnabled();
  });

  it("sem modelo treinado, o relatório diz o que falta e não oferece o CSV", async () => {
    comRisco({
      disponivel: false,
      motivo: "O modelo ainda não foi treinado.",
      ajuda: "Um administrador ou gestor treina o modelo na tela Modelo.",
      itens: [],
      total: 0,
      pagina: 1,
      tamanho: 50,
    });
    renderizar("/relatorios/risco");

    expect(await screen.findByText("O modelo ainda não foi treinado.")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Exportar CSV" })).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("sem plano, a nota diz por que a coluna da ação está vazia", async () => {
    comRisco({ ...RISCO, plano: null, no_plano: 0 });
    renderizar("/relatorios/risco");

    const resumo = await screen.findByRole("region", { name: "Resumo do recorte" });
    expect(resumo).toHaveTextContent("Nenhum plano de campanha foi calculado ainda");
  });
});

// ========================================================= campanha (H86)
const grupo = (chave, rotulo, extra = {}) => ({
  chave, rotulo, parceiros: 2, custo: "180.00", ganho_esperado: "250.50", ...extra,
});

const CAMPANHA = {
  plano: RISCO.plano,
  periodo_base: PERIODO,
  orcamento: "5000.00",
  total: grupo(null, "Total", { parceiros: 3, custo: "440.00", ganho_esperado: "550.50" }),
  por_acao: [grupo("Destaque na vitrine", "Destaque na vitrine"), grupo("Visita", "Visita")],
  por_categoria: [grupo("4", "Padaria"), grupo(null, "Sem categoria")],
  por_segmento: [grupo("EM_RISCO", "Em risco"), grupo("TOP", "Top")],
};

const PLANOS = [
  CAMPANHA.plano,
  { ...CAMPANHA.plano, execucao_id: 20, concluida_em: "2026-03-09T12:00:00Z" },
];

describe("relatório da campanha (H86)", () => {
  function comCampanha(dados = CAMPANHA, planos = PLANOS) {
    return comPedidos({
      "GET /api/relatorios/campanha/planos": planos,
      "GET /api/relatorios/campanha": dados,
    });
  }

  it("mostra o total e os três agrupamentos, com o ganho marcado como estimativa", async () => {
    comCampanha();
    renderizar("/relatorios/campanha");

    const total = await screen.findByRole("region", { name: "Total do plano" });
    expect(within(total).getByText("Estimativa")).toBeVisible();
    expect(within(total).getByText("R$ 550,50")).toBeVisible();
    expect(within(total).getByText("R$ 440,00")).toBeVisible();
    expect(within(total).getByText("R$ 5.000,00")).toBeVisible();
    expect(total).toHaveTextContent("estimativa, pela previsão rede-7 (RN10)");

    for (const nome of ["Por ação", "Por categoria", "Por segmento"]) {
      const bloco = screen.getByRole("region", { name: nome });
      const linhas = within(bloco).getAllByRole("row");
      expect(linhas).toHaveLength(4);
      expect(linhas.at(-1)).toHaveTextContent("Total");
      expect(linhas.at(-1)).toHaveTextContent("R$ 440,00");
    }
    expect(screen.getByRole("region", { name: "Por segmento" })).toHaveTextContent(
      "O segmento é o do período de 09/03/2026 a 15/03/2026, de onde o plano partiu.",
    );
  });

  it("leva ao plano, parceiro a parceiro", async () => {
    comCampanha();
    renderizar("/relatorios/campanha");

    const link = await screen.findByRole("link", { name: "Abrir o plano, parceiro a parceiro" });
    expect(link).toHaveAttribute("href", "/execucoes/31");
  });

  it("escolher outro plano pede o dele, e o CSV também", async () => {
    const pedidos = comCampanha();
    const usuario = userEvent.setup();
    renderizar("/relatorios/campanha");

    const seletor = await screen.findByLabelText("Plano");
    expect(within(seletor).getAllByRole("option")).toHaveLength(2);
    await usuario.selectOptions(seletor, "20");
    await screen.findByRole("region", { name: "Total do plano" });

    expect(ultimo(pedidos, "/api/relatorios/campanha?")).toContain("execucao_id=20");
    expect(screen.getByRole("link", { name: "Exportar CSV" })).toHaveAttribute(
      "href",
      "/api/relatorios/campanha/exportacao.csv?execucao_id=20",
    );
  });

  it("sem plano, o relatório leva à tela que o calcula e não oferece o CSV", async () => {
    comCampanha({ plano: null, total: null, por_acao: [], por_categoria: [], por_segmento: [] }, []);
    renderizar("/relatorios/campanha");

    expect(await screen.findByText("Nenhum plano de campanha calculado ainda")).toBeVisible();
    expect(screen.getByRole("link", { name: "Ir para a Campanha" })).toHaveAttribute(
      "href",
      "/campanha",
    );
    expect(screen.queryByRole("link", { name: "Exportar CSV" })).toBeNull();
  });

  it("execução sem plano mostra o porquê que a API mandou", async () => {
    comPedidos({
      "GET /api/relatorios/campanha/planos": PLANOS,
      "GET /api/relatorios/campanha": () => ({
        status: 409,
        corpo: {
          detail: {
            erro: "A execução 12 não tem plano: terminou sem plano viável.",
            ajuda: "O relatório é de um plano calculado. Escolha uma execução viável.",
          },
        },
      }),
    });
    renderizar("/relatorios/campanha?execucao=12");

    expect(await screen.findByRole("alert")).toHaveTextContent("A execução 12 não tem plano");
    /* O seletor não finge que está no último plano enquanto a página mostra o erro. */
    expect(
      within(screen.getByLabelText("Plano")).getByRole("option", { selected: true }),
    ).toHaveTextContent("Execução 12");
  });
});

// ======================================================== operações (H87)
const OPERACOES = {
  de: "2026-09-02",
  ate: "2026-10-01",
  autor: null,
  acao: null,
  total: 120,
  pessoas: 18,
  por_acao: [
    { chave: "LOGIN_SUCESSO", rotulo: "Entrada no sistema", total: 80 },
    { chave: "USUARIO_CRIADO", rotulo: "Usuário criado", total: 40 },
  ],
  por_usuario: [
    { chave: "1", rotulo: "Chefia (chefia)", total: 90 },
    { chave: null, rotulo: "sem usuário", total: 10 },
  ],
  outras_pessoas: { chave: null, rotulo: "Outras 16 pessoas", total: 20 },
  por_dia: [
    { chave: "2026-09-30", rotulo: "2026-09-30", total: 100 },
    { chave: "2026-10-01", rotulo: "2026-10-01", total: 20 },
  ],
};

describe("relatório de operações (H87)", () => {
  const USUARIOS = [{ id: 1, login: "chefia", nome: "Chefia", perfil: "ADMINISTRADOR", ativo: true }];
  const ACOES = [
    { acao: "LOGIN_SUCESSO", rotulo: "Entrada no sistema" },
    { acao: "USUARIO_CRIADO", rotulo: "Usuário criado" },
  ];

  function comOperacoes(dados = OPERACOES) {
    return comPedidos({
      "GET /api/auditoria/acoes": ACOES,
      "GET /api/usuarios": USUARIOS,
      "GET /api/relatorios/operacoes": dados,
    });
  }

  it("escreve o intervalo que a API devolveu, e não o do endereço", async () => {
    comOperacoes();
    renderizar("/relatorios/operacoes", ADMINISTRADOR);

    await screen.findByRole("region", { name: "Total do intervalo" });
    expect(
      screen.getByText("De 02/09/2026 a 01/10/2026 · todas as pessoas · todas as ações"),
    ).toBeVisible();
  });

  it("cada grupo tem a contagem em texto, e não só a barra", async () => {
    comOperacoes();
    renderizar("/relatorios/operacoes", ADMINISTRADOR);

    const acoes = await screen.findByRole("region", { name: "Por tipo de ação" });
    const linhas = within(acoes).getAllByRole("row");
    expect(linhas[1]).toHaveTextContent("Entrada no sistema");
    expect(linhas[1]).toHaveTextContent("80");
    /* A barra repete o número: fica fora da leitura de quem usa leitor de tela. */
    expect(linhas[1].querySelector(".contagem__barra").closest("td")).toHaveAttribute(
      "aria-hidden",
      "true",
    );

    const dias = screen.getByRole("region", { name: "Por dia" });
    expect(within(dias).getByText("30/09/2026")).toBeVisible();
  });

  it("lista as pessoas que mais fizeram e a linha das outras, com o total de pessoas", async () => {
    comOperacoes();
    renderizar("/relatorios/operacoes", ADMINISTRADOR);

    const pessoas = await screen.findByRole("region", { name: "Por pessoa" });
    expect(within(pessoas).getByText("as 2 que mais fizeram")).toBeVisible();
    const linhas = within(pessoas).getAllByRole("row");
    expect(linhas.at(-1)).toHaveTextContent("Outras 16 pessoas");
    expect(linhas.at(-1)).toHaveTextContent("20");
    expect(pessoas).toHaveTextContent("O arquivo CSV traz todas as pessoas");
    const total = screen.getByRole("region", { name: "Total do intervalo" });
    expect(total).toHaveTextContent("Pessoas18");
  });

  it("os filtros vão para a API e para o CSV, e o recorte diz quem e o quê pelo nome", async () => {
    const pedidos = comOperacoes({ ...OPERACOES, autor: 1, acao: "USUARIO_CRIADO", outras_pessoas: null });
    const usuario = userEvent.setup();
    renderizar("/relatorios/operacoes", ADMINISTRADOR);

    await usuario.selectOptions(await screen.findByLabelText("Quem fez"), "1");
    await usuario.selectOptions(screen.getByLabelText("Ação"), "USUARIO_CRIADO");
    await screen.findByText(/feitas por Chefia · ação: Usuário criado/);

    const consulta = new URL(ultimo(pedidos, "/api/relatorios/operacoes"), "http://local");
    expect(Object.fromEntries(consulta.searchParams)).toEqual({ autor: "1", acao: "USUARIO_CRIADO" });
    expect(screen.getByRole("link", { name: "Exportar CSV" })).toHaveAttribute(
      "href",
      "/api/relatorios/operacoes/exportacao.csv?autor=1&acao=USUARIO_CRIADO",
    );
  });

  it("leva à trilha com o mesmo recorte, e as datas que valeram", async () => {
    comOperacoes();
    renderizar("/relatorios/operacoes?acao=LOGIN_SUCESSO", ADMINISTRADOR);

    const link = await screen.findByRole("link", { name: "Ver estas operações na trilha" });
    expect(link).toHaveAttribute(
      "href",
      "/auditoria?de=2026-09-02&ate=2026-10-01&acao=LOGIN_SUCESSO",
    );
  });

  it("recorte sem operação diz isso, em vez de três tabelas vazias", async () => {
    comOperacoes({ ...OPERACOES, total: 0, pessoas: 0, por_acao: [], por_usuario: [], outras_pessoas: null, por_dia: [] });
    renderizar("/relatorios/operacoes", ADMINISTRADOR);

    expect(await screen.findByText("Nenhuma operação nesse recorte")).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("datas invertidas mostram a recusa da API, com a ajuda", async () => {
    comPedidos({
      "GET /api/auditoria/acoes": ACOES,
      "GET /api/usuarios": USUARIOS,
      "GET /api/relatorios/operacoes": () => ({
        status: 422,
        corpo: {
          detail: {
            erro: "A data inicial é depois da final.",
            ajuda: "Troque as datas, ou deixe uma delas em branco.",
          },
        },
      }),
    });
    renderizar("/relatorios/operacoes?de=2026-10-10&ate=2026-10-01", ADMINISTRADOR);

    expect(await screen.findByRole("alert")).toHaveTextContent("A data inicial é depois da final.");
    expect(screen.getByText("Troque as datas, ou deixe uma delas em branco.")).toBeVisible();
  });
});
