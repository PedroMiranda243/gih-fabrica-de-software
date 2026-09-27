import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Mensagens, { INTERVALO_MS } from "./Mensagens";

const FORA_DO_AR = "O serviço do modelo de linguagem não respondeu.";

function estado(extra = {}) {
  return {
    assistente: { disponivel: true, modelo: "qwen2.5:7b", motivo: null },
    em_andamento: null,
    ultimo: null,
    maximo: 500,
    ...extra,
  };
}

const CATEGORIAS = [
  { id: 1, nome: "Mercado", ativa: true },
  { id: 2, nome: "Pizzaria", ativa: true },
];

const HISTORICO = {
  itens: [
    {
      id: 5,
      situacao: "CONCLUIDA",
      viavel: true,
      acoes: 23,
      concluida_em: "2026-09-27T14:05:00Z",
      parametros: { aplicacao_inicio: "2026-10-05", aplicacao_fim: "2026-10-11" },
    },
    { id: 4, situacao: "CONCLUIDA", viavel: false, acoes: null, concluida_em: "2026-09-27T13:00:00Z", parametros: {} },
    { id: 3, situacao: "FALHOU", viavel: null, acoes: null, concluida_em: null, parametros: {} },
  ],
  total: 3,
  pagina: 1,
  tamanho: 20,
};

function previa(extra = {}) {
  return {
    descricao: "Em risco",
    total: 2,
    parceiros: [
      { id: 11, nome: "Beta", segmento: "EM_RISCO", categoria: "Mercado", acao: null },
      { id: 12, nome: "Delta", segmento: "EM_RISCO", categoria: null, acao: null },
    ],
    excluidos: { desativado: 1 },
    maximo: 500,
    pode_gerar: true,
    motivo: null,
    ...extra,
  };
}

function mensagem(id, parceiro, extra = {}) {
  return {
    id,
    parceiro_id: id + 10,
    parceiro,
    segmento: "EM_RISCO",
    acao: null,
    texto: `Olá, ${parceiro}! Estamos aqui para ajudar.`,
    texto_gerado: `Olá, ${parceiro}! Estamos aqui para ajudar.`,
    estado: "PENDENTE",
    redator: "MODELO",
    modelo: "qwen2.5:7b",
    motivo_redator: null,
    fatos: [
      { fato: "Parceiro", valor: parceiro },
      { fato: "Faturamento no período", valor: "R$ 7.000,00" },
    ],
    lote_id: 9,
    gerada_em: "2026-09-27T14:10:00Z",
    ...extra,
  };
}

function lote(extra = {}) {
  return {
    id: 9,
    situacao: "CONCLUIDA",
    autor: "Analista",
    publico: { tipo: "FILTRO", segmento: "EM_RISCO", categoria_id: null, execucao_id: null, parceiros: null },
    descricao: "Em risco",
    iniciado_em: "2026-09-27T14:10:00Z",
    concluido_em: "2026-09-27T14:11:00Z",
    total: 2,
    geradas: 2,
    pelo_modelo: 2,
    falhas: [],
    modelo: "qwen2.5:7b",
    motivo: null,
    mensagens: [mensagem(1, "Beta"), mensagem(2, "Delta")],
    ...extra,
  };
}

function basico(extra = {}) {
  return {
    "GET /api/mensagens/geracao": { corpo: estado() },
    "GET /api/categorias": { corpo: CATEGORIAS },
    "GET /api/otimizacoes": { corpo: HISTORICO },
    ...extra,
  };
}

function corpoDe(chamadas, metodo, caminho) {
  const chamada = chamadas.mock.calls.find(
    ([url, opcoes]) => String(url).split("?")[0] === caminho && (opcoes?.method ?? "GET") === metodo,
  );
  return chamada ? JSON.parse(chamada[1].body) : undefined;
}

function renderizar(endereco = "/mensagens") {
  return render(
    <MemoryRouter initialEntries={[endereco]}>
      <Mensagens />
    </MemoryRouter>,
  );
}

describe("tela de mensagens", () => {
  it("abre sem geração, com o próximo passo dito", async () => {
    simularApi(basico());
    renderizar();
    expect(await screen.findByText("Nenhuma mensagem gerada ainda.")).toBeInTheDocument();
    expect(screen.getByText(/Redigidas pelo qwen2\.5:7b/)).toBeInTheDocument();
    expect(screen.queryByText("O assistente está indisponível.")).not.toBeInTheDocument();
  });

  it("sem o assistente, diz por quê, e que a fila funciona igual (ADR-013)", async () => {
    simularApi(
      basico({
        "GET /api/mensagens/geracao": {
          corpo: estado({ assistente: { disponivel: false, modelo: "qwen2.5:7b", motivo: FORA_DO_AR } }),
        },
      }),
    );
    renderizar();
    expect(await screen.findByText("O assistente está indisponível.")).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`${FORA_DO_AR} As mensagens saem do modelo fixo`))).toBeInTheDocument();
  });

  it("a prévia vem antes de gerar: quem entra, quem ficou de fora, e o botão com a conta", async () => {
    const chamadas = simularApi(basico({ "POST /api/mensagens/publico": { corpo: previa() } }));
    const usuario = userEvent.setup();
    renderizar();

    await usuario.selectOptions(await screen.findByLabelText("Segmento"), "EM_RISCO");
    await usuario.selectOptions(screen.getByLabelText("Categoria"), "1");
    await usuario.click(screen.getByRole("button", { name: "Ver quem entra" }));

    const tabela = await screen.findByRole("table", { name: "Parceiros que recebem mensagem" });
    expect(within(tabela).getAllByRole("row").slice(1).map((l) => l.cells[0].textContent)).toEqual(["Beta", "Delta"]);
    expect(screen.getByText(/Ficaram de fora: 1 parceiro \(desativado\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gerar 2 mensagens" })).toBeEnabled();
    expect(corpoDe(chamadas, "POST", "/api/mensagens/publico")).toEqual({
      tipo: "FILTRO",
      segmento: "EM_RISCO",
      categoria_id: 1,
    });
  });

  it("mudar o público apaga a prévia, que era de outro público", async () => {
    simularApi(basico({ "POST /api/mensagens/publico": { corpo: previa() } }));
    const usuario = userEvent.setup();
    renderizar();
    await usuario.selectOptions(await screen.findByLabelText("Segmento"), "EM_RISCO");
    await usuario.click(screen.getByRole("button", { name: "Ver quem entra" }));
    await screen.findByRole("button", { name: "Gerar 2 mensagens" });

    await usuario.selectOptions(screen.getByLabelText("Segmento"), "TOP");
    expect(screen.queryByRole("button", { name: "Gerar 2 mensagens" })).not.toBeInTheDocument();
  });

  it("o critério que falta é a API quem diz, com a frase dela", async () => {
    simularApi(
      basico({
        "POST /api/mensagens/publico": {
          status: 422,
          corpo: { erro: "Escolha um segmento, uma categoria, ou os dois.", campos: [] },
        },
      }),
    );
    const usuario = userEvent.setup();
    renderizar();
    await usuario.click(await screen.findByRole("button", { name: "Ver quem entra" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Escolha um segmento, uma categoria, ou os dois.");
  });

  it("público vazio ou grande demais não gera: a prévia diz por quê (UC10-E1)", async () => {
    simularApi(
      basico({
        "POST /api/mensagens/publico": {
          corpo: previa({
            total: 0,
            parceiros: [],
            excluidos: {},
            pode_gerar: false,
            motivo: "Nenhum parceiro ativo neste público: nada a gerar.",
          }),
        },
      }),
    );
    const usuario = userEvent.setup();
    renderizar();
    await usuario.selectOptions(await screen.findByLabelText("Segmento"), "RECEM_CHEGADO");
    await usuario.click(screen.getByRole("button", { name: "Ver quem entra" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nenhum parceiro ativo neste público");
    expect(screen.queryByRole("button", { name: /^Gerar/ })).not.toBeInTheDocument();
  });

  it("gera, e as mensagens aparecem conforme ficam prontas (UC10-A1)", async () => {
    let consultas = 0;
    const chamadas = simularApi(
      basico({
        "POST /api/mensagens/publico": { corpo: previa() },
        "POST /api/mensagens/lotes": {
          status: 202,
          corpo: lote({ situacao: "EM_ANDAMENTO", concluido_em: null, geradas: 0, pelo_modelo: 0, mensagens: null }),
        },
        "GET /api/mensagens/lotes/9": () => {
          consultas += 1;
          return consultas === 1
            ? {
                corpo: lote({
                  situacao: "EM_ANDAMENTO",
                  concluido_em: null,
                  geradas: 1,
                  pelo_modelo: 1,
                  mensagens: [mensagem(1, "Beta")],
                }),
              }
            : { corpo: lote() };
        },
      }),
    );
    const usuario = userEvent.setup();
    renderizar();
    await usuario.selectOptions(await screen.findByLabelText("Segmento"), "EM_RISCO");
    await usuario.click(screen.getByRole("button", { name: "Ver quem entra" }));
    await usuario.click(await screen.findByRole("button", { name: "Gerar 2 mensagens" }));

    expect(await screen.findByRole("heading", { name: "Gerando mensagens" })).toBeInTheDocument();
    expect(screen.getByText(/primeira mensagem pode levar cerca de um minuto/)).toBeInTheDocument();
    expect(corpoDe(chamadas, "POST", "/api/mensagens/lotes")).toEqual({
      tipo: "FILTRO",
      segmento: "EM_RISCO",
      categoria_id: null,
    });

    expect(
      await screen.findByText("1 de 2 prontas · 1 pelo assistente, 0 pelo modelo fixo", {}, { timeout: INTERVALO_MS + 2000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Andamento da geração" })).toHaveAttribute("value", "1");
    const lista = screen.getByRole("list", { name: "Mensagens geradas" });
    expect(within(lista).getAllByRole("listitem")).toHaveLength(1);

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Geração concluída: 2 de 2 mensagens."), {
      timeout: INTERVALO_MS * 2 + 2000,
    });
    expect(screen.getByText("2 mensagens geradas.")).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Mensagens geradas" })).getAllByRole("listitem")).toHaveLength(2);
  }, 15000);

  it("o cartão diz quem redigiu, por que saiu do modelo fixo, e os dados que ele usou", async () => {
    const fixa = mensagem(2, "Delta", {
      redator: "MODELO_FIXO",
      modelo: null,
      motivo_redator: "O texto do assistente trazia números que não vieram dos dados (13%), e foi trocado pelo modelo fixo.",
    });
    simularApi(
      basico({
        "GET /api/mensagens/geracao": { corpo: estado({ ultimo: lote({ mensagens: null }) }) },
        "GET /api/mensagens/lotes/9": { corpo: lote({ pelo_modelo: 1, mensagens: [mensagem(1, "Beta"), fixa] }) },
      }),
    );
    renderizar();
    const lista = await screen.findByRole("list", { name: "Mensagens geradas" });
    const [beta, delta] = within(lista).getAllByRole("listitem");
    expect(within(beta).getByText("Assistente")).toBeInTheDocument();
    expect(within(delta).getByText("Modelo fixo")).toBeInTheDocument();
    expect(within(delta).getByText(/Redigida pelo modelo fixo: .*\(13%\)/)).toBeInTheDocument();
    expect(within(delta).getByText("R$ 7.000,00")).toBeInTheDocument();
    expect(screen.getByText("2 de 2 prontas · 1 pelo assistente, 1 pelo modelo fixo")).toBeInTheDocument();
  });

  it("quem falhou aparece com o motivo, e tenta de novo (UC10-A2)", async () => {
    const falhou = lote({
      geradas: 1,
      pelo_modelo: 1,
      falhas: [{ parceiro_id: 12, parceiro: "Delta", motivo: "Erro interno ao gerar a mensagem (registro abc123)." }],
      mensagens: [mensagem(1, "Beta")],
    });
    const chamadas = simularApi(
      basico({
        "GET /api/mensagens/geracao": { corpo: estado({ ultimo: falhou }) },
        "GET /api/mensagens/lotes/9": { corpo: falhou },
        "POST /api/mensagens/lotes/9/refazer": {
          status: 202,
          corpo: lote({ situacao: "EM_ANDAMENTO", geradas: 1, falhas: [], mensagens: null }),
        },
      }),
    );
    const usuario = userEvent.setup();
    renderizar();

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("1 parceiro ficou sem mensagem.");
    expect(aviso).toHaveTextContent("Delta: Erro interno ao gerar a mensagem (registro abc123).");
    await usuario.click(within(aviso).getByRole("button", { name: "Tentar de novo" }));

    await waitFor(() =>
      expect(chamadas.mock.calls.some(([url, o]) => String(url).endsWith("/refazer") && o?.method === "POST")).toBe(
        true,
      ),
    );
    expect(await screen.findByRole("heading", { name: "Gerando mensagens" })).toBeInTheDocument();
    // As que já estavam prontas continuam na tela enquanto as que faltaram são geradas.
    expect(within(screen.getByRole("list", { name: "Mensagens geradas" })).getAllByRole("listitem")).toHaveLength(1);
  });

  it("da Campanha, o plano chega escolhido, com a prévia e a ação de cada parceiro", async () => {
    const chamadas = simularApi(
      basico({
        "POST /api/mensagens/publico": {
          corpo: previa({
            descricao: "Plano de campanha de 05/10/2026 a 11/10/2026",
            parceiros: [
              { id: 11, nome: "Beta", segmento: "EM_RISCO", categoria: "Mercado", acao: "Cupom de reativação" },
              { id: 12, nome: "Delta", segmento: "TOP", categoria: null, acao: "Destaque na vitrine" },
            ],
            excluidos: {},
          }),
        },
      }),
    );
    renderizar("/mensagens?plano=5");

    const tabela = await screen.findByRole("table", { name: "Parceiros que recebem mensagem" });
    expect(within(tabela).getByRole("columnheader", { name: "Ação do plano" })).toBeInTheDocument();
    expect(within(tabela).getByText("Cupom de reativação")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Plano de campanha" })).toBeChecked();
    expect(corpoDe(chamadas, "POST", "/api/mensagens/publico")).toEqual({ tipo: "PLANO", execucao_id: 5 });
  });

  it("a escolha do plano lista só os planos calculados e viáveis", async () => {
    simularApi(basico());
    const usuario = userEvent.setup();
    renderizar();
    await usuario.click(await screen.findByRole("radio", { name: "Plano de campanha" }));
    const opcoes = within(screen.getByLabelText("Plano"))
      .getAllByRole("option")
      .map((o) => o.textContent);
    expect(opcoes).toHaveLength(2);
    expect(opcoes[1]).toMatch(/^05\/10\/2026 a 11\/10\/2026 · 23 ações · calculado em/);
  });

  it("sem plano calculado, leva à campanha", async () => {
    simularApi(basico({ "GET /api/otimizacoes": { corpo: { ...HISTORICO, itens: [] } } }));
    const usuario = userEvent.setup();
    renderizar();
    await usuario.click(await screen.findByRole("radio", { name: "Plano de campanha" }));
    expect(screen.getByText("Nenhum plano calculado ainda.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para a campanha" })).toHaveAttribute("href", "/campanha");
  });

  it("a seleção manual busca pelo nome, escolhe e tira", async () => {
    const chamadas = simularApi(
      basico({
        "GET /api/parceiros": {
          corpo: { itens: [{ id: 21, nome: "Alfa" }, { id: 22, nome: "Alfama" }], total: 2, pagina: 1, tamanho: 8 },
        },
        "POST /api/mensagens/publico": { corpo: previa() },
      }),
    );
    const usuario = userEvent.setup();
    renderizar();
    await usuario.click(await screen.findByRole("radio", { name: "Escolher parceiros" }));
    await usuario.type(screen.getByLabelText("Buscar parceiro"), "alf");

    await usuario.click(await screen.findByRole("button", { name: "Adicionar Alfa" }, { timeout: 2000 }));
    await usuario.click(screen.getByRole("button", { name: "Adicionar Alfama" }));
    expect(screen.getByRole("button", { name: "Alfa já escolhido" })).toBeDisabled();
    const escolhidos = screen.getByRole("list", { name: "2 parceiros escolhidos" });
    expect(within(escolhidos).getAllByRole("listitem").map((i) => i.firstChild.textContent)).toEqual([
      "Alfa",
      "Alfama",
    ]);

    await usuario.click(screen.getByRole("button", { name: "Remover Alfama" }));
    await usuario.click(screen.getByRole("button", { name: "Ver quem entra" }));
    await screen.findByRole("button", { name: "Gerar 2 mensagens" });
    expect(corpoDe(chamadas, "POST", "/api/mensagens/publico")).toEqual({ tipo: "SELECAO", parceiros: [21] });

    const busca = chamadas.mock.calls.find(([url]) => String(url).startsWith("/api/parceiros"))[0];
    expect(busca).toContain("busca=alf");
    expect(busca).toContain("ativo=true");
  });

  it("a geração em andamento ao abrir é acompanhada", async () => {
    const andando = lote({ situacao: "EM_ANDAMENTO", concluido_em: null, geradas: 1, mensagens: [mensagem(1, "Beta")] });
    simularApi(
      basico({
        "GET /api/mensagens/geracao": { corpo: estado({ em_andamento: { ...andando, mensagens: null } }) },
        "GET /api/mensagens/lotes/9": { corpo: andando },
      }),
    );
    renderizar();
    expect(await screen.findByRole("heading", { name: "Gerando mensagens" })).toBeInTheDocument();
    expect(screen.getByText(/você pode sair e voltar/)).toBeInTheDocument();
  });
});
