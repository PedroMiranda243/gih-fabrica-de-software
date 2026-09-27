import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ContextoSessao } from "../api/contextoSessao";
import PlanoDeCampanha from "./PlanoDeCampanha";

const EXECUCAO = {
  id: 7,
  situacao: "CONCLUIDA",
  autor: "Gestora",
  modo: "SERIAL",
  concluida_em: "2026-09-26T12:00:06Z",
  parametros: {
    orcamento: "12000.00",
    maximo_acoes: 45,
    cotas_categoria: [],
    aplicacao_inicio: "2026-09-21",
    aplicacao_fim: "2026-09-27",
  },
  periodo_base: { id: 12, data_inicio: "2026-09-14", data_fim: "2026-09-20" },
  modelo_versao: "rede-1",
  viavel: true,
  uplift_total: "4180.00",
  custo_total: "90.00",
  tempo_ms: 6400,
  parcial: false,
  acoes: 1,
  cotas: [],
  folga_orcamento: "11910.00",
  folga_acoes: 44,
  ganho_guloso: "4180.00",
  itens: [
    {
      parceiro_id: 16,
      parceiro: "Villa da Praça",
      segmento: "EM_RISCO",
      categoria: "Restaurante",
      cauda_longa: true,
      acao_id: 1,
      acao: "Visita de relacionamento",
      custo: "90.00",
      ganho: "4180.00",
    },
  ],
};

function renderizar(telas) {
  const plano = (
    <MemoryRouter>
      <PlanoDeCampanha execucao={EXECUCAO} />
    </MemoryRouter>
  );
  return render(
    telas ? (
      <ContextoSessao.Provider value={{ usuario: { nome: "Quem testa", telas }, sair: () => {} }}>
        {plano}
      </ContextoSessao.Provider>
    ) : (
      plano
    ),
  );
}

describe("plano de campanha", () => {
  it("leva às mensagens com o plano já escolhido, para quem gera mensagens (H60)", () => {
    renderizar(["campanha", "execucao", "mensagens"]);
    expect(screen.getByRole("link", { name: "Gerar mensagens para este plano" })).toHaveAttribute(
      "href",
      "/mensagens?plano=7",
    );
  });

  it("quem não gera mensagens não vê o caminho", () => {
    renderizar(["execucoes"]);
    expect(screen.queryByRole("link", { name: "Gerar mensagens para este plano" })).not.toBeInTheDocument();
  });

  it("sem sessão em volta, o plano aparece igual, sem o caminho", () => {
    renderizar(null);
    expect(screen.getByRole("heading", { name: "Plano recomendado" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Gerar mensagens para este plano" })).not.toBeInTheDocument();
  });
});
