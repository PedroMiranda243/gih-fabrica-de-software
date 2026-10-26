import { describe, expect, it } from "vitest";

import { escalaLinear, escalaLog, marcas, marcasLog } from "./escala";

/* Só geometria de desenho: onde cada valor cai no gráfico, e quais marcas o eixo mostra. */
describe("as escalas dos gráficos", () => {
  it("a linear leva o domínio ao intervalo de desenho, inclusive invertido (o eixo y cresce para baixo)", () => {
    const y = escalaLinear([0, 100], [200, 0]);
    expect(y(0)).toBe(200);
    expect(y(50)).toBe(100);
    expect(y(100)).toBe(0);
  });

  it("domínio de um valor só não divide por zero", () => {
    expect(escalaLinear([5, 5], [0, 10])(5)).toBe(0);
  });

  it("as marcas são redondas e cobrem o intervalo", () => {
    expect(marcas(0, 1000)).toEqual([0, 250, 500, 750, 1000]);
    const m = marcas(13, 87);
    expect(m[0]).toBeLessThanOrEqual(13);
    expect(m.at(-1)).toBeGreaterThanOrEqual(87);
  });

  it("intervalo de um valor só ganha folga em volta", () => {
    const m = marcas(100, 100);
    expect(m[0]).toBeLessThan(100);
    expect(m.at(-1)).toBeGreaterThan(100);
  });

  it("a logarítmica do benchmark põe cada potência de 10 à mesma distância", () => {
    const x = escalaLog([1, 1000], [0, 300]);
    expect(x(1)).toBeCloseTo(0);
    expect(x(10)).toBeCloseTo(100);
    expect(x(100)).toBeCloseTo(200);
    expect(marcasLog(3, 4200)).toEqual([1, 10, 100, 1000, 10000]);
  });
});
