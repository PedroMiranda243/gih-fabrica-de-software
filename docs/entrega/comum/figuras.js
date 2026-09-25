/**
 * Figuras do documento: diagramas e capturas de tela, com legenda.
 *
 * **Os diagramas entram rasterizados, e a razão é um defeito medido, não gosto.**
 *
 * O SVG parecia a escolha óbvia: o Word aceita vetor, e a figura ficaria nítida
 * em qualquer zoom. E o documento até gerava. Mas ao conferir o PDF exportado,
 * os diagramas apareciam **com as caixas e as setas, e sem nenhum texto dentro**.
 * O Word desenha as formas do SVG do mermaid e descarta os rótulos, que vêm em
 * `foreignObject`. Um diagrama de classes sem os nomes das classes não é um
 * diagrama ruim — é uma figura vazia.
 *
 * Não dava para perceber isso olhando o .docx aberto na tela: só o PDF exportado
 * mostra. Esse é o motivo de a verificação desta entrega incluir abrir o PDF e
 * olhar as páginas, e não apenas conferir que o arquivo foi gerado.
 *
 * A compensação é resolução: os PNG saem do mermaid em escala 4, o que dá cerca
 * de 350 dpi no tamanho em que entram na página — resolução de impressão de
 * verdade. A legibilidade impressa, que é o critério de aceite, fica preservada.
 *
 * O SVG continua sendo gerado e versionado em `docs/diagramas/`, onde o GitHub
 * o renderiza como vetor e os rótulos aparecem normalmente.
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
 * @param {string} [congelado]  pasta, dentro de `diagramas/`, com a figura como
 *   foi entregue — ver `PARTE_II` em `secoes/sprint02.js`
 */
function diagrama(nome, limiteLargura, congelado) {
  // A figura congelada traz o SVG junto: a proporção tem de ser a da figura
  // entregue, e não a do diagrama vivo, que pode ter ganhado caixas desde então.
  const svg = congelado
    ? path.join(DIAGRAMAS, congelado, `${nome}.svg`)
    : path.join(RAIZ, 'docs', 'diagramas', `${nome}.svg`);
  const png = path.join(DIAGRAMAS, congelado ?? '', `${nome}.png`);

  for (const arquivo of [svg, png]) {
    if (!fs.existsSync(arquivo)) {
      throw new Error(
        `Falta ${path.basename(arquivo)}. Rode "node docs/entrega/renderizar_diagramas.js" antes de gerar.`,
      );
    }
  }

  // A proporção vem do SVG, que é a fonte exata; os pixels vêm do PNG.
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
    children: [new ImageRun({
      type: 'png',
      data: fs.readFileSync(png),
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

/** Captura de evidência: Swagger, terminal, qualquer prova de execução. */
function evidencia(nome, limiteLargura) {
  const arquivo = path.join(__dirname, '..', 'evidencias', `${nome}.png`);
  if (!fs.existsSync(arquivo)) {
    throw new Error(
      `Falta ${nome}.png. Rode "node docs/entrega/capturar_evidencias.js" com a API no ar.`,
    );
  }

  const dados = fs.readFileSync(arquivo);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
    children: [new ImageRun({
      type: 'png',
      data: dados,
      transformation: medir(dados.readUInt32BE(16) / dados.readUInt32BE(20), limiteLargura),
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

module.exports = { diagrama, captura, evidencia, imagem, legenda, reiniciarContador };
