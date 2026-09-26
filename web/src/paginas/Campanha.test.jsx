import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Campanha, { INTERVALO_MS } from "./Campanha";

const BASE = { id: 12, data_inicio: "2026-09-14", data_fim: "2026-09-20" };
const ACOES = [
  {
    id: 1,
    nome: "Visita de relacionamento",
    custo_unitario: "90.00",
    efeito_crescimento: "0.0600",
    efeito_retencao: "0.3000",
    ativa: true,
  },
  {
    id: 2,
    nome: "Destaque na vitrine",
    custo_unitario: "260.00",
    efeito_crescimento: "0.1400",
    efeito_retencao: "0.0500",
    ativa: true,
  },
];

function execucao(extra = {}) {
  return {
    id: 7,
    situacao: "CONCLUIDA",
    autor: "Gestora",
    modo: "SERIAL",
    iniciada_em: "2026-09-26T12:00:00Z",
    concluida_em: "2026-09-26T12:00:06Z",
    parametros: {
      orcamento: "12000.00",
      maximo_acoes: 45,
      cota_cauda_longa: "0.3000",
      cotas_categoria: [],
      aplicacao_inicio: "2026-09-21",
      aplicacao_fim: "2026-09-27",
    },
    periodo_base: BASE,
    modelo_versao: "rede-1",
    viavel: true,
    restricao_violada: null,
    motivo: null,
    ajuda: null,
    uplift_total: "47320.00",
    custo_total: "11640.00",
    tempo_ms: 6400,
    parcial: false,
    acoes: 2,
    elegiveis: 469,
    excluidos: null,
    cotas: [{ categoria_id: null, nome: "Cauda longa", acoes: 14, minimo: 14, maximo: 45 }],
    folga_orcamento: "360.00",
    folga_acoes: 43,
    ganho_guloso: "45000.00",
    itens: [
      {
        parceiro_id: 16,
        parceiro: "Villa da Praça",
        segmento: "EM_RISCO",
        categoria: "Restaurante",
        cauda_longa: true,
        acao_id: 1,
        acao: "Visita de relacionamento",
        custo: "90.00",
        ganho: "4180.00",
      },
      {
        parceiro_id: 21,
        parceiro: "Quintal da Serra",
        segmento: "EM_ASCENSAO",
        categoria: null,
        cauda_longa: false,
        acao_id: 2,
        acao: "Destaque na vitrine",
        custo: "260.00",
        ganho: "3940.00",
      },
    ],
    ...extra,
  };
}

const SEM_GPU = "Não há GPU compatível disponível nesta instalação.";

function estado(extra = {}) {
  return {
    modelo_versao: "rede-1",
    periodo_base: BASE,
    top_n: 15,
    elegiveis: 469,
    excluidos: {
      historico_curto: 31,
      fora_do_periodo: 0,
      sem_previsao: 0,
      inativos: 2,
      em_prospeccao: 0,
    },
    sem_categoria: 12,
    categorias: [
      { id: 3, nome: "Pizzaria", elegiveis: 42 },
      { id: 4, nome: "Mercado", elegiveis: 38 },
    ],
    acoes: ACOES,
    em_andamento: null,
    ultima: null,
    pode_executar: true,
    motivo_bloqueio: null,
    pode_editar_catalogo: true,
    modos: [
      { modo: "GPU", disponivel: false, motivo: SEM_GPU },
      { modo: "CPU_PARALELO", disponivel: true, motivo: null },
      { modo: "SERIAL", disponivel: true, motivo: null },
    ],
    modo_automatico: "CPU_PARALELO",
    ...extra,
  };
}

function renderizar() {
  return render(
    <MemoryRouter>
      <Campanha />
    </MemoryRouter>,
  );
}

describe("tela da campanha", () => {
  it("sem modelo treinado, diz por quê — com a frase da API", async () => {
    simularApi({
      "GET /api/campanha": {
        corpo: estado({
          modelo_versao: null,
          periodo_base: null,
          elegiveis: 0,
          excluidos: null,
          pode_executar: false,
          motivo_bloqueio: "O modelo ainda não foi treinado.",
        }),
      },
    });
    renderizar();
    expect(await screen.findByText("O modelo ainda não foi treinado.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Calcular plano" })).not.toBeInTheDocument();
  });

  it("diz quem entra e quem fica fora antes de a pessoa configurar", async () => {
    simularApi({ "GET /api/campanha": { corpo: estado() } });
    renderizar();
    const nota = await screen.findByText(/parceiros podem receber ação/);
    expect(nota).toHaveTextContent("469 parceiros podem receber ação");
    expect(nota).toHaveTextContent("31 com histórico curto, 2 inativos");
    // O período de aplicação já vem sugerido: o seguinte ao das previsões.
    expect(screen.getByLabelText(/Início da aplicação/)).toHaveValue("2026-09-21");
    expect(screen.getByLabelText(/Fim da aplicação/)).toHaveValue("2026-09-27");
  });

  it("calcular manda frações e reais no formato da API, acompanha e mostra o plano", async () => {
    let enviado = null;
    let terminou = false;
    simularApi({
      "GET /api/campanha": () => ({
        corpo: terminou ? estado({ ultima: execucao() }) : estado(),
      }),
      "POST /api/otimizacoes": (_url, opcoes) => {
        enviado = JSON.parse(opcoes.body);
        return { status: 202, corpo: execucao({ situacao: "EM_ANDAMENTO", itens: null }) };
      },
      "GET /api/otimizacoes/7": () => {
        terminou = true;
        return { corpo: execucao() };
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(await screen.findByLabelText(/Orçamento/), "12.000,00");
    await usuario.type(screen.getByLabelText(/Máximo de ações/), "45");
    await usuario.type(screen.getByLabelText(/Cota mínima da cauda longa/), "30");
    await usuario.click(screen.getByRole("button", { name: "Adicionar cota de categoria" }));
    await usuario.selectOptions(screen.getByLabelText("Categoria da cota 1"), "3");
    await usuario.type(screen.getByLabelText("mín. %"), "10");

    await usuario.click(screen.getByRole("button", { name: "Calcular plano" }));
    expect(enviado).toBeNull(); // a confirmação vem antes
    expect(screen.getByRole("group", { name: "Confirmação" })).toHaveTextContent("R$ 12.000,00");

    await usuario.click(screen.getByRole("button", { name: "Calcular" }));
    expect(enviado).toEqual({
      orcamento: "12000.00",
      maximo_acoes: 45,
      cota_cauda_longa: "0.3000",
      cotas_categoria: [{ categoria_id: 3, minimo: "0.1000", maximo: null }],
      aplicacao_inicio: "2026-09-21",
      aplicacao_fim: "2026-09-27",
      modo: null, // sem escolha: a API roda o mais rápido disponível
    });
    expect(await screen.findByText("Calculando o plano…")).toBeInTheDocument();

    await waitFor(
      () =>
        expect(screen.getByRole("status")).toHaveTextContent(
          "Plano calculado: 2 ações, ganho esperado de R$ 47.320,00.",
        ),
      { timeout: INTERVALO_MS + 2000 },
    );
    const tabela = screen.getByRole("table", { name: /Ações do plano/ });
    const linhas = within(tabela).getAllByRole("row");
    expect(linhas[1]).toHaveTextContent("Villa da Praça");
    expect(linhas[1]).toHaveTextContent("Visita de relacionamento");
    expect(linhas[2]).toHaveTextContent("Pendente"); // sem categoria confirmada
    expect(screen.getByRole("link", { name: "Villa da Praça" })).toHaveAttribute("href", "/parceiros/16");
    expect(screen.getByText(/acima do plano guloso/)).toBeInTheDocument();
  });

  it("o modo: o automático diz qual roda, o indisponível fica desabilitado com o porquê", async () => {
    let enviado = null;
    simularApi({
      "GET /api/campanha": { corpo: estado() },
      "POST /api/otimizacoes": (_url, opcoes) => {
        enviado = JSON.parse(opcoes.body);
        return { status: 202, corpo: execucao({ situacao: "EM_ANDAMENTO", itens: null }) };
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    const modo = await screen.findByLabelText("Modo de execução");
    expect(modo).toHaveValue("");
    expect(within(modo).getByRole("option", { name: "Automático (CPU paralelo)" })).toBeInTheDocument();
    expect(within(modo).getByRole("option", { name: "GPU — indisponível" })).toBeDisabled();
    expect(within(modo).getByRole("option", { name: "Serial" })).toBeEnabled();
    // A opção desabilitada não se explica sozinha: o porquê está na ajuda do campo.
    expect(modo).toHaveAccessibleDescription(
      `Sem escolha, roda o mais rápido disponível nesta instalação: CPU paralelo. GPU: ${SEM_GPU}`,
    );

    await usuario.selectOptions(modo, "SERIAL");
    expect(modo).toHaveAccessibleDescription(expect.stringContaining("A referência, em Python"));
    await usuario.type(screen.getByLabelText(/Orçamento/), "12.000,00");
    await usuario.type(screen.getByLabelText(/Máximo de ações/), "45");
    await usuario.click(screen.getByRole("button", { name: "Calcular plano" }));
    expect(screen.getByRole("group", { name: "Confirmação" })).toHaveTextContent("no modo serial?");
    await usuario.click(screen.getByRole("button", { name: "Calcular" }));
    expect(enviado.modo).toBe("SERIAL");
  });

  it("o plano diz em que modo rodou, com as threads, e a troca quando houve", async () => {
    const troca = `Pedido em GPU, calculado em CPU paralelo: n${SEM_GPU.slice(1)}`;
    simularApi({
      "GET /api/campanha": {
        corpo: estado({
          ultima: execucao({ modo: "CPU_PARALELO", threads: 8, tempo_ms: 62, substituicao: troca }),
        }),
      },
    });
    renderizar();
    expect(await screen.findByText(/CPU paralelo, 8 threads · 62 ms/)).toBeInTheDocument();
    expect(screen.getByText(troca)).toBeInTheDocument();
  });

  it("campanha inviável: sem plano, com a restrição e o que falta", async () => {
    simularApi({
      "GET /api/campanha": {
        corpo: estado({
          ultima: execucao({
            viavel: false,
            restricao_violada: "orcamento",
            motivo:
              "As cotas mínimas exigem pelo menos R$ 1.350,00, acima do orçamento de R$ 100,00: " +
              "faltam R$ 1.250,00.",
            ajuda: "Aumente o orçamento ou reduza as cotas mínimas.",
            uplift_total: null,
            itens: [],
          }),
        }),
      },
    });
    renderizar();
    expect(await screen.findByText(/Sem solução viável\. As cotas mínimas exigem/)).toHaveTextContent(
      "faltam R$ 1.250,00",
    );
    expect(screen.getByText("Aumente o orçamento ou reduza as cotas mínimas.")).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: /Ações do plano/ })).not.toBeInTheDocument();
  });

  it("o analista consulta: vê o motivo da API no lugar do botão, e não edita o catálogo", async () => {
    simularApi({
      "GET /api/campanha": {
        corpo: estado({
          ultima: execucao(),
          pode_executar: false,
          motivo_bloqueio: "Só o gestor calcula o plano; o analista consulta.",
          pode_editar_catalogo: false,
        }),
      },
    });
    renderizar();
    expect(await screen.findByText("Só o gestor calcula o plano; o analista consulta.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Calcular plano" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nova ação" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Editar/ })).not.toBeInTheDocument();
    // O plano continua visível para consulta.
    expect(screen.getByRole("table", { name: /Ações do plano/ })).toBeInTheDocument();
  });

  it("a recusa do servidor aparece com a ajuda, e a tela passa a acompanhar o que já roda", async () => {
    let posts = 0;
    simularApi({
      "GET /api/campanha": () => ({
        corpo: posts ? estado({ em_andamento: execucao({ id: 9, situacao: "EM_ANDAMENTO" }) }) : estado(),
      }),
      "POST /api/otimizacoes": () => {
        posts += 1;
        return {
          status: 409,
          corpo: {
            detail: {
              erro: "Já existe uma otimização em andamento.",
              ajuda: "Acompanhe a atual; quando ela terminar, você pode calcular outra.",
              em_andamento: 9,
            },
          },
        };
      },
      "GET /api/otimizacoes/9": { corpo: execucao({ id: 9, situacao: "EM_ANDAMENTO" }) },
    });
    const usuario = userEvent.setup();
    renderizar();
    await usuario.type(await screen.findByLabelText(/Orçamento/), "5000");
    await usuario.type(screen.getByLabelText(/Máximo de ações/), "30");
    await usuario.click(screen.getByRole("button", { name: "Calcular plano" }));
    await usuario.click(screen.getByRole("button", { name: "Calcular" }));

    expect(await screen.findByText("Já existe uma otimização em andamento.")).toBeInTheDocument();
    expect(await screen.findByText("Calculando o plano…")).toBeInTheDocument();
  });

  it("os erros de campo da API aparecem embaixo do campo", async () => {
    simularApi({
      "GET /api/campanha": { corpo: estado() },
      "POST /api/otimizacoes": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "orcamento", mensagem: "Informe um número." }],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await usuario.type(await screen.findByLabelText(/Orçamento/), "abc");
    await usuario.click(screen.getByRole("button", { name: "Calcular plano" }));
    await usuario.click(screen.getByRole("button", { name: "Calcular" }));
    expect(await screen.findByText("Informe um número.")).toBeInTheDocument();
    expect(screen.getByLabelText(/Orçamento/)).toHaveAttribute("aria-invalid", "true");
  });

  it("o gestor edita o efeito de uma ação em porcentagem, e a API recebe a fração", async () => {
    let enviado = null;
    simularApi({
      "GET /api/campanha": { corpo: estado() },
      "PATCH /api/acoes-comerciais/1": (_url, opcoes) => {
        enviado = JSON.parse(opcoes.body);
        return { corpo: { ...ACOES[0], efeito_retencao: "0.2500" } };
      },
    });
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Editar Visita de relacionamento" }));
    const retencao = screen.getByLabelText("Efeito de retenção, em %");
    expect(retencao).toHaveValue("30");
    await usuario.clear(retencao);
    await usuario.type(retencao, "25");
    await usuario.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() => expect(enviado).not.toBeNull());
    expect(enviado).toEqual({
      nome: "Visita de relacionamento",
      custo_unitario: "90.00",
      efeito_crescimento: "0.0600",
      efeito_retencao: "0.2500",
      ativa: true,
    });
  });
});
