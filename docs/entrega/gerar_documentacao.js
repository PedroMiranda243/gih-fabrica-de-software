/**
 * Gera a documentação técnica final consolidada — história H73.
 *
 * **A documentação viva, num documento só.** A arquitetura e as decisões
 * (`docs/07`), o modelo de dados (`docs/08`), as classes e os serviços
 * (`docs/10`) e os resultados medidos (`docs/medicoes/`) entram como estão no
 * repositório, convertidos pelo `comum/markdown.js`. Nada é reescrito à mão: o
 * documento sai igual ao que a equipe mantém, e se regera a cada mudança.
 *
 * É diferente das entregas da disciplina (`gerar.js`), que são o retrato de cada
 * sprint e não se regeram depois de entregues. Esta é a referência técnica do
 * sistema como ele está.
 *
 * Uso:
 *   node docs/entrega/renderizar_diagramas.js   # os diagramas, a partir do markdown
 *   node docs/entrega/gerar_documentacao.js     # este arquivo
 *
 * Depois, o PDF pelo Word (Arquivo > Exportar > Criar PDF).
 */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, Footer, PageNumber,
  convertMillimetersToTwip,
} = require('docx');

const { p, rich, h1, espaco, quebra, AZUL } = require('./comum/estilos');
const { parte } = require('./comum/markdown');

const RAIZ = path.join(__dirname, '..', '..');
const GRUPO = '18';
const PROJETO = 'GROWTH INTELLIGENCE HUB (GIH)';
const SAIDA = path.join(RAIZ, 'docs', 'entregas', `GRUPO-${GRUPO}-GIH-DOCUMENTACAO-TECNICA.docx`);

const EQUIPE = [
  ['Ingryd Vitoria de Araújo Barbosa', '01642893'],
  ['João Pedro Nunes de França', '01626444'],
  ['Marcio Maycom', '01607574'],
  ['Pedro Miranda', '01607408'],
  ['Thiago José Falcão de Freitas', '01597267'],
];

// A legenda de cada diagrama, pelo nome do marcador no markdown. Toda figura sai
// identificada — a orientação da disciplina não aceita diagrama sem legenda.
const LEGENDAS = {
  'arquitetura-geral': 'Arquitetura geral: as camadas e o que cada uma faz',
  'mer-conceitual': 'Modelo entidade-relacionamento: o domínio do sistema',
  'mer-previsao': 'Modelo entidade-relacionamento: o treino e as previsões',
  'classes-integracao': 'Classes: a integração entre as camadas',
  'classes-dominio-acesso': 'Classes do domínio: acesso, usuários e auditoria',
  'classes-dominio-desempenho': 'Classes do domínio: parceiros, períodos e desempenho',
  'classes-dominio-nucleo': 'Classes do domínio: campanha, otimização e comunicação',
  'servicos-acesso': 'Serviços: autenticação, sessão e autorização',
  'servicos-negocio': 'Serviços: as regras de negócio, o redator e o assistente',
  'nucleo-estruturas': 'Núcleo computacional: as estruturas da instância',
  'nucleo-otimizadores': 'Núcleo computacional: os otimizadores serial, OpenMP e CUDA',
};

/* As partes, na ordem da leitura: como o sistema é, como os dados são, como o
   código se organiza, e o que foi medido. */
const PARTES = [
  { arquivo: 'docs/07-arquitetura-preliminar.md', titulo: 'Parte I — Arquitetura e decisões' },
  { arquivo: 'docs/08-modelo-de-dados.md', titulo: 'Parte II — Modelo de dados' },
  { arquivo: 'docs/10-diagrama-de-classes.md', titulo: 'Parte III — Classes e serviços' },
];
const MEDICOES = [
  'docs/medicoes/nucleo.md',
  'docs/medicoes/otimizador.md',
  'docs/medicoes/modelo.md',
  'docs/medicoes/assistente.md',
  // As capturas das vinte telas ficam no repositório: no documento, o resultado.
  { arquivo: 'docs/medicoes/acessibilidade.md', parar: (t) => t === 'As capturas' },
];

function versao() {
  try {
    const commit = execFileSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: RAIZ }).toString().trim();
    const data = execFileSync('git', ['log', '-1', '--format=%cd', '--date=format:%d/%m/%Y'], { cwd: RAIZ })
      .toString().trim();
    return { commit, data };
  } catch {
    return { commit: '?', data: new Date().toLocaleDateString('pt-BR') };
  }
}

function capa({ commit, data }) {
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
  c.push(p('DOCUMENTAÇÃO TÉCNICA FINAL', { align: AlignmentType.CENTER, bold: true, size: 26, color: '2C5B8F', after: 60 }));
  c.push(p(`Arquitetura, modelo de dados, decisões e resultados medidos · versão ${commit}, de ${data}`, {
    align: AlignmentType.CENTER, size: 19, color: '5A6B7E',
  }));
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
  c.push(quebra());
  return c;
}

function sobre({ commit }) {
  const c = [h1('Sobre este documento')];
  c.push(p(
    'Este documento reúne a documentação técnica do Growth Intelligence Hub num lugar só: como o sistema '
    + 'está organizado e por quê, como os dados são modelados, como o código se divide em classes e '
    + 'serviços, e o que foi medido — o otimizador em CPU e em GPU, o modelo preditivo, o assistente e a '
    + 'acessibilidade das telas.',
  ));
  c.push(p(
    'Ele não foi escrito à parte. Cada parte é o arquivo correspondente do repositório, convertido como '
    + 'está: a arquitetura e as decisões registradas (ADRs) em docs/07, o modelo de dados em docs/08, as '
    + 'classes e os serviços em docs/10, e as medições em docs/medicoes/. As medições, por sua vez, são '
    + 'geradas por script a cada execução, com o comando e a semente que as reproduzem.',
  ));
  c.push(rich([
    { t: 'Versão: ', b: true, s: 19 },
    { t: `commit ${commit} do repositório github.com/PedroMiranda243/gih-fabrica-de-software. `, s: 19 },
    { t: 'Para regerar: ', b: true, s: 19 },
    { t: 'node docs/entrega/renderizar_diagramas.js e node docs/entrega/gerar_documentacao.js.', s: 19 },
  ]));
  c.push(p(
    'Os requisitos, os casos de uso, o backlog, o cronograma e o processo estão nas entregas da disciplina '
    + '(docs/entregas/) e em docs/01 a docs/06; o sistema visual, em docs/09.',
    { color: '5A6B7E', size: 19 },
  ));
  return c;
}

function sumario(titulos) {
  const c = [h1('Sumário')];
  for (const { nivel, texto } of titulos) {
    if (nivel === 1) c.push(p(texto, { bold: true, size: 21, color: '2C5B8F', before: 200, after: 80 }));
    else if (nivel === 2) c.push(p(texto, { size: 19, after: 50, indent: { left: 280 } }));
  }
  c.push(quebra());
  return c;
}

function main() {
  const ver = versao();
  const titulos = [];
  const corpo = [];
  const ler = (arquivo) => fs.readFileSync(path.join(RAIZ, arquivo), 'utf8');

  for (const { arquivo, titulo } of PARTES) {
    corpo.push(quebra());
    corpo.push(...parte(ler(arquivo), { titulo, legendas: LEGENDAS, titulos }));
  }

  corpo.push(quebra());
  titulos.push({ nivel: 1, texto: 'Parte IV — Resultados medidos' });
  corpo.push(h1('Parte IV — Resultados medidos'));
  corpo.push(p(
    'Cada resultado desta parte é o relatório que o script de medição gerou, sem edição à mão: o comando '
    + 'que o reproduz está no próprio relatório. O núcleo em C++ e em CUDA é medido no contêiner, que é '
    + 'onde ele roda; o modelo preditivo, o otimizador serial e o assistente, contra a massa sintética do '
    + 'gerador, num banco à parte; as telas, no navegador, com a aplicação no ar.',
  ));
  for (const item of MEDICOES) {
    const { arquivo, parar } = typeof item === 'string' ? { arquivo: item } : item;
    corpo.push(...parte(ler(arquivo), { deslocamento: 1, legendas: LEGENDAS, titulos, parar }));
  }

  const children = [...capa(ver), ...sobre(ver), quebra(), ...sumario(titulos), ...corpo];

  const doc = new Document({
    creator: `Grupo ${GRUPO} — Equipe GIH`,
    title: `Documentação técnica final — ${PROJETO}`,
    description: 'Arquitetura, modelo de dados, decisões e resultados medidos — Fábrica de Software e Tópicos Avançados, 2026.2',
    styles: { default: { document: { run: { font: 'Calibri', size: 20 } } } },
    numbering: { config: [] },
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
              children: [`Growth Intelligence Hub · Grupo ${GRUPO} · Documentação técnica · `, PageNumber.CURRENT],
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
    const partes = titulos.filter((t) => t.nivel === 1).length;
    console.log(`gerado: ${path.relative(RAIZ, SAIDA)}`);
    console.log(`        ${(buf.length / 1024).toFixed(0)} KB · ${partes} partes · ${children.length} blocos`);
  });
}

main();
