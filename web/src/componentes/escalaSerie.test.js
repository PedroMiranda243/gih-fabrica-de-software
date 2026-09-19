import { describe, expect, it } from "vitest";

import {
  FOLGA_EIXO,
  FOLGA_ROTULO_FINAL,
  FONTE_EIXO,
  FONTE_ROTULO_FINAL,
  FRACOES_DA_GRADE,
  larguraDoTexto,
  MARGEM,
  rotuloCompacto,
  tetoBonito,
} from "./escalaSerie";

/* Faturamentos de várias ordens de grandeza: de uma rede minúscula a uma
   muito maior que a do gerador. O rótulo mais largo não é o de hoje — é o
   maior que o eixo pode vir a mostrar. */
const MAXIMOS = [
  850, 9_999, 45_000, 450_000, 999_999, 1_994_018, 7_450_000, 99_999_999, 999_999_999,
];

describe("margens da série histórica", () => {
  it.each(MAXIMOS)("os rótulos do eixo cabem à esquerda com máximo %s", (maximo) => {
    /* A primeira versão tinha 60 px e cortava o "R" de "R$ 500 mil" — o defeito
       apareceu na captura do documento de entrega, não num teste. */
    const teto = tetoBonito(maximo);
    FRACOES_DA_GRADE.forEach((fracao) => {
      const rotulo = rotuloCompacto(teto * (1 - fracao));
      const ocupa = larguraDoTexto(rotulo, FONTE_EIXO) + FOLGA_EIXO;
      expect(ocupa, `"${rotulo}" ocupa ${ocupa}px`).toBeLessThanOrEqual(MARGEM.esquerda);
    });
  });

  it.each(MAXIMOS)("o rótulo do último ponto cabe à direita com valor %s", (valor) => {
    const rotulo = rotuloCompacto(valor);
    const ocupa = larguraDoTexto(rotulo, FONTE_ROTULO_FINAL) + FOLGA_ROTULO_FINAL;
    expect(ocupa, `"${rotulo}" ocupa ${ocupa}px`).toBeLessThanOrEqual(MARGEM.direita);
  });

  it("a conta de largura é a da Fira Code, monoespaçada a 0,6 em", () => {
    /* Se alguém trocar a fonte dos rótulos por uma proporcional, esta conta
       deixa de valer — e este teste é o lembrete. */
    expect(larguraDoTexto("R$ 500 mil", 10)).toBe(60);
  });
});
