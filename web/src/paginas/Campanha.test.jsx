import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const CAMPANHA = () => amostra("GET_api_campanha");
const PLANO = () => amostra("GET_api_otimizacoes_execucao_id");
const ROTAS = (extra = {}) => ({ "GET /api/campanha": { corpo: CAMPANHA() }, ...extra });

async function calcular(usuario, { orcamento = "20.000,00", maximo = "30", cauda } = {}) {
  await usuario.type(await screen.findByLabelText(/^Orçamento/), orcamento);
  await usuario.type(screen.getByLabelText(/^Máximo de ações/), maximo);
  if (cauda) await usuario.type(screen.getByLabelText(/^Cota mínima da cauda longa/), cauda);
  await usuario.click(screen.getByRole("button", { name: /Calcular plano/ }));
  const confirmacao = screen.getByText(/^Calcular o plano com orçamento de/).closest(".confirmacao");
  await usuario.click(within(confirmacao).getByRole("button", { name: /Calcular plano/ }));
}

/* RF29 (configurar a campanha), RF31 (respeitar as restrições e dizer quando
   não há solução), RF32 (escolher o modo, com o automático) e RNF23 (progresso). */
describe("a campanha", () => {
  it("manda o orçamento como texto, o máximo de ações, a cota em fração e o período já sugerido (RF29)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/campanha", {
      rotas: ROTAS({
        "POST /api/otimizacoes": { status: 202, corpo: { ...PLANO(), id: 20, situacao: "EM_ANDAMENTO" } },
        "GET /api/otimizacoes/:id": { corpo: { ...PLANO(), id: 20 } },
      }),
    });

    await calcular(usuario, { cauda: "30" });

    expect(corpoDe("POST /api/otimizacoes")).toEqual({
      orcamento: "20000.00",
      maximo_acoes: 30,
      cota_cauda_longa: "0.3000",
      cotas_categoria: [],
      aplicacao_inicio: "2026-10-05",
      aplicacao_fim: "2026-10-11",
      modo: null,
    });
  });

  it("a confirmação repete o que vai ser calculado, e campo em branco aparece como travessão", async () => {
    const usuario = userEvent.setup();
    abrir("/campanha", { rotas: ROTAS() });

    await usuario.type(await screen.findByLabelText(/^Orçamento/), "8.000,00");
    await usuario.click(screen.getByRole("button", { name: /Calcular plano/ }));

    expect(screen.getByText("Calcular o plano com orçamento de R$ 8.000,00 e até — ações?")).toBeInTheDocument();
  });

  it("enquanto calcula, diz que está calculando (RNF23)", async () => {
    const usuario = userEvent.setup();
    abrir("/campanha", {
      rotas: ROTAS({
        "POST /api/otimizacoes": { status: 202, corpo: { ...PLANO(), id: 20, situacao: "EM_ANDAMENTO" } },
        "GET /api/otimizacoes/:id": { corpo: { ...PLANO(), id: 20, situacao: "EM_ANDAMENTO" } },
      }),
    });

    await calcular(usuario);

    expect(await screen.findByRole("button", { name: /Calculando…/ })).toBeDisabled();
  });

  it("os modos vêm da API; sem escolha, o automático diz qual vai rodar (RF32)", async () => {
    const usuario = userEvent.setup();
    const estado = CAMPANHA();
    estado.modos = [
      { modo: "GPU", disponivel: false, motivo: "Nenhuma placa compatível nesta máquina." },
      { modo: "CPU_PARALELO", disponivel: true, motivo: null },
      { modo: "SERIAL", disponivel: true, motivo: null },
    ];
    estado.modo_automatico = "CPU_PARALELO";
    const { corpoDe } = abrir("/campanha", {
      rotas: ROTAS({
        "GET /api/campanha": { corpo: estado },
        "POST /api/otimizacoes": { status: 202, corpo: { ...PLANO(), id: 20, situacao: "EM_ANDAMENTO" } },
        "GET /api/otimizacoes/:id": { corpo: { ...PLANO(), id: 20 } },
      }),
    });

    const modo = await screen.findByLabelText("Modo de execução");
    expect(screen.getByText(/Nesta instalação: CPU paralelo\./)).toBeInTheDocument();
    expect(within(modo).getByRole("option", { name: /GPU — indisponível/ })).toBeDisabled();
    await usuario.selectOptions(modo, "SERIAL");
    await calcular(usuario);

    expect(corpoDe("POST /api/otimizacoes").modo).toBe("SERIAL");
  });

  it("sem solução viável, diz qual restrição não fechou e por quê (RF31)", async () => {
    const usuario = userEvent.setup();
    abrir("/campanha", {
      rotas: ROTAS({
        "POST /api/otimizacoes": { status: 202, corpo: { ...PLANO(), id: 21, situacao: "EM_ANDAMENTO" } },
        "GET /api/otimizacoes/:id": {
          corpo: {
            ...PLANO(),
            id: 21,
            viavel: false,
            restricao_violada: "cauda_longa",
            motivo: "A cota pede 30 ações para a cauda longa, e só 12 parceiros fora do Top cabem no orçamento.",
            itens: [],
            acoes: 0,
            uplift_total: null,
          },
        },
      }),
    });

    await calcular(usuario, { cauda: "100" });

    expect(await screen.findByText("Sem solução viável: cota da cauda longa.")).toBeInTheDocument();
    // O motivo aparece no plano e no aviso para o leitor de tela.
    expect(screen.getAllByText(/A cota pede 30 ações para a cauda longa/).length).toBeGreaterThan(0);
  });

  it("o valor que a API recusa volta ao lado do campo (RF29)", async () => {
    const usuario = userEvent.setup();
    abrir("/campanha", {
      rotas: ROTAS({
        "POST /api/otimizacoes": {
          status: 422,
          corpo: { erro: "Alguns campos precisam de correção.", campos: [{ campo: "maximo_acoes", mensagem: "Informe o máximo de ações." }] },
        },
      }),
    });

    await usuario.type(await screen.findByLabelText(/^Orçamento/), "8.000,00");
    await usuario.click(screen.getByRole("button", { name: /Calcular plano/ }));
    await usuario.click(within(screen.getByText(/^Calcular o plano com orçamento de/).closest(".confirmacao")).getByRole("button", { name: /Calcular plano/ }));

    expect((await screen.findAllByText("Informe o máximo de ações.")).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/^Máximo de ações/)).toHaveAttribute("aria-invalid", "true");
  });

  it("diz quantos parceiros podem receber ação e quantos ficam fora, como a API contou", async () => {
    abrir("/campanha", { rotas: ROTAS() });

    expect(await screen.findByText(/parceiros podem receber ação/)).toHaveTextContent("469");
  });
});
