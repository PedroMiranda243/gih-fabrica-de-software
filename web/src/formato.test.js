import { describe, expect, it } from "vitest";

import { comoDinheiro, comoPercentual, sentidoDa, TRACO } from "./formato";

describe("formatação", () => {
  it("variação nula vira travessão, e nunca zero", () => {
    /* Zero diz "não mudou"; nulo diz "não dá para dizer". Desenhar 0% numa
       variação indefinida afirmaria estabilidade que ninguém mediu. */
    expect(comoPercentual(null)).toBe(TRACO);
    expect(comoPercentual(undefined)).toBe(TRACO);
    expect(sentidoDa(null)).toBe("indefinida");
  });

  it("variação zero é estável, e não indefinida", () => {
    /* A primeira versão fundia os dois, e a tela mostrava "sem variação
       calculável" para um período que simplesmente não mudou. */
    expect(comoPercentual("0.00")).toBe("0,00%");
    expect(sentidoDa("0.00")).toBe("estavel");
  });

  it("o sinal aparece nos dois sentidos", () => {
    expect(comoPercentual("12.5")).toBe("+12,50%");
    expect(comoPercentual("-66.67")).toBe("-66,67%");
  });

  it("dinheiro chega como texto da API e sai em reais", () => {
    /* A API manda "12500.40" como texto de propósito: ponto flutuante perde
       centavo. A tela só formata. */
    expect(comoDinheiro("12500.40")).toMatch(/12\.500,40/);
    expect(comoDinheiro(null)).toBe(TRACO);
  });
});
