import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra, endereco } from "../testes/montar";

const ROTAS = () => ({ "GET /api/otimizacoes": { corpo: amostra("GET_api_otimizacoes") } });
const ultima = (chamadas) => chamadas().filter((c) => c.startsWith("GET /api/otimizacoes?")).at(-1) ?? "";

/* RF34 (o histórico das execuções: autor, data, parâmetros, modo, tempo e
   resultado) e RF51 (filtrar por modo, resultado, autor e data). */
describe("as execuções do otimizador", () => {
  it("lista quem calculou, quando, em que modo e o resultado (RF34)", async () => {
    abrir("/execucoes", { rotas: ROTAS() });

    const tabela = await screen.findByRole("region", { name: "Tabela: Execuções" });
    expect(tabela).toHaveTextContent("Medição Gestor");
    expect(tabela).toHaveTextContent("GPU");
    expect(tabela).toHaveTextContent("05/10/2026");
  });

  it("filtra por resultado, modo, autor e data, e o filtro vai para a API (RF51)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/execucoes", { rotas: ROTAS() });

    await usuario.selectOptions(await screen.findByLabelText("Resultado"), "INVIAVEL");
    await waitFor(() => expect(ultima(chamadas)).toContain("resultado=INVIAVEL"));
    await usuario.selectOptions(screen.getByLabelText("Modo em que rodou"), "CPU_PARALELO");
    await waitFor(() => expect(ultima(chamadas)).toContain("modo=CPU_PARALELO"));
    await screen.findByRole("option", { name: "Gestora do Laboratório" });
    await usuario.selectOptions(screen.getByLabelText("Quem calculou"), "3");
    await waitFor(() => expect(ultima(chamadas)).toContain("autor=3"));
  });

  it("marca dois planos e abre a comparação deles (RF35)", async () => {
    const usuario = userEvent.setup();
    abrir("/execucoes", {
      rotas: {
        ...ROTAS(),
        "GET /api/otimizacoes/comparacao": { corpo: amostra("GET_api_otimizacoes_comparacao") },
      },
    });

    const caixas = await screen.findAllByRole("checkbox", { name: /Marcar a execução de/ });
    const comparar = screen.getByRole("button", { name: "Comparar os dois" });
    expect(comparar).toBeDisabled();
    await usuario.click(caixas[0]);
    await usuario.click(caixas[1]);
    await usuario.click(comparar);

    await waitFor(() => expect(endereco()).toMatch(/^\/execucoes\/comparar\?a=\d+&b=\d+$/));
  });
});
