import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { abrir, amostra } from "../testes/montar";

const FILA = () => amostra("GET_api_mensagens");
const PRIMEIRA = () => FILA().itens[0];
const cartaoDe = (parceiro) => screen.getByRole("heading", { name: new RegExp(parceiro) }).closest("article");

/* RF37 (a fila, no estado pendente), RF38 (aprovar, editar ou rejeitar cada uma),
   RF39 (só o Gestor decide) e RF40 (o histórico das decididas). */
describe("a fila de aprovação", () => {
  it("lista as pendentes, com o texto e os fatos que a API conferiu (RF37)", async () => {
    abrir("/aprovacao", { rotas: { "GET /api/mensagens": { corpo: FILA() } } });

    expect(await screen.findByRole("heading", { name: /Quintal Verde 2/ })).toBeInTheDocument();
    const cartao = cartaoDe("Quintal Verde 2");
    expect(cartao).toHaveTextContent("R$ 57.841,79");
    expect(screen.getByRole("navigation", { name: "Estado das mensagens" }).querySelector('[aria-current="page"]')).toHaveTextContent(/Pendentes/);
  });

  it("o Gestor aprova uma mensagem, e ela sai da fila (RF38)", async () => {
    const usuario = userEvent.setup();
    const { chamadas } = abrir("/aprovacao", {
      rotas: {
        "GET /api/mensagens": { corpo: FILA() },
        "POST /api/mensagens/:id/aprovacao": { corpo: { ...PRIMEIRA(), estado: "APROVADA" } },
      },
    });

    await screen.findByRole("heading", { name: /Quintal Verde 2/ });
    await usuario.click(within(cartaoDe("Quintal Verde 2")).getByRole("button", { name: "Aprovar" }));

    expect(chamadas()).toContain(`POST /api/mensagens/${PRIMEIRA().id}/aprovacao`);
    expect((await screen.findAllByText("Mensagem para Quintal Verde 2 aprovada.")).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.queryByRole("heading", { name: /Quintal Verde 2/ })).not.toBeInTheDocument());
  });

  it("edita o texto, que continua na fila esperando a decisão (RF38)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/aprovacao", {
      rotas: {
        "GET /api/mensagens": { corpo: FILA() },
        "POST /api/mensagens/:id/edicao": (_url, opcoes) => ({ corpo: { ...PRIMEIRA(), texto: JSON.parse(opcoes.body).texto, editada: true } }),
      },
    });

    await screen.findByRole("heading", { name: /Quintal Verde 2/ });
    await usuario.click(within(cartaoDe("Quintal Verde 2")).getByRole("button", { name: "Editar" }));
    const caixa = within(cartaoDe("Quintal Verde 2")).getByRole("textbox");
    await usuario.clear(caixa);
    await usuario.type(caixa, "Olá, Quintal Verde 2! Conte com a gente nesta semana.");
    await usuario.click(within(cartaoDe("Quintal Verde 2")).getByRole("button", { name: "Salvar o texto" }));

    expect(corpoDe(`POST /api/mensagens/${PRIMEIRA().id}/edicao`)).toEqual({ texto: "Olá, Quintal Verde 2! Conte com a gente nesta semana." });
    expect((await screen.findAllByText(/Texto da mensagem para Quintal Verde 2 salvo\. Ela continua na fila/)).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /Quintal Verde 2/ })).toBeInTheDocument();
  });

  it("rejeita com um motivo, que é opcional (RF38)", async () => {
    const usuario = userEvent.setup();
    const { corpoDe } = abrir("/aprovacao", {
      rotas: {
        "GET /api/mensagens": { corpo: FILA() },
        "POST /api/mensagens/:id/rejeicao": { corpo: { ...PRIMEIRA(), estado: "REJEITADA" } },
      },
    });

    await screen.findByRole("heading", { name: /Quintal Verde 2/ });
    await usuario.click(within(cartaoDe("Quintal Verde 2")).getByRole("button", { name: "Rejeitar" }));
    await usuario.type(screen.getByLabelText("Motivo da rejeição (opcional)"), "Tom inadequado.");
    await usuario.click(screen.getByRole("button", { name: "Rejeitar mensagem" }));

    expect(corpoDe(`POST /api/mensagens/${PRIMEIRA().id}/rejeicao`)).toEqual({ motivo: "Tom inadequado." });
    expect((await screen.findAllByText("Mensagem para Quintal Verde 2 rejeitada.")).length).toBeGreaterThan(0);
  });

  it("o Analista acompanha a mesma fila, sem botão de decidir (RF39)", async () => {
    abrir("/aprovacao", { perfil: "ANALISTA", rotas: { "GET /api/mensagens": { corpo: FILA() } } });

    await screen.findByRole("heading", { name: /Quintal Verde 2/ });
    expect(screen.queryByRole("button", { name: "Aprovar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rejeitar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("as rejeitadas trazem quem decidiu, quando e o motivo (RF40)", async () => {
    const rejeitadas = {
      ...FILA(),
      itens: [{ ...PRIMEIRA(), id: 31, estado: "REJEITADA", decidida_por: "Gestora do Laboratório", decidida_em: "2026-10-06T10:00:00Z", motivo_rejeicao: "Tom inadequado." }],
      total: 1,
    };
    const { chamadas } = abrir("/aprovacao?estado=REJEITADA", { rotas: { "GET /api/mensagens": { corpo: rejeitadas } } });

    expect(await screen.findByRole("heading", { name: /Quintal Verde 2/ })).toBeInTheDocument();
    const cartao = cartaoDe("Quintal Verde 2");
    expect(cartao).toHaveTextContent(/Rejeitada por Gestora do Laboratório em 06\/10\/2026/);
    expect(cartao).toHaveTextContent("Tom inadequado.");
    expect(chamadas().some((c) => c.startsWith("GET /api/mensagens?") && c.includes("estado=REJEITADA"))).toBe(true);
  });

  it("as aprovadas saem lacradas, com quem aprovou, e dizem se há contato para enviar (RF40)", async () => {
    const aprovadas = {
      ...FILA(),
      itens: [{ ...PRIMEIRA(), id: 32, estado: "APROVADA", decidida_por: "Gestora do Laboratório", decidida_em: "2026-10-06T10:05:00Z", contato: null }],
      total: 1,
    };
    abrir("/aprovacao?estado=APROVADA", { rotas: { "GET /api/mensagens": { corpo: aprovadas } } });

    expect(await screen.findByRole("heading", { name: /Quintal Verde 2/ })).toBeInTheDocument();
    const cartao = cartaoDe("Quintal Verde 2");
    expect(cartao).toHaveTextContent("Aprovada");
    expect(cartao).toHaveTextContent("por Gestora do Laboratório");
    expect(cartao).toHaveTextContent("Parceiro sem contato cadastrado");
  });

  it("fila vazia diz isso, e oferece gerar mensagens a quem pode", async () => {
    abrir("/aprovacao", { rotas: { "GET /api/mensagens": { corpo: { itens: [], total: 0, pagina: 1, tamanho: 20 } } } });

    expect(await screen.findByText("Nenhuma mensagem pendente.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gerar mensagens" })).toHaveAttribute("href", "/mensagens");
  });
});
