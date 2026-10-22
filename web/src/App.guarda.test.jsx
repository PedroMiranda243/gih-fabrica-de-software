import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { abrir, amostra, endereco } from "./testes/montar";

/*
 * RF05 — quem pode o quê vem do servidor (`usuario.telas`). A guarda dos
 * endereços não é controle de acesso (quem decide é a API, a cada requisição):
 * é a interface deixando de montar uma tela que ela já sabe que será recusada.
 */
describe("a guarda dos endereços", () => {
  it("mostra 'Sem acesso' a quem não abre a tela, sem chamar a API dela", async () => {
    const { chamadas } = abrir("/auditoria", { perfil: "ANALISTA" });

    expect(await screen.findByRole("heading", { level: 1, name: "Sem acesso" })).toBeInTheDocument();
    expect(screen.getByText(/O seu perfil não abre esta tela/)).toBeInTheDocument();
    expect(chamadas().filter((c) => c.includes("/api/auditoria"))).toEqual([]);
  });

  it("abre a tela para quem tem a área na sessão", async () => {
    abrir("/auditoria", {
      perfil: "ADMINISTRADOR",
      rotas: {
        "GET /api/auditoria": { corpo: amostra("GET_api_auditoria") },
        "GET /api/auditoria/acoes": { corpo: amostra("GET_api_auditoria_acoes") },
        "GET /api/usuarios": { corpo: amostra("GET_api_usuarios") },
      },
    });

    expect(await screen.findByRole("heading", { level: 1, name: "Auditoria" })).toBeInTheDocument();
    expect(screen.queryByText(/O seu perfil não abre esta tela/)).not.toBeInTheDocument();
  });

  it("leva o Parceiro, que não tem painel, ao próprio desempenho", async () => {
    abrir("/", { perfil: "PARCEIRO", rotas: { "GET /api/meu-desempenho": { corpo: amostra("GET_api_meu_desempenho") } } });

    await waitFor(() => expect(endereco()).toBe("/meu-desempenho"));
  });

  it("nega ao Parceiro a lista da rede, mesmo pelo endereço digitado", async () => {
    const { chamadas } = abrir("/parceiros", { perfil: "PARCEIRO" });

    expect(await screen.findByRole("heading", { level: 1, name: "Sem acesso" })).toBeInTheDocument();
    expect(chamadas().filter((c) => c.includes("/api/parceiros"))).toEqual([]);
  });

  it("manda quem não tem sessão para a entrada", async () => {
    abrir("/parceiros?segmento=TOP", { perfil: null });

    await waitFor(() => expect(endereco()).toBe("/entrar"));
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("sem a lista de telas na sessão, não adivinha: deixa a API responder", async () => {
    const usuario = { ...amostra("sessao_de_cada_perfil").ANALISTA, telas: undefined };
    const { chamadas } = abrir("/auditoria", {
      usuario,
      rotas: {
        "GET /api/auditoria": { status: 403, corpo: { detail: "O seu perfil não tem acesso a esta operação." } },
        "GET /api/auditoria/acoes": { status: 403, corpo: { detail: "O seu perfil não tem acesso a esta operação." } },
        "GET /api/usuarios": { status: 403, corpo: { detail: "O seu perfil não tem acesso a esta operação." } },
      },
    });

    await waitFor(() => expect(chamadas().some((c) => c.startsWith("GET /api/auditoria"))).toBe(true));
    expect((await screen.findAllByText("O seu perfil não tem acesso a esta operação.")).length).toBeGreaterThan(0);
  });
});
