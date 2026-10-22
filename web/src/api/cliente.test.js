import { afterEach, describe, expect, it, vi } from "vitest";

import { simularApi } from "../testes/preparar";
import { aoEncerrarSessao, api, comConsulta, ErroDaApi } from "./cliente";

/*
 * Tudo que fala com a API passa pelo cliente: a sessão vai no cookie HttpOnly
 * (o JavaScript não a vê), o erro é o texto do servidor, e o 401 é a sessão que
 * terminou — menos o 401 da própria tentativa de entrar, que é senha errada.
 */
describe("o cliente da API", () => {
  let desligar = () => {};
  afterEach(() => desligar());

  it("manda a sessão pelo cookie, sem cabeçalho de autorização", async () => {
    const fetch = simularApi({ "GET /api/parceiros": { corpo: { itens: [] } } });
    await api.get("/api/parceiros");
    const [, opcoes] = fetch.mock.calls[0];
    expect(opcoes.credentials).toBe("same-origin");
    expect(opcoes.headers).not.toHaveProperty("Authorization");
  });

  it("leva só os parâmetros com valor: busca vazia não filtra por texto vazio", () => {
    expect(comConsulta("/api/parceiros", { busca: "", segmento: "TOP", pagina: 1, categoria_id: null })).toBe(
      "/api/parceiros?segmento=TOP&pagina=1",
    );
    expect(comConsulta("/api/parceiros")).toBe("/api/parceiros");
  });

  it("manda o corpo em JSON", async () => {
    const fetch = simularApi({ "POST /api/parceiros": { status: 201, corpo: { id: 9 } } });
    expect(await api.post("/api/parceiros", { nome: "Padaria Sol" })).toEqual({ id: 9 });
    const [, opcoes] = fetch.mock.calls[0];
    expect(opcoes.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(opcoes.body)).toEqual({ nome: "Padaria Sol" });
  });

  it("o erro é o texto do servidor, com a ajuda e os campos", async () => {
    simularApi({
      "POST /api/importacoes": {
        status: 422,
        corpo: { detail: { erro: "Informe o período.", ajuda: "Sem as datas, a segmentação classifica errado." }, campos: [{ campo: "periodo_inicio", mensagem: "Obrigatório." }] },
      },
    });
    const erro = await api.post("/api/importacoes", {}).catch((e) => e);
    expect(erro).toBeInstanceOf(ErroDaApi);
    expect(erro.status).toBe(422);
    expect(erro.message).toBe("Informe o período.");
    expect(erro.ajuda).toBe("Sem as datas, a segmentação classifica errado.");
    expect(erro.campos).toEqual([{ campo: "periodo_inicio", mensagem: "Obrigatório." }]);
  });

  it("sem resposta do servidor, diz para conferir a conexão", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const erro = await api.get("/api/painel/indicadores").catch((e) => e);
    expect(erro.status).toBe(0);
    expect(erro.message).toMatch(/Não foi possível falar com o servidor/);
  });

  it("o 401 avisa que a sessão terminou", async () => {
    const ouvinte = vi.fn();
    desligar = aoEncerrarSessao(ouvinte);
    simularApi({ "GET /api/parceiros": { status: 401, corpo: { detail: "Sessão expirada." } } });
    await api.get("/api/parceiros").catch(() => {});
    expect(ouvinte).toHaveBeenCalledTimes(1);
  });

  it("o 401 de quem tenta entrar é senha errada, e não fim de sessão", async () => {
    const ouvinte = vi.fn();
    desligar = aoEncerrarSessao(ouvinte);
    simularApi({ "POST /api/sessao": { status: 401, corpo: { detail: "Login ou senha incorretos." } } });
    const erro = await api.post("/api/sessao", { login: "a", senha: "b" }).catch((e) => e);
    expect(erro.message).toBe("Login ou senha incorretos.");
    expect(ouvinte).not.toHaveBeenCalled();
  });
});
