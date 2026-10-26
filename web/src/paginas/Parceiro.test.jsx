import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { avisariaAoFechar } from "../testes/preparar";
import { abrir, amostra, endereco } from "../testes/montar";

const DO_PARCEIRO = (extra = {}) => ({
  "GET /api/parceiros/:id": { corpo: amostra("GET_api_parceiros_parceiro_id") },
  "GET /api/parceiros/:id/previsao": { corpo: amostra("GET_api_parceiros_parceiro_id_previsao") },
  "GET /api/parceiros/:id/campanha": { corpo: amostra("GET_api_parceiros_parceiro_id_campanha") },
  "GET /api/parceiros/:id/historico": { corpo: amostra("GET_api_parceiros_parceiro_id_historico") },
  "GET /api/painel/series": { corpo: amostra("GET_api_painel_series") },
  "GET /api/categorias": { corpo: amostra("GET_api_categorias") },
  ...extra,
});

/* RF14 (cadastrar, editar, desativar), RF15 (sugerir a categoria), RF28
   (previsão e risco) e RF50 (histórico do cadastro). */
describe("o cadastro do parceiro", () => {
  it("cadastra um parceiro novo e abre a ficha dele (RF14)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/parceiros/novo", {
      rotas: DO_PARCEIRO({
        "GET /api/categorias/sugestao": { corpo: { categoria: null } },
        "POST /api/parceiros": { status: 201, corpo: { ...amostra("GET_api_parceiros_parceiro_id"), id: 501, nome: "Padaria Sol" } },
      }),
    });

    await usuario.type(await screen.findByLabelText(/^Nome/), "Padaria Sol");
    await usuario.type(screen.getByLabelText("Contato"), "compras@padariasol.exemplo");
    await usuario.click(screen.getByRole("button", { name: "Cadastrar parceiro" }));

    expect(corpoDe("POST /api/parceiros")).toEqual({ nome: "Padaria Sol", categoria_id: null, status: "ATIVO", contato: "compras@padariasol.exemplo" });
    await waitFor(() => expect(endereco()).toBe("/parceiros/501"));
    expect(await screen.findByText("Parceiro cadastrado.")).toBeInTheDocument();
  });

  it("sugere a categoria pelo nome, como sugestão, e só a usa com o clique da pessoa (RF15)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/parceiros/novo", {
      rotas: DO_PARCEIRO({ "GET /api/categorias/sugestao": { corpo: amostra("GET_api_categorias_sugestao") } }),
    });

    await usuario.type(await screen.findByLabelText(/^Nome/), "Pizzaria do Vale");
    await usuario.tab();

    expect(await screen.findByText(/Pelo nome, parece/)).toHaveTextContent("Pelo nome, parece Pizzaria.");
    expect(chamadas().some((c) => c.startsWith("GET /api/categorias/sugestao") && c.includes("nome=Pizzaria"))).toBe(true);
    expect(screen.getByLabelText("Categoria")).toHaveValue("");
    await usuario.click(screen.getByRole("button", { name: "Usar Pizzaria" }));
    expect(screen.getByLabelText("Categoria")).toHaveValue("3");
  });

  it("edita mandando só o que mudou, e avisa antes de sair com alteração não salva (RF14, H97)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/parceiros/246", {
      rotas: DO_PARCEIRO({ "PATCH /api/parceiros/:id": { corpo: { ...amostra("GET_api_parceiros_parceiro_id"), contato: "(81) 3000-0000" } } }),
    });

    const contato = await screen.findByLabelText("Contato");
    expect(avisariaAoFechar()).toBe(false);
    await usuario.type(contato, "(81) 3000-0000");
    expect(avisariaAoFechar()).toBe(true);
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
    expect(corpoDe("PATCH /api/parceiros/246")).toEqual({ contato: "(81) 3000-0000" });
    expect(avisariaAoFechar()).toBe(false);
  });

  it("nome repetido vem com o link para o cadastro que já existe", async () => {
    const usuario = userEvent.setup();
    abrir("/parceiros/novo", {
      rotas: DO_PARCEIRO({
        "GET /api/categorias/sugestao": { corpo: { categoria: null } },
        "POST /api/parceiros": { status: 409, corpo: { detail: { erro: "Já existe um parceiro com esse nome.", existente: { id: 246, nome: "Ponto Azul 2" } } } },
      }),
    });

    await usuario.type(await screen.findByLabelText(/^Nome/), "Ponto Azul 2");
    await usuario.click(screen.getByRole("button", { name: "Cadastrar parceiro" }));

    expect(await screen.findByRole("link", { name: "Abrir o cadastro de Ponto Azul 2" })).toHaveAttribute("href", "/parceiros/246");
  });

  it("mostra a previsão e a chance de queda como estimativa, com a versão do modelo (RF28)", async () => {
    abrir("/parceiros/246", { rotas: DO_PARCEIRO() });

    const previsao = (await screen.findByRole("heading", { name: "Próximo período" })).closest("section");
    await waitFor(() => expect(previsao).toHaveTextContent("84.818"));
    expect(previsao).toHaveTextContent("Estimativa");
    expect(previsao).toHaveTextContent("84.818");
    expect(previsao).toHaveTextContent("24%");
    expect(previsao).toHaveTextContent("rede-1");
  });

  it("sem previsão, diz o porquê que a API mandou, e não mostra zero (RF28)", async () => {
    abrir("/parceiros/246", {
      rotas: DO_PARCEIRO({
        "GET /api/parceiros/:id/previsao": {
          corpo: { disponivel: false, faturamento_previsto: null, probabilidade_queda: null, periodo_base: null, modelo_versao: null, origem: null, gerada_em: null, desatualizada: false, motivo: "Parceiro com histórico curto demais para prever.", ajuda: null },
        },
      }),
    });

    expect(await screen.findByText("Parceiro com histórico curto demais para prever.")).toBeInTheDocument();
  });

  it("o histórico diz o que mudou no cadastro, quem e quando (RF50)", async () => {
    abrir("/parceiros/246", {
      rotas: DO_PARCEIRO({
        "GET /api/parceiros/:id/historico": {
          corpo: [{ acao: "PARCEIRO_EDITADO", rotulo: "Categoria", resumo: "de Lanchonete para Mercado", autor: "Gestora do Laboratório", ocorrido_em: "2026-10-05T12:00:00Z" }],
        },
      }),
    });

    const historico = (await screen.findByRole("heading", { name: "Histórico do cadastro" })).closest("section");
    await waitFor(() => expect(historico).toHaveTextContent("Categoria de Lanchonete para Mercado"));
    expect(historico).toHaveTextContent("Gestora do Laboratório");
  });

  it("desativa com confirmação, em vez de apagar (RF14)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/parceiros/246", {
      rotas: DO_PARCEIRO({ "PATCH /api/parceiros/:id": { corpo: { ...amostra("GET_api_parceiros_parceiro_id"), ativo: false } } }),
    });

    await usuario.click(await screen.findByRole("button", { name: "Desativar" }));
    expect(screen.getByText(/Desativar Ponto Azul 2\? Ele deixa de entrar nas próximas campanhas\./)).toBeInTheDocument();
    const confirmar = screen.getAllByRole("button", { name: "Desativar" }).at(-1);
    await usuario.click(confirmar);

    await waitFor(() => expect(corpoDe("PATCH /api/parceiros/246")).toEqual({ ativo: false }));
  });

  it("endereço de parceiro que não existe diz isso, e oferece a volta", async () => {
    abrir("/parceiros/99999", { rotas: DO_PARCEIRO({ "GET /api/parceiros/:id": { status: 404, corpo: { detail: "Parceiro não encontrado." } } }) });

    expect(await screen.findByText("Parceiro não encontrado", { selector: "p, h2, h3, strong" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voltar para a lista" })).toHaveAttribute("href", "/parceiros");
  });
});
