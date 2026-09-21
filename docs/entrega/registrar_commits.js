/**
 * Registra, a partir do `git log`, como o trabalho entrou no repositório.
 *
 * A Sprint 04 pede "commits organizados". Organização se mostra com o
 * histórico, e não com uma frase: quantos commits de cada tipo, em que semanas,
 * com que coautoria, e quais Pull Requests entraram em cada janela de entrega.
 * **Gerado, nunca escrito à mão** — o número que vai para o documento é o que o
 * git responde no momento da geração.
 *
 * Lê a `main` do remoto por padrão, que é o que a disciplina avalia; um ramo
 * local com trabalho ainda não incorporado inflaria a contagem.
 *
 * Uso:
 *   git fetch origin
 *   node docs/entrega/registrar_commits.js > docs/entrega/evidencias/sprint04/commits.txt
 *   node docs/entrega/registrar_commits.js outra-ref      # outra referência
 */
const { execFileSync } = require('child_process');

const REF = process.argv[2] || 'origin/main';
const REPOSITORIO = 'https://github.com/PedroMiranda243/gih-fabrica-de-software';

/* As janelas de entrega da disciplina (docs/05, seção 1). As Sprints 02 e 03
   venceram no mesmo dia, e por isso dividem a janela. */
const JANELAS = [
  { rotulo: 'Sprint 01 — até 05/09', ate: '2026-09-05' },
  { rotulo: 'Sprints 02 e 03 — 06/09 a 19/09', ate: '2026-09-19' },
  { rotulo: 'Sprint 04 — 20/09 a 26/09', ate: '2026-09-26' },
];

// Separadores de controle: nenhum deles aparece em mensagem de commit.
const CAMPO = '\x1f';
const REGISTRO = '\x1e';

function git(...args) {
  return execFileSync('git', args, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
}

function registros(...args) {
  return git('log', REF, ...args)
    .split(REGISTRO)
    .map((r) => r.replace(/^\n+/, ''))
    .filter(Boolean)
    .map((r) => r.split(CAMPO));
}

/** O tipo do Conventional Commits, ou `null` quando o assunto não segue a convenção. */
function tipo(assunto) {
  const m = /^([a-z]+)(\([^)]*\))?!?: /.exec(assunto);
  return m ? m[1] : null;
}

/** A segunda-feira da semana da data, em AAAA-MM-DD. */
function segunda(data) {
  const d = new Date(`${data}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}

function ddmm(data) {
  return `${data.slice(8, 10)}/${data.slice(5, 7)}`;
}

function somarDias(data, dias) {
  const d = new Date(`${data}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

/** Corta na última palavra inteira que cabe: título cortado no meio da palavra parece erro. */
function cortar(texto, largura) {
  if (texto.length <= largura) return texto;
  const corte = texto.slice(0, largura - 1);
  return `${corte.slice(0, corte.lastIndexOf(' ')).replace(/[\s,—-]+$/, '')}…`;
}

function contar(itens) {
  const mapa = new Map();
  for (const i of itens) mapa.set(i, (mapa.get(i) || 0) + 1);
  return [...mapa.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(b[0]));
}

function titulo(texto) {
  console.log(`\n${texto}\n${'-'.repeat(texto.length)}`);
}

function main() {
  const topo = git('rev-parse', '--short', REF).trim();

  // Commits de trabalho: sem os de merge, que só registram a incorporação.
  const commits = registros(
    '--no-merges',
    `--format=%an${CAMPO}%as${CAMPO}%s${CAMPO}%(trailers:key=Co-authored-by,valueonly,separator=;)${REGISTRO}`,
  ).map(([autor, data, assunto, coautores]) => ({
    autor,
    data,
    assunto,
    tipo: tipo(assunto),
    coautores: (coautores || '')
      .split(';')
      .map((c) => c.replace(/<[^>]*>/, '').trim())
      .filter(Boolean),
  }));

  // A linha principal da `main`: cada item é um PR incorporado (commit de
  // merge) ou um commit feito direto nela, antes de a `main` ser protegida.
  const principal = registros(
    '--first-parent',
    `--format=%P${CAMPO}%cs${CAMPO}%s${CAMPO}%b${REGISTRO}`,
  ).map(([pais, data, assunto, corpo]) => ({
    merge: pais.trim().split(' ').length > 1,
    data,
    assunto,
    titulo: (corpo || '').trim().split('\n')[0],
  }));
  const prs = principal
    .filter((c) => c.merge)
    .map((c) => ({ ...c, numero: Number((/#(\d+)/.exec(c.assunto) || [])[1]) }))
    .reverse();
  const diretos = principal.filter((c) => !c.merge);

  const datas = commits.map((c) => c.data).sort();
  console.log('Commits do repositório');
  console.log(`${REPOSITORIO}`);
  console.log(`Referência ${REF} em ${topo} · de ${datas[0]} a ${datas[datas.length - 1]}`);
  console.log('Gerado a partir do git log; nenhum número foi escrito à mão.');

  // ------------------------------------------------------------------ totais
  titulo('Totais');
  console.log(`  commits de trabalho             ${String(commits.length).padStart(4)}`);
  console.log(`  Pull Requests incorporados      ${String(prs.length).padStart(4)}`);
  if (diretos.length) {
    const ultimo = diretos.map((c) => c.data).sort().pop();
    console.log(`  commits direto na main          ${String(diretos.length).padStart(4)}` +
      `   (até ${ddmm(ultimo)}, antes de a main ser protegida)`);
  }

  // -------------------------------------------------------------------- tipo
  titulo('Por tipo (Conventional Commits)');
  const semTipo = commits.filter((c) => !c.tipo);
  for (const [t, n] of contar(commits.filter((c) => c.tipo).map((c) => c.tipo))) {
    const pct = ((100 * n) / commits.length).toFixed(0).padStart(3);
    console.log(`  ${t.padEnd(8)} ${String(n).padStart(4)}  ${pct}%`);
  }
  if (semTipo.length) {
    console.log(`  ${'fora'.padEnd(8)} ${String(semTipo.length).padStart(4)}  ` +
      '(fora da convenção:)');
    for (const c of semTipo) console.log(`             ${c.data}  ${cortar(c.assunto, 74)}`);
  }

  // ------------------------------------------------------------------ semana
  titulo('Por semana (segunda a domingo)');
  const porSemana = new Map(contar(commits.map((c) => segunda(c.data))));
  const semanas = [...porSemana.keys()].sort();
  const maior = Math.max(...porSemana.values());
  for (let s = semanas[0]; s <= semanas[semanas.length - 1]; s = somarDias(s, 7)) {
    const n = porSemana.get(s) || 0;
    const barra = '█'.repeat(Math.round((40 * n) / maior));
    console.log(`  ${ddmm(s)} a ${ddmm(somarDias(s, 6))}  ${String(n).padStart(3)}  ${barra}`);
  }

  // --------------------------------------------------------------- coautoria
  titulo('Autoria e coautoria');
  console.log('  Cada commit tem um autor e, por área, o colega responsável como coautor');
  console.log('  (trailer Co-authored-by, que o GitHub credita ao coautor).');
  for (const [autor, n] of contar(commits.map((c) => c.autor))) {
    console.log(`  autor     ${autor.padEnd(40)} ${String(n).padStart(4)}`);
  }
  for (const [coautor, n] of contar(commits.flatMap((c) => c.coautores))) {
    console.log(`  coautor   ${coautor.padEnd(40)} ${String(n).padStart(4)}`);
  }
  const sozinhos = commits.filter((c) => !c.coautores.length).length;
  console.log(`  sem coautor${' '.repeat(39)}${String(sozinhos).padStart(4)}`);

  // --------------------------------------------------------------------- PRs
  titulo('Pull Requests incorporados, por janela de entrega');
  let desde = '0000-00-00';
  for (const janela of JANELAS) {
    const daqui = prs.filter((p) => p.data > desde && p.data <= janela.ate);
    desde = janela.ate;
    console.log(`\n  ${janela.rotulo}: ${daqui.length}`);
    for (const p of daqui) {
      console.log(`    #${String(p.numero).padEnd(3)} ${ddmm(p.data)}  ${cortar(p.titulo, 78)}`);
    }
  }
  const depois = prs.filter((p) => p.data > desde);
  if (depois.length) console.log(`\n  depois de ${ddmm(desde)}: ${depois.length}`);
}

main();
