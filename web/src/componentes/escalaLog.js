/**
 * Geometria do gráfico de escalabilidade do benchmark (UC09, passo 7): tempo por
 * número de parceiros, **nas duas escalas logarítmicas**.
 *
 * Por que logarítmica nas duas:
 * - no tempo, os modos vão de milissegundos (GPU) a minutos (Python): numa
 *   escala linear, três das quatro linhas se deitariam no zero;
 * - nos parceiros, a faixa vai de 100 a 10.000, e 500 e 2.000 se amontoariam
 *   no canto esquerdo. E, nas duas em log, crescer em proporção aos parceiros
 *   vira uma reta de inclinação 1: a GPU, que cresce menos, fica visivelmente
 *   mais deitada que o resto — que é a história do gráfico.
 *
 * O eixo dos parceiros é **fixo na faixa do cenário** (RF16): o mesmo tamanho
 * cai sempre no mesmo lugar, de uma execução para outra. O do tempo vai da
 * potência de dez abaixo do menor tempo à potência acima do maior.
 *
 * Mora fora do componente para ser testada sem desenhar nada, como a da série
 * histórica (`escalaSerie.js`).
 */
import { comoInteiro } from "../formato";

export const LARGURA = 720;
export const ALTURA = 280;

/* O maior rótulo do eixo do tempo é "100 ms" (6 caracteres de Fira Code, 10 px):
   36 px, mais a folga até o eixo. À direita, o nome da série no fim da linha:
   "C++ serial", em Fira Sans de 11 px, com folga. */
export const MARGEM = { topo: 14, direita: 88, baixo: 30, esquerda: 52 };
export const AREA = {
  largura: LARGURA - MARGEM.esquerda - MARGEM.direita,
  altura: ALTURA - MARGEM.topo - MARGEM.baixo,
};

export const PARCEIROS = [100, 10_000];
export const MARCAS_PARCEIROS = [100, 200, 500, 1000, 2000, 5000, 10_000];

/* Dois rótulos no fim das linhas mais perto que isto se sobrepõem, na fonte de
   11 px: o de baixo sai, e a legenda e a dica dizem de quem é a linha. */
export const DISTANCIA_MINIMA_ROTULOS = 13;

/** A posição de `valor` num eixo logarítmico de `[a, b]`, de 0 a 1. */
export function fracaoLog(valor, [a, b]) {
  return (Math.log10(valor) - Math.log10(a)) / (Math.log10(b) - Math.log10(a));
}

/** Das potências de dez que cercam os valores: `[0.0073, 26]` vira `[0.001, 100]`. */
export function dominioDoTempo(valores) {
  const positivos = valores.filter((v) => v > 0);
  if (!positivos.length) return [0.001, 1];
  const menor = 10 ** Math.floor(Math.log10(Math.min(...positivos)));
  let maior = 10 ** Math.ceil(Math.log10(Math.max(...positivos)));
  if (maior <= menor) maior = menor * 10;
  return [menor, maior];
}

/** As potências de dez de um domínio, das marcas do eixo do tempo. */
export function marcasDoTempo([menor, maior]) {
  const marcas = [];
  for (let e = Math.round(Math.log10(menor)); e <= Math.round(Math.log10(maior)); e += 1) {
    marcas.push(10 ** e);
  }
  return marcas;
}

/** O rótulo de uma potência de dez de segundos: "1 ms", "100 ms", "1 s", "100 s". */
export function rotuloDoTempo(segundos) {
  if (segundos < 1) return `${comoInteiro(Math.round(segundos * 1000))} ms`;
  return `${comoInteiro(Math.round(segundos))} s`;
}

export function xDosParceiros(parceiros) {
  return MARGEM.esquerda + AREA.largura * fracaoLog(parceiros, PARCEIROS);
}

export function yDoTempo(segundos, dominio) {
  return MARGEM.topo + AREA.altura * (1 - fracaoLog(segundos, dominio));
}

/**
 * Os rótulos do fim das linhas que cabem: de cima para baixo, cada um só entra
 * se ficar a `DISTANCIA_MINIMA_ROTULOS` do anterior. Os que não cabem não são
 * empurrados para longe da linha — rótulo descolado da própria linha lê como
 * ruído (skill de visualização); a legenda e a dica cobrem.
 */
export function rotulosQueCabem(rotulos) {
  const ordenados = [...rotulos].sort((a, b) => a.y - b.y);
  const cabem = [];
  for (const r of ordenados) {
    const anterior = cabem[cabem.length - 1];
    if (!anterior || r.y - anterior.y >= DISTANCIA_MINIMA_ROTULOS) cabem.push(r);
  }
  return cabem;
}
