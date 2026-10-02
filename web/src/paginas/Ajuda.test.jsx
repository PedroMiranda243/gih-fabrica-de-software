import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import { simularApi } from "../testes/preparar";
import Ajuda from "./Ajuda";

const GESTOR = {
  nome: "Gestora de Exemplo",
  perfil: "GESTOR",
  telas: ["painel", "painel_decisao", "importar", "historico_importacoes", "parceiros", "modelo", "campanha",
    "calcular_campanha", "execucoes", "execucao", "benchmark", "mensagens", "aprovacao", "decidir_mensagens",
    "relatorios", "assistente", "ajuda_regras"],
};
const ANALISTA = {
  nome: "Ana de Exemplo",
  perfil: "ANALISTA",
  telas: ["painel", "painel_decisao", "importar", "historico_importacoes", "parceiros", "campanha", "execucoes",
    "execucao", "mensagens", "aprovacao", "relatorios", "assistente", "ajuda_regras"],
};
const ADMINISTRADOR = {
  nome: "Administração",
  perfil: "ADMINISTRADOR",
  telas: ["painel", "historico_importacoes", "usuarios", "auditoria", "configuracao", "modelo", "execucoes",
    "benchmark", "relatorio_operacoes", "ajuda_regras"],
};
const PARCEIRO = { nome: "Comércio do Vale", perfil: "PARCEIRO", telas: ["meu_desempenho"] };

const REGRAS = {
  segmentos: ["PROSPECCAO", "RECEM_CHEGADO", "EM_RISCO", "TOP", "EM_ASCENSAO", "ESTAVEL"],
  top_n: 15,
  periodos_tendencia: 2,
  periodos_novato: 3,
  previsao: {
    versao_em_uso: "rede-4",
    origem: "MODELO",
    periodos_minimos_do_treino: 8,
    periodos_minimos_do_parceiro: 4,
  },
};

function renderizar(usuario, { regras = REGRAS, endereco = "/ajuda" } = {}) {
  const espia = simularApi(
    regras instanceof Error
      ? { "GET /api/ajuda/regras": { status: 500, corpo: { detail: "Erro interno." } } }
      : { "GET /api/ajuda/regras": { corpo: regras } },
  );
  render(
    <ContextoSessao.Provider value={{ usuario }}>
      <MemoryRouter initialEntries={[endereco]}>
        <Ajuda />
      </MemoryRouter>
    </ContextoSessao.Provider>,
  );
  return espia;
}

const bloco = (nome) => screen.getByRole("region", { name: nome });
const areas = () =>
  within(bloco("O que você pode fazer"))
    .getAllByRole("listitem")
    .map((li) => li.textContent);

describe("ajuda — o que o perfil pode fazer", () => {
  it("lista as áreas do perfil, com o caminho até cada uma, e a Minha conta, que é de todos", async () => {
    renderizar(GESTOR);
    const lista = bloco("O que você pode fazer");

    expect(within(lista).getByText("perfil Gestor")).toBeInTheDocument();
    expect(within(lista).getByRole("link", { name: "Campanha" })).toHaveAttribute("href", "/campanha");
    expect(within(lista).getByRole("link", { name: "Minha conta" })).toHaveAttribute("href", "/conta");
    // Nada de administração na ajuda de quem não administra.
    expect(within(lista).queryByRole("link", { name: "Usuários" })).not.toBeInTheDocument();
    await screen.findByRole("region", { name: "Os segmentos" });
  });

  it("o gestor calcula a campanha e decide as mensagens; o analista consulta e acompanha", async () => {
    renderizar(GESTOR);
    expect(areas()).toContain(
      "CampanhaCalcular o plano de campanha, com o orçamento e as restrições, e consultar o catálogo de ações.",
    );
    expect(areas().find((a) => a.startsWith("Aprovação"))).toMatch(/Aprovar, editar ou rejeitar cada mensagem/);
    await screen.findByRole("region", { name: "Os segmentos" });

    document.body.innerHTML = "";
    renderizar(ANALISTA);
    expect(areas().find((a) => a.startsWith("Campanha"))).toMatch(/Calcular o plano não faz parte do seu perfil/);
    expect(areas().find((a) => a.startsWith("Aprovação"))).toMatch(/Acompanhar a fila de mensagens/);
    // Uma frase por área: a do gestor não aparece junto.
    expect(areas().filter((a) => a.startsWith("Campanha"))).toHaveLength(1);
    await screen.findByRole("region", { name: "Os segmentos" });
  });

  it("o administrador lê o histórico das importações e das execuções, sem importar nem abrir o plano", async () => {
    renderizar(ADMINISTRADOR);

    expect(areas().find((a) => a.startsWith("Importação"))).toMatch(/Importar não faz parte do seu perfil/);
    expect(areas().find((a) => a.startsWith("Execuções"))).toMatch(/Abrir o plano não faz parte do seu perfil/);
    expect(areas().find((a) => a.startsWith("Configuração"))).toMatch(/limiares da segmentação/);
    await screen.findByRole("region", { name: "Os segmentos" });
  });
});

describe("ajuda — os segmentos, a estimativa e o ganho", () => {
  it("os segmentos vêm na ordem que a API mandou, com os limiares em vigor no critério", async () => {
    renderizar(GESTOR, {
      regras: { ...REGRAS, top_n: 10, periodos_tendencia: 3, periodos_novato: 4 },
    });

    const itens = within(await screen.findByRole("region", { name: "Os segmentos" })).getAllByRole("listitem");

    expect(itens.map((li) => li.firstElementChild.textContent)).toEqual([
      "Prospecção", "Recém-chegado", "Em risco", "Top 10", "Em ascensão", "Estável",
    ]);
    expect(itens[1]).toHaveTextContent("Tem menos de 4 períodos de histórico");
    expect(itens[2]).toHaveTextContent("O faturamento caiu em 3 períodos seguidos, ou mais.");
    expect(itens[3]).toHaveTextContent("Está entre os 10 maiores faturamentos do período mais recente.");
    expect(itens[4]).toHaveTextContent("O faturamento subiu em 3 períodos seguidos, ou mais");
  });

  it("a ordem é a da API, e não uma ordem da tela", async () => {
    renderizar(GESTOR, { regras: { ...REGRAS, segmentos: ["TOP", "EM_RISCO"] } });

    const itens = within(await screen.findByRole("region", { name: "Os segmentos" })).getAllByRole("listitem");

    expect(itens.map((li) => li.firstElementChild.textContent)).toEqual(["Top 15", "Em risco"]);
  });

  it("um período só se escreve no singular", async () => {
    renderizar(GESTOR, { regras: { ...REGRAS, periodos_tendencia: 1, periodos_novato: 1 } });

    const segmentos = await screen.findByRole("region", { name: "Os segmentos" });

    expect(segmentos).toHaveTextContent("Tem menos de 1 período de histórico");
    expect(segmentos).toHaveTextContent("O faturamento caiu no último período.");
  });

  it("quem muda os limiares tem o caminho até a Configuração; os outros leem quem muda", async () => {
    renderizar(ADMINISTRADOR);
    const doAdministrador = await screen.findByRole("region", { name: "Os segmentos" });
    expect(within(doAdministrador).getByRole("link", { name: "Configuração" })).toHaveAttribute(
      "href",
      "/configuracao",
    );

    document.body.innerHTML = "";
    renderizar(ANALISTA);
    const doAnalista = await screen.findByRole("region", { name: "Os segmentos" });
    expect(doAnalista).toHaveTextContent("Quem os muda é o administrador.");
    expect(within(doAnalista).queryByRole("link")).not.toBeInTheDocument();
  });

  it("a estimativa diz o modelo em uso e o histórico que ela pede", async () => {
    renderizar(GESTOR);

    const estimativa = await screen.findByRole("region", { name: "Estimativa" });

    expect(estimativa).toHaveTextContent("As estimativas de agora saem do modelo rede-4.");
    expect(estimativa).toHaveTextContent("Parceiro com menos de 4 períodos de histórico não recebe estimativa");
    expect(estimativa).toHaveTextContent("com o faturamento caindo em 2 períodos seguidos, ou mais");
  });

  it("sem modelo treinado, diz que não há estimativa e quanto histórico o treino pede (UC16-A2)", async () => {
    renderizar(GESTOR, {
      regras: { ...REGRAS, previsao: { ...REGRAS.previsao, versao_em_uso: null, origem: null } },
    });

    const estimativa = await screen.findByRole("region", { name: "Estimativa" });

    expect(estimativa).toHaveTextContent("Ainda não há modelo em uso");
    expect(estimativa).toHaveTextContent("O primeiro treino precisa de 8 períodos importados.");
  });

  it("a previsão que sai da referência é dita como referência", async () => {
    renderizar(GESTOR, {
      regras: {
        ...REGRAS,
        previsao: { ...REGRAS.previsao, versao_em_uso: "referencia-7", origem: "REFERENCIA" },
      },
    });

    expect(await screen.findByRole("region", { name: "Estimativa" })).toHaveTextContent(
      "saem da referência referencia-7: nenhuma rede treinada a superou ainda",
    );
  });

  it("o ganho esperado mostra as duas parcelas da conta", async () => {
    renderizar(GESTOR);

    expect(await screen.findByRole("region", { name: "Ganho esperado" })).toHaveTextContent(
      "ganho = previsto × crescimento + previsto × chance de queda × retenção",
    );
  });

  it("quem chega por 'o que é isto?' cai no bloco pedido, com o foco nele", async () => {
    renderizar(GESTOR, { endereco: "/ajuda#estimativa" });

    await waitFor(() => expect(screen.getByRole("heading", { name: "Estimativa" })).toHaveFocus());
  });

  it("se as regras não chegam, a tela diz isso e mantém o que o perfil pode fazer", async () => {
    renderizar(GESTOR, { regras: new Error("fora") });

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "O que você pode fazer" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Os segmentos" })).not.toBeInTheDocument();
  });
});

describe("ajuda — o portal do parceiro (UC16-A1)", () => {
  it("o parceiro lê só a ajuda do portal dele, e a tela não pede as regras da rede", () => {
    const espia = renderizar(PARCEIRO);

    const caminhos = within(bloco("O que você pode fazer")).getAllByRole("link");
    expect(caminhos.map((a) => a.textContent)).toEqual(["Meu desempenho", "Minha conta"]);
    const portal = bloco("O seu portal");
    expect(portal).toHaveTextContent("O portal mostra só o seu comércio.");
    expect(portal).toHaveTextContent("O ticket médio é o faturamento dividido pelo número de pedidos.");
    expect(screen.queryByRole("region", { name: "Os segmentos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Estimativa" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Ganho esperado" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Top/)).not.toBeInTheDocument();
    expect(espia).not.toHaveBeenCalled();
  });
});
