import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const PERIODO = { id: null, data_inicio: "2026-10-05", data_fim: "2026-10-11" };
const PREVIA = {
  periodo: PERIODO,
  reconhecidos: [
    { linha: 2, nome: "Ponto Azul 2", faturamento: "1234.50", pedidos: 40 },
    { linha: 3, nome: "Padaria Nova", faturamento: "987.00", pedidos: 31 },
  ],
  rejeitados: [{ linha: 4, conteudo: "linha sem sentido", motivo: "A linha precisa de três colunas: nome, faturamento e pedidos." }],
  parceiros_novos: ["Padaria Nova"],
  total_reconhecido: 2,
  total_rejeitado: 1,
  periodo_ja_importado: false,
};
const JA_IMPORTADO = {
  status: 409,
  corpo: {
    detail: {
      erro: "Este período já foi importado.",
      ajuda: "O padrão é cancelar, para não duplicar nem apagar dados sem querer.",
      ja_existe: { importacao: 17, autor: "Analista da Evidência", enviado_em: "2026-10-03T00:11:21Z", metricas_que_serao_apagadas: 500 },
    },
  },
};
const ROTAS = (extra = {}) => ({ "GET /api/importacoes": { corpo: amostra("GET_api_importacoes") }, ...extra });

async function preencher(usuario, texto = "Parceiro;Faturamento;Pedidos\nPonto Azul 2;1234,50;40") {
  await usuario.type(await screen.findByLabelText(/^Início do período/), "2026-10-05");
  await usuario.type(screen.getByLabelText(/^Fim do período/), "2026-10-11");
  await usuario.type(screen.getByRole("textbox", { name: /^Relatório/ }), texto);
}

/* RF09 (importar texto ou CSV), RF10 (período obrigatório), RF11 (prévia antes
   de gravar), RF12 (período repetido), RF13 (histórico) e RNF23 (progresso). */
describe("a importação", () => {
  it("mostra a prévia antes de gravar: o que entra, o que é rejeitado e o porquê (RF11)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/importacao", { rotas: ROTAS({ "POST /api/importacoes/previa": { corpo: PREVIA } }) });

    await preencher(usuario);
    await usuario.click(screen.getByRole("button", { name: "Ver a prévia" }));

    const previa = (await screen.findByRole("heading", { level: 3 })).closest("section");
    expect(previa).toHaveTextContent("2 linhas serão gravadas · 1 linha rejeitada · 1 parceiro novo");
    const rejeitadas = within(previa).getByRole("region", { name: "Tabela: Linhas rejeitadas" });
    expect(rejeitadas).toHaveTextContent("linha sem sentido");
    expect(rejeitadas).toHaveTextContent("A linha precisa de três colunas");
    expect(corpoDe("POST /api/importacoes/previa")).toEqual({ periodo_inicio: "2026-10-05", periodo_fim: "2026-10-11", texto: "Parceiro;Faturamento;Pedidos\nPonto Azul 2;1234,50;40" });
    expect(screen.getByRole("button", { name: "Gravar 2 registros" })).toBeInTheDocument();
  });

  it("grava e leva ao painel, que é o passo seguinte (RF09)", async () => {
    const usuario = userEvent.setup();
    abrir("/importacao", {
      rotas: ROTAS({
        "POST /api/importacoes/previa": { corpo: PREVIA },
        "POST /api/importacoes": { status: 201, corpo: { id: 18, periodo: { ...PERIODO, id: 13 }, total_gravado: 2, total_rejeitado: 1, parceiros_novos: ["Padaria Nova"] } },
      }),
    });

    await preencher(usuario);
    await usuario.click(screen.getByRole("button", { name: "Ver a prévia" }));
    await usuario.click(await screen.findByRole("button", { name: "Gravar 2 registros" }));

    expect(await screen.findByText(/Importação gravada: 2 registros do período 05\/10\/2026 a 11\/10\/2026, e 1 linha rejeitada\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Ver no painel/ })).toHaveAttribute("href", "/");
  });

  it("período repetido: explica, diz quanto será apagado e só substitui se a pessoa pedir (RF12)", async () => {
    const usuario = userEvent.setup();
    const pedidos = [];
    abrir("/importacao", {
      rotas: ROTAS({
        "POST /api/importacoes/previa": { corpo: { ...PREVIA, periodo_ja_importado: true } },
        "POST /api/importacoes": (_url, opcoes) => {
          const corpo = JSON.parse(opcoes.body);
          pedidos.push(corpo);
          return corpo.substituir ? { status: 201, corpo: { id: 19, periodo: PERIODO, total_gravado: 2, total_rejeitado: 1, parceiros_novos: [] } } : JA_IMPORTADO;
        },
      }),
    });

    await preencher(usuario);
    await usuario.click(screen.getByRole("button", { name: "Ver a prévia" }));
    await usuario.click(await screen.findByRole("button", { name: "Gravar 2 registros" }));

    expect(await screen.findByText(/Já existem/)).toHaveTextContent("Já existem 500 registros deste período, importados por Analista da Evidência");
    expect(pedidos).toEqual([expect.not.objectContaining({ substituir: true })]);
    await usuario.click(screen.getByRole("button", { name: "Substituir mesmo assim" }));
    await waitFor(() => expect(pedidos.at(-1)).toMatchObject({ substituir: true }));
  });

  it("sem período, a recusa da API aparece junto das datas, com a ajuda dela (RF10)", async () => {
    const usuario = userEvent.setup();
    abrir("/importacao", {
      rotas: ROTAS({
        "POST /api/importacoes/previa": {
          status: 422,
          corpo: {
            erro: "Alguns campos precisam de correção.",
            campos: [{ campo: "periodo_inicio", mensagem: "Informe a data inicial do período.", ajuda: "Sem o período, a segmentação classifica errado." }],
          },
        },
      }),
    });

    await usuario.type(await screen.findByRole("textbox", { name: /^Relatório/ }), "Parceiro;Faturamento;Pedidos");
    await usuario.click(screen.getByRole("button", { name: "Ver a prévia" }));

    expect((await screen.findAllByText(/Informe a data inicial do período\./)).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/^Início do período/)).toHaveAttribute("aria-invalid", "true");
  });

  it("o botão diz que está conferindo enquanto a prévia não volta (RNF23)", async () => {
    const usuario = userEvent.setup();
    let responder;
    abrir("/importacao", {
      rotas: ROTAS({ "POST /api/importacoes/previa": () => new Promise((r) => (responder = r)) }),
    });
    // A resposta pendente: o simulador aceita uma promessa no lugar do objeto.
    await preencher(usuario);
    await usuario.click(screen.getByRole("button", { name: "Ver a prévia" }));

    expect(await screen.findByRole("button", { name: "Conferindo…" })).toBeDisabled();
    responder({ corpo: PREVIA });
    expect(await screen.findByRole("button", { name: "Gravar 2 registros" })).toBeInTheDocument();
  });

  it("o histórico traz quem importou, quando, o período e os totais (RF13)", async () => {
    abrir("/importacao", { rotas: ROTAS() });

    const historico = await screen.findByRole("region", { name: "Tabela: Importações anteriores" });
    const primeira = amostra("GET_api_importacoes").itens[0];
    expect(historico).toHaveTextContent(primeira.autor.nome);
    expect(historico).toHaveTextContent("28/09/2026 a 04/10/2026");
  });

  it("o Administrador vê o histórico, mas não o formulário", async () => {
    abrir("/importacao", { perfil: "ADMINISTRADOR", rotas: ROTAS() });

    expect(await screen.findByRole("region", { name: "Tabela: Importações anteriores" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ver a prévia" })).not.toBeInTheDocument();
  });
});
