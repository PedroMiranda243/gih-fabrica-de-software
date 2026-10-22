import { describe, expect, it } from "vitest";

import app from "../App.jsx?raw";
import { EXIGE, grupoDe, itemAtivo, MENU } from "./telas";

/*
 * H94 — o menu e a guarda dos endereços leem a mesma tabela. Quando cada um
 * tinha a sua lista, o menu escondia a Auditoria do analista e o endereço a
 * montava para ele, vazia, com a recusa da API dentro.
 */
describe("a tabela do que cada endereço exige", () => {
  it("todo item do menu exige o mesmo que a guarda do endereço dele", () => {
    const guardaDe = Object.fromEntries(Object.values(EXIGE).map((v) => [v.join(","), v]));
    for (const item of MENU.flatMap((g) => g.itens)) {
      expect(Object.values(EXIGE)).toContain(item.exige);
      expect(guardaDe[item.exige.join(",")]).toBe(item.exige);
    }
  });

  it("a guarda das rotas lê a mesma tabela, e nenhuma rota tem lista própria", () => {
    expect(app).not.toMatch(/T\(\[/);
    expect(app).not.toMatch(/exige=\{\[/);
    expect(app.match(/EXIGE\.\w+/g).length).toBeGreaterThanOrEqual(23);
  });

  it("a Importação aparece para quem importa ou para quem só lê o histórico", () => {
    expect(EXIGE.importacao).toEqual(["importar", "historico_importacoes"]);
  });

  it("o histórico de execuções e abrir um plano exigem coisas diferentes", () => {
    expect(EXIGE.execucoes).toEqual(["execucoes"]);
    expect(EXIGE.execucao).toEqual(["execucao"]);
  });
});

describe("o menu como mapa de rotas", () => {
  it("as áreas vêm na ordem do fluxo do produto, cada uma com a sua cor", () => {
    expect(MENU.map((g) => g.grupo)).toEqual(["Análise", "Previsão", "Otimização", "Comunicação", "Administração"]);
    expect(new Set(MENU.map((g) => g.rota)).size).toBe(MENU.length);
  });

  it("todo item diz o que há lá dentro", () => {
    for (const item of MENU.flatMap((g) => g.itens)) expect(item.dica).toMatch(/\S{3}/);
  });

  it("marca o item certo também nas telas de detalhe", () => {
    expect(itemAtivo("/")).toBe("/");
    expect(itemAtivo("/parceiros/12")).toBe("/parceiros");
    expect(itemAtivo("/execucoes/comparar")).toBe("/execucoes");
    expect(itemAtivo("/relatorios/risco")).toBe("/relatorios");
    expect(itemAtivo("/relatorios/operacoes")).toBe("/relatorios/operacoes");
    expect(itemAtivo("/conta")).toBeNull();
  });

  it("diz a área de cada item, e nenhuma fora das áreas", () => {
    expect(grupoDe("/campanha").grupo).toBe("Otimização");
    expect(grupoDe("/relatorios/operacoes").grupo).toBe("Administração");
    expect(grupoDe(null)).toBeNull();
  });
});
