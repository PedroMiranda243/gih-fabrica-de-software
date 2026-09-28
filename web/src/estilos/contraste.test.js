import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * O contraste de cada par de texto e fundo, nos dois temas, medido do
 * `tokens.css` — RNF22, história H76.
 *
 * **Os números saem do arquivo, e não de uma tabela copiada dele.** Se alguém
 * clarear o `--ink-2`, este teste reprova no mesmo PR.
 *
 * **O instrumento é conferido antes de medir** (`CLAUDE.md` §7): uma auditoria
 * anterior lia `oklch()` com um regex de `rgb()`, lia zeros, e acusava falha
 * que não existia. Aqui, cor que não é hexadecimal de seis dígitos reprova alto,
 * e a fórmula precisa dar os valores conhecidos — 21:1 e 4,54:1 — antes de valer.
 *
 * **Os pares são os que a CSS usa.** Um segundo teste lê todas as folhas e
 * reprova a cor de texto que não está na tabela: sem isso, a tabela passaria
 * enquanto um `color: var(--ink-3)` novo, a 2,76:1, entrava na tela.
 */
const RAIZ = dirname(fileURLToPath(import.meta.url));
const TOKENS = readFileSync(join(RAIZ, "tokens.css"), "utf8");

/* WCAG 2.1: texto normal pede 4,5:1; o que não é texto — o contorno de um campo,
   o anel de foco — pede 3:1 contra o que está em volta (1.4.11). */
const TEXTO = 4.5;
const CONTORNO = 3;

/* Cada tinta de texto, e os fundos sobre os quais ela aparece. */
const PARES_DE_TEXTO = {
  "--ink": ["--ground", "--surface", "--surface-2", "--acao-fraca"],
  "--ink-2": ["--ground", "--surface", "--surface-2", "--acao-fraca"],
  /* Link, item selecionado do menu, sugestão sob o ponteiro. */
  "--acao-ink": ["--ground", "--surface", "--surface-2", "--acao-fraca"],
  /* O rótulo do botão principal. */
  "--acao-sobre": ["--acao"],
};

/* O que não é texto e precisa ser visto: a borda de um campo e o anel de foco,
   sobre qualquer superfície em que eles apareçam. */
const PARES_DE_CONTORNO = {
  "--borda-controle": ["--ground", "--surface", "--surface-2"],
  "--acao-ink": ["--ground", "--surface", "--surface-2"],
};

function bloco(seletor) {
  const inicio = TOKENS.indexOf(seletor);
  if (inicio < 0) throw new Error(`bloco ausente: ${seletor}`);
  const abre = TOKENS.indexOf("{", inicio);
  const fecha = TOKENS.indexOf("}", abre);
  const corpo = TOKENS.slice(abre + 1, fecha);
  return Object.fromEntries([...corpo.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
}

const CLARO = bloco(":root {");
const ESCURO = { ...CLARO, ...bloco(':root[data-tema="escuro"]') };
const ESCURO_DO_SISTEMA = bloco(':root:not([data-tema="claro"])');

function canal(valor) {
  const c = valor / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function luminancia(hex) {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) {
    throw new Error(`cor que o teste não sabe medir: ${hex} — só hexadecimal de seis dígitos`);
  }
  const [r, g, b] = [1, 3, 5].map((i) => canal(parseInt(hex.slice(i, i + 2), 16)));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function razao(a, b) {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (escuro + 0.05);
}

function medir(pares, tema) {
  return Object.entries(pares).flatMap(([frente, fundos]) =>
    fundos.map((fundo) => ({
      par: `${frente} sobre ${fundo}`,
      razao: Math.round(razao(tema[frente], tema[fundo]) * 100) / 100,
    })),
  );
}

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
    expect(ESCURO_DO_SISTEMA).toEqual(bloco(':root[data-tema="escuro"]'));
  });

  it.each([
    ["claro", CLARO],
    ["escuro", ESCURO],
  ])("todo texto passa de 4,5:1 no tema %s", (_nome, tema) => {
    const reprovados = medir(PARES_DE_TEXTO, tema).filter((m) => m.razao < TEXTO);
    expect(reprovados).toEqual([]);
  });

  it.each([
    ["claro", CLARO],
    ["escuro", ESCURO],
  ])("a borda do campo e o anel de foco passam de 3:1 no tema %s", (_nome, tema) => {
    const reprovados = medir(PARES_DE_CONTORNO, tema).filter((m) => m.razao < CONTORNO);
    expect(reprovados).toEqual([]);
  });
});

/* ------------------------------------------------------ o que a CSS usa */
function folhas() {
  return readdirSync(RAIZ)
    .filter((nome) => nome.endsWith(".css"))
    .map((nome) => ({ nome, texto: readFileSync(join(RAIZ, nome), "utf8") }));
}

/* As regras de uma folha: o seletor e as declarações. Sem comentários, que
   carregam exemplos de CSS e confundiriam a leitura. */
function regras(texto) {
  const limpo = texto.replace(/\/\*[\s\S]*?\*\//g, "");
  return [...limpo.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({
    seletor: m[1].trim().replace(/\s+/g, " "),
    corpo: m[2],
  }));
}

describe("as cores que a CSS usa", () => {
  it("todo texto usa uma tinta medida acima", () => {
    const fora = [];
    for (const { nome, texto } of folhas()) {
      for (const { seletor, corpo } of regras(texto)) {
        /* A seta do indicador é marca gráfica, redundante com o sinal do número
           (`componentes.css`): a cor de segmento vai nela, e não no texto. */
        if (/\bsvg$/.test(seletor)) continue;
        for (const [, token] of corpo.matchAll(/(?:^|[;\s])color\s*:\s*var\((--[a-z0-9-]+)\)/g)) {
          if (!(token in PARES_DE_TEXTO)) fora.push(`${nome}: ${seletor} → ${token}`);
        }
      }
    }
    expect(fora).toEqual([]);
  });

  it("o anel de foco usa a tinta da ação, medida acima", () => {
    const focos = folhas().flatMap(({ nome, texto }) =>
      regras(texto)
        .filter((r) => r.seletor.includes(":focus-visible") && /outline\s*:/.test(r.corpo))
        .map((r) => `${nome}: ${r.seletor} → ${r.corpo.match(/outline\s*:\s*([^;]+)/)[1].trim()}`),
    );
    expect(focos.length).toBeGreaterThan(0);
    expect(focos.filter((f) => !f.includes("var(--acao-ink)"))).toEqual([]);
  });

  it("todo campo tem a borda de controle, e não a decorativa", () => {
    const decorativas = [];
    for (const { nome, texto } of folhas()) {
      for (const { seletor, corpo } of regras(texto)) {
        const campo = /\b(input|select|textarea)\b|__edicao\b/.test(seletor);
        if (campo && /border(-color)?\s*:[^;]*var\(--border\)/.test(corpo)) {
          decorativas.push(`${nome}: ${seletor}`);
        }
      }
    }
    expect(decorativas).toEqual([]);
  });
});
