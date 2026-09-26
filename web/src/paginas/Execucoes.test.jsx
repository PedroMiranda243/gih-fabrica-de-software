import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { simularApi } from "../testes/preparar";
import Execucao from "./Execucao";
import Execucoes from "./Execucoes";

const GESTOR = ["painel", "campanha", "execucoes", "execucao"];
const ADMINISTRADOR = ["painel", "usuarios", "execucoes"];
const BASE = { id: 12, data_inicio: "2026-09-14", data_fim: "2026-09-20" };

function execucao(extra = {}) {
  return {
    id: 7,
    situacao: "CONCLUIDA",
    autor: "Gestora",
    modo: "CPU_PARALELO",
    substituicao: null,
    threads: 8,
    iniciada_em: "2026-09-26T12:00:00Z",
    concluida_em: "2026-09-26T12:00:01Z",
    parametros: {
      orcamento: "12000.00",
      maximo_acoes: 45,
      cota_cauda_longa: "0.3000",
      cotas_categoria: [{ categoria_id: 3, minimo: "0.1000", maximo: null }],
      aplicacao_inicio: "2026-09-21",
      aplicacao_fim: "2026-09-27",
      modo: null,
    },
    periodo_base: BASE,
    modelo_versao: "rede-1",
    viavel: true,
    restricao_violada: null,
    motivo: null,
    ajuda: null,
    uplift_total: "47320.00",
    custo_total: "11640.00",
    tempo_ms: 62,
    parcial: false,
    acoes: 2,
    elegiveis: 469,
    excluidos: null,
    cotas: [
      { categoria_id: 3, nome: "Pizzaria", acoes: 5, minimo: 5, maximo: 45 },
      { categoria_id: null, nome: "Cauda longa", acoes: 14, minimo: 14, maximo: 45 },
    ],
    folga_orcamento: "360.00",
    folga_acoes: 43,
    ganho_guloso: "45000.00",
    itens: null,
    ...extra,
  };
}

const HISTORICO = [
  execucao({
    substituicao: "Pedido em GPU, calculado em CPU paralelo: não há GPU compatível.",
    parametros: { ...execucao().parametros, modo: "GPU" },
  }),
  execucao({
    id: 6,
    modo: "SERIAL",
    threads: null,
    tempo_ms: 6400,
    viavel: false,
    restricao_violada: "orcamento",
    motivo: "As cotas mínimas exigem pelo menos R$ 1.350,00: faltam R$ 1.250,00.",
    acoes: null,
    uplift_total: null,
  }),
  execucao({
    id: 5,
    situacao: "FALHOU",
    modo: "SERIAL",
    threads: null,
    tempo_ms: null,
    viavel: null,
    motivo: "A otimização falhou por um erro interno (registro abc123).",
    autor: null,
  }),
];

function renderizar(telas, caminho = "/execucoes") {
  return render(
    <ContextoSessao.Provider value={{ usuario: { nome: "Quem Testa", telas }, sair: () => {} }}>
      <MemoryRouter initialEntries={[caminho]}>
        <Routes>
          <Route path="/execucoes" element={<Execucoes />} />
          <Route path="/execucoes/:id" element={<Execucao />} />
        </Routes>
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

describe("histórico de execuções", () => {
  it("cada linha traz autor, data, parâmetros, modo, tempo e resultado (RF34)", async () => {
    simularApi({ "GET /api/otimizacoes": { corpo: { itens: HISTORICO, total: 3, pagina: 1, tamanho: 20 } } });
    renderizar(GESTOR);

    const tabela = await screen.findByRole("table", { name: /Execuções do otimizador/ });
    const [, viavel, inviavel, falhou] = within(tabela).getAllByRole("row");
    expect(viavel).toHaveTextContent("Gestora");
    expect(viavel).toHaveTextContent("R$ 12.000,00 · até 45 ações · cauda longa ≥ 30% · 1 cota de categoria");
    expect(viavel).toHaveTextContent("CPU paralelo, 8 threads");
    expect(viavel).toHaveTextContent("pedido em GPU");
    expect(viavel).toHaveTextContent("62 ms");
    expect(viavel).toHaveTextContent("2 ações · ganho de R$ 47.320,00");
    expect(inviavel).toHaveTextContent("6,4 s");
    expect(inviavel).toHaveTextContent("Sem solução viávelrestrição: orçamento");
    expect(falhou).toHaveTextContent("Terminal");
    expect(falhou).toHaveTextContent("Falhou");
    expect(falhou).toHaveTextContent("registro abc123");
    expect(screen.getByText("3 no total")).toBeInTheDocument();
  });

  it("quem abre o plano tem o link; o Administrador vê o resumo, sem ele", async () => {
    const rotas = { "GET /api/otimizacoes": { corpo: { itens: HISTORICO, total: 3, pagina: 1, tamanho: 20 } } };
    simularApi(rotas);
    const { unmount } = renderizar(GESTOR);
    const tabela = await screen.findByRole("table", { name: /Execuções do otimizador/ });
    expect(within(tabela).getAllByRole("link")[0]).toHaveAttribute("href", "/execucoes/7");
    expect(screen.queryByText(/O plano de cada execução, parceiro a parceiro/)).not.toBeInTheDocument();
    unmount();

    renderizar(ADMINISTRADOR);
    const doAdmin = await screen.findByRole("table", { name: /Execuções do otimizador/ });
    expect(within(doAdmin).queryAllByRole("link")).toHaveLength(0);
    expect(screen.getByText(/O plano de cada execução, parceiro a parceiro/)).toBeInTheDocument();
  });

  it("pagina de 20 em 20", async () => {
    const paginas = [];
    simularApi({
      "GET /api/otimizacoes": (url) => {
        const pagina = Number(new URL(url, "http://x").searchParams.get("pagina"));
        paginas.push(pagina);
        return { corpo: { itens: [execucao({ id: 100 - pagina })], total: 25, pagina, tamanho: 20 } };
      },
    });
    const usuario = userEvent.setup();
    renderizar(GESTOR);

    expect(await screen.findByText("1–20 de 25")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Próxima" }));
    expect(await screen.findByText("21–25 de 25")).toBeInTheDocument();
    expect(paginas).toEqual([1, 2]);
    expect(screen.getByRole("button", { name: "Próxima" })).toBeDisabled();
  });

  it("sem execução ainda, diz onde elas nascem", async () => {
    simularApi({ "GET /api/otimizacoes": { corpo: { itens: [], total: 0, pagina: 1, tamanho: 20 } } });
    renderizar(GESTOR);
    expect(await screen.findByText("Nenhuma execução ainda")).toBeInTheDocument();
  });
});

describe("execução aberta pelo histórico", () => {
  it("mostra o que foi pedido e o plano que saiu", async () => {
    const itens = [
      {
        parceiro_id: 16,
        parceiro: "Villa da Praça",
        segmento: "EM_RISCO",
        categoria: "Pizzaria",
        cauda_longa: true,
        acao_id: 1,
        acao: "Visita de relacionamento",
        custo: "90.00",
        ganho: "4180.00",
      },
    ];
    simularApi({ "GET /api/otimizacoes/7": { corpo: execucao({ itens }) } });
    renderizar(GESTOR, "/execucoes/7");

    const pedido = await screen.findByRole("region", { name: "O que foi pedido" });
    expect(pedido).toHaveTextContent("Por Gestora");
    expect(pedido).toHaveTextContent("R$ 12.000,00");
    expect(pedido).toHaveTextContent("ao menos 30% das ações");
    expect(pedido).toHaveTextContent("Pizzaria: mín. 10%");
    expect(pedido).toHaveTextContent("Automático, o mais rápido disponível");

    const plano = screen.getByRole("region", { name: /Plano recomendado/ });
    expect(plano).toHaveTextContent("CPU paralelo, 8 threads · 62 ms");
    expect(within(plano).getByRole("link", { name: "Villa da Praça" })).toHaveAttribute("href", "/parceiros/16");
    expect(screen.getByRole("link", { name: "Execuções" })).toHaveAttribute("href", "/execucoes");
  });

  it("execução que não existe", async () => {
    simularApi({});
    renderizar(GESTOR, "/execucoes/999");
    expect(await screen.findByText("Execução não encontrada")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para as execuções" })).toHaveAttribute("href", "/execucoes");
  });
});
