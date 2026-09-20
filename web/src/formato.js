/**
 * Formatação para leitura. **Nada aqui calcula** (regra 2.4).
 *
 * A API devolve os valores monetários como texto — "12500.40" — de propósito:
 * ponto flutuante perde centavo, e o backend guarda `Numeric`. Converter para
 * número aqui é só para exibir; nenhuma conta de negócio acontece na tela.
 *
 * O travessão aparece onde o valor é **nulo**, e nulo não é zero: zero diz "não
 * mudou", nulo diz "não dá para dizer". Desenhar 0% numa variação indefinida
 * afirmaria estabilidade que ninguém mediu.
 */

export const TRACO = "—";

const dinheiro = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 2,
});

const dinheiroCompacto = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  maximumFractionDigits: 1,
});

const inteiro = new Intl.NumberFormat("pt-BR");

export function comoDinheiro(valor, { compacto = false } = {}) {
  if (valor === null || valor === undefined) return TRACO;
  const numero = Number(valor);
  if (Number.isNaN(numero)) return TRACO;
  return compacto ? dinheiroCompacto.format(numero) : dinheiro.format(numero);
}

export function comoInteiro(valor) {
  if (valor === null || valor === undefined) return TRACO;
  const numero = Number(valor);
  return Number.isNaN(numero) ? TRACO : inteiro.format(numero);
}

export function comoPercentual(valor) {
  if (valor === null || valor === undefined) return TRACO;
  const numero = Number(valor);
  if (Number.isNaN(numero)) return TRACO;
  /* O sinal vem sempre, inclusive o de mais: "+12,50%" e "12,50%" são lidos
     com esforços diferentes numa coluna cheia de variações. */
  const sinal = numero > 0 ? "+" : "";
  return `${sinal}${numero.toFixed(2).replace(".", ",")}%`;
}

/**
 * "sobe", "cai", "estavel" ou "indefinida" — o que decide seta, sinal e cor.
 *
 * **Estável e indefinida são coisas diferentes**, e a primeira versão desta
 * função as fundia: zero virava "indefinida" e a tela mostrava travessão com
 * "sem variação calculável" para um período que não mudou nada. Zero é uma
 * medição; nulo é a ausência dela.
 */
export function sentidoDa(valor) {
  if (valor === null || valor === undefined) return "indefinida";
  const numero = Number(valor);
  if (Number.isNaN(numero)) return "indefinida";
  if (numero === 0) return "estavel";
  return numero > 0 ? "sobe" : "cai";
}

/** `2026-03-02` vira `02/03`. A data vem como texto ISO, sem fuso. */
export function comoDiaMes(iso) {
  if (!iso) return TRACO;
  const [, mes, dia] = iso.split("-");
  return `${dia}/${mes}`;
}

/** `2026-03-02` vira `02/03/2026`. */
export function comoData(iso) {
  if (!iso) return TRACO;
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

/** O período inteiro, como as pessoas falam dele. */
export function comoPeriodo(periodo) {
  if (!periodo) return TRACO;
  return `${comoData(periodo.data_inicio)} a ${comoData(periodo.data_fim)}`;
}

/**
 * O rótulo de cada segmento, em texto.
 *
 * O rótulo é **neutro** de propósito: a cor do segmento vai no ponto ou na
 * barra ao lado, nunca no texto (`docs/09`, regra 1.1). "Top 15" repetido doze
 * vezes em cor é ruído puro — e cor como único canal reprovaria a RNF22.
 */
export const ROTULO_SEGMENTO = {
  TOP: "Top 15",
  EM_ASCENSAO: "Em ascensão",
  EM_RISCO: "Em risco",
  RECEM_CHEGADO: "Recém-chegado",
  PROSPECCAO: "Prospecção",
  ESTAVEL: "Estável",
};

/**
 * Uma diferença de contagem, em palavras: "6 a mais", "2 a menos", "igual".
 *
 * Contagem pede diferença absoluta, e não percentual: de 1 para 2 também é
 * +100%, e o gestor que lê "+100% em risco" entende outra coisa do que
 * aconteceu.
 */
export function comoDelta(valor) {
  if (valor === null || valor === undefined) return TRACO;
  const numero = Number(valor);
  if (Number.isNaN(numero)) return TRACO;
  if (numero === 0) return "igual ao anterior";
  return `${Math.abs(numero)} a ${numero > 0 ? "mais" : "menos"}`;
}
