/**
 * Estilos e auxiliares do documento de entrega.
 *
 * Extraídos do gerador da Sprint 01 sem alteração de comportamento. Ficam aqui
 * porque cada sprint acrescenta uma seção nova: manter tudo num arquivo só já
 * tinha levado o gerador a 59 KB, e a próxima entrega dobraria isso.
 */
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, PageBreak, Footer, PageNumber, convertMillimetersToTwip,
} = require('docx');

const CW = 9638;                       // largura útil (A4, margens de 2 cm)
const AZUL = '1F3A5F';
const CINZA = 'F2F5F9';
const VERDE = 'E6F4EC';

// ---------- helpers ----------
const p = (text, opts = {}) => new Paragraph({
  alignment: opts.align,
  spacing: { before: opts.before ?? 0, after: opts.after ?? 120 },
  indent: opts.indent,
  children: [new TextRun({
    text, bold: opts.bold, italics: opts.italics, size: opts.size ?? 20,
    color: opts.color, font: 'Calibri',
  })],
});

const rich = (runs, opts = {}) => new Paragraph({
  alignment: opts.align,
  spacing: { before: opts.before ?? 0, after: opts.after ?? 120 },
  children: runs.map(r => new TextRun({
    text: r.t, bold: r.b, italics: r.i, size: r.s ?? 20, color: r.c, font: 'Calibri',
  })),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 360, after: 180 },
  children: [new TextRun({ text, bold: true, size: 30, color: AZUL, font: 'Calibri' })],
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 260, after: 120 },
  children: [new TextRun({ text, bold: true, size: 24, color: AZUL, font: 'Calibri' })],
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  spacing: { before: 200, after: 100 },
  children: [new TextRun({ text, bold: true, size: 21, color: '2C5B8F', font: 'Calibri' })],
});

const bullet = (text, level = 0) => new Paragraph({
  bullet: { level },
  spacing: { after: 60 },
  children: [new TextRun({ text, size: 20, font: 'Calibri' })],
});

function cell(text, w, opts = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: opts.fill ? { type: ShadingType.CLEAR, fill: opts.fill, color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: String(text).split('||').map((t, i) => new Paragraph({
      alignment: opts.align,
      spacing: { after: 0, before: i ? 40 : 0 },
      children: [new TextRun({
        text: t, bold: opts.bold, size: opts.size ?? 18,
        color: opts.color, font: 'Calibri',
      })],
    })),
  });
}

/** rows[0] é o cabeçalho. widths deve somar CW. */
function table(widths, rows, opts = {}) {
  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: widths,
    borders: {
      top:    { style: BorderStyle.SINGLE, size: 2, color: 'C8D2DE' },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: 'C8D2DE' },
      left:   { style: BorderStyle.SINGLE, size: 2, color: 'C8D2DE' },
      right:  { style: BorderStyle.SINGLE, size: 2, color: 'C8D2DE' },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: 'DDE4EC' },
      insideVertical:   { style: BorderStyle.SINGLE, size: 2, color: 'DDE4EC' },
    },
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((c, ci) => cell(c, widths[ci], {
        fill: ri === 0 ? AZUL : (opts.zebra && ri % 2 === 0 ? CINZA : opts.fills?.[ri]),
        bold: ri === 0 || (opts.boldCol === ci),
        color: ri === 0 ? 'FFFFFF' : undefined,
        align: opts.align?.[ci],
        size: opts.size,
      })),
    })),
  });
}

const espaco = (h = 120) => new Paragraph({ spacing: { after: h }, children: [] });
const quebra = () => new Paragraph({ children: [new PageBreak()] });

/**
 * Bloco monoespacado: notacao relacional e saida de terminal.
 *
 * Devolve um paragrafo por linha, sem espaco entre eles, para o alinhamento em
 * coluna sobreviver — que e o unico motivo de usar monoespacada aqui.
 */
const mono = (linhas) => linhas.map((linha) => new Paragraph({
  spacing: { after: 0 },
  children: [new TextRun({ text: linha, font: 'Consolas', size: 16 })],
}));

module.exports = {
  CW, AZUL, CINZA, VERDE,
  p, rich, h1, h2, h3, bullet, cell, table, espaco, quebra, mono,
};
