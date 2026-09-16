/**
 * Figuras do documento: diagramas e capturas de tela, com legenda.
 *
 * Os diagramas entram como **SVG**, não como imagem rasterizada. O Word desenha
 * o vetor, então a figura continua nítida em qualquer zoom e na impressão — que
 * é critério de aceite da entrega ("os diagramas deverão estar legíveis"). O PNG
 * vai junto só como reserva, exigida pela biblioteca para visualizadores antigos.
 */
const fs = require('fs');
const path = require('path');
const { Paragraph, TextRun, ImageRun, AlignmentType } = require('docx');

const DIAGRAMAS = path.join(__dirname, '..', 'diagramas');
const RAIZ = path.join(__dirname, '..', '..', '..');

// A4 com margens de 2 cm: 170 mm de largura útil e 257 mm de altura. Convertido
// a 96 dpi, que é a unidade que o `docx` usa em `transformation`.
const LARGURA_MAXIMA = 642;
const ALTURA_MAXIMA = 790;   // sobra espaço para a legenda na mesma página

/** Proporção do SVG, lida do `viewBox` — é o que existe de confiável no arquivo. */
function proporcaoDoSvg(caminho) {
  const conteudo = fs.readFileSync(caminho, 'utf8');
  const viewBox = conteudo.match(/viewBox="([\d.\s-]+)"/);
  if (viewBox) {
    const [, , largura, altura] = viewBox[1].trim().split(/\s+/).map(Number);
    if (largura > 0 && altura > 0) return largura / altura;
  }
  throw new Error(`Não consegui ler o viewBox de ${path.basename(caminho)}.`);
}

function medir(proporcao, limiteLargura) {
  let largura = Math.min(limiteLargura ?? LARGURA_MAXIMA, LARGURA_MAXIMA);
  let altura = Math.round(largura / proporcao);

  // Diagrama alto demais estoura a página e o Word o corta em duas partes sem
  // avisar. Encolher pela altura é o que mantém a figura inteira num lugar só.
  if (altura > ALTURA_MAXIMA) {
    altura = ALTURA_MAXIMA;
    largura = Math.round(altura * proporcao);
  }
  return { width: largura, height: altura };
}

/**
 * Diagrama vetorial com reserva rasterizada.
 * @param {string} nome  nome do arquivo, sem extensão
 * @param {number} [limiteLargura]  para diagramas que não precisam da página toda
 */
function diagrama(nome, limiteLargura) {
  const svg = path.join(RAIZ, 'docs', 'diagramas', `${nome}.svg`);
  const png = path.join(DIAGRAMAS, `${nome}.png`);

  for (const arquivo of [svg, png]) {
    if (!fs.existsSync(arquivo)) {
      throw new Error(
        `Falta ${path.basename(arquivo)}. Rode "node docs/entrega/renderizar_diagramas.js" antes de gerar.`,
      );
    }
  }

  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
    children: [new ImageRun({
      type: 'svg',
      data: fs.readFileSync(svg),
      fallback: { type: 'png', data: fs.readFileSync(png) },
      transformation: medir(proporcaoDoSvg(svg), limiteLargura),
    })],
  });
}

/** Captura de tela do protótipo. Aqui não há vetor: a origem é pixel. */
function captura(nome, limiteLargura) {
  const arquivo = path.join(RAIZ, 'docs', 'prototipo', 'telas', `${nome}.png`);
  if (!fs.existsSync(arquivo)) {
    throw new Error(
      `Falta ${nome}.png. Rode "node docs/entrega/capturar_prototipo.js" antes de gerar.`,
    );
  }

  // O `deviceScaleFactor` da captura é 2, então a proporção sai da própria
  // janela usada no script — 1280 x 900.
  const largura = Math.min(limiteLargura ?? LARGURA_MAXIMA, LARGURA_MAXIMA);

  // Lê as dimensões reais do cabeçalho do PNG: a captura é de página inteira e
  // a altura varia com o conteúdo de cada tela.
  const cabecalho = fs.readFileSync(arquivo).subarray(16, 24);
  const larguraReal = cabecalho.readUInt32BE(0);
  const alturaReal = cabecalho.readUInt32BE(4);

  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
    children: [new ImageRun({
      type: 'png',
      data: fs.readFileSync(arquivo),
      transformation: medir(larguraReal / alturaReal, largura),
    })],
  });
}

/** Imagem já rasterizada que veio da Sprint 01. */
function imagem(nomeArquivo, limiteLargura) {
  const arquivo = path.join(DIAGRAMAS, nomeArquivo);
  const dados = fs.readFileSync(arquivo);
  const larguraReal = dados.readUInt32BE(16);
  const alturaReal = dados.readUInt32BE(20);

  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
    children: [new ImageRun({
      type: 'png',
      data: dados,
      transformation: medir(larguraReal / alturaReal, limiteLargura),
    })],
  });
}

/**
 * Legenda numerada.
 *
 * A entrega é explícita: "não entreguem apenas imagens ou diagramas sem
 * identificação". Toda figura deste documento passa por aqui.
 */
let contador = 0;
const legenda = (texto) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 240 },
  children: [
    new TextRun({ text: `Figura ${++contador} — `, bold: true, size: 17, color: '5A6B7E', font: 'Calibri' }),
    new TextRun({ text: texto, size: 17, color: '5A6B7E', font: 'Calibri' }),
  ],
});

const reiniciarContador = () => { contador = 0; };

module.exports = { diagrama, captura, imagem, legenda, reiniciarContador };
