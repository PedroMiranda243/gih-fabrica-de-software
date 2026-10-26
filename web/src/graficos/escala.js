/** Escalas e marcas de eixo — só geometria de desenho, nenhuma regra de negócio. */

export function escalaLinear([d0, d1], [r0, r1]) {
  const span = d1 - d0 || 1;
  return (v) => r0 + ((v - d0) / span) * (r1 - r0);
}

/** Marcas "redondas" entre min e max (1, 2, 2,5, 5 × 10^n). */
export function marcas(min, max, quantas = 4) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0];
  if (min === max) {
    const d = Math.abs(min) * 0.1 || 1;
    min -= d;
    max += d;
  }
  const bruto = (max - min) / quantas;
  const mag = 10 ** Math.floor(Math.log10(bruto));
  const passo = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((p) => p >= bruto) ?? 10 * mag;
  const inicio = Math.floor(min / passo) * passo;
  const fim = Math.ceil(max / passo) * passo;
  const lista = [];
  for (let v = inicio; v <= fim + passo / 2; v += passo) lista.push(Number(v.toFixed(10)));
  return lista;
}

/** Escala logarítmica de base 10. */
export function escalaLog([d0, d1], [r0, r1]) {
  const l0 = Math.log10(d0);
  const l1 = Math.log10(d1);
  return (v) => r0 + ((Math.log10(v) - l0) / (l1 - l0 || 1)) * (r1 - r0);
}

export function marcasLog(min, max) {
  const lista = [];
  for (let e = Math.floor(Math.log10(min)); e <= Math.ceil(Math.log10(max)); e++) lista.push(10 ** e);
  return lista;
}
