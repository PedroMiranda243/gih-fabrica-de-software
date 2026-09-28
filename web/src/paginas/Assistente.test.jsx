import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { simularApi } from "../testes/preparar";
import Assistente, { ESPERA_LONGA_MS } from "./Assistente";

const EXEMPLOS = [
  {
    tipo: "desempenho_do_parceiro",
    descricao: "O faturamento, os pedidos e o ticket médio de um parceiro num período.",
    exemplo: "Quanto a Esquina da Serra faturou na semana passada?",
  },
  {
    tipo: "resumo_do_periodo",
    descricao: "O faturamento da rede num período.",
    exemplo: "Como foi a rede na semana passada?",
  },
];

function estado({ disponivel = true, motivo = null } = {}) {
  return {
    assistente: { disponivel, modelo: "qwen2.5:7b", motivo },
    exemplos: EXEMPLOS,
    tamanho_maximo: 1000,
  };
}

const RELATORIO = {
  periodo: { id: 12, data_inicio: "2026-09-14", data_fim: "2026-09-20" },
  importado_em: "2026-09-21T13:05:00Z",
  importado_por: "Fulana",
  origem: "CSV",
};

function resposta(extra = {}) {
  return {
    situacao: "RESPONDIDA",
    tipo: "resumo_do_periodo",
    texto: "Em 14/09/2026 a 20/09/2026, a rede faturou R$ 24.000,00 em 40 pedidos.",
    fonte: {
      texto: "Relatório de 14/09/2026 a 20/09/2026.",
      relatorios: [RELATORIO],
      modelo_versao: null,
      execucao_id: null,
    },
    redator: "MODELO",
    motivo: null,
    fatos: [
      { fato: "Faturamento", valor: "R$ 24.000,00" },
      { fato: "Pedidos", valor: "40" },
    ],
    candidatos: [],
    ...extra,
  };
}

function simular(respostaDaPergunta, { disponivel = true, motivo = null } = {}) {
  const perguntas = [];
  const chamadas = simularApi({
    "GET /api/assistente": { corpo: estado({ disponivel, motivo }) },
    "POST /api/assistente/perguntas": (_url, opcoes) => {
      const corpo = JSON.parse(opcoes.body);
      perguntas.push(corpo.texto);
      return typeof respostaDaPergunta === "function"
        ? respostaDaPergunta(corpo.texto)
        : { corpo: respostaDaPergunta };
    },
  });
  return { chamadas, perguntas };
}

function renderizar() {
  return render(
    <MemoryRouter>
      <Assistente />
    </MemoryRouter>,
  );
}

async function perguntar(usuario, texto) {
  const campo = await screen.findByLabelText("Sua pergunta");
  await usuario.clear(campo);
  await usuario.type(campo, texto);
  await usuario.click(screen.getByRole("button", { name: "Perguntar" }));
}

afterEach(() => {
  vi.useRealTimers();
});

describe("assistente", () => {
  it("abre com a pergunta, o modelo que redige e os exemplos do catálogo", async () => {
    simular(resposta());
    renderizar();

    expect(await screen.findByRole("heading", { name: "Pergunte sobre os dados" })).toBeInTheDocument();
    expect(screen.getByText(/Os números vêm do sistema; o qwen2\.5:7b lê a pergunta e redige/)).toBeInTheDocument();
    const exemplos = screen.getByRole("list", { name: "O que o assistente responde" });
    expect(within(exemplos).getAllByRole("button").map((b) => b.textContent)).toEqual(
      EXEMPLOS.map((e) => e.exemplo),
    );
    expect(screen.getByText("0 de 1.000 caracteres. Enter pergunta; Shift+Enter quebra a linha.")).toBeInTheDocument();
    // Sem pergunta, não há o que enviar.
    expect(screen.getByRole("button", { name: "Perguntar" })).toBeDisabled();
  });

  it("indisponível, avisa sem alarme e deixa o resto do sistema seguir (UC12-E1)", async () => {
    simular(resposta(), { disponivel: false, motivo: "O serviço do modelo de linguagem não respondeu." });
    renderizar();

    expect(await screen.findByText("O assistente está indisponível agora.")).toBeInTheDocument();
    expect(screen.getByText(/O serviço do modelo de linguagem não respondeu\. O painel e as outras telas seguem/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("responde com a fonte sempre à vista, e quem redigiu (H66)", async () => {
    const { perguntas } = simular(resposta());
    const usuario = userEvent.setup();
    renderizar();

    await perguntar(usuario, "Como foi a rede?");

    expect(perguntas).toEqual(["Como foi a rede?"]);
    const cartao = (await screen.findByRole("heading", { name: "Como foi a rede?", level: 3 })).closest("li");
    expect(within(cartao).getByText(/a rede faturou R\$ 24\.000,00 em 40 pedidos/)).toBeInTheDocument();
    const fonte = within(cartao).getByText(/Relatório de 14\/09\/2026 a 20\/09\/2026\./);
    expect(fonte).toBeVisible();
    expect(fonte.textContent).toMatch(/^Fonte Relatório de 14\/09\/2026 a 20\/09\/2026\. Importado em 21\/09\/2026 às \d{2}:05 por Fulana\.$/);
    expect(within(cartao).getByText("Redigida pelo qwen2.5:7b, com os números do sistema conferidos.")).toBeInTheDocument();
    // Os números da resposta, a um clique, como vieram da API.
    expect(within(cartao).getByText("Os números da resposta")).toBeInTheDocument();
    expect(within(cartao).getByText("R$ 24.000,00", { selector: "dd" })).toBeInTheDocument();
    // O campo volta vazio, e a resposta recebe o foco.
    expect(screen.getByLabelText("Sua pergunta")).toHaveValue("");
    expect(screen.getByRole("heading", { name: "Como foi a rede?", level: 3 })).toHaveFocus();
    expect(screen.getByRole("status")).toHaveTextContent("Resposta pronta.");
  });

  it("a fonte de vários relatórios diz quando veio o mais recente", async () => {
    const anterior = { ...RELATORIO, periodo: { id: 11, data_inicio: "2026-09-07", data_fim: "2026-09-13" } };
    simular(
      resposta({
        fonte: {
          texto: "Relatórios de 07/09/2026 a 13/09/2026 e de 14/09/2026 a 20/09/2026.",
          relatorios: [anterior, RELATORIO],
          modelo_versao: null,
          execucao_id: null,
        },
      }),
    );
    const usuario = userEvent.setup();
    renderizar();

    await perguntar(usuario, "Como foi a rede?");

    expect(await screen.findByText(/O mais recente foi importado em 21\/09\/2026 às \d{2}:05 por Fulana\./)).toBeInTheDocument();
  });

  it("a resposta montada pelo sistema diz por que o modelo não redigiu (H67)", async () => {
    const motivo =
      "O texto do modelo trazia números que não vieram dos dados (R$ 25.000,00): a resposta é a que o sistema montou.";
    simular(resposta({ redator: "MODELO_FIXO", motivo }));
    const usuario = userEvent.setup();
    renderizar();

    await perguntar(usuario, "Como foi a rede?");

    expect(await screen.findByText(motivo)).toBeInTheDocument();
    expect(screen.queryByText(/Redigida pelo/)).not.toBeInTheDocument();
  });

  it("as listas da resposta saem como listas", async () => {
    simular(
      resposta({
        tipo: "ranking",
        redator: "MODELO_FIXO",
        texto: "Os maiores faturamentos em 14/09/2026 a 20/09/2026:\n1º Alfa — R$ 9.000,00\n2º Beta — R$ 7.000,00",
      }),
    );
    const usuario = userEvent.setup();
    renderizar();

    await perguntar(usuario, "Quem são os maiores?");

    const cartao = (await screen.findByRole("heading", { name: "Quem são os maiores?", level: 3 })).closest("li");
    const itens = within(cartao).getAllByRole("listitem").map((li) => li.textContent);
    expect(itens).toEqual(["1º Alfa — R$ 9.000,00", "2º Beta — R$ 7.000,00"]);
    expect(within(cartao).getByText("Montada pelo sistema, com os números dele.")).toBeInTheDocument();
  });

  it("a abstenção é uma resposta, e não um erro (H68, UC12-A1)", async () => {
    simular(
      resposta({
        situacao: "ABSTENCAO",
        tipo: "fora_do_catalogo",
        texto: "Essa pergunta pede uma conta, e o assistente não faz contas.",
        fonte: null,
        redator: "MODELO_FIXO",
        fatos: [],
      }),
    );
    const usuario = userEvent.setup();
    renderizar();

    await perguntar(usuario, "Qual a média das pizzarias?");

    const cartao = (await screen.findByRole("heading", { name: "Qual a média das pizzarias?", level: 3 })).closest(
      "li",
    );
    expect(within(cartao).getByText("Sem base para responder")).toBeInTheDocument();
    expect(within(cartao).getByText(/o assistente não faz contas/)).toBeInTheDocument();
    expect(cartao).toHaveClass("resposta--sem-base");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(within(cartao).queryByText(/Fonte/)).not.toBeInTheDocument();
    expect(within(cartao).queryByText("Os números da resposta")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("O assistente não tem base para responder.");
  });

  it("o pedido de precisão traz as opções, e a escolhida vai junto da pergunta (A2)", async () => {
    const { perguntas } = simular((texto) =>
      texto.includes("(")
        ? { corpo: resposta() }
        : {
            corpo: resposta({
              situacao: "PRECISAO",
              tipo: "desempenho_do_parceiro",
              texto: 'Há 2 parceiros com "Cantina" no nome. De qual deles?',
              fonte: null,
              redator: "MODELO_FIXO",
              fatos: [],
              candidatos: ["Cantina Central", "Cantina Verde"],
            }),
          },
    );
    const usuario = userEvent.setup();
    renderizar();

    await perguntar(usuario, "Quanto a Cantina faturou?");
    const opcoes = await screen.findByRole("list", { name: "Escolha uma opção para perguntar de novo" });
    expect(within(opcoes).getAllByRole("button").map((b) => b.textContent)).toEqual([
      "Cantina Central",
      "Cantina Verde",
    ]);
    expect(screen.getByText("Falta uma precisão")).toBeInTheDocument();

    await usuario.click(within(opcoes).getByRole("button", { name: "Cantina Verde" }));

    expect(perguntas).toEqual(["Quanto a Cantina faturou?", "Quanto a Cantina faturou? (Cantina Verde)"]);
    // A resposta nova vem em cima, e a de antes continua na tela.
    const titulos = (await screen.findAllByRole("heading", { level: 3 })).map((h) => h.textContent);
    expect(titulos.slice(-2)).toEqual(["Quanto a Cantina faturou? (Cantina Verde)", "Quanto a Cantina faturou?"]);
  });

  it("o exemplo clicado vira a pergunta", async () => {
    const { perguntas } = simular(resposta());
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: EXEMPLOS[1].exemplo }));

    expect(perguntas).toEqual([EXEMPLOS[1].exemplo]);
    expect(await screen.findByRole("heading", { name: EXEMPLOS[1].exemplo, level: 3 })).toBeInTheDocument();
  });

  it("Enter pergunta, e Shift+Enter quebra a linha", async () => {
    const { perguntas } = simular(resposta());
    const usuario = userEvent.setup();
    renderizar();

    const campo = await screen.findByLabelText("Sua pergunta");
    await usuario.type(campo, "Como foi{Shift>}{Enter}{/Shift}a rede?");
    expect(perguntas).toEqual([]);
    expect(campo).toHaveValue("Como foi\na rede?");

    await usuario.type(campo, "{Enter}");
    expect(perguntas).toEqual(["Como foi\na rede?"]);
  });

  it("a pergunta recusada mostra o motivo embaixo do campo (UC12-E2)", async () => {
    simular(() => ({
      status: 422,
      corpo: {
        erro: "Alguns campos precisam de correção.",
        campos: [{ campo: "texto", mensagem: "Longo demais: use no máximo 1000 caracteres." }],
      },
    }));
    const usuario = userEvent.setup();
    renderizar();

    await perguntar(usuario, "Uma pergunta");

    expect(await screen.findByText("Longo demais: use no máximo 1000 caracteres.")).toBeInTheDocument();
    expect(screen.getByLabelText("Sua pergunta")).toHaveAttribute("aria-invalid", "true");
    // O texto fica no campo, para a pessoa corrigir.
    expect(screen.getByLabelText("Sua pergunta")).toHaveValue("Uma pergunta");
  });

  it("a espera longa diz por quê, e a tela não parece travada", async () => {
    simular(() => new Promise(() => {}));
    renderizar();
    const campo = await screen.findByLabelText("Sua pergunta");

    vi.useFakeTimers();
    fireEvent.change(campo, { target: { value: "Como foi a rede?" } });
    fireEvent.click(screen.getByRole("button", { name: "Perguntar" }));

    expect(screen.getByText(/Lendo a pergunta e buscando os números no sistema/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Perguntando…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: EXEMPLOS[0].exemplo })).toBeDisabled();

    act(() => {
      vi.advanceTimersByTime(ESPERA_LONGA_MS + 1000);
    });
    expect(screen.getByText(/o modelo de linguagem deve estar sendo carregado/)).toBeInTheDocument();
    expect(screen.getByText("13 s")).toBeInTheDocument();
  });
});
