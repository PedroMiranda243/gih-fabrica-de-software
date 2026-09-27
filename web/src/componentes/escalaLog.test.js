import { describe, expect, it } from "vitest";

import {
  ALTURA_DA_AREA,
  dominioDoTempo,
  fracaoLog,
  larguraDaArea,
  marcasDosParceiros,
  MARGEM,
  marcasDoTempo,
  rotuloDoTempo,
  rotulosQueCabem,
  xDosParceiros,
  yDoTempo,
} from "./escalaLog";

describe("escala logarítmica do benchmark", () => {
  it("a mesma razão ocupa a mesma distância", () => {
    expect(fracaoLog(100, [100, 10_000])).toBe(0);
    expect(fracaoLog(1000, [100, 10_000])).toBeCloseTo(0.5);
    expect(fracaoLog(10_000, [100, 10_000])).toBe(1);
    // De 500 para 2.000 é o mesmo 4x que de 2.500 para 10.000.
    expect(xDosParceiros(2000) - xDosParceiros(500)).toBeCloseTo(
      xDosParceiros(10_000) - xDosParceiros(2500),
    );
  });

  it("o eixo dos parceiros ocupa a largura real do painel, na faixa do cenário", () => {
    for (const largura of [600, 720, 1600]) {
      expect(xDosParceiros(100, largura)).toBe(MARGEM.esquerda);
      expect(xDosParceiros(10_000, largura)).toBe(MARGEM.esquerda + larguraDaArea(largura));
    }
  });

  it("as marcas dos parceiros nunca se atropelam: com pouca largura, só as potências de dez", () => {
    for (const largura of [360, 480, 600, 720, 1600]) {
      const xs = marcasDosParceiros(largura).map((m) => xDosParceiros(m, largura));
      const vizinhas = xs.slice(1).map((x, i) => x - xs[i]);
      // "10.000" em Fira Code de 10 px tem 36 px.
      expect(Math.min(...vizinhas)).toBeGreaterThan(40);
    }
    expect(marcasDosParceiros(1600)).toContain(2000);
    expect(marcasDosParceiros(360)).toEqual([100, 1000, 10_000]);
  });

  it("o tempo vai da potência de dez abaixo do menor à acima do maior", () => {
    expect(dominioDoTempo([0.0073, 0.195, 26.3])).toEqual([0.001, 100]);
    expect(dominioDoTempo([0.02, 0.05])).toEqual([0.01, 0.1]);
    // Um valor que já é potência de dez não fica colado na borda de cima sozinho.
    expect(dominioDoTempo([1, 1])).toEqual([1, 10]);
    expect(dominioDoTempo([])).toEqual([0.001, 1]);
    expect(marcasDoTempo([0.001, 100])).toHaveLength(6);
  });

  it("os rótulos do tempo cabem na margem", () => {
    expect(marcasDoTempo([0.001, 100]).map(rotuloDoTempo)).toEqual([
      "1 ms",
      "10 ms",
      "100 ms",
      "1 s",
      "10 s",
      "100 s",
    ]);
    const maior = Math.max(...marcasDoTempo([0.001, 1000]).map((m) => rotuloDoTempo(m).length));
    // 0,6 em por caractere em Fira Code, 10 px, mais 8 px de folga até o eixo.
    expect(maior * 0.6 * 10 + 8).toBeLessThanOrEqual(MARGEM.esquerda);
  });

  it("mais tempo fica mais alto", () => {
    const dominio = [0.001, 100];
    expect(yDoTempo(100, dominio)).toBe(MARGEM.topo);
    expect(yDoTempo(0.001, dominio)).toBe(MARGEM.topo + ALTURA_DA_AREA);
    expect(yDoTempo(1, dominio)).toBeLessThan(yDoTempo(0.1, dominio));
  });

  it("rótulos que se encontram saem os dois: o de um cairia ao lado da marca do outro", () => {
    // A GPU e o OpenMP terminam juntos com 10.000 parceiros (245 ms e 256 ms).
    const rotulos = [
      { coluna: "GPU", y: 100 },
      { coluna: "OPENMP", y: 106 },
      { coluna: "CPP_SERIAL", y: 60 },
      { coluna: "PYTHON", y: 20 },
    ];
    expect(rotulosQueCabem(rotulos).map((r) => r.coluna)).toEqual(["CPP_SERIAL", "PYTHON"]);
  });
});
