import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const RESPOSTAS = amostra("POST_api_assistente_perguntas").map((x) => x.resposta);
const DE = (situacao, tipo) => structuredClone(RESPOSTAS.find((r) => r.situacao === situacao && (!tipo || r.tipo === tipo)));
const ROTAS = (resposta, extra = {}) => ({
  "GET /api/assistente": { corpo: amostra("GET_api_assistente") },
  "POST /api/assistente/perguntas": typeof resposta === "function" ? resposta : { corpo: resposta },
  ...extra,
});
const respostaDe = (pergunta) => screen.getByRole("heading", { level: 3, name: pergunta }).closest("article");

/* RF41 (responder em linguagem natural sobre os dados) e RF42 (citar o período e
   a origem, e declarar quando não há base). O assistente não calcula: o número
   vem pronto da API. */
describe("o assistente", () => {
  it("responde e cita a fonte: os relatórios e quando foram importados (RF41, RF42)", async () => {
    const usuario = userEvent.setup();
    abrir("/assistente", { rotas: ROTAS(DE("RESPONDIDA", "resumo_do_periodo")) });

    await usuario.type(await screen.findByLabelText("Sua pergunta"), "Como foi a rede na última semana?");
    await usuario.click(screen.getByRole("button", { name: "Perguntar" }));

    const resposta = await waitFor(() => respostaDe("Como foi a rede na última semana?"));
    expect(resposta).toHaveTextContent("Fonte:");
    expect(resposta).toHaveTextContent("Relatórios de 21/09/2026 a 27/09/2026 e de 28/09/2026 a 04/10/2026.");
    expect(resposta).toHaveTextContent(/O mais recente foi importado em/);
    expect(screen.getByLabelText("Sua pergunta")).toHaveValue("");
  });

  it("a abstenção é resposta, e não erro: diz que não tem base (RF42)", async () => {
    const usuario = userEvent.setup();
    abrir("/assistente", { rotas: ROTAS(DE("ABSTENCAO")) });

    await usuario.type(await screen.findByLabelText("Sua pergunta"), "Qual a média de faturamento das pizzarias?");
    await usuario.click(screen.getByRole("button", { name: "Perguntar" }));

    const resposta = await waitFor(() => respostaDe("Qual a média de faturamento das pizzarias?"));
    expect(resposta).toHaveTextContent("Sem base para responder");
    expect(resposta).toHaveTextContent(/o assistente não faz contas/);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("pede uma precisão com as opções clicáveis, e a escolha pergunta de novo", async () => {
    const usuario = userEvent.setup();
    const perguntas = [];
    abrir("/assistente", {
      rotas: ROTAS((_url, opcoes) => {
        const { texto } = JSON.parse(opcoes.body);
        perguntas.push(texto);
        return { corpo: perguntas.length === 1 ? DE("PRECISAO") : DE("RESPONDIDA", "resumo_do_periodo") };
      }),
    });

    await usuario.type(await screen.findByLabelText("Sua pergunta"), "Como foi o Ponto Azul?");
    await usuario.click(screen.getByRole("button", { name: "Perguntar" }));
    const opcoes = await screen.findByRole("group", { name: "Escolha uma das opções" });
    expect(within(opcoes).getByRole("button", { name: "Ponto Azul 2" })).toBeInTheDocument();
    await usuario.click(within(opcoes).getByRole("button", { name: "Ponto Azul 2" }));

    await waitFor(() => expect(perguntas).toEqual(["Como foi o Ponto Azul?", "Como foi o Ponto Azul? (Ponto Azul 2)"]));
  });

  it("Enter pergunta; Shift+Enter quebra a linha", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/assistente", { rotas: ROTAS(DE("RESPONDIDA", "resumo_do_periodo")) });

    const campo = await screen.findByLabelText("Sua pergunta");
    await usuario.type(campo, "Primeira linha{Shift>}{Enter}{/Shift}segunda");
    expect(campo).toHaveValue("Primeira linha\nsegunda");
    expect(chamadas().filter((c) => c.startsWith("POST"))).toEqual([]);
    await usuario.keyboard("{Enter}");
    await waitFor(() => expect(chamadas()).toContain("POST /api/assistente/perguntas"));
  });

  it("enquanto o modelo pensa, a espera é dita, com os segundos", async () => {
    const usuario = userEvent.setup();
    abrir("/assistente", { rotas: ROTAS(() => new Promise(() => {})) });

    await usuario.type(await screen.findByLabelText("Sua pergunta"), "Como foi a rede?");
    await usuario.click(screen.getByRole("button", { name: "Perguntar" }));

    expect(await screen.findByText(/Lendo a pergunta e buscando os números no sistema… \d+ s\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Perguntando…/ })).toBeDisabled();
  });

  it("sem o modelo no ar, a tela diz que o assistente está indisponível — e o resto segue", async () => {
    const estado = { ...amostra("GET_api_assistente"), assistente: { disponivel: false, modelo: null, motivo: "O serviço do modelo de linguagem não respondeu." } };
    abrir("/assistente", { rotas: ROTAS(DE("INDISPONIVEL"), { "GET /api/assistente": { corpo: estado } }) });

    expect(await screen.findByText(/O serviço do modelo de linguagem não respondeu\./)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("os exemplos de pergunta vêm da API, e um clique os põe no campo", async () => {
    const usuario = userEvent.setup();
    abrir("/assistente", { rotas: ROTAS(DE("RESPONDIDA", "resumo_do_periodo")) });

    const exemplos = (await screen.findByRole("heading", { name: "O que o assistente responde" })).closest("aside");
    const primeiro = amostra("GET_api_assistente").exemplos[0].exemplo;
    await usuario.click(within(exemplos).getByRole("button", { name: (nome) => nome.startsWith(primeiro) }));

    expect(screen.getByLabelText("Sua pergunta")).toHaveValue(primeiro);
    expect(screen.getByLabelText("Sua pergunta")).toHaveFocus();
  });
});
