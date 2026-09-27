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
 * **Desenhado na largura real do painel**, em pixels, e não num tamanho fixo
 * esticado: esticado, o texto crescia junto, e num monitor largo os rótulos do
 * gráfico saíam com o dobro do tamanho do resto da tela. A largura muda; a
 * altura, as margens e as fontes, não.
 *
 * O eixo dos parceiros é **fixo na faixa do cenário** (RF16): o mesmo tamanho
 * cai sempre no mesmo lugar, de uma execução para outra. O do tempo vai da
 * potência de dez abaixo do menor tempo à potência acima do maior.
 *
 * Mora fora do componente para ser testada sem desenhar nada, como a da série
 * histórica (`escalaSerie.js`).
 */
import { comoInteiro } from "../formato";

/* A largura antes de medir — e a do jsdom, que não mede nada. */
export const LARGURA_PADRAO = 720;
export const ALTURA = 300;

/* O maior rótulo do eixo do tempo é "1.000 s" (7 caracteres de Fira Code, 10 px):
   42 px, mais a folga até o eixo. À direita, o nome da série no fim da linha:
   "C++ serial", em Fira Sans de 11 px, com folga. */
export const MARGEM = { topo: 14, direita: 88, baixo: 30, esquerda: 52 };

export function larguraDaArea(largura) {
  return largura - MARGEM.esquerda - MARGEM.direita;
}

export const ALTURA_DA_AREA = ALTURA - MARGEM.topo - MARGEM.baixo;

export const PARCEIROS = [100, 10_000];
const TODAS_AS_MARCAS = [100, 200, 500, 1000, 2000, 5000, 10_000];

/* "10.000" em Fira Code de 10 px tem 36 px: marcas mais perto que isto se
   atropelam, e o eixo fica só com as potências de dez. */
const DISTANCIA_MINIMA_MARCAS = 44;

/* Dois rótulos no fim das linhas mais perto que isto se sobrepõem, na fonte de
   11 px. */
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

export function xDosParceiros(parceiros, largura = LARGURA_PADRAO) {
  return MARGEM.esquerda + larguraDaArea(largura) * fracaoLog(parceiros, PARCEIROS);
}

export function yDoTempo(segundos, dominio) {
  return MARGEM.topo + ALTURA_DA_AREA * (1 - fracaoLog(segundos, dominio));
}

/** As marcas do eixo dos parceiros que cabem nesta largura sem se atropelar. */
export function marcasDosParceiros(largura = LARGURA_PADRAO) {
  const menorDistancia = larguraDaArea(largura) * fracaoLog(200, [100, 10_000]);
  return menorDistancia >= DISTANCIA_MINIMA_MARCAS ? TODAS_AS_MARCAS : [100, 1000, 10_000];
}

/**
 * Os rótulos do fim das linhas que ficam: só os que não chegam perto de nenhum
 * outro. Quando dois se encontram, **saem os dois** — o rótulo de um cairia ao
 * lado da marca do outro e diria o nome errado; empurrá-los descolaria o nome
 * da linha (skill de visualização). A legenda e a dica cobrem.
 */
export function rotulosQueCabem(rotulos) {
  return rotulos.filter((r) =>
    rotulos.every((outro) => outro === r || Math.abs(outro.y - r.y) >= DISTANCIA_MINIMA_ROTULOS),
  );
}
