import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { avisariaAoFechar, simularApi } from "../testes/preparar";
import Aprovacao from "./Aprovacao";

const GESTOR = ["painel", "mensagens", "aprovacao", "decidir_mensagens"];
const ANALISTA = ["painel", "mensagens", "aprovacao"];

function mensagem(id, parceiro, extra = {}) {
  return {
    id,
    parceiro_id: id + 10,
    parceiro,
    segmento: "EM_RISCO",
    acao: "Cupom de reativação",
    texto: `Olá, ${parceiro}! Estamos aqui para ajudar.`,
    texto_gerado: `Olá, ${parceiro}! Estamos aqui para ajudar.`,
    estado: "PENDENTE",
    redator: "MODELO",
    modelo: "qwen2.5:7b",
    motivo_redator: null,
    fatos: [{ fato: "Parceiro", valor: parceiro }],
    lote_id: 9,
    gerada_em: "2026-09-27T14:10:00Z",
    categoria: "Mercado",
    editada: false,
    numeros_fora_dos_fatos: [],
    decidida_por: null,
    decidida_em: null,
    motivo_rejeicao: null,
    ...extra,
  };
}

function pagina(itens, total = itens.length) {
  return { itens, total, pagina: 1, tamanho: 20 };
}

const FILA = pagina([mensagem(1, "Beta"), mensagem(2, "Gama"), mensagem(3, "Delta", { segmento: "TOP" })]);

function renderizar({ telas = GESTOR, endereco = "/aprovacao" } = {}) {
  return render(
    <ContextoSessao.Provider value={{ usuario: { nome: "Quem Testa", telas }, sair: () => {} }}>
      <MemoryRouter initialEntries={[endereco]}>
        <Aprovacao />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
}

function corpoDe(chamadas, metodo, caminho) {
  const chamada = chamadas.mock.calls.find(
    ([url, opcoes]) => String(url).split("?")[0] === caminho && (opcoes?.method ?? "GET") === metodo,
  );
  return chamada ? JSON.parse(chamada[1].body) : undefined;
}

function cartao(nome) {
  return screen.getByRole("heading", { name: nome }).closest("li");
}

describe("fila de aprovação", () => {
  it("o gestor vê as pendentes, com para quem, o segmento, a categoria, a ação e as três decisões", async () => {
    simularApi({ "GET /api/mensagens": { corpo: FILA } });
    renderizar();
    const beta = (await screen.findByRole("heading", { name: "Beta" })).closest("li");
    expect(within(beta).getByText("Em risco")).toBeInTheDocument();
    expect(within(beta).getByText("Mercado")).toBeInTheDocument();
    expect(within(beta).getByText("Cupom de reativação")).toBeInTheDocument();
    for (const botao of ["Aprovar", "Editar", "Rejeitar"]) {
      expect(within(beta).getByRole("button", { name: botao })).toBeEnabled();
    }
    expect(screen.getByText(/3 mensagens esperando a decisão/)).toBeInTheDocument();
    expect(screen.queryByText("Só um gestor decide.")).not.toBeInTheDocument();
  });

  it("o analista vê a mesma fila, sem caixa de seleção e sem botão (RN06)", async () => {
    simularApi({ "GET /api/mensagens": { corpo: FILA } });
    renderizar({ telas: ANALISTA });
    expect(await screen.findByRole("heading", { name: "Beta" })).toBeInTheDocument();
    expect(screen.getByText("Só um gestor decide.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aprovar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("aprovar tira da fila, anuncia, e leva o foco à próxima (UC11, passo 6)", async () => {
    const chamadas = simularApi({
      "GET /api/mensagens": { corpo: FILA },
      "POST /api/mensagens/1/aprovacao": { corpo: mensagem(1, "Beta", { estado: "APROVADA" }) },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Beta" });
    await usuario.click(within(cartao("Beta")).getByRole("button", { name: "Aprovar" }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: "Beta" })).not.toBeInTheDocument());
    expect(screen.getByRole("status")).toHaveTextContent("Mensagem para Beta aprovada. Próxima: mensagem para Gama.");
    expect(document.activeElement).toBe(screen.getByRole("heading", { name: "Gama" }));
    expect(screen.getByText(/2 mensagens esperando a decisão/)).toBeInTheDocument();
    expect(chamadas.mock.calls.some(([url, o]) => url === "/api/mensagens/1/aprovacao" && o.method === "POST")).toBe(
      true,
    );
  });

  it("editar salva o texto, deixa a mensagem na fila e aponta o número que não veio dos dados", async () => {
    const editada = mensagem(1, "Beta", {
      texto: "Olá, Beta! 20% de desconto nesta semana.",
      editada: true,
      numeros_fora_dos_fatos: ["20%"],
    });
    const chamadas = simularApi({
      "GET /api/mensagens": { corpo: FILA },
      "POST /api/mensagens/1/edicao": { corpo: editada },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Beta" });
    await usuario.click(within(cartao("Beta")).getByRole("button", { name: "Editar" }));

    const campo = screen.getByLabelText("Texto da mensagem para Beta");
    expect(screen.getByText("Salvar não aprova: a mensagem continua na fila.")).toBeInTheDocument();
    await usuario.clear(campo);
    await usuario.type(campo, "Olá, Beta! 20% de desconto nesta semana.");
    await usuario.click(screen.getByRole("button", { name: "Salvar o texto" }));

    expect(await within(cartao("Beta")).findByText("Números que não vieram dos dados: 20%.")).toBeInTheDocument();
    expect(within(cartao("Beta")).getByText("Olá, Beta! 20% de desconto nesta semana.")).toBeInTheDocument();
    expect(within(cartao("Beta")).getByText("Editada — ver o texto redigido")).toBeInTheDocument();
    expect(within(cartao("Beta")).getByRole("button", { name: "Aprovar" })).toBeInTheDocument();
    expect(corpoDe(chamadas, "POST", "/api/mensagens/1/edicao")).toEqual({
      texto: "Olá, Beta! 20% de desconto nesta semana.",
    });
    expect(screen.getByRole("status")).toHaveTextContent("Ela continua na fila, esperando a decisão.");
  });

  it("rejeitar pede o motivo, opcional, e tira da fila (UC11-A2)", async () => {
    const chamadas = simularApi({
      "GET /api/mensagens": { corpo: FILA },
      "POST /api/mensagens/2/rejeicao": { corpo: mensagem(2, "Gama", { estado: "REJEITADA" }) },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Gama" });
    await usuario.click(within(cartao("Gama")).getByRole("button", { name: "Rejeitar" }));
    await usuario.type(screen.getByLabelText("Motivo da rejeição (opcional)"), "Tom errado");
    await usuario.click(screen.getByRole("button", { name: "Rejeitar mensagem" }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: "Gama" })).not.toBeInTheDocument());
    expect(corpoDe(chamadas, "POST", "/api/mensagens/2/rejeicao")).toEqual({ motivo: "Tom errado" });
    expect(screen.getByRole("status")).toHaveTextContent("Mensagem para Gama rejeitada. Próxima: mensagem para Delta.");
  });

  it("a decisão que chegou tarde diz quem decidiu, e a fila se atualiza (UC11-E1)", async () => {
    let consultas = 0;
    simularApi({
      "GET /api/mensagens": () => {
        consultas += 1;
        return { corpo: consultas === 1 ? FILA : pagina([mensagem(2, "Gama"), mensagem(3, "Delta")]) };
      },
      "POST /api/mensagens/1/aprovacao": {
        status: 409,
        corpo: {
          detail: {
            erro: "Esta mensagem já foi decidida.",
            ajuda: "Ela foi rejeitada por Outra Gestora enquanto você a revisava. A fila foi atualizada.",
            estado: "REJEITADA",
          },
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Beta" });
    await usuario.click(within(cartao("Beta")).getByRole("button", { name: "Aprovar" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Esta mensagem já foi decidida.");
    expect(alerta).toHaveTextContent("rejeitada por Outra Gestora");
    await waitFor(() => expect(consultas).toBeGreaterThanOrEqual(2));
    expect(screen.queryByRole("heading", { name: "Beta" })).not.toBeInTheDocument();
  });

  it("aprova em lote as selecionadas, com confirmação, e diz o que já tinha sido decidido (UC11-A3)", async () => {
    const chamadas = simularApi({
      "GET /api/mensagens": { corpo: FILA },
      "POST /api/mensagens/aprovacao-em-lote": {
        corpo: {
          aprovadas: [1],
          ja_decididas: [{ mensagem_id: 3, estado: "REJEITADA", decidida_por: "Outra", decidida_em: null }],
          nao_encontradas: [],
        },
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Beta" });
    const lote = screen.getByRole("button", { name: "Aprovar selecionadas" });
    expect(lote).toBeDisabled();

    await usuario.click(screen.getByRole("checkbox", { name: "Selecionar a mensagem para Beta" }));
    await usuario.click(screen.getByRole("checkbox", { name: "Selecionar a mensagem para Delta" }));
    await usuario.click(screen.getByRole("button", { name: "Aprovar selecionadas (2)" }));
    expect(screen.getByText(/^Aprovar 2 mensagens\? Cada uma fica registrada/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Aprovar as 2" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("1 mensagem aprovada.");
    expect(alerta).toHaveTextContent("1 já tinha sido decidida por outra pessoa, e ficou como estava.");
    expect(corpoDe(chamadas, "POST", "/api/mensagens/aprovacao-em-lote")).toEqual({ ids: [1, 3] });
  });

  it("selecionar todas marca e desmarca a página inteira", async () => {
    simularApi({ "GET /api/mensagens": { corpo: FILA } });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Beta" });
    const todas = screen.getByRole("checkbox", { name: "Selecionar as 3 desta página" });
    await usuario.click(todas);
    expect(screen.getByRole("button", { name: "Aprovar selecionadas (3)" })).toBeEnabled();
    await usuario.click(todas);
    expect(screen.getByRole("button", { name: "Aprovar selecionadas" })).toBeDisabled();
  });

  it("o filtro do segmento e o da geração vão na consulta, e o da geração se desfaz", async () => {
    const chamadas = simularApi({ "GET /api/mensagens": { corpo: FILA } });
    const usuario = userEvent.setup();
    renderizar({ endereco: "/aprovacao?lote=9" });
    expect(await screen.findByText(/Só as mensagens de uma geração/)).toBeInTheDocument();
    expect(chamadas.mock.calls[0][0]).toContain("lote_id=9");

    await usuario.selectOptions(screen.getByLabelText("Segmento"), "TOP");
    await waitFor(() => expect(chamadas.mock.calls.at(-1)[0]).toContain("segmento=TOP"));
    expect(chamadas.mock.calls.at(-1)[0]).toContain("lote_id=9");

    await usuario.click(screen.getByRole("button", { name: "Ver toda a fila" }));
    await waitFor(() => expect(chamadas.mock.calls.at(-1)[0]).not.toContain("lote_id"));
  });

  it("fila vazia leva a gerar mensagens", async () => {
    simularApi({ "GET /api/mensagens": { corpo: pagina([]) } });
    renderizar();
    expect(await screen.findByText("Nenhuma mensagem pendente.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gerar mensagens" })).toHaveAttribute("href", "/mensagens");
  });
});

describe("histórico das mensagens decididas (RF40, H64)", () => {
  const aprovada = mensagem(1, "Beta", {
    estado: "APROVADA",
    texto: "Olá, Beta! Texto final do gestor.",
    editada: true,
    decidida_por: "Gestora",
    decidida_em: "2026-09-27T17:05:00Z",
    contato: "(81) 99999-0000",
  });
  const rejeitada = mensagem(2, "Gama", {
    estado: "REJEITADA",
    decidida_por: "Gestora",
    decidida_em: "2026-09-27T17:06:00Z",
    motivo_rejeicao: "Tom errado",
  });

  it("as aprovadas trazem quem decidiu, o contato, o texto redigido e copiar o texto, sem botão de decidir", async () => {
    simularApi({ "GET /api/mensagens": { corpo: pagina([aprovada]) } });
    const usuario = userEvent.setup();
    renderizar({ endereco: "/aprovacao?estado=APROVADA" });

    const beta = (await screen.findByRole("heading", { name: "Beta" })).closest("li");
    expect(screen.getByRole("heading", { name: "Aprovadas" })).toBeInTheDocument();
    expect(within(beta).getByText(/^Aprovada por Gestora em 27\/09\/2026/)).toBeInTheDocument();
    expect(within(beta).getByText("Contato: (81) 99999-0000")).toBeInTheDocument();
    expect(within(beta).getByText("Editada — ver o texto redigido")).toBeInTheDocument();
    expect(within(beta).queryByRole("button", { name: "Aprovar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByText(/prontas para envio: o sistema não envia/)).toBeInTheDocument();

    await usuario.click(within(beta).getByRole("button", { name: "Copiar texto" }));
    expect(await within(beta).findByRole("button", { name: "Copiado" })).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe("Olá, Beta! Texto final do gestor.");
    expect(screen.getByRole("status")).toHaveTextContent("Texto da mensagem para Beta copiado.");
  });

  it("as rejeitadas trazem o motivo, e não se copiam", async () => {
    simularApi({ "GET /api/mensagens": { corpo: pagina([rejeitada]) } });
    renderizar({ endereco: "/aprovacao?estado=REJEITADA" });
    const gama = (await screen.findByRole("heading", { name: "Gama" })).closest("li");
    expect(within(gama).getByText(/^Rejeitada por Gestora em .*\. Motivo: Tom errado\.$/)).toBeInTheDocument();
    expect(within(gama).queryByRole("button", { name: "Copiar texto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Exportar aprovadas (CSV)" })).not.toBeInTheDocument();
  });

  it("a vista, o período e a exportação vivem no endereço, e o período some na fila", async () => {
    const chamadas = simularApi({ "GET /api/mensagens": { corpo: pagina([aprovada]) } });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Beta" });
    expect(screen.queryByLabelText("Decididas de")).not.toBeInTheDocument();

    await usuario.click(screen.getByRole("radio", { name: "Aprovadas" }));
    await waitFor(() => expect(chamadas.mock.calls.at(-1)[0]).toContain("estado=APROVADA"));
    await usuario.type(screen.getByLabelText("Decididas de"), "2026-09-01");
    await waitFor(() => expect(chamadas.mock.calls.at(-1)[0]).toContain("de=2026-09-01"));
    expect(screen.getByRole("link", { name: "Exportar aprovadas (CSV)" })).toHaveAttribute(
      "href",
      "/api/mensagens/exportacao.csv?de=2026-09-01",
    );

    await usuario.click(screen.getByRole("radio", { name: "Pendentes" }));
    await waitFor(() => expect(chamadas.mock.calls.at(-1)[0]).toContain("estado=PENDENTE"));
    expect(chamadas.mock.calls.at(-1)[0]).not.toContain("de=");
  });

  it("histórico vazio leva de volta às pendentes", async () => {
    simularApi({ "GET /api/mensagens": { corpo: pagina([]) } });
    renderizar({ endereco: "/aprovacao?estado=REJEITADA" });
    expect(await screen.findByText("Nenhuma mensagem rejeitada neste recorte.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver as pendentes" })).toHaveAttribute("href", "/aprovacao");
  });
});

describe("fila de aprovação — alterações não salvas (H97)", () => {
  it("o texto reescrito e ainda não salvo é alteração; salvo, deixa de ser", async () => {
    simularApi({
      "GET /api/mensagens": { corpo: FILA },
      "POST /api/mensagens/1/edicao": {
        corpo: mensagem(1, "Beta", { texto: "Olá, Beta! Estamos aqui para ajudar. Conte com a gente.", editada: true }),
      },
    });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Beta" });

    await usuario.click(within(cartao("Beta")).getByRole("button", { name: "Editar" }));
    expect(avisariaAoFechar()).toBe(false);

    await usuario.type(screen.getByLabelText("Texto da mensagem para Beta"), " Conte com a gente.");
    expect(avisariaAoFechar()).toBe(true);

    await usuario.click(screen.getByRole("button", { name: "Salvar o texto" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Ela continua na fila");
    expect(avisariaAoFechar()).toBe(false);
  });

  it("o motivo da rejeição digitado e não enviado também", async () => {
    simularApi({ "GET /api/mensagens": { corpo: FILA } });
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByRole("heading", { name: "Gama" });

    await usuario.click(within(cartao("Gama")).getByRole("button", { name: "Rejeitar" }));
    expect(avisariaAoFechar()).toBe(false);

    await usuario.type(screen.getByLabelText("Motivo da rejeição (opcional)"), "Tom errado");
    expect(avisariaAoFechar()).toBe(true);
  });
});
