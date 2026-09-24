import { describe, expect, it } from "vitest";

import { comoDataHora, comoDinheiro, comoPercentual, sentidoDa, TRACO } from "./formato";

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

  it("instante vira dia e hora no relógio de quem olha, e ausente vira travessão", () => {
    /* A hora exata depende do fuso da máquina — a integração contínua roda em
       UTC —, então o que se confere é o formato, não o valor. */
    expect(comoDataHora("2026-09-14T13:05:00Z")).toMatch(/^\d{2}\/\d{2}\/2026 às \d{2}:\d{2}$/);
    expect(comoDataHora(null)).toBe(TRACO);
    expect(comoDataHora("não é data")).toBe(TRACO);
  });
});
