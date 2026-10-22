/**
 * Como escrever o que a API mandou. Nada aqui calcula regra de negócio: só converte
 * para exibir. Nulo vira travessão — e nulo não é zero.
 */

export const TRACO = "—";

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const moedaInteira = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const decimal = (casas) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

const nulo = (v) => v === null || v === undefined || v === "";
const numero = (v) => (nulo(v) ? NaN : Number(v));

export function comoDinheiro(valor, { semCentavos = false } = {}) {
  const n = numero(valor);
  if (Number.isNaN(n)) return TRACO;
  return (semCentavos ? moedaInteira : moeda).format(n).replace(/ /g, " ");
}

/** Dinheiro partido para a tipografia: a parte inteira grande e os centavos menores. */
export function partesDoDinheiro(valor) {
  const n = numero(valor);
  if (Number.isNaN(n)) return null;
  const [inteiros, centavos] = decimal(2).format(Math.abs(n)).split(",");
  return { sinal: n < 0 ? "−" : "", inteiros, centavos };
}

/** Dinheiro curto para eixo de gráfico: "1,84 mi", "820 mil", "R$ 950". */
export function comoDinheiroCurto(valor) {
  const n = numero(valor);
  if (Number.isNaN(n)) return TRACO;
  const abs = Math.abs(n);
  if (abs >= 1e6) return `${decimal(2).format(n / 1e6)} mi`;
  if (abs >= 1e3) return `${inteiro.format(Math.round(n / 1e3))} mil`;
  return inteiro.format(Math.round(n));
}

export function comoInteiro(valor) {
  const n = numero(valor);
  return Number.isNaN(n) ? TRACO : inteiro.format(n);
}

/** Variação que já chega em porcentagem ("-15.06"): sempre com sinal. */
export function comoVariacao(valor) {
  const n = numero(valor);
  if (Number.isNaN(n)) return TRACO;
  if (n === 0) return "0,00%";
  return `${n > 0 ? "+" : "−"}${decimal(2).format(Math.abs(n))}%`;
}

/** "sobe", "cai", "estavel" ou "indefinida": zero é medição; nulo é ausência dela. */
export function sentidoDa(valor) {
  const n = numero(valor);
  if (Number.isNaN(n)) return "indefinida";
  if (n === 0) return "estavel";
  return n > 0 ? "sobe" : "cai";
}

/** Diferença de contagem: "8 a mais", "2 a menos", "igual". */
export function comoDelta(valor) {
  const n = numero(valor);
  if (Number.isNaN(n)) return TRACO;
  if (n === 0) return "igual";
  return `${inteiro.format(Math.abs(n))} a ${n > 0 ? "mais" : "menos"}`;
}

/** Fração sem sinal: erro, taxa, cota — 0.0922 vira "9,2%". */
export function comoFracao(valor, casas = 1) {
  const n = numero(valor);
  if (Number.isNaN(n)) return TRACO;
  return `${decimal(casas).format(n * 100)}%`;
}

/** Chance estimada sem fingir certeza. */
export function comoProbabilidade(valor) {
  const n = numero(valor);
  if (Number.isNaN(n)) return TRACO;
  if (n < 0.005) return "menos de 1%";
  if (n >= 0.995) return "mais de 99%";
  return `${Math.round(n * 100)}%`;
}

export function comoDecimal(valor, casas = 3) {
  const n = numero(valor);
  return Number.isNaN(n) ? TRACO : decimal(casas).format(n);
}

/** Um tempo medido, com três algarismos onde importam. */
export function comoTempo(segundos) {
  const s = numero(segundos);
  if (Number.isNaN(s)) return TRACO;
  if (s < 1) {
    const ms = s * 1000;
    if (ms < 10) return `${decimal(1).format(ms)} ms`;
    return `${inteiro.format(Math.round(ms))} ms`;
  }
  if (s < 10) return `${decimal(2).format(s)} s`;
  if (s < 60) return `${decimal(1).format(s)} s`;
  const minutos = Math.floor(s / 60);
  const resto = Math.round(s - minutos * 60);
  return resto ? `${minutos} min ${resto} s` : `${minutos} min`;
}

export const comoMilissegundos = (ms) => (nulo(ms) ? TRACO : comoTempo(Number(ms) / 1000));

/** Fator de ganho: 8 → "8,0x", 135.4 → "135x". */
export function comoVezes(fator) {
  const f = numero(fator);
  if (Number.isNaN(f)) return TRACO;
  return f >= 100 ? `${inteiro.format(Math.round(f))}x` : `${decimal(1).format(f)}x`;
}

/** Dia de um período, sem fuso: "2026-09-21" → "21/09/2026". */
export function comoData(iso) {
  if (!iso) return TRACO;
  const [ano, mes, dia] = String(iso).slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

export function comoDiaMes(iso) {
  if (!iso) return TRACO;
  const [, mes, dia] = String(iso).slice(0, 10).split("-");
  return `${dia}/${mes}`;
}

export function comoPeriodo(periodo) {
  if (!periodo) return TRACO;
  return `${comoData(periodo.data_inicio)} a ${comoData(periodo.data_fim)}`;
}

/** Um instante, no relógio de quem olha: "21/09/2026 às 18:33". */
export function comoDataHora(iso) {
  if (!iso) return TRACO;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return TRACO;
  const dia = d.toLocaleDateString("pt-BR");
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${dia} às ${hora}`;
}

/** "1 período" / "3 períodos". */
export const plural = (n, um, varios) => `${inteiro.format(n)} ${Number(n) === 1 ? um : varios}`;

/* ---------- o que a pessoa digita, no formato da API ---------- */

/** "12.000,50" → "12000.50". Não valida: o que não é número segue como veio. */
export function lerReais(texto) {
  return String(texto ?? "").replace(/R\$/g, "").replace(/\s/g, "").replace(/\./g, "").replace(",", ".");
}

/** "30" (%) → "0.3000". Vazio é nulo; texto que não é número vai como veio. */
export function paraFracao(percentual) {
  const texto = String(percentual ?? "").trim();
  if (texto === "") return null;
  const n = Number(texto.replace(",", "."));
  if (Number.isNaN(n)) return texto;
  return (Math.round(n * 100) / 10000).toFixed(4);
}

/** "0.1400" → "14" (para preencher um campo em %). */
export function deFracao(fracao) {
  const n = numero(fracao);
  if (Number.isNaN(n)) return "";
  return String(Math.round(n * 10000) / 100).replace(".", ",");
}

/** "12000.5" → "12.000,50" (para preencher um campo em reais). */
export function paraCampoDeReais(valor) {
  const n = numero(valor);
  return Number.isNaN(n) ? "" : decimal(2).format(n);
}

/* ---------- os rótulos: valor da API → o que se lê ---------- */

export const ROTULO_PERFIL = { ADMINISTRADOR: "Administrador", GESTOR: "Gestor", ANALISTA: "Analista", PARCEIRO: "Parceiro" };
export const ROTULO_SEGMENTO = { PROSPECCAO: "Prospecção", RECEM_CHEGADO: "Recém-chegado", EM_RISCO: "Em risco", TOP: "Top", EM_ASCENSAO: "Em ascensão", ESTAVEL: "Estável" };
export const ORDEM_SEGMENTOS = ["PROSPECCAO", "RECEM_CHEGADO", "EM_RISCO", "TOP", "EM_ASCENSAO", "ESTAVEL"];
export const ROTULO_STATUS = { ATIVO: "Ativo", PROSPECCAO: "Prospecção", INATIVO: "Inativo" };
export const ROTULO_ORIGEM = { TEXTO: "Texto colado", CSV: "Arquivo CSV" };
export const ROTULO_ORIGEM_PREVISAO = { MODELO: "Rede neural", REFERENCIA: "Referência (contas simples)" };
export const ROTULO_MODO = { SERIAL: "Serial (a referência, em Python)", CPU_PARALELO: "CPU paralelo", GPU: "GPU" };
export const ROTULO_MODO_CURTO = { SERIAL: "Serial", CPU_PARALELO: "CPU paralelo", GPU: "GPU" };
export const ROTULO_COLUNA = { PYTHON: "Python", CPP_SERIAL: "C++ serial", OPENMP: "OpenMP", GPU: "GPU" };
export const ORDEM_COLUNAS = ["PYTHON", "CPP_SERIAL", "OPENMP", "GPU"];
export const ROTULO_REDATOR = { MODELO: "Assistente", MODELO_FIXO: "Modelo fixo" };
export const ROTULO_SITUACAO_TREINO = { EM_ANDAMENTO: "Em andamento", CONCLUIDO: "Concluído", FALHOU: "Falhou" };
export const ROTULO_RESTRICAO = { orcamento: "orçamento", maximo_acoes: "máximo de ações", cauda_longa: "cota da cauda longa", cota_categoria: "cota de categoria", elegiveis_categoria: "elegíveis da categoria" };
export const ROTULO_PARAMETRO = { orcamento: "Orçamento", maximo_acoes: "Máximo de ações", cota_cauda_longa: "Cauda longa", cotas_categoria: "Cotas por categoria", aplicacao_inicio: "Início da aplicação", aplicacao_fim: "Fim da aplicação", modo: "Modo" };

/** As cotas por categoria pedidas, em texto: "Pizzaria: mín. 10%, máx. 40%". */
export function cotasDoPedido(execucao, nomesDasCategorias = {}) {
  const nomes = { ...nomesDasCategorias };
  for (const c of execucao?.cotas ?? []) if (c.categoria_id !== null) nomes[c.categoria_id] = c.nome;
  return (execucao?.parametros?.cotas_categoria ?? []).map((c) => {
    const limites = [
      !nulo(c.minimo) && `mín. ${comoFracao(c.minimo, 0)}`,
      !nulo(c.maximo) && `máx. ${comoFracao(c.maximo, 0)}`,
    ].filter(Boolean);
    return `${nomes[c.categoria_id] ?? `Categoria ${c.categoria_id}`}: ${limites.join(", ")}`;
  });
}
