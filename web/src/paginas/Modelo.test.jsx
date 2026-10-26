import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const TREINO = () => amostra("GET_api_modelo_treinos_treino_id");
const ROTAS = (extra = {}) => ({
  "GET /api/modelo": { corpo: amostra("GET_api_modelo") },
  "GET /api/modelo/treinos": { corpo: amostra("GET_api_modelo_treinos") },
  ...extra,
});

async function treinar(usuario) {
  await usuario.click(await screen.findByRole("button", { name: /Treinar agora/ }));
  const confirmacao = screen.getByText(/Treinar com os 12 períodos da base\?/).closest(".confirmacao");
  await usuario.click(within(confirmacao).getByRole("button", { name: "Treinar" }));
}

/* RF27 (treinar o modelo, com data, volume e métricas) e RNF23 (progresso em
   operação longa). */
describe("o modelo preditivo", () => {
  it("mostra a versão em uso, o volume do treino e o erro contra as contas simples (RF27)", async () => {
    abrir("/modelo", { rotas: ROTAS() });

    expect(await screen.findByRole("heading", { level: 1, name: "Modelo preditivo" })).toBeInTheDocument();
    const pagina = screen.getByRole("main");
    await waitFor(() => expect(pagina).toHaveTextContent("rede-1"));
    expect(pagina).toHaveTextContent("Parceiros500");
    expect(pagina).toHaveTextContent("Amostras de teste469");
    expect(pagina).toHaveTextContent("9,2%");
  });

  it("enquanto treina, diz que está treinando e acompanha (RNF23)", async () => {
    const usuario = userEvent.setup();
    abrir("/modelo", {
      rotas: ROTAS({
        "POST /api/modelo/treinos": { status: 202, corpo: { ...TREINO(), id: 2, situacao: "EM_ANDAMENTO", versao: "rede-2", concluido_em: null } },
        "GET /api/modelo/treinos/:id": { corpo: { ...TREINO(), id: 2, situacao: "EM_ANDAMENTO", versao: "rede-2", concluido_em: null } },
      }),
    });

    await treinar(usuario);

    expect(await screen.findByText(/Treinando a versão rede-2…/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Treinando…/ })).toBeDisabled();
  });

  it("no fim, diz se a versão nova entrou em uso — quem decide é o servidor (RF27)", async () => {
    const usuario = userEvent.setup();
    abrir("/modelo", {
      rotas: ROTAS({
        "POST /api/modelo/treinos": { status: 202, corpo: { ...TREINO(), id: 2, situacao: "EM_ANDAMENTO", versao: "rede-2" } },
        "GET /api/modelo/treinos/:id": { corpo: { ...TREINO(), id: 2, situacao: "CONCLUIDO", versao: "rede-2", promovido: true } },
      }),
    });

    await treinar(usuario);

    // O texto aparece na confirmação e no aviso para o leitor de tela.
    expect((await screen.findAllByText("Treino concluído: a versão rede-2 entrou em uso.")).length).toBeGreaterThan(0);
  });

  it("a versão que não erra menos que as contas simples não entra, e a tela diz o porquê (RF27)", async () => {
    const usuario = userEvent.setup();
    abrir("/modelo", {
      rotas: ROTAS({
        "POST /api/modelo/treinos": { status: 202, corpo: { ...TREINO(), id: 2, situacao: "EM_ANDAMENTO", versao: "rede-2" } },
        "GET /api/modelo/treinos/:id": {
          corpo: { ...TREINO(), id: 2, situacao: "CONCLUIDO", versao: "rede-2", promovido: false, motivo: "Errou mais que a média móvel: a rede-1 continua em uso." },
        },
      }),
    });

    await treinar(usuario);

    expect(await screen.findByText("Errou mais que a média móvel: a rede-1 continua em uso.")).toBeInTheDocument();
  });

  it("sem histórico bastante, o botão fica desligado e a tela diz o motivo da API", async () => {
    const modelo = { ...amostra("GET_api_modelo"), pode_treinar: false, motivo_bloqueio: "São precisos 8 períodos na base; há 3." };
    abrir("/modelo", { rotas: ROTAS({ "GET /api/modelo": { corpo: modelo } }) });

    expect(await screen.findByText("São precisos 8 períodos na base; há 3.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Treinar agora/ })).toBeDisabled();
  });
});
