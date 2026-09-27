import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { simularApi } from "../testes/preparar";
import Comparacao from "./Comparacao";
import Execucoes from "./Execucoes";

const GESTOR = ["painel", "campanha", "execucoes", "execucao"];

function plano(extra = {}) {
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
    periodo_base: { id: 12, data_inicio: "2026-09-14", data_fim: "2026-09-20" },
    modelo_versao: "rede-1",
    viavel: true,
    restricao_violada: null,
    motivo: null,
    ajuda: null,
    uplift_total: "47320.00",
    custo_total: "11640.00",
    tempo_ms: 62,
    parcial: false,
    acoes: 43,
    elegiveis: 469,
    excluidos: null,
    cotas: [{ categoria_id: 3, nome: "Pizzaria", acoes: 5, minimo: 5, maximo: 45 }],
    folga_orcamento: "360.00",
    folga_acoes: 2,
    ganho_guloso: "45000.00",
    itens: null,
    ...extra,
  };
}

function item(parceiro_id, parceiro, situacao, a, b) {
  return {
    parceiro_id,
    parceiro,
    segmento: "TOP",
    situacao,
    acao_a: a?.[0] ?? null,
    ganho_a: a?.[1] ?? null,
    acao_b: b?.[0] ?? null,
    ganho_b: b?.[1] ?? null,
  };
}

function comparacao(extra = {}) {
  return {
    a: plano({ id: 6, iniciada_em: "2026-09-26T11:00:00Z" }),
    b: plano({
      parametros: { ...plano().parametros, orcamento: "15000.00" },
      uplift_total: "50320.00",
      custo_total: "14600.00",
      acoes: 50,
    }),
    parametros_diferentes: ["orcamento"],
    mesmas_previsoes: true,
    diferenca_uplift: "3000.00",
    diferenca_custo: "2960.00",
    diferenca_acoes: 7,
    resumo: { mudaram: 1, so_a: 0, so_b: 1, iguais: 1 },
    itens: [
      item(1, "Villa da Praça", "MUDOU", ["Visita de relacionamento", "4180.00"], ["Destaque na vitrine", "4900.00"]),
      item(2, "Quintal da Serra", "SO_B", null, ["Cupom de primeira compra", "900.00"]),
      item(3, "Recanto do Vale", "IGUAL", ["Visita de relacionamento", "700.00"], ["Visita de relacionamento", "700.00"]),
    ],
    ...extra,
  };
}

function renderizar(caminho) {
  return render(
    <ContextoSessao.Provider value={{ usuario: { nome: "Quem Testa", telas: GESTOR }, sair: () => {} }}>
      <MemoryRouter initialEntries={[caminho]}>
        <Routes>
          <Route path="/execucoes" element={<Execucoes />} />
          <Route path="/execucoes/comparar" element={<Comparacao />} />
        </Routes>
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

describe("comparação de dois planos (RF35)", () => {
  it("os parâmetros lado a lado, com o que mudou marcado em texto", async () => {
    simularApi({ "GET /api/otimizacoes/comparacao": { corpo: comparacao() } });
    renderizar("/execucoes/comparar?a=6&b=7");

    const tabela = await screen.findByRole("table", { name: "Os parâmetros dos dois planos" });
    const orcamento = within(tabela).getByRole("rowheader", { name: /Orçamento/ }).closest("tr");
    expect(orcamento).toHaveTextContent("mudou");
    expect(orcamento).toHaveTextContent("R$ 12.000,00R$ 15.000,00");
    const maximo = within(tabela).getByRole("rowheader", { name: "Máximo de ações" }).closest("tr");
    expect(maximo).not.toHaveTextContent("mudou");
    expect(screen.getByText("1 parâmetro mudou")).toBeInTheDocument();
  });

  it("o resultado de cada um, e a diferença do B para o A", async () => {
    simularApi({ "GET /api/otimizacoes/comparacao": { corpo: comparacao() } });
    renderizar("/execucoes/comparar?a=6&b=7");

    const tabela = await screen.findByRole("table", { name: "O resultado dos dois planos e a diferença" });
    const linha = (rotulo) => within(tabela).getByRole("rowheader", { name: rotulo }).closest("tr");
    expect(linha("Ganho esperado")).toHaveTextContent("+R$ 3.000,00 (+6,34%)");
    expect(linha("Ações")).toHaveTextContent("+7");
  });

  it("parceiro a parceiro: as diferenças primeiro, e os iguais a um clique", async () => {
    simularApi({ "GET /api/otimizacoes/comparacao": { corpo: comparacao() } });
    const usuario = userEvent.setup();
    renderizar("/execucoes/comparar?a=6&b=7");

    expect(await screen.findByText("1 mudou de ação · 0 só no A · 1 só no B · 1 igual")).toBeInTheDocument();
    const tabela = screen.getByRole("table", { name: /Os parceiros dos dois planos/ });
    const linhas = () => within(tabela).getAllByRole("row").slice(1);
    expect(linhas().map((l) => l.cells[0].textContent)).toEqual(["Villa da Praça", "Quintal da Serra"]);
    expect(linhas()[0]).toHaveTextContent("Visita de relacionamentoganho de R$ 4.180,00");
    expect(linhas()[1]).toHaveTextContent("sem ação");
    expect(linhas()[1]).toHaveTextContent("só no plano B");

    await usuario.click(screen.getByRole("button", { name: "Mostrar também o que ficou igual" }));
    expect(linhas().map((l) => l.cells[0].textContent)).toContain("Recanto do Vale");
  });

  it("avisa quando os dois partiram de previsões diferentes", async () => {
    const outra = comparacao({ mesmas_previsoes: false });
    outra.b.modelo_versao = "rede-2";
    simularApi({ "GET /api/otimizacoes/comparacao": { corpo: outra } });
    renderizar("/execucoes/comparar?a=6&b=7");
    expect(await screen.findByText("Os dois planos partiram de previsões diferentes.")).toBeInTheDocument();
    expect(screen.getByText(/O plano A usou a rede-1 e o plano B, a rede-2/)).toBeInTheDocument();
  });

  it("a recusa da API aparece com a frase dela", async () => {
    simularApi({
      "GET /api/otimizacoes/comparacao": {
        status: 422,
        corpo: {
          detail: {
            erro: "Esta execução não tem plano para comparar.",
            ajuda: "Só se comparam planos calculados e viáveis: escolha outra no histórico.",
          },
        },
      },
    });
    renderizar("/execucoes/comparar?a=6&b=5");
    expect(await screen.findByRole("alert")).toHaveTextContent("Esta execução não tem plano para comparar.");
  });

  it("sem os dois planos no endereço, diz como escolher", () => {
    renderizar("/execucoes/comparar?a=6");
    expect(screen.getByText("Escolha dois planos para comparar")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para as execuções" })).toHaveAttribute("href", "/execucoes");
  });

  it("no histórico, dois planos marcados abrem a comparação, do mais antigo para o mais novo", async () => {
    const inviavel = plano({ id: 5, viavel: false, restricao_violada: "orcamento", uplift_total: null });
    simularApi({
      "GET /api/otimizacoes": {
        corpo: { itens: [plano(), plano({ id: 6 }), inviavel], total: 3, pagina: 1, tamanho: 20 },
      },
      "GET /api/otimizacoes/comparacao": (url) => {
        const busca = new URL(url, "http://x").searchParams;
        return busca.get("a") === "6" && busca.get("b") === "7" ? { corpo: comparacao() } : { status: 400, corpo: {} };
      },
    });
    const usuario = userEvent.setup();
    renderizar("/execucoes");

    const botao = await screen.findByRole("button", { name: "Comparar os dois" });
    expect(botao).toBeDisabled();
    const caixas = screen.getAllByRole("checkbox");
    // A execução inviável não tem plano: não se marca.
    expect(caixas).toHaveLength(2);
    await usuario.click(caixas[0]);
    expect(screen.getByText("Marque mais um plano.")).toBeInTheDocument();
    await usuario.click(caixas[1]);
    await usuario.click(botao);
    expect(await screen.findByRole("table", { name: "Os parâmetros dos dois planos" })).toBeInTheDocument();
  });
});
