import { describe, expect, it } from "vitest";

import {
  comoData,
  comoDataHora,
  comoDelta,
  comoDinheiro,
  comoDinheiroCurto,
  comoFracao,
  comoInteiro,
  comoPeriodo,
  comoProbabilidade,
  comoTempo,
  comoVariacao,
  comoVezes,
  cotasDoPedido,
  deFracao,
  lerReais,
  paraCampoDeReais,
  paraFracao,
  partesDoDinheiro,
  ROTULO_SEGMENTO,
  sentidoDa,
  TRACO,
} from "./formato";

/*
 * Como a tela escreve o que a API mandou. Nada aqui calcula regra: só converte
 * para exibir, e de volta para o formato da API. A regra que mais importa é a
 * primeira — nulo não é zero.
 */
describe("nulo é travessão, e não zero", () => {
  it.each([
    ["dinheiro", comoDinheiro],
    ["inteiro", comoInteiro],
    ["variação", comoVariacao],
    ["diferença", comoDelta],
    ["fração", comoFracao],
    ["probabilidade", comoProbabilidade],
    ["tempo", comoTempo],
    ["fator", comoVezes],
    ["data", comoData],
    ["instante", comoDataHora],
    ["período", comoPeriodo],
  ])("%s nulo, indefinido ou vazio vira —", (_, formatar) => {
    expect(formatar(null)).toBe(TRACO);
    expect(formatar(undefined)).toBe(TRACO);
    expect(formatar("")).toBe(TRACO);
  });

  it("zero continua zero", () => {
    expect(comoDinheiro("0.00")).toBe("R$ 0,00");
    expect(comoInteiro(0)).toBe("0");
    expect(comoVariacao("0.00")).toBe("0,00%");
  });
});

describe("dinheiro chega como texto", () => {
  it("escreve em reais, com os centavos", () => {
    expect(comoDinheiro("12500.40")).toBe("R$ 12.500,40");
    expect(comoDinheiro("12500.4", { semCentavos: true })).toBe("R$ 12.500");
  });

  it("escreve 'R$' com espaço comum, como a API escreve nas mensagens e no assistente", () => {
    // api/app/formato.py: "R$ " + valor. O gestor lê o mesmo número nos dois lugares.
    expect(comoDinheiro("1234.50")).toBe("R$ 1.234,50");
    expect(comoDinheiro("1234.50")).not.toContain(" ");
  });

  it("parte o valor para a tipografia, com o sinal de menos de verdade", () => {
    expect(partesDoDinheiro("-1234.5")).toEqual({ sinal: "−", inteiros: "1.234", centavos: "50" });
    expect(partesDoDinheiro(null)).toBeNull();
  });

  it("encurta para eixo de gráfico", () => {
    expect(comoDinheiroCurto("1840000")).toBe("1,84 mi");
    expect(comoDinheiroCurto("820400")).toBe("820 mil");
    expect(comoDinheiroCurto("950")).toBe("950");
  });

  it("lê o que a pessoa digitou e devolve no formato da API, sem validar", () => {
    expect(lerReais("R$ 12.000,50")).toBe("12000.50");
    expect(lerReais("abc")).toBe("abc");
    expect(paraCampoDeReais("12000.5")).toBe("12.000,50");
    expect(paraCampoDeReais(null)).toBe("");
  });
});

describe("variação: o sinal é parte da notícia", () => {
  it("escreve o sinal nos dois sentidos", () => {
    expect(comoVariacao("15.06")).toBe("+15,06%");
    expect(comoVariacao("-15.06")).toBe("−15,06%");
  });

  it("diz o sentido: zero é medição (estável), nulo é ausência dela", () => {
    expect(sentidoDa("3.2")).toBe("sobe");
    expect(sentidoDa("-3.2")).toBe("cai");
    expect(sentidoDa("0")).toBe("estavel");
    expect(sentidoDa(null)).toBe("indefinida");
  });

  it("diferença de contagem em palavras", () => {
    expect(comoDelta(8)).toBe("8 a mais");
    expect(comoDelta(-2)).toBe("2 a menos");
    expect(comoDelta(0)).toBe("igual");
  });
});

describe("frações e chances", () => {
  it("fração vira percentual", () => {
    expect(comoFracao("0.0922")).toBe("9,2%");
    expect(comoFracao("0.25", 0)).toBe("25%");
  });

  it("a chance estimada não finge certeza nas pontas", () => {
    expect(comoProbabilidade(0.001)).toBe("menos de 1%");
    expect(comoProbabilidade(0.999)).toBe("mais de 99%");
    expect(comoProbabilidade(0.42)).toBe("42%");
  });

  it("o percentual digitado vai como fração de quatro casas, e volta", () => {
    expect(paraFracao("30")).toBe("0.3000");
    expect(paraFracao("14,5")).toBe("0.1450");
    expect(paraFracao("")).toBeNull();
    expect(paraFracao("muito")).toBe("muito");
    expect(deFracao("0.1400")).toBe("14");
    expect(deFracao("0.1450")).toBe("14,5");
  });
});

describe("tempo e fator do benchmark", () => {
  it("escreve o tempo com a unidade que cabe", () => {
    expect(comoTempo(0.0042)).toBe("4,2 ms");
    expect(comoTempo(0.306)).toBe("306 ms");
    expect(comoTempo(4.2)).toBe("4,20 s");
    expect(comoTempo(42)).toBe("42,0 s");
    expect(comoTempo(125)).toBe("2 min 5 s");
  });

  it("escreve o ganho como fator", () => {
    expect(comoVezes(8)).toBe("8,0x");
    expect(comoVezes(135.4)).toBe("135x");
  });
});

describe("datas", () => {
  it("o dia de um período sai sem fuso", () => {
    expect(comoData("2026-09-21")).toBe("21/09/2026");
    expect(comoPeriodo({ data_inicio: "2026-09-28", data_fim: "2026-10-04" })).toBe("28/09/2026 a 04/10/2026");
  });

  it("um instante sai no relógio de quem olha", () => {
    expect(comoDataHora("2026-10-05T12:30:00")).toMatch(/^05\/10\/2026 às \d{2}:\d{2}$/);
  });
});

describe("rótulos", () => {
  it("o segmento Top não leva número: o tamanho do Top vem da API (#229)", () => {
    expect(ROTULO_SEGMENTO.TOP).toBe("Top");
    for (const rotulo of Object.values(ROTULO_SEGMENTO)) expect(rotulo).not.toMatch(/\d/);
  });

  it("as cotas pedidas saem com o nome da categoria", () => {
    const execucao = {
      cotas: [{ categoria_id: 3, nome: "Pizzaria" }],
      parametros: { cotas_categoria: [{ categoria_id: 3, minimo: "0.10", maximo: "0.40" }, { categoria_id: 9, minimo: null, maximo: "0.20" }] },
    };
    expect(cotasDoPedido(execucao)).toEqual(["Pizzaria: mín. 10%, máx. 40%", "Categoria 9: máx. 20%"]);
  });
});
