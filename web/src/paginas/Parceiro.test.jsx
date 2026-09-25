import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { simularApi } from "../testes/preparar";
import Parceiro from "./Parceiro";

const CATEGORIAS = [
  { id: 1, nome: "Padaria", ativa: true },
  { id: 2, nome: "Mercado", ativa: true },
];

const CASA_AZUL = {
  id: 7,
  nome: "Casa Azul",
  categoria: CATEGORIAS[0],
  origem_categoria: "MANUAL",
  status: "ATIVO",
  contato: "contato@exemplo.test",
  ativo: true,
  criado_em: "2026-03-01T10:00:00Z",
  desempenho: {
    segmento: "EM_RISCO",
    faturamento: "1000.00",
    pedidos: 20,
    ticket_medio: "50.00",
    variacao_percentual: "-12.50",
  },
};

const SERIE = {
  escopo: "parceiro",
  parceiro_id: 7,
  parceiro_nome: "Casa Azul",
  pontos: [
    { periodo: { id: 1, data_inicio: "2026-03-02", data_fim: "2026-03-08" }, faturamento: "1200.00", pedidos: 22, ticket_medio: "54.55" },
    { periodo: { id: 2, data_inicio: "2026-03-09", data_fim: "2026-03-15" }, faturamento: "1000.00", pedidos: 20, ticket_medio: "50.00" },
  ],
};

/** Mostra para onde a tela navegou — é o que se confere depois de criar ou excluir. */
function Lista() {
  const lugar = useLocation();
  return (
    <p>
      lista:{lugar.pathname}
      {lugar.search}
      {lugar.state?.aviso && ` aviso:${lugar.state.aviso}`}
    </p>
  );
}

function renderizar(entrada) {
  return render(
    <MemoryRouter initialEntries={[entrada]}>
      <Routes>
        <Route path="/parceiros" element={<Lista />} />
        <Route path="/parceiros/novo" element={<Parceiro />} />
        <Route path="/parceiros/:id" element={<Parceiro />} />
      </Routes>
    </MemoryRouter>,
  );
}

function rotasDoCadastro(extra = {}) {
  return {
    "GET /api/categorias": { corpo: CATEGORIAS },
    "GET /api/parceiros/7": { corpo: CASA_AZUL },
    "GET /api/painel/series": { corpo: SERIE },
    ...extra,
  };
}

describe("Parceiro — cadastro novo", () => {
  it("campo recusado pelo servidor mostra o erro embaixo dele e recebe o foco", async () => {
    /* A validação é do servidor; a tela mostra onde ele disse que está o erro.
       Mensagem só no topo obrigaria a ligar as duas coisas de cabeça. */
    simularApi({
      "GET /api/categorias": { corpo: CATEGORIAS },
      "POST /api/parceiros": {
        status: 422,
        corpo: {
          erro: "Alguns campos precisam de correção.",
          campos: [{ campo: "nome", mensagem: "Obrigatório: informe ao menos 2 caracteres." }],
        },
      },
    });
    renderizar("/parceiros/novo");

    await userEvent.click(await screen.findByRole("button", { name: "Cadastrar parceiro" }));

    const nome = screen.getByLabelText(/Nome/);
    await waitFor(() => expect(nome).toHaveFocus());
    expect(nome).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Obrigatório: informe ao menos 2 caracteres.")).toBeVisible();
    expect(nome).toHaveAttribute("aria-describedby", "erro-nome");
  });

  it("nome em uso oferece abrir o cadastro que já existe", async () => {
    /* UC04-E1: a recusa mostra o existente, para o usuário decidir entre
       corrigir o nome e editar o que já está cadastrado. */
    simularApi({
      "GET /api/categorias": { corpo: CATEGORIAS },
      "POST /api/parceiros": {
        status: 409,
        corpo: {
          detail: {
            erro: "Já existe um parceiro com o nome 'Casa Azul'.",
            ajuda: "Corrija o nome, ou abra o cadastro existente e edite-o em vez de criar outro.",
            existente: { id: 7, nome: "Casa Azul" },
          },
        },
      },
    });
    renderizar("/parceiros/novo");

    await userEvent.type(await screen.findByLabelText(/Nome/), "Casa Azul");
    await userEvent.click(screen.getByRole("button", { name: "Cadastrar parceiro" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Já existe um parceiro com o nome 'Casa Azul'.");
    expect(within(alerta).getByRole("link", { name: "Abrir o cadastro de Casa Azul" })).toHaveAttribute(
      "href",
      "/parceiros/7",
    );
  });

  it("cadastrar leva ao cadastro recém-criado, com a confirmação", async () => {
    simularApi(
      rotasDoCadastro({
        "POST /api/parceiros": { status: 201, corpo: CASA_AZUL },
      }),
    );
    renderizar("/parceiros/novo");

    await userEvent.type(await screen.findByLabelText(/Nome/), "Casa Azul");
    await userEvent.click(screen.getByRole("button", { name: "Cadastrar parceiro" }));

    expect(await screen.findByText("Parceiro cadastrado.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Cadastro" })).toBeVisible();
  });
});

describe("Parceiro — cadastro existente", () => {
  it("carrega o cadastro no formulário e o desempenho ao lado", async () => {
    simularApi(rotasDoCadastro());
    renderizar("/parceiros/7");

    expect(await screen.findByLabelText(/Nome/)).toHaveValue("Casa Azul");
    expect(screen.getByLabelText("Categoria")).toHaveValue("1");
    expect(screen.getByLabelText("Contato")).toHaveValue("contato@exemplo.test");

    const desempenho = screen.getByRole("heading", { name: "Desempenho" }).closest("section");
    expect(within(desempenho).getByText("Em risco")).toBeVisible();
    expect(within(desempenho).getByText("R$ 1.000,00")).toBeVisible();
  });

  it("salvar confirma, e a confirmação some assim que algo muda", async () => {
    simularApi(
      rotasDoCadastro({
        "PATCH /api/parceiros/7": { corpo: { ...CASA_AZUL, nome: "Casa Azul Ltda" } },
      }),
    );
    renderizar("/parceiros/7");

    const nome = await screen.findByLabelText(/Nome/);
    await userEvent.clear(nome);
    await userEvent.type(nome, "Casa Azul Ltda");
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText("Alterações salvas.")).toBeVisible();
    await userEvent.type(nome, "!");
    expect(screen.queryByText("Alterações salvas.")).not.toBeInTheDocument();
  });

  it("excluir pede confirmação antes", async () => {
    /* É a única ação sem volta. Um clique sem confirmação apagaria o parceiro
       de quem só queria desativá-lo. */
    const chamadas = [];
    simularApi(
      rotasDoCadastro({
        "DELETE /api/parceiros/7": (url) => {
          chamadas.push(url);
          return { status: 204 };
        },
      }),
    );
    renderizar("/parceiros/7");

    await userEvent.click(await screen.findByRole("button", { name: "Excluir parceiro" }));

    expect(screen.getByText("Excluir Casa Azul? Isto não pode ser desfeito.")).toBeVisible();
    expect(chamadas).toHaveLength(0);
  });

  it("exclusão recusada por histórico oferece desativar", async () => {
    /* UC04-A4: com histórico, excluir falsearia as séries. A saída certa é
       desativar — e a tela oferece o botão em vez de explicar como. */
    const desativacoes = [];
    simularApi(
      rotasDoCadastro({
        "DELETE /api/parceiros/7": {
          status: 409,
          corpo: {
            detail: {
              erro: "O parceiro 'Casa Azul' tem histórico e não pode ser excluído.",
              ajuda: "Para tirá-lo de circulação sem perder o histórico, desative o parceiro.",
              vinculos: { metricas: 12, total: 12 },
            },
          },
        },
        "PATCH /api/parceiros/7": (_url, opcoes) => {
          desativacoes.push(JSON.parse(opcoes.body));
          return { corpo: { ...CASA_AZUL, ativo: false } };
        },
      }),
    );
    renderizar("/parceiros/7");

    await userEvent.click(await screen.findByRole("button", { name: "Excluir parceiro" }));
    await userEvent.click(screen.getByRole("button", { name: "Excluir" }));

    /* A recusa aparece **na seção onde se clicou**. A primeira versão a punha
       no topo da página, fora da vista de quem estava lá embaixo — e o teste
       passava, porque só procurava o texto em qualquer lugar. */
    const situacao = screen.getByRole("heading", { name: "Situação" }).closest("section");
    expect(await within(situacao).findByRole("alert")).toHaveTextContent("tem histórico");
    await userEvent.click(
      within(situacao).getByRole("button", { name: "Desativar em vez de excluir" }),
    );

    await waitFor(() => expect(desativacoes).toEqual([{ ativo: false }]));
    expect(await within(situacao).findByText(/Parceiro desativado/)).toBeVisible();
  });

  it("parceiro inexistente mostra o motivo e o caminho de volta", async () => {
    simularApi({
      "GET /api/categorias": { corpo: CATEGORIAS },
      "GET /api/parceiros/999": { status: 404, corpo: { detail: "Parceiro não encontrado." } },
      "GET /api/painel/series": { corpo: SERIE },
    });
    renderizar("/parceiros/999");

    expect(await screen.findByText("Parceiro não encontrado")).toBeVisible();
    expect(screen.getByRole("link", { name: "Voltar para a lista" })).toHaveAttribute(
      "href",
      "/parceiros",
    );
  });

  it("voltar devolve a lista com o filtro que ela tinha", async () => {
    /* Quem filtrou por "em risco" e abriu um parceiro espera voltar ao mesmo
       recorte, e não à base inteira. */
    simularApi(rotasDoCadastro());
    renderizar({ pathname: "/parceiros/7", state: { lista: "/parceiros?segmento=EM_RISCO" } });

    await userEvent.click(await screen.findByRole("link", { name: "Voltar para a lista" }));

    expect(await screen.findByText("lista:/parceiros?segmento=EM_RISCO")).toBeVisible();
  });
});

describe("Parceiro — sugestão de categoria pelo nome (RN05, H27)", () => {
  it("ao sair do nome, oferece a categoria que o nome aponta, e usar a preenche", async () => {
    const perguntas = [];
    simularApi(
      rotasDoCadastro({
        "GET /api/categorias/sugestao": (url) => {
          perguntas.push(String(url));
          return { corpo: { categoria: CATEGORIAS[0] } };
        },
      }),
    );
    const usuario = userEvent.setup();
    renderizar("/parceiros/novo");

    await usuario.type(await screen.findByLabelText(/^Nome/), "Padaria do Bairro");
    await usuario.tab();

    await usuario.click(await screen.findByRole("button", { name: "Usar Padaria" }));
    expect(screen.getByLabelText(/^Categoria/)).toHaveValue("1");
    expect(screen.queryByRole("button", { name: "Usar Padaria" })).not.toBeInTheDocument();
    expect(perguntas.at(-1)).toContain("nome=Padaria");
  });

  it("nome que não aponta categoria não oferece nada", async () => {
    simularApi(
      rotasDoCadastro({ "GET /api/categorias/sugestao": { corpo: { categoria: null } } }),
    );
    const usuario = userEvent.setup();
    renderizar("/parceiros/novo");

    await usuario.type(await screen.findByLabelText(/^Nome/), "Forno Real");
    await usuario.tab();

    expect(await screen.findByText(/Escolher uma categoria confirma/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Usar/ })).not.toBeInTheDocument();
  });

  it("categoria só sugerida pela importação diz que salvar a confirma", async () => {
    simularApi(
      rotasDoCadastro({
        "GET /api/parceiros/7": { corpo: { ...CASA_AZUL, origem_categoria: "INFERIDA" } },
      }),
    );
    renderizar("/parceiros/7");

    expect(await screen.findByText(/Sugerida pelo nome, ainda não confirmada/)).toBeInTheDocument();
  });
});

describe("Parceiro — previsão do próximo período (RF28, H44)", () => {
  const PREVISTO = {
    disponivel: true,
    faturamento_previsto: "1100.00",
    probabilidade_queda: 0.24,
    periodo_base: SERIE.pontos[1].periodo,
    modelo_versao: "rede-2",
    origem: "MODELO",
    gerada_em: "2026-09-24T20:00:02Z",
    desatualizada: false,
    motivo: null,
    ajuda: null,
  };

  it("mostra a estimativa marcada como tal, com a base e a versão", async () => {
    simularApi(rotasDoCadastro({ "GET /api/parceiros/7/previsao": { corpo: PREVISTO } }));
    renderizar("/parceiros/7");

    const secao = (await screen.findByRole("heading", { name: "Próximo período" })).closest(
      "section",
    );
    expect(within(secao).getByText("Estimativa")).toBeVisible();
    expect(within(secao).getByText("R$ 1.100,00")).toBeVisible();
    expect(within(secao).getByText("24%")).toBeVisible();
    expect(within(secao).getByText(/Rede neural · rede-2/)).toBeVisible();
    expect(within(secao).getByText(/não medição/)).toBeVisible();

    // A série ganha o trecho tracejado até o próximo período.
    expect(screen.getByText(/estimativa do modelo para o próximo período/)).toBeInTheDocument();
  });

  it("sem previsão, diz o motivo que a API deu", async () => {
    simularApi(
      rotasDoCadastro({
        "GET /api/parceiros/7/previsao": {
          corpo: {
            ...PREVISTO,
            disponivel: false,
            faturamento_previsto: null,
            probabilidade_queda: null,
            motivo: "Com 2 períodos de histórico, ainda não há previsão: são necessários 4.",
            ajuda: "A previsão aparece no primeiro treino depois que o parceiro completar a janela.",
          },
        },
      }),
    );
    renderizar("/parceiros/7");

    expect(await screen.findByText(/são necessários 4/)).toBeVisible();
    expect(screen.queryByText(/estimativa do modelo para o próximo período/)).toBeNull();
  });

  it("previsão de antes do período mais recente fica fora do gráfico, e avisa", async () => {
    simularApi(
      rotasDoCadastro({
        "GET /api/parceiros/7/previsao": { corpo: { ...PREVISTO, desatualizada: true } },
      }),
    );
    renderizar("/parceiros/7");

    expect(await screen.findByText(/o próximo treino a refaz/)).toBeVisible();
    // Estimativa de um período que já aconteceu não se desenha como futuro.
    expect(screen.queryByText(/estimativa do modelo para o próximo período/)).toBeNull();
  });
});

