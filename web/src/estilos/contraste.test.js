import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * O contraste de cada par de texto e fundo, nos dois temas, medido dos tokens —
 * RNF22, história H76.
 *
 * **Os números saem dos arquivos, e não de uma tabela copiada deles.** Se alguém
 * clarear o `--carbono-3`, este teste reprova no mesmo PR.
 *
 * **O instrumento é conferido antes de medir** (`CLAUDE.md` §7): uma auditoria
 * anterior lia `oklch()` com um regex de `rgb()`, lia zeros, e acusava falha que
 * não existia. Aqui, cor que não é hexadecimal de seis dígitos reprova alto, e a
 * fórmula precisa dar os valores conhecidos — 21:1 e 4,54:1 — antes de valer.
 *
 * **Os pares são os que a CSS usa.** O segundo bloco lê todas as folhas e reprova
 * a cor de texto que não está na tabela: sem isso, a tabela passaria enquanto uma
 * tinta nova, sem medida, entrava na tela.
 */
const RAIZ = dirname(fileURLToPath(import.meta.url));
const ler = (nome) => readFileSync(join(RAIZ, nome), "utf8");
/* As cores ficam no tokens.css; a tinta do botão principal, no base.css; a faixa
   refletiva da entrada, no bloco da `.bolsa`, em telas.css. */
const TOKENS = ler("tokens.css") + ler("base.css");
const TELAS = ler("telas.css");

const TEXTO = 4.5;
/* O que não é texto — a borda de um campo, o anel de foco — pede 3:1 contra o
   que está em volta (WCAG 1.4.11). */
const CONTORNO = 3;

const SUPERFICIES = ["--chao", "--etiqueta", "--etiqueta-2"];
const FUNDOS_DE_ESTADO = ["--acao-fundo", "--neutro-fundo", "--erro-fundo", "--atencao-fundo", "--sucesso-fundo"];
const ROTAS = ["--rota-analise", "--rota-previsao", "--rota-otimizacao", "--rota-comunicacao", "--rota-administracao"];
const SEGMENTOS = ["prospeccao", "recem-chegado", "em-risco", "top", "em-ascensao", "estavel"];

/* Cada tinta de texto, e os fundos sobre os quais ela aparece. */
const PARES_DE_TEXTO = {
  "--carbono": [...SUPERFICIES, ...FUNDOS_DE_ESTADO],
  "--carbono-2": [...SUPERFICIES, ...FUNDOS_DE_ESTADO],
  /* O texto ausente (o travessão), o exemplo do campo e o separador: só sobre a
     etiqueta. No chão cinza ele daria 4,32:1 — por isso não vai lá. */
  "--carbono-3": ["--etiqueta", "--etiqueta-2"],
  "--acao": [...SUPERFICIES, "--acao-fundo"],
  "--erro": [...SUPERFICIES, "--erro-fundo"],
  "--atencao": [...SUPERFICIES, "--atencao-fundo"],
  "--sucesso": [...SUPERFICIES, "--sucesso-fundo"],
  "--variacao-boa": SUPERFICIES,
  "--variacao-ruim": SUPERFICIES,
  /* O rótulo dos botões: o principal, o de perigo, o lacre. */
  "--acao-tinta": ["--acao", "--acao-forte"],
  "--erro-tinta": ["--erro"],
  "--lacre-tinta": ["--lacre"],
  /* O avatar, a letra da comparação, a dica do gráfico: branco sobre carbono. */
  "--etiqueta": ["--carbono"],
  /* O trilho, de náilon preto. */
  "--nailon-tinta": ["--nailon", "--nailon-2"],
  "--nailon-tinta-2": ["--nailon", "--nailon-2"],
  "--nailon-tinta-forte": ["--nailon", "--nailon-2"],
  /* A etiqueta da área: texto quase preto sobre a cor viva da rota. */
  "--rota-tinta": ROTAS,
};
/* Os segmentos em etiqueta: a tinta de cada um sobre o fundo dele. */
for (const s of SEGMENTOS) PARES_DE_TEXTO[`--seg-${s}-tinta`] = [`--seg-${s}-fundo`];

/* Tintas que a CSS usa por um apelido: `--rota` é a cor viva da área do grupo (o
   nome do grupo no trilho), e `--seg-tinta` é a tinta do segmento da etiqueta. */
const APELIDOS = {
  "--rota": ROTAS,
  "--seg-tinta": SEGMENTOS.map((s) => `--seg-${s}-tinta`),
};

const PARES_DE_CONTORNO = {
  "--fio-forte": ["--etiqueta", "--etiqueta-2"],
  "--foco": SUPERFICIES,
};

/** As variáveis de todo bloco com aquele seletor, em ordem: o último vence. */
function blocos(texto, seletor) {
  const saida = {};
  let i = texto.indexOf(seletor);
  while (i >= 0) {
    const abre = texto.indexOf("{", i);
    const fecha = texto.indexOf("}", abre);
    for (const m of texto.slice(abre + 1, fecha).matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) saida[m[1]] = m[2].trim();
    i = texto.indexOf(seletor, fecha);
  }
  return saida;
}

/* No bloco claro há também apelidos (`--rota: var(--fio-forte)`) e medidas; a
   medição usa só as cores. */
const soCores = (tokens) => Object.fromEntries(Object.entries(tokens).filter(([, v]) => v.startsWith("#")));
const CLARO = soCores(blocos(TOKENS, ":root {"));
const ESCURO = { ...CLARO, ...blocos(TOKENS, ':root[data-tema="escuro"]') };
const ESCURO_DO_SISTEMA = blocos(TOKENS, ':root:not([data-tema="claro"])');

function canal(valor) {
  const c = valor / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminancia(hex) {
  if (!/^#[0-9a-f]{6}$/i.test(hex ?? "")) {
    throw new Error(`cor que o teste não sabe medir: ${hex} — só hexadecimal de seis dígitos`);
  }
  const [r, g, b] = [1, 3, 5].map((i) => canal(parseInt(hex.slice(i, i + 2), 16)));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function razao(a, b) {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (escuro + 0.05);
}

function medir(pares, tema) {
  return Object.entries(pares).flatMap(([frente, fundos]) =>
    fundos.map((fundo) => ({ par: `${frente} sobre ${fundo}`, razao: Math.round(razao(tema[frente], tema[fundo]) * 100) / 100 })),
  );
}

const TEMAS = [
  ["claro", CLARO],
  ["escuro", ESCURO],
];

describe("contraste (RNF22)", () => {
  it("o instrumento dá os valores conhecidos antes de medir qualquer coisa", () => {
    expect(razao("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(razao("#767676", "#ffffff")).toBeCloseTo(4.54, 2);
    expect(() => luminancia("oklch(0.5 0.1 200)")).toThrow(/não sabe medir/);
  });

  it("o escuro do sistema e o escuro escolhido são a mesma paleta", () => {
    /* Os dois blocos repetem os valores porque o CSS não deixa um herdar do
       outro. Se divergirem, quem segue o sistema vê uma cor e quem escolheu o
       escuro vê outra — e o teste mediria só uma delas. */
    expect(ESCURO_DO_SISTEMA).toEqual(blocos(TOKENS, ':root[data-tema="escuro"]'));
  });

  it.each(TEMAS)("todo texto passa de 4,5:1 no tema %s", (_nome, tema) => {
    expect(medir(PARES_DE_TEXTO, tema).filter((m) => m.razao < TEXTO)).toEqual([]);
  });

  it.each(TEMAS)("o nome de cada área, na cor dela, passa de 4,5:1 sobre o trilho no tema %s", (_nome, tema) => {
    const pares = Object.fromEntries(ROTAS.map((r) => [r, ["--nailon", "--nailon-2"]]));
    expect(medir(pares, tema).filter((m) => m.razao < TEXTO)).toEqual([]);
  });

  it.each(TEMAS)("a borda do campo e o anel de foco passam de 3:1 no tema %s", (_nome, tema) => {
    expect(medir(PARES_DE_CONTORNO, tema).filter((m) => m.razao < CONTORNO)).toEqual([]);
  });

  it("o nome na faixa refletiva da entrada passa de 4,5:1 até no tom mais escuro dela, nos dois temas", () => {
    const faixas = [blocos(TELAS, ".bolsa {"), blocos(TELAS, ':root[data-tema="escuro"] .bolsa')];
    for (const faixa of faixas) {
      for (const tom of ["--faixa-claro", "--faixa-meio", "--faixa-escuro", "--faixa-fundo"]) {
        expect(razao(CLARO["--nailon"], faixa[tom])).toBeGreaterThanOrEqual(TEXTO);
      }
    }
  });
});

/* ------------------------------------------------------ o que a CSS usa */
function folhas() {
  return readdirSync(RAIZ)
    .filter((nome) => nome.endsWith(".css"))
    .map((nome) => ({ nome, texto: ler(nome) }));
}

/* As regras de uma folha: o seletor e as declarações. Sem comentários, que
   carregam exemplos de CSS e confundiriam a leitura. */
function regras(texto) {
  const limpo = texto.replace(/\/\*[\s\S]*?\*\//g, "");
  return [...limpo.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ seletor: m[1].trim().replace(/\s+/g, " "), corpo: m[2] }));
}

describe("as cores que a CSS usa", () => {
  it("todo texto usa uma tinta medida acima", () => {
    const medidas = new Set([...Object.keys(PARES_DE_TEXTO), ...Object.keys(APELIDOS), "--nailon"]);
    const fora = [];
    for (const { nome, texto } of folhas()) {
      for (const { seletor, corpo } of regras(texto)) {
        for (const [, token] of corpo.matchAll(/(?:^|[;\s])color\s*:\s*var\((--[a-z0-9-]+)/g)) {
          if (!medidas.has(token)) fora.push(`${nome}: ${seletor} → ${token}`);
        }
      }
    }
    expect(fora).toEqual([]);
  });

  it("o foco dos controles se vê: anel na cor de foco, ou a borda que vira cobalto", () => {
    /* O campo de texto troca a borda para o cobalto (de 6,5 a 7,4:1) e põe um
       halo translúcido em volta: o halo é reforço, e quem garante os 3:1 é a borda. */
    const focos = folhas().flatMap(({ nome, texto }) =>
      regras(texto)
        .filter((r) => r.seletor.includes(":focus-visible") && /outline\s*:/.test(r.corpo))
        .map((r) => ({ onde: `${nome}: ${r.seletor}`, anel: r.corpo.match(/outline\s*:\s*([^;]+)/)[1].trim(), corpo: r.corpo })),
    );
    expect(focos.length).toBeGreaterThan(0);
    /* O título da tela e o conteúdo recebem o foco por programa (a troca de tela,
       o "pular para o conteúdo"), não do teclado: não são controles, e o anel ali
       seria uma moldura em volta da página inteira. */
    const alvoDePrograma = (f) => /\.(cabecalho__titulo|conteudo):focus/.test(f.onde);
    const invisiveis = focos.filter(
      (f) =>
        !alvoDePrograma(f) &&
        !/var\(--(foco|nailon-tinta-forte|fio-forte)\)/.test(f.anel) &&
        !/border-color\s*:\s*var\(--(acao|foco)\)/.test(f.corpo),
    );
    expect(invisiveis.map((f) => `${f.onde} → ${f.anel}`)).toEqual([]);
  });

  it("todo campo tem a borda de 3:1, e não o fio decorativo", () => {
    const decorativas = [];
    for (const { nome, texto } of folhas()) {
      for (const { seletor, corpo } of regras(texto)) {
        const campo = /\b(input|select|textarea)\b|\.entrada\b/.test(seletor) && !/::placeholder|::file-selector/.test(seletor);
        if (campo && /border(-color)?\s*:[^;]*var\(--fio\)/.test(corpo)) decorativas.push(`${nome}: ${seletor}`);
      }
    }
    expect(decorativas).toEqual([]);
  });
});
