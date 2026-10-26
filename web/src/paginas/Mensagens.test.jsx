import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const PREVIA = (extra = {}) => ({
  descricao: "Em risco, em Mercado",
  total: 2,
  parceiros: [
    { id: 246, nome: "Ponto Azul 2", segmento: "EM_RISCO", categoria: "Mercado", acao: null },
    { id: 89, nome: "Ponto Azul", segmento: "EM_RISCO", categoria: "Mercado", acao: null },
  ],
  excluidos: {},
  maximo: 200,
  pode_gerar: true,
  motivo: null,
  ...extra,
});
const ROTAS = (extra = {}) => ({
  "GET /api/mensagens/geracao": { corpo: { ...amostra("GET_api_mensagens_geracao"), ultimo: null } },
  "GET /api/categorias": { corpo: amostra("GET_api_categorias") },
  "GET /api/otimizacoes": { corpo: amostra("GET_api_otimizacoes") },
  ...extra,
});

/* RF36 — gerar mensagens por segmento e categoria, a partir do plano ou de uma
   seleção. Nada é enviado: toda mensagem nasce pendente, na fila. */
describe("a geração de mensagens (RF36)", () => {
  it("vindo de um plano, a prévia do público chega sozinha, sem mais um clique", async () => {
    const { corpoDe } = abrir("/mensagens?plano=4", {
      rotas: ROTAS({ "POST /api/mensagens/publico": { corpo: PREVIA({ descricao: "Plano de campanha de 05/10/2026 a 11/10/2026" }) } }),
    });

    expect(await screen.findByText("Plano de campanha de 05/10/2026 a 11/10/2026")).toBeInTheDocument();
    expect(corpoDe("POST /api/mensagens/publico")).toEqual({ tipo: "PLANO", execucao_id: 4 });
    expect(screen.getByRole("button", { name: /Gerar 2 mensagens/ })).toBeEnabled();
  });

  it("por segmento: mostra quem entra antes, e gera para esse público", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/mensagens", {
      rotas: ROTAS({
        "POST /api/mensagens/publico": { corpo: PREVIA() },
        "POST /api/mensagens/lotes": { status: 202, corpo: { ...amostra("GET_api_mensagens_lotes_lote_id"), id: 7, situacao: "EM_ANDAMENTO", mensagens: [] } },
        "GET /api/mensagens/lotes/:id": { corpo: { ...amostra("GET_api_mensagens_lotes_lote_id"), id: 7 } },
      }),
    });

    await usuario.selectOptions(await screen.findByLabelText("Segmento"), "EM_RISCO");
    await usuario.click(screen.getByRole("button", { name: "Ver quem entra" }));
    expect(await screen.findByText("Em risco, em Mercado")).toBeInTheDocument();
    expect(corpoDe("POST /api/mensagens/publico")).toEqual({ tipo: "FILTRO", segmento: "EM_RISCO", categoria_id: null });

    await usuario.click(screen.getByRole("button", { name: /Gerar 2 mensagens/ }));
    expect(corpoDe("POST /api/mensagens/lotes")).toEqual({ tipo: "FILTRO", segmento: "EM_RISCO", categoria_id: null });
    expect(await screen.findByRole("link", { name: /Ver estas mensagens na fila de aprovação/ })).toHaveAttribute("href", expect.stringContaining("/aprovacao"));
  });

  it("mudar o público apaga a prévia, que era de outro público", async () => {
    const usuario = userEvent.setup();
    abrir("/mensagens", { rotas: ROTAS({ "POST /api/mensagens/publico": { corpo: PREVIA() } }) });

    await usuario.selectOptions(await screen.findByLabelText("Segmento"), "EM_RISCO");
    await usuario.click(screen.getByRole("button", { name: "Ver quem entra" }));
    await screen.findByText("Em risco, em Mercado");
    await usuario.selectOptions(screen.getByLabelText("Segmento"), "TOP");

    await waitFor(() => expect(screen.queryByText("Em risco, em Mercado")).not.toBeInTheDocument());
  });

  it("público grande demais: a API diz por quê, e não dá para gerar", async () => {
    const usuario = userEvent.setup();
    abrir("/mensagens", {
      rotas: ROTAS({ "POST /api/mensagens/publico": { corpo: PREVIA({ total: 469, pode_gerar: false, motivo: "O público passa do maior lote, de 200 parceiros." }) } }),
    });

    await usuario.click(await screen.findByRole("button", { name: "Ver quem entra" }));

    expect(await screen.findByText("O público passa do maior lote, de 200 parceiros.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Gerar 469 mensagens/ })).toBeNull();
  });

  it("sem o modelo de linguagem, avisa que as mensagens saem do modelo fixo — e não é erro", async () => {
    const geracao = { ...amostra("GET_api_mensagens_geracao"), ultimo: null, assistente: { disponivel: false, modelo: null, motivo: "O assistente não respondeu." } };
    abrir("/mensagens", { rotas: ROTAS({ "GET /api/mensagens/geracao": { corpo: geracao } }) });

    expect(await screen.findByText("Redigidas pelo modelo fixo, com os números do sistema.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
