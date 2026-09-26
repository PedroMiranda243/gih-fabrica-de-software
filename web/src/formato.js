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

/**
 * Um instante, no relógio de quem está olhando: `21/09/2026 às 18:33`.
 *
 * Diferente de `comoData`, aqui o valor tem hora e fuso — é quando algo
 * aconteceu, e não o dia de um período. Mostrar em UTC faria uma importação da
 * noite aparecer no dia seguinte.
 */
export function comoDataHora(iso) {
  if (!iso) return TRACO;
  const instante = new Date(iso);
  if (Number.isNaN(instante.getTime())) return TRACO;
  const dia = instante.toLocaleDateString("pt-BR");
  const hora = instante.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${dia} às ${hora}`;
}

/** O perfil de acesso como as pessoas o chamam (RF04). */
export const ROTULO_PERFIL = {
  ADMINISTRADOR: "Administrador",
  GESTOR: "Gestor",
  ANALISTA: "Analista",
  PARCEIRO: "Parceiro",
};

/** Por onde o relatório entrou — o nome que a tela de importação usa para cada caminho. */
export const ROTULO_ORIGEM = {
  TEXTO: "Texto colado",
  CSV: "Arquivo CSV",
};

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
 * O rótulo do status comercial.
 *
 * A tabela mostrava o valor interno — "PROSPECCAO", em caixa alta e sem
 * acento — como se fosse texto para o usuário ler. **Precisa bater com
 * `api/app/rotas/parceiros.py`**, que escreve os mesmos rótulos no CSV: o
 * usuário exporta o que está vendo.
 */
export const ROTULO_STATUS = {
  ATIVO: "Ativo",
  PROSPECCAO: "Prospecção",
  INATIVO: "Inativo",
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

/**
 * Uma fração como porcentagem, sem sinal: `0.0922` vira `9,2%`.
 *
 * Para erro e probabilidade, que a API manda em fração e não têm sentido de
 * "subiu" ou "caiu" — `comoPercentual` põe o sinal de mais, e "+9,2% de erro"
 * leria como piora.
 */
export function comoFracao(valor, casas = 1) {
  if (valor === null || valor === undefined) return TRACO;
  const numero = Number(valor);
  if (Number.isNaN(numero)) return TRACO;
  return `${(numero * 100).toFixed(casas).replace(".", ",")}%`;
}

/** Um número com vírgula decimal e casas fixas: o Brier `0.1051` vira `0,105`. */
export function comoDecimal(valor, casas = 3) {
  if (valor === null || valor === undefined) return TRACO;
  const numero = Number(valor);
  return Number.isNaN(numero) ? TRACO : numero.toFixed(casas).replace(".", ",");
}

/** Abaixo de um segundo, em milissegundos: "0,1 s" esconderia a diferença entre os modos de execução. */
export function comoDuracao(ms) {
  if (ms === null || ms === undefined) return TRACO;
  return ms < 1000 ? `${comoInteiro(ms)} ms` : `${comoDecimal(ms / 1000, 1)} s`;
}

/**
 * Os modos de execução do otimizador (RF32), na ordem em que aceleram — a mesma
 * das séries do benchmark (docs/09): o rótulo, o nome no meio da frase e o que o
 * modo é.
 */
export const MODOS_DE_EXECUCAO = [
  ["SERIAL", "Serial", "serial", "A referência, em Python: o mesmo plano, em muito mais tempo. Serve para comparar."],
  ["CPU_PARALELO", "CPU paralelo", "CPU paralelo", "O núcleo em C++, com os núcleos do processador em paralelo."],
  ["GPU", "GPU", "GPU", "O núcleo em CUDA, na placa de vídeo."],
];
export const ROTULO_MODO = Object.fromEntries(MODOS_DE_EXECUCAO.map(([modo, rotulo]) => [modo, rotulo]));
export const NOME_MODO = Object.fromEntries(MODOS_DE_EXECUCAO.map(([modo, , nome]) => [modo, nome]));

/**
 * A restrição que tornou a campanha inviável (RN07), pelo código da API — em
 * poucas palavras, para caber numa linha do histórico. A frase inteira, com o
 * quanto falta, vem da API no `motivo`.
 */
export const ROTULO_RESTRICAO = {
  orcamento: "orçamento",
  maximo_acoes: "máximo de ações",
  cauda_longa: "cota da cauda longa",
  cota_categoria: "cota de categoria",
  elegiveis_categoria: "elegíveis da categoria",
};

/** A situação de um treino do modelo (UC07). */
export const ROTULO_SITUACAO_TREINO = {
  EM_ANDAMENTO: "Em andamento",
  CONCLUIDO: "Concluído",
  FALHOU: "Falhou",
};

/**
 * De onde sai a previsão em uso (RN09, item 4): da rede treinada, ou das
 * contas simples, enquanto nenhuma versão da rede as superou.
 */
export const ROTULO_ORIGEM_PREVISAO = {
  MODELO: "Rede neural",
  REFERENCIA: "Referência (contas simples)",
};

/**
 * Uma probabilidade estimada, sem fingir certeza: `0.24` vira `24%`, e os
 * extremos viram "menos de 1%" e "mais de 99%".
 *
 * Arredondar 0,998 para "100%" diria que o parceiro **vai** entrar em risco, e
 * 0,002 para "0%", que ele não tem como — nenhum dos dois é o que uma
 * estimativa sabe.
 */
export function comoProbabilidade(valor) {
  if (valor === null || valor === undefined) return TRACO;
  const numero = Number(valor);
  if (Number.isNaN(numero)) return TRACO;
  if (numero < 0.005) return "menos de 1%";
  if (numero >= 0.995) return "mais de 99%";
  return `${Math.round(numero * 100)}%`;
}

/**
 * O que a pessoa digita num valor em reais, no formato que a API lê: "12.000,50"
 * vira "12000.50". Ponto é milhar e vírgula é decimal, como se escreve aqui.
 * Não valida: o que não for número segue como veio, e a API recusa com a
 * mensagem dela.
 */
export function lerReais(texto) {
  const limpo = String(texto ?? "")
    .replace(/R\$/g, "")
    .replace(/\s/g, "")
    .replace(/\./g, "")
    .replace(",", ".");
  return limpo;
}

/** "30" (por cento) → "0.3000". Vazio é "sem cota"; texto que não é número vai como
    veio, para a API recusar com a mensagem dela. */
export function paraFracao(percentual) {
  const texto = String(percentual ?? "").trim();
  if (texto === "") return null;
  const numero = Number(texto.replace(",", "."));
  if (Number.isNaN(numero)) return texto;
  return (Math.round(numero * 100) / 10000).toFixed(4);
}
