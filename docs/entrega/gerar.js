/**
 * Gera o documento de entrega do GIH.
 *
 * A disciplina pede um PDF acumulado: cada entrega traz todas as sprints
 * anteriores mais a atual. Por isso o documento é montado a partir de módulos —
 * um por sprint — e não reescrito a cada vez.
 *
 * Uso:
 *   node docs/entrega/renderizar_diagramas.js     # os diagramas, a partir do markdown
 *   node docs/entrega/capturar_prototipo.js       # as telas do protótipo
 *   node docs/entrega/gerar.js                    # este arquivo
 *
 * Depois, converter para PDF pelo Word (Arquivo > Exportar > Criar PDF).
 */
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, AlignmentType,
  Footer, PageNumber, convertMillimetersToTwip,
} = require('docx');

const { p, rich, h1, espaco, quebra, AZUL } = require('./comum/estilos');
const sprint01 = require('./secoes/sprint01');
const sprint02 = require('./secoes/sprint02');

const GRUPO = '18';
const PROJETO = 'GROWTH INTELLIGENCE HUB (GIH)';
const SAIDA = path.join(__dirname, '..', 'entregas', `GRUPO-${GRUPO}-GIH-SPRINT-02.docx`);

// Ordem alfabética por nome, como consta na documentação da equipe.
const EQUIPE = [
  ['Ingryd Vitoria de Araújo Barbosa', '01642893'],
  ['João Pedro Nunes de França', '01626444'],
  ['Marcio Maycom', '01607574'],
  ['Pedro Miranda', '01607408'],
  ['Thiago José Falcão de Freitas', '01597267'],
];

function capa() {
  const c = [];
  c.push(espaco(1000));
  c.push(p('CENTRO UNIVERSITÁRIO MAURÍCIO DE NASSAU', { align: AlignmentType.CENTER, bold: true, size: 22, color: AZUL }));
  c.push(p('Bacharelado em Ciência da Computação', { align: AlignmentType.CENTER, size: 20 }));
  c.push(espaco(500));

  c.push(p(`GRUPO ${GRUPO}`, { align: AlignmentType.CENTER, bold: true, size: 26, color: '2C5B8F', after: 240 }));

  c.push(p(PROJETO, { align: AlignmentType.CENTER, bold: true, size: 44, color: AZUL, after: 100 }));
  c.push(p('Plataforma de inteligência de crescimento para redes de parceiros', { align: AlignmentType.CENTER, size: 24, after: 40 }));
  c.push(p('em marketplaces regionais de delivery', { align: AlignmentType.CENTER, size: 24 }));
  c.push(espaco(420));

  c.push(p('SPRINT 02 — ARQUITETURA E MODELAGEM DO SISTEMA', { align: AlignmentType.CENTER, bold: true, size: 24, color: '2C5B8F', after: 60 }));
  c.push(p('Documento acumulado: inclui a Sprint 01 — Planejamento e Descoberta', { align: AlignmentType.CENTER, size: 19, color: '5A6B7E' }));
  c.push(espaco(480));

  c.push(p('EQUIPE', { align: AlignmentType.CENTER, bold: true, size: 20, color: '5A6B7E', after: 100 }));
  EQUIPE.forEach(([nome, matricula]) => c.push(
    p(`${nome}  —  ${matricula}`, { align: AlignmentType.CENTER, size: 20, after: 50 }),
  ));
  c.push(espaco(420));

  c.push(p('Projeto Integrador', { align: AlignmentType.CENTER, bold: true, size: 21, after: 60 }));
  c.push(p('Fábrica de Software  ·  Prof.ª Pryscilla Gonçalves', { align: AlignmentType.CENTER, size: 20, after: 40 }));
  c.push(p('Tópicos Avançados  ·  Prof. Antenor Parnaíba', { align: AlignmentType.CENTER, size: 20 }));
  c.push(espaco(420));

  c.push(p('2026.2', { align: AlignmentType.CENTER, bold: true, size: 22 }));
  c.push(p('Entrega final da disciplina: 05 de dezembro de 2026', { align: AlignmentType.CENTER, size: 18, color: '5A6B7E' }));
  c.push(quebra());
  return c;
}

function sumario() {
  const c = [];
  c.push(h1('Sumário'));

  c.push(p('PARTE I — SPRINT 01 · PLANEJAMENTO E DESCOBERTA', { bold: true, size: 21, color: '2C5B8F', before: 120, after: 100 }));
  [
    '1. Identificação da equipe', '2. Tema', '3. Definição do problema', '4. Objetivos do sistema',
    '5. Público-alvo', '6. Requisitos Funcionais', '7. Requisitos Não Funcionais',
    '8. Casos de Uso', '9. Product Backlog', '10. Cronograma inicial', '11. Repositório GitHub',
  ].forEach((t) => c.push(p(t, { size: 20, after: 70, indent: { left: 280 } })));

  c.push(p('PARTE II — SPRINT 02 · ARQUITETURA E MODELAGEM', { bold: true, size: 21, color: '2C5B8F', before: 260, after: 100 }));
  [
    '1. Arquitetura do sistema', '2. Diagrama de classes', '3. Modelo Entidade-Relacionamento',
    '4. Modelo relacional', '5. Protótipo das telas principais', '6. Banco de dados criado',
    '7. Projeto estruturado no GitHub',
  ].forEach((t) => c.push(p(t, { size: 20, after: 70, indent: { left: 280 } })));

  c.push(espaco(300));
  c.push(rich([
    { t: 'Documentação completa e versionada em: ', s: 19, c: '5A6B7E' },
    { t: 'github.com/PedroMiranda243/gih-fabrica-de-software', s: 19, b: true, c: '2C5B8F' },
  ]));
  c.push(quebra());
  return c;
}

function main() {
  const children = [
    ...capa(),
    ...sumario(),
    ...sprint01.montar(),
    ...sprint02.montar(),
  ];

  const doc = new Document({
    creator: `Grupo ${GRUPO} — Equipe GIH`,
    title: `Sprint 02 — ${PROJETO}`,
    description: 'Entregáveis das Sprints 01 e 02 — Fábrica de Software e Tópicos Avançados, 2026.2',
    styles: { default: { document: { run: { font: 'Calibri', size: 20 } } } },
    sections: [{
      properties: {
        page: {
          margin: {
            top: convertMillimetersToTwip(20), bottom: convertMillimetersToTwip(20),
            left: convertMillimetersToTwip(20), right: convertMillimetersToTwip(20),
          },
        },
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({
              children: [`Growth Intelligence Hub · Grupo ${GRUPO} · Sprint 02 · `, PageNumber.CURRENT],
              size: 16, color: '8A97A8', font: 'Calibri',
            })],
          })],
        }),
      },
      children,
    }],
  });

  fs.mkdirSync(path.dirname(SAIDA), { recursive: true });
  Packer.toBuffer(doc).then((buf) => {
    fs.writeFileSync(SAIDA, buf);
    console.log(`gerado: ${path.relative(path.join(__dirname, '..', '..'), SAIDA)}`);
    console.log(`        ${(buf.length / 1024).toFixed(0)} KB · ${children.length} blocos`);
  });
}

main();
