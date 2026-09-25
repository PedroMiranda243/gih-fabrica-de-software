import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Modelo, { INTERVALO_MS } from "./Modelo";

const BASE = { id: 12, data_inicio: "2026-09-14", data_fim: "2026-09-20" };

function treino(extra = {}) {
  return {
    id: 2,
    situacao: "CONCLUIDO",
    autor: "Gestora",
    iniciado_em: "2026-09-24T20:00:00Z",
    concluido_em: "2026-09-24T20:00:02Z",
    periodo_base: BASE,
    volume: {
      parceiros: 500,
      periodos: 12,
      amostras_treino: 2820,
      amostras_validacao: 470,
      amostras_teste: 469,
    },
    metricas: {
      mape_modelo: 0.0922,
      mape_ultimo: 0.1154,
      mape_media_movel: 0.0997,
      brier_modelo: 0.1051,
      brier_referencia: 0.1215,
      calibracao_modelo: 0.04,
      calibracao_referencia: 0.003,
    },
    curva: [],
    segundos: 1.2,
    promovido: true,
    versao: "rede-2",
    versao_em_uso: "rede-2",
    motivo: null,
    ...extra,
  };
}

function estado(extra = {}) {
  return {
    versao_em_uso: "rede-2",
    origem: "MODELO",
    treino_da_versao: treino(),
    ultimo_treino: treino(),
    em_andamento: null,
    periodos_na_base: 12,
    periodos_minimos: 8,
    periodo_mais_recente: BASE,
    periodo_das_previsoes: BASE,
    desatualizado: false,
    pode_treinar: true,
    motivo_bloqueio: null,
    ...extra,
  };
}

const SEM_HISTORICO = { itens: [], total: 0, pagina: 1, tamanho: 10 };

function renderizar() {
  return render(
    <MemoryRouter>
      <Modelo />
    </MemoryRouter>,
  );
}

describe("tela do modelo", () => {
  it("sem treino, diz por que não dá para treinar — com a frase da API", async () => {
    simularApi({
      "GET /api/modelo": {
        corpo: estado({
          versao_em_uso: null,
          origem: null,
          treino_da_versao: null,
          ultimo_treino: null,
          periodos_na_base: 5,
          pode_treinar: false,
          motivo_bloqueio: "O treino precisa de 8 períodos importados, e a base tem 5.",
        }),
      },
      "GET /api/modelo/treinos": { corpo: SEM_HISTORICO },
    });
    renderizar();

    expect(await screen.findByText("O modelo ainda não foi treinado")).toBeInTheDocument();
    expect(screen.getByText(/precisa de 8 períodos importados/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Treinar agora" })).toBeDisabled();
  });

  it("a versão em uso mostra o volume e a comparação com as referências", async () => {
    simularApi({
      "GET /api/modelo": { corpo: estado() },
      "GET /api/modelo/treinos": { corpo: SEM_HISTORICO },
    });
    renderizar();

    expect(await screen.findByText(/rede-2 · Rede neural/)).toBeInTheDocument();
    expect(screen.getByText("469")).toBeInTheDocument();

    const faturamento = screen.getByRole("figure", { name: /Erro no faturamento previsto/ });
    const linhas = within(faturamento).getAllByRole("listitem");
    expect(linhas.map((l) => l.textContent)).toEqual([
      "Rede9,2%",
      "Média móvel dos últimos 410,0%",
      "Repetir o último período11,5%",
    ]);
    // A rede é a série em destaque; as referências ficam em cinza.
    expect(linhas[0]).toHaveClass("comparacao__linha--destaque");
    expect(linhas[1]).not.toHaveClass("comparacao__linha--destaque");

    const risco = screen.getByRole("figure", { name: /Erro no risco de queda/ });
    expect(within(risco).getByText("0,105")).toBeInTheDocument();
  });

  it("treinar pede confirmação, acompanha o andamento e anuncia o resultado", async () => {
    let posts = 0;
    let consultas = 0;
    simularApi({
      // Em andamento entre o pedido e a primeira consulta que o encontra concluído.
      "GET /api/modelo": () => ({
        corpo:
          posts && !consultas
            ? estado({ em_andamento: treino({ id: 3, situacao: "EM_ANDAMENTO" }), pode_treinar: false })
            : estado(),
      }),
      "POST /api/modelo/treinos": () => {
        posts += 1;
        return { status: 202, corpo: treino({ id: 3, situacao: "EM_ANDAMENTO", concluido_em: null }) };
      },
      "GET /api/modelo/treinos/3": () => {
        consultas += 1;
        return { corpo: treino({ id: 3, versao: "rede-3", versao_em_uso: "rede-3" }) };
      },
      "GET /api/modelo/treinos": { corpo: SEM_HISTORICO },
    });
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Treinar agora" }));
    // Nada foi disparado ainda: a confirmação diz o que vai acontecer antes.
    expect(posts).toBe(0);
    expect(screen.getByRole("group", { name: "Confirmação" })).toHaveTextContent(
      "só entra em uso se errar menos",
    );

    await usuario.click(screen.getByRole("button", { name: "Treinar" }));
    expect(await screen.findByText("Treinando o modelo…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Treinando…" })).toBeDisabled();

    // O anúncio do leitor de tela e o aviso visível dizem a mesma coisa.
    const anuncio = screen.getByRole("status");
    await waitFor(
      () => expect(anuncio).toHaveTextContent("Treino concluído: a versão rede-3 entrou em uso."),
      { timeout: INTERVALO_MS + 2000 },
    );
    expect(screen.getByText(/As previsões de cada parceiro já saem dela/)).toBeInTheDocument();
    expect(consultas).toBeGreaterThan(0);
  });

  it("versão nova que não superou as referências: diz qual ficou e por quê", async () => {
    let terminou = false;
    simularApi({
      "GET /api/modelo": () => ({
        corpo: terminou
          ? estado()
          : estado({ em_andamento: treino({ id: 4, situacao: "EM_ANDAMENTO" }) }),
      }),
      "GET /api/modelo/treinos/4": () => {
        terminou = true;
        return {
          corpo: treino({
            id: 4,
            versao: "rede-4",
            promovido: false,
            versao_em_uso: "rede-2",
            motivo:
              "Não superou a referência: no faturamento, errou 10,4% contra 10,0% de média móvel.",
          }),
        };
      },
      "GET /api/modelo/treinos": { corpo: SEM_HISTORICO },
    });
    renderizar();

    // O treino em andamento veio do servidor: a tela o acompanha sem ninguém ter clicado.
    expect(await screen.findByText("Treinando o modelo…")).toBeInTheDocument();
    expect(
      await screen.findByText(/não entrou em uso\. Em uso: rede-2/, {}, { timeout: INTERVALO_MS + 2000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/errou 10,4% contra 10,0%/)).toBeInTheDocument();
  });

  it("a recusa do servidor aparece com a ajuda", async () => {
    simularApi({
      "GET /api/modelo": { corpo: estado() },
      "POST /api/modelo/treinos": {
        status: 409,
        corpo: {
          detail: {
            erro: "Já existe um treino em andamento.",
            ajuda: "Acompanhe o treino atual; quando ele terminar, você pode disparar outro.",
          },
        },
      },
      "GET /api/modelo/treinos": { corpo: SEM_HISTORICO },
    });
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Treinar agora" }));
    await usuario.click(screen.getByRole("button", { name: "Treinar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Já existe um treino em andamento.");
    expect(screen.getByRole("alert")).toHaveTextContent("Acompanhe o treino atual");
  });

  it("depois da recusa, a tela passa a acompanhar o treino que já roda (#108)", async () => {
    /* Outra aba disparou um treino: a tela desta ainda o ignora, e o pedido é
       recusado. Reler o estado faz ela encontrar o treino e acompanhá-lo. */
    let recusou = false;
    let terminou = false;
    simularApi({
      "GET /api/modelo": () => ({
        corpo:
          recusou && !terminou
            ? estado({ em_andamento: treino({ id: 5, situacao: "EM_ANDAMENTO" }), pode_treinar: false })
            : estado(),
      }),
      "POST /api/modelo/treinos": () => {
        recusou = true;
        return {
          status: 409,
          corpo: { detail: { erro: "Já existe um treino em andamento.", ajuda: "Acompanhe." } },
        };
      },
      "GET /api/modelo/treinos/5": () => {
        terminou = true;
        return { corpo: treino({ id: 5, versao: "rede-5", versao_em_uso: "rede-5" }) };
      },
      "GET /api/modelo/treinos": { corpo: SEM_HISTORICO },
    });
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Treinar agora" }));
    await usuario.click(screen.getByRole("button", { name: "Treinar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Já existe um treino em andamento.");
    expect(await screen.findByText("Treinando o modelo…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Treinando…" })).toBeDisabled();

    // Quando o treino da outra aba termina, a recusa deixa de valer e some.
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull(), {
      timeout: INTERVALO_MS + 2000,
    });
    expect(screen.getByRole("status")).toHaveTextContent("a versão rede-5 entrou em uso");
  });

  it("período mais novo que as previsões avisa, com os dois períodos", async () => {
    simularApi({
      "GET /api/modelo": {
        corpo: estado({
          desatualizado: true,
          periodo_mais_recente: { id: 13, data_inicio: "2026-09-21", data_fim: "2026-09-27" },
        }),
      },
      "GET /api/modelo/treinos": { corpo: SEM_HISTORICO },
    });
    renderizar();

    expect(await screen.findByText("Há período importado depois do último treino.")).toBeInTheDocument();
    expect(screen.getByText(/partem de 14\/09\/2026 a 20\/09\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/21\/09\/2026 a 27\/09\/2026/)).toBeInTheDocument();
  });

  it("o histórico diz o que cada treino deixou", async () => {
    simularApi({
      "GET /api/modelo": { corpo: estado() },
      "GET /api/modelo/treinos": {
        corpo: {
          itens: [
            treino({ id: 3, versao: "rede-3", promovido: false, versao_em_uso: "rede-2" }),
            treino({ id: 2 }),
            treino({ id: 1, situacao: "FALHOU", autor: null, motivo: "O treino falhou por um erro interno (registro abc)." }),
          ],
          total: 3,
          pagina: 1,
          tamanho: 10,
        },
      },
    });
    renderizar();

    const tabela = await screen.findByRole("table", { name: /Treinos do modelo/ });
    const linhas = within(tabela).getAllByRole("row").slice(1);
    expect(linhas[0]).toHaveTextContent("Mantida: rede-2");
    expect(linhas[1]).toHaveTextContent("rede-2 entrou em uso");
    expect(linhas[2]).toHaveTextContent("terminal");
    expect(linhas[2]).toHaveTextContent("Falhou");
    expect(linhas[2]).toHaveTextContent("erro interno");
  });
});
