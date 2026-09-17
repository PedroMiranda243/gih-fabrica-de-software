/**
 * Renderiza os diagramas Mermaid da documentação para SVG e PNG.
 *
 * A fonte de verdade de cada diagrama é o bloco ```mermaid dentro do markdown:
 * assim ele renderiza no GitHub, fica versionado e o diff é legível. Este script
 * extrai esses blocos e os rasteriza para o documento de entrega.
 *
 * Cada bloco é identificado por um comentário logo acima dele, invisível quando
 * o markdown é renderizado:
 *
 *     <!-- diagrama: classes-dominio -->
 *     ```mermaid
 *     classDiagram
 *     ```
 *
 * Nomear pelo marcador, e não pela posição, é o que permite reordenar as seções
 * do documento sem trocar silenciosamente um diagrama por outro.
 *
 * Saída: SVG (o que o Word exibe, vetorial e legível em qualquer zoom) e PNG
 * (fallback exigido pela biblioteca `docx` para visualizadores antigos).
 *
 * Uso:  node docs/entrega/renderizar_diagramas.js
 */
const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const RAIZ = path.join(__dirname, '..', '..');
const SAIDA_SVG = path.join(RAIZ, 'docs', 'diagramas');
const SAIDA_PNG = path.join(__dirname, 'diagramas');
const MMDC = path.join(__dirname, 'node_modules', '@mermaid-js', 'mermaid-cli', 'src', 'cli.js');

// Arquivos varridos em busca de blocos marcados.
const FONTES = [
  'docs/03-casos-de-uso.md',
  'docs/05-cronograma.md',
  'docs/07-arquitetura-preliminar.md',
  'docs/08-modelo-de-dados.md',
  'docs/10-diagrama-de-classes.md',
];

// `theme: neutral` imprime bem em preto e branco, que é como a maioria dos
// documentos acadêmicos acaba sendo lida. O fundo branco evita a faixa cinza
// que o tema padrão deixa em volta do desenho dentro do Word.
const CONFIG = {
  theme: 'neutral',
  themeVariables: { fontFamily: 'Segoe UI, Calibri, sans-serif', fontSize: '15px' },
};

function extrair(caminhoRelativo) {
  const caminho = path.join(RAIZ, caminhoRelativo);
  if (!fs.existsSync(caminho)) return [];

  const linhas = fs.readFileSync(caminho, 'utf8').split('\n');
  const achados = [];

  for (let i = 0; i < linhas.length; i += 1) {
    const marcador = linhas[i].match(/^<!--\s*diagrama:\s*([a-z0-9-]+)\s*-->$/);
    if (!marcador) continue;

    if (!linhas[i + 1] || !linhas[i + 1].startsWith('```mermaid')) {
      throw new Error(
        `${caminhoRelativo}:${i + 1} — marcador "${marcador[1]}" não é seguido por um bloco mermaid.`,
      );
    }

    const corpo = [];
    let j = i + 2;
    while (j < linhas.length && !linhas[j].startsWith('```')) {
      corpo.push(linhas[j]);
      j += 1;
    }
    if (j >= linhas.length) {
      throw new Error(`${caminhoRelativo}: bloco "${marcador[1]}" não foi fechado.`);
    }

    achados.push({ nome: marcador[1], fonte: caminhoRelativo, corpo: corpo.join('\n') });
    i = j;
  }

  return achados;
}

function renderizar(diagrama, configuracao) {
  const entrada = path.join(os.tmpdir(), `gih-${diagrama.nome}.mmd`);
  fs.writeFileSync(entrada, diagrama.corpo, 'utf8');

  for (const [pasta, extensao, extras] of [
    [SAIDA_SVG, 'svg', []],
    // 4x: a figura entra na página com 642 px de largura, então esta escala dá
    // cerca de 350 dpi — resolução de impressão. O PNG deixou de ser reserva e
    // passou a ser o que o documento usa; ver o comentário em comum/figuras.js.
    [SAIDA_PNG, 'png', ['--scale', '4']],
  ]) {
    fs.mkdirSync(pasta, { recursive: true });
    const destino = path.join(pasta, `${diagrama.nome}.${extensao}`);
    // Chama o `cli.js` direto pelo Node em vez de passar pelo `npx`: no Windows
    // o `npx` e um .cmd, e `execFileSync` sem shell nao o encontra.
    execFileSync(
      process.execPath,
      [MMDC, '-i', entrada, '-o', destino,
        '-c', configuracao, '-b', 'white', '--quiet', ...extras],
      { cwd: __dirname, stdio: 'inherit' },
    );
  }

  fs.unlinkSync(entrada);
}

function main() {
  const configuracao = path.join(os.tmpdir(), 'gih-mermaid.json');
  fs.writeFileSync(configuracao, JSON.stringify(CONFIG), 'utf8');

  const diagramas = FONTES.flatMap(extrair);
  if (!diagramas.length) {
    console.error('Nenhum bloco marcado encontrado. Falta o comentário <!-- diagrama: nome -->?');
    process.exit(1);
  }

  // Nome repetido sobrescreveria um diagrama pelo outro sem avisar.
  const vistos = new Map();
  for (const d of diagramas) {
    if (vistos.has(d.nome)) {
      throw new Error(`Diagrama "${d.nome}" aparece em ${vistos.get(d.nome)} e em ${d.fonte}.`);
    }
    vistos.set(d.nome, d.fonte);
  }

  for (const d of diagramas) {
    process.stdout.write(`${d.nome}  (${d.fonte})\n`);
    renderizar(d, configuracao);
  }

  fs.unlinkSync(configuracao);
  console.log(`\n${diagramas.length} diagramas renderizados.`);
  console.log(`  SVG: docs/diagramas/`);
  console.log(`  PNG: docs/entrega/diagramas/`);
}

main();
