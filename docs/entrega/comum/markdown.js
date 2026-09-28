/**
 * Markdown da documentação para blocos do Word, com o estilo das entregas.
 *
 * A documentação técnica final (H73) é **a documentação viva, e não uma cópia
 * dela**: o que está em `docs/07`, `docs/08`, `docs/10` e `docs/medicoes/` entra
 * no documento como está no repositório. Uma cópia escrita à parte divergiria na
 * primeira correção — o mesmo defeito que as figuras da Parte II já tiveram.
 *
 * O que o Markdown da equipe usa, e como vira Word:
 *
 * - títulos: o `#` do arquivo vira o título da parte, e os demais descem um nível
 *   por vez — `deslocamento` empurra os de um arquivo que entra dentro de outra
 *   parte, como as medições;
 * - parágrafos, listas (aninhadas ou numeradas), tabelas e citações, com negrito,
 *   itálico e código em linha;
 * - **diagramas**: o bloco ```mermaid com o marcador `<!-- diagrama: nome -->`
 *   logo acima entra como a figura já rasterizada por `renderizar_diagramas.js`,
 *   com a legenda de `LEGENDAS` — nunca como código;
 * - o resto do código, em monoespaçada;
 * - `<details>` — as tabelas de cada execução nas medições — fica de fora: é
 *   detalhe para quem quer conferir, e o repositório o guarda.
 */
const { marked } = require('marked');
const {
  Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle,
} = require('docx');

const { CW, AZUL, CINZA } = require('./estilos');
const { diagrama, legenda } = require('./figuras');

const COR_CITACAO = '3A4A5E';

/** O texto puro de uma sequência de tokens em linha — para títulos e cálculos de largura. */
function plano(tokens = []) {
  return tokens
    .map((t) => (t.tokens ? plano(t.tokens) : t.type === 'br' ? ' ' : (t.text ?? '')))
    .join('')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

function entidades(texto) {
  return texto
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

/** Os trechos de um parágrafo, com a formatação de cada um. */
function trechos(tokens = [], base = {}) {
  const saida = [];
  for (const t of tokens) {
    if (t.type === 'strong') saida.push(...trechos(t.tokens, { ...base, bold: true }));
    else if (t.type === 'em') saida.push(...trechos(t.tokens, { ...base, italics: true }));
    else if (t.type === 'del') saida.push(...trechos(t.tokens, { ...base, strike: true }));
    else if (t.type === 'link') saida.push(...trechos(t.tokens, base));
    else if (t.type === 'codespan') {
      saida.push(new TextRun({
        text: entidades(t.text), font: 'Consolas', size: (base.size ?? 20) - 2,
        bold: base.bold, color: base.color ?? '2C3E55',
      }));
    } else if (t.type === 'br') saida.push(new TextRun({ break: 1 }));
    else if (t.type === 'html') continue;
    else if (t.tokens) saida.push(...trechos(t.tokens, base));
    else if (t.text) {
      saida.push(new TextRun({
        text: entidades(t.text), font: 'Calibri', size: base.size ?? 20, bold: base.bold,
        italics: base.italics, strike: base.strike, color: base.color,
      }));
    }
  }
  return saida;
}

function titulo(texto, nivel) {
  const estilos = {
    1: { heading: HeadingLevel.HEADING_1, size: 30, color: AZUL, before: 360, after: 180 },
    2: { heading: HeadingLevel.HEADING_2, size: 24, color: AZUL, before: 260, after: 120 },
    3: { heading: HeadingLevel.HEADING_3, size: 21, color: '2C5B8F', before: 200, after: 100 },
  };
  const e = estilos[nivel] ?? { size: 20, color: '2C5B8F', before: 160, after: 80 };
  return new Paragraph({
    heading: e.heading,
    spacing: { before: e.before, after: e.after },
    keepNext: true,
    children: [new TextRun({ text: texto, bold: true, size: e.size, color: e.color, font: 'Calibri' })],
  });
}

/* Largura das colunas pela quantidade de texto de cada uma — com um piso, para
   a coluna curta não virar uma letra por linha, e um teto, para a longa não
   espremer as outras. */
function larguras(linhas) {
  const n = linhas[0].length;
  const pesos = Array.from({ length: n }, (_, i) => {
    const maior = Math.max(...linhas.map((l) => (l[i] ?? '').length));
    return Math.min(Math.max(maior, 6), 60);
  });
  const soma = pesos.reduce((a, b) => a + b, 0);
  const brutas = pesos.map((p) => Math.floor((CW * p) / soma));
  brutas[brutas.length - 1] += CW - brutas.reduce((a, b) => a + b, 0);
  return brutas;
}

function tabela(token) {
  const cabecalho = token.header.map((c) => c.tokens);
  const linhas = token.rows.map((r) => r.map((c) => c.tokens));
  const texto = [cabecalho, ...linhas].map((l) => l.map((c) => plano(c)));
  const w = larguras(texto);
  const alinhamento = token.align.map((a) =>
    a === 'right' ? AlignmentType.RIGHT : a === 'center' ? AlignmentType.CENTER : undefined);
  const celula = (tokens, i, ri) => new TableCell({
    width: { size: w[i], type: WidthType.DXA },
    shading: ri === 0
      ? { type: ShadingType.CLEAR, fill: AZUL, color: 'auto' }
      : ri % 2 === 0 ? { type: ShadingType.CLEAR, fill: CINZA, color: 'auto' } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({
      alignment: alinhamento[i],
      spacing: { after: 0 },
      children: trechos(tokens, ri === 0 ? { bold: true, color: 'FFFFFF', size: 17 } : { size: 17 }),
    })],
  });
  const borda = { style: BorderStyle.SINGLE, size: 2, color: 'C8D2DE' };
  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: w,
    borders: {
      top: borda, bottom: borda, left: borda, right: borda,
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: 'DDE4EC' },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: 'DDE4EC' },
    },
    rows: [cabecalho, ...linhas].map((l, ri) => new TableRow({
      tableHeader: ri === 0,
      cantSplit: true,
      children: l.map((c, i) => celula(c, i, ri)),
    })),
  });
}

function lista(token, nivel, contexto) {
  const saida = [];
  token.items.forEach((item, i) => {
    const marcador = token.ordered ? `${(Number(token.start) || 1) + i}. ` : null;
    const aninhadas = [];
    const texto = [];
    for (const t of item.tokens) {
      if (t.type === 'list') aninhadas.push(t);
      else if (t.type === 'text' || t.type === 'paragraph') texto.push(...(t.tokens ?? [t]));
      else if (t.type !== 'space') aninhadas.push(t);
    }
    const base = contexto.citacao ? { color: COR_CITACAO, size: 19 } : {};
    const runs = trechos(texto, base);
    saida.push(new Paragraph({
      ...(marcador ? { indent: { left: 360 * (nivel + 1), hanging: 280 } } : { bullet: { level: nivel } }),
      spacing: { after: 60 },
      children: marcador ? [new TextRun({ text: marcador, font: 'Calibri', size: 20, ...base }), ...runs] : runs,
    }));
    for (const sub of aninhadas) {
      if (sub.type === 'list') saida.push(...lista(sub, nivel + 1, contexto));
      else saida.push(...converter([sub], contexto));
    }
  });
  return saida;
}

/**
 * Os blocos do Word para uma lista de tokens.
 * @param contexto.deslocamento quantos níveis os títulos descem
 * @param contexto.legendas o texto da legenda de cada diagrama, pelo nome
 */
function converter(tokens, contexto) {
  const saida = [];
  for (const t of tokens) {
    if (contexto.pulando) {
      if (t.type === 'html' && /<\/details>/i.test(t.raw)) contexto.pulando = false;
      continue;
    }
    switch (t.type) {
      case 'heading': {
        const nivel = t.depth + contexto.deslocamento;
        const texto = plano(t.tokens);
        if (contexto.parar && contexto.parar(texto)) {
          contexto.parado = true;
          return saida;
        }
        contexto.titulos.push({ nivel, texto });
        saida.push(titulo(texto, nivel));
        break;
      }
      case 'paragraph': {
        const base = contexto.citacao ? { color: COR_CITACAO, size: 19 } : {};
        saida.push(new Paragraph({
          spacing: { after: 120 },
          indent: contexto.citacao ? { left: 360 } : undefined,
          children: trechos(t.tokens, base),
        }));
        break;
      }
      case 'list':
        saida.push(...lista(t, 0, contexto));
        break;
      case 'table':
        saida.push(tabela(t), new Paragraph({ spacing: { after: 120 }, children: [] }));
        break;
      case 'blockquote':
        saida.push(...converter(t.tokens, { ...contexto, citacao: true }));
        break;
      case 'code':
        if (t.lang === 'mermaid' && contexto.diagrama) {
          const nome = contexto.diagrama;
          contexto.diagrama = null;
          saida.push(diagrama(nome));
          saida.push(legenda(contexto.legendas[nome] ?? nome.replace(/-/g, ' ')));
        } else {
          for (const linha of t.text.split('\n')) {
            saida.push(new Paragraph({
              spacing: { after: 0 },
              shading: { type: ShadingType.CLEAR, fill: 'F4F6F9', color: 'auto' },
              children: [new TextRun({ text: linha || ' ', font: 'Consolas', size: 16 })],
            }));
          }
          saida.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
        }
        break;
      case 'html': {
        const marcador = t.raw.match(/<!--\s*diagrama:\s*([a-z0-9-]+)\s*-->/i);
        if (marcador) contexto.diagrama = marcador[1];
        else if (/<details>/i.test(t.raw) && !/<\/details>/i.test(t.raw)) contexto.pulando = true;
        break;
      }
      case 'hr':
        saida.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
        break;
      default:
        break;
    }
    if (contexto.parado) break;
  }
  return saida;
}

/**
 * Um arquivo de Markdown inteiro, como uma parte do documento.
 * @param {string} texto o Markdown
 * @param {object} opcoes
 * @param {number} [opcoes.deslocamento=0] quantos níveis os títulos descem
 * @param {string} [opcoes.titulo] o título que substitui o `#` do arquivo
 * @param {(t: string) => boolean} [opcoes.parar] para antes do título em que isto for verdade
 * @param {object} opcoes.legendas a legenda de cada diagrama
 * @param {Array} opcoes.titulos onde guardar os títulos, para o sumário
 */
function parte(texto, opcoes) {
  const tokens = marked.lexer(texto.replace(/\r\n/g, '\n'));
  if (opcoes.titulo) {
    const primeiro = tokens.find((t) => t.type === 'heading' && t.depth === 1);
    if (primeiro) primeiro.tokens = [{ type: 'text', text: opcoes.titulo }];
  }
  return converter(tokens, {
    deslocamento: opcoes.deslocamento ?? 0,
    legendas: opcoes.legendas,
    titulos: opcoes.titulos,
    parar: opcoes.parar,
    diagrama: null,
    pulando: false,
    citacao: false,
  });
}

module.exports = { parte };
