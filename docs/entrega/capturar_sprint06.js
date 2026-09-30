/**
 * Captura as evidências da Sprint 06 — o terceiro módulo, a integração entre
 * os módulos e as melhorias de interface e de navegação, como o usuário as vê.
 *
 * O enunciado pede o registro das melhorias e a demonstração dos ajustes de
 * navegação. Melhoria só se mostra com o antes ao lado do depois, e o antes
 * precisa ser fotografado **antes** da mudança — depois não há mais como. Por
 * isso o roteiro tem etapas, rodadas em momentos diferentes:
 *
 *   node docs/entrega/capturar_sprint06.js antes    # da main anterior à H79
 *   node docs/entrega/capturar_sprint06.js depois   # com as melhorias no ar
 *
 * Cada etapa grava em `evidencias/sprint06/` as capturas com o prefixo dela, e
 * um `navegacao-<etapa>.txt`: para cada endereço, o título da aba, onde a página
 * de fato parou e a trilha — o que uma captura de tela não mostra.
 *
 * **Nenhuma senha é digitada em formulário.** O script cria, pela API, um gestor
 * um analista e um administrador descartáveis, com senha aleatória que nunca é
 * impressa, e os autentica com `fetch` dentro da página. No fim, são desativados.
 *
 * **As gravações saem no fim**: os planos que o gestor da captura calcula saem
 * pela mesma limpeza da verificação de ponta a ponta (`api/e2e/limpeza.py`).
 *
 * A API e a interface precisam estar no ar (docker compose up -d), com a base de
 * demonstração e o modelo treinado:
 *   GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint06.js <etapa>
 *
 * Captura em modo claro, que é o que imprime com contraste no PDF.
 */
const { execFileSync } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const WEB = process.env.GIH_WEB_URL || 'http://localhost:5173';
const API = process.env.GIH_URL || 'http://localhost:8000';
const ADMIN = process.env.GIH_ADMIN_LOGIN || 'admin';
const SENHA_ADMIN = process.env.GIH_ADMIN_SENHA;
const SAIDA = path.join(__dirname, 'evidencias', 'sprint06');
const RAIZ_API = path.join(__dirname, '..', '..', 'api');

/* Os parâmetros de um plano viável na base de demonstração, os mesmos da
   verificação de ponta a ponta (`verificacao.py`, seção da campanha). O segundo
   orçamento dá um plano diferente, para a comparação ter o que comparar. */
const PARAMETROS = {
  orcamento: '5000.00',
  maximo_acoes: 30,
  cota_cauda_longa: '0.3',
  aplicacao_inicio: '2026-10-05',
  aplicacao_fim: '2026-10-11',
};

async function esperar(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ------------------------------------------------------------ API, pelo Node
async function sessaoAdmin() {
  const r = await fetch(`${API}/api/sessao`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login: ADMIN, senha: SENHA_ADMIN }),
  });
  if (r.status !== 201) throw new Error(`O administrador não autenticou (${r.status}).`);
  const cookie = r.headers.getSetCookie().map((c) => c.split(';')[0]).join('; ');
  return (metodo, caminho, corpo) =>
    fetch(`${API}${caminho}`, {
      method: metodo,
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
}

function python() {
  for (const p of [path.join(RAIZ_API, '.venv', 'Scripts', 'python.exe'),
    path.join(RAIZ_API, '.venv', 'bin', 'python')]) {
    if (fs.existsSync(p)) return p;
  }
  return 'python';
}

/** O que a captura gravou sai pela limpeza da verificação, que recusa dado alheio. */
function limparExecucao(marca) {
  const codigo = [
    'import sys',
    "sys.path.insert(0, '.')",
    'from e2e.limpeza import limpar_execucao',
    `print(limpar_execucao(${JSON.stringify(marca)}))`,
  ].join('; ');
  return execFileSync(python(), ['-c', codigo], {
    cwd: RAIZ_API, encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  }).trim();
}

// ------------------------------------------------------------ na página
async function fotografar(pagina, nome, opcoes = {}) {
  await esperar(400); // transições de 180 ms terminadas
  await pagina.screenshot({ path: path.join(SAIDA, `${nome}.png`), ...opcoes });
  console.log(`${nome.padEnd(36)} ok`);
}

function recorte(caixa, margem) {
  return {
    captureBeyondViewport: true,
    clip: {
      x: Math.max(0, caixa.x - margem),
      y: Math.max(0, caixa.y - margem),
      width: caixa.width + 2 * margem,
      height: caixa.height + 2 * margem,
    },
  };
}

/**
 * Só o elemento, com uma margem — a tela inteira dilui o que se quer mostrar.
 * `altura` corta o que passa dela: numa lista, as primeiras linhas já mostram as colunas.
 */
async function fotografarElemento(pagina, nome, seletor, margem = 16, altura = Infinity) {
  const caixa = await pagina.$eval(seletor, (el) => {
    el.scrollIntoView({ block: 'start' });
    const r = el.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, width: r.width, height: r.height };
  });
  await fotografar(pagina, nome, recorte({ ...caixa, height: Math.min(caixa.height, altura) }, margem));
}

/** A trilha, do primeiro ao último passo: o elemento ocupa a largura toda, e o resto é vazio. */
async function fotografarTrilha(pagina, nome) {
  const caixa = await pagina.evaluate(() => {
    const passos = [...document.querySelector('nav.trilha').children].map((e) => e.getBoundingClientRect());
    const x = Math.min(...passos.map((r) => r.left));
    const y = Math.min(...passos.map((r) => r.top));
    return {
      x: x + window.scrollX,
      y: y + window.scrollY,
      width: Math.max(...passos.map((r) => r.right)) - x,
      height: Math.max(...passos.map((r) => r.bottom)) - y,
    };
  });
  await fotografar(pagina, nome, recorte(caixa, 12));
}

/** O menu, da marca ao último item: o trilho ocupa a altura da tela, e o resto é vazio. */
async function fotografarMenu(pagina, nome) {
  const caixa = await pagina.evaluate(() => {
    const menu = document.querySelector('nav.trilho').getBoundingClientRect();
    const itens = [...document.querySelectorAll('nav.trilho a')];
    const fim = Math.max(...itens.map((i) => i.getBoundingClientRect().bottom));
    return { x: menu.x, y: menu.y, width: menu.width, height: fim - menu.y + 16 };
  });
  await fotografar(pagina, nome, recorte(caixa, 0));
}

async function ir(pagina, caminho, seletor) {
  await pagina.goto(`${WEB}${caminho}`, { waitUntil: 'networkidle0' });
  if (seletor) await pagina.waitForSelector(seletor, { timeout: 15000 });
}

/** Cada pessoa num contexto próprio: páginas do mesmo contexto dividem o cookie. */
async function paginaDe(navegador, login, senha) {
  const contexto = await navegador.createBrowserContext();
  const pagina = await contexto.newPage();
  await pagina.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }]);
  await pagina.setViewport({ width: 1280, height: 900, deviceScaleFactor: 2 });
  try {
    await ir(pagina, '/entrar', '#login');
  } catch {
    throw new Error(`A interface não respondeu em ${WEB}. Suba com: docker compose up -d`);
  }
  const status = await pagina.evaluate(
    async (l, s) => (await fetch('/api/sessao', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login: l, senha: s }),
    })).status,
    login,
    senha,
  );
  if (status !== 201) throw new Error(`A autenticação respondeu ${status}.`);
  return pagina;
}

/** Um plano calculado pela página, com a sessão do gestor, e esperado até o fim. */
async function calcularPlano(pagina, parametros) {
  return pagina.evaluate(async (corpo) => {
    const pedido = await fetch('/api/otimizacoes', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
    });
    if (pedido.status !== 202) return { erro: `o cálculo respondeu ${pedido.status}` };
    const { id } = await pedido.json();
    const limite = Date.now() + 180000;
    for (;;) {
      const execucao = await (await fetch(`/api/otimizacoes/${id}`, { credentials: 'same-origin' })).json();
      if (execucao.situacao !== 'EM_ANDAMENTO') return execucao;
      if (Date.now() > limite) return { erro: 'o cálculo não terminou em 3 minutos' };
      await new Promise((r) => setTimeout(r, 1000));
    }
  }, parametros);
}

/**
 * Para cada endereço: o título da aba, onde a página parou, a trilha e os grupos
 * do menu. É a evidência da navegação que a captura não mostra — a aba do
 * navegador e o redirecionamento ficam fora do quadro.
 */
async function registrarNavegacao(visitas, arquivo, titulo) {
  const linhas = [
    titulo,
    `Gerado por docs/entrega/capturar_sprint06.js em ${new Date().toLocaleString('pt-BR')}, na interface em ${WEB}.`,
    '',
  ];
  for (const [indice, [pagina, endereco]] of visitas.entries()) {
    await ir(pagina, endereco);
    await esperar(600);
    const lido = await pagina.evaluate(() => ({
      titulo: document.title,
      parou: location.pathname + location.search,
      // Os passos da trilha, e não o texto corrido: o separador vem do CSS.
      trilha: [...(document.querySelector('nav.trilha')?.children ?? [])]
        .map((e) => e.textContent.trim()).filter((x) => x && x !== '›').join(' › '),
      grupos: [...document.querySelectorAll('.trilho__grupo-titulo')].map((g) => g.textContent.trim()),
    }));
    linhas.push(`${endereco}`);
    linhas.push(`  título da aba: ${lido.titulo}`);
    linhas.push(`  a página parou em: ${lido.parou}${lido.parou === endereco ? '' : '   (redirecionada)'}`);
    linhas.push(`  trilha: ${lido.trilha || '(nenhuma)'}`);
    if (indice === 0) {
      linhas.push(`  grupos do menu: ${lido.grupos.length ? lido.grupos.join(' · ') : '(nenhum — itens soltos)'}`);
    }
    linhas.push('');
  }
  fs.writeFileSync(path.join(SAIDA, arquivo), linhas.join('\n'), 'utf8');
  console.log(`${arquivo.padEnd(36)} ok`);
}

// -------------------------------------------------------------------- etapas
/** Dois planos, para a execução e a comparação existirem, e um parceiro que está no primeiro. */
async function planos(gestor) {
  const primeiro = await calcularPlano(gestor, PARAMETROS);
  if (primeiro.erro || !primeiro.viavel) {
    throw new Error(`Sem plano viável para as capturas: ${primeiro.erro ?? primeiro.motivo}`);
  }
  const segundo = await calcularPlano(gestor, { ...PARAMETROS, orcamento: '3000.00' });
  return { primeiro, segundo, noPlano: primeiro.itens[0].parceiro_id };
}

/** Os mesmos endereços nas duas etapas: é o que torna o antes e o depois comparáveis. */
async function registrarEnderecos({ gestor, administrador, pessoas }, { primeiro, segundo, noPlano }, etapa, titulo) {
  /* As telas de administração são do Administrador; as outras, do Gestor. */
  const doGestor = [
    '/',
    '/importacao',
    '/parceiros',
    `/parceiros/${noPlano}`,
    '/modelo',
    '/campanha',
    '/execucoes',
    `/execucoes/${primeiro.id}`,
    ...(segundo.id ? [`/execucoes/comparar?a=${primeiro.id}&b=${segundo.id}`] : []),
    '/benchmark',
    '/mensagens',
    '/aprovacao',
    '/pagina-que-nao-existe',
  ].map((e) => [gestor, e]);
  const doAdministrador = ['/usuarios', `/usuarios/${pessoas.GESTOR.id}`, '/configuracao']
    .map((e) => [administrador, e]);
  await registrarNavegacao([...doGestor, ...doAdministrador], `navegacao-${etapa}.txt`, titulo);
}

/**
 * O antes: a main anterior à H79, H80 e H81. O menu solto, a lista sem o risco,
 * o ranking e o cadastro do parceiro sem ligação com a campanha, e o endereço
 * inválido caindo no painel.
 */
async function antes(contexto) {
  const { gestor, analista } = contexto;
  const calculados = await planos(gestor);
  const { primeiro, noPlano } = calculados;

  await ir(gestor, '/', '.trilho');
  await fotografarMenu(gestor, 'antes-menu-gestor');
  await ir(analista, '/', '.trilho');
  await fotografarMenu(analista, 'antes-menu-analista');

  await ir(gestor, '/', 'section[aria-labelledby="titulo-ranking"] table');
  await fotografarElemento(gestor, 'antes-painel-ranking', 'section[aria-labelledby="titulo-ranking"]', 16, 560);

  await ir(gestor, '/parceiros', 'section[aria-labelledby="titulo-parceiros"] table');
  await fotografarElemento(gestor, 'antes-parceiros-lista', 'section[aria-labelledby="titulo-parceiros"]', 16, 560);

  await ir(gestor, `/parceiros/${noPlano}`, 'nav.trilha');
  await fotografar(gestor, 'antes-parceiro-cadastro');

  await ir(gestor, `/execucoes/${primeiro.id}`, 'section[aria-labelledby="titulo-pedido"]');
  await fotografar(gestor, 'antes-execucao');

  await ir(gestor, '/pagina-que-nao-existe');
  await esperar(600);
  await fotografar(gestor, 'antes-endereco-invalido');

  await registrarEnderecos(contexto, calculados, 'antes', 'Navegação — antes da H79 (main de 30/09/2026)');
}

/**
 * O depois, com as melhorias no ar. H79: o menu por módulo em cada perfil, a
 * página do endereço inválido e o título de cada aba.
 */
async function depois(contexto) {
  const { gestor, analista, administrador } = contexto;
  const calculados = await planos(gestor);

  await ir(gestor, '/', '.trilho__grupo');
  await fotografarMenu(gestor, 'depois-menu-gestor');
  await ir(analista, '/', '.trilho__grupo');
  await fotografarMenu(analista, 'depois-menu-analista');
  await ir(administrador, '/', '.trilho__grupo');
  await fotografarMenu(administrador, 'depois-menu-administrador');

  await ir(gestor, '/pagina-que-nao-existe', 'section[aria-label="Página não encontrada"]');
  await fotografar(gestor, 'depois-endereco-invalido');

  /* No tablet (768 px, RNF21) o trilho vira barra horizontal: os títulos dos
     grupos ficam só para o leitor de tela, e um fio separa um módulo do outro. */
  await gestor.setViewport({ width: 768, height: 900, deviceScaleFactor: 2 });
  await ir(gestor, '/', '.trilho__grupo');
  await fotografarElemento(gestor, 'depois-menu-768', 'nav.trilho', 0);
  await gestor.setViewport({ width: 1280, height: 900, deviceScaleFactor: 2 });

  /* H80: a lista ordenada pelo risco, do maior para o menor, com a nota de onde
     ele vem. E o tempo da consulta com o risco, mediana de cinco (RNF03). */
  await ir(gestor, '/parceiros?ordenar_por=risco&descendente=true', 'section[aria-labelledby="titulo-parceiros"] table');
  await fotografarElemento(gestor, 'depois-parceiros-lista', 'section[aria-labelledby="titulo-parceiros"]', 16, 560);
  const tempos = await gestor.evaluate(async () => {
    const medidos = [];
    for (let i = 0; i < 5; i += 1) {
      const inicio = performance.now();
      await fetch('/api/parceiros?tamanho=50&ordenar_por=risco&descendente=true', { credentials: 'same-origin' });
      medidos.push(performance.now() - inicio);
    }
    return medidos.sort((x, y) => x - y);
  });
  console.log(`lista ordenada pelo risco: mediana de ${tempos[2].toFixed(0)} ms (de ${tempos[0].toFixed(0)} a ${tempos[4].toFixed(0)} ms)`);

  /* H81: o cadastro de um parceiro que está no último plano — é o plano mais
     recente que vale, o segundo —, com a ação e o link para o plano. E o mesmo
     cadastro aberto pelo ranking do painel: a trilha volta para o painel. */
  const ultimo = calculados.segundo?.viavel ? calculados.segundo : calculados.primeiro;
  /* A coluna do lado do cadastro junta os três módulos: o desempenho medido, a
     previsão e a ação no plano. */
  await ir(gestor, `/parceiros/${ultimo.itens[0].parceiro_id}`, 'section[aria-labelledby="titulo-na-campanha"] dl');
  await fotografarElemento(gestor, 'depois-parceiro-cadastro', '.cadastro__lateral');
  await ir(gestor, '/', 'section[aria-labelledby="titulo-ranking"] a.nome__link');
  await gestor.click('section[aria-labelledby="titulo-ranking"] a.nome__link');
  await gestor.waitForSelector('section[aria-labelledby="titulo-na-campanha"]');
  await fotografarTrilha(gestor, 'depois-trilha-do-painel');

  await registrarEnderecos(contexto, calculados, 'depois', 'Navegação — depois da H79');
}

const ETAPAS = { antes, depois };

// -------------------------------------------------------------------- roteiro
async function main() {
  const etapa = process.argv[2];
  if (!ETAPAS[etapa]) {
    throw new Error(`Informe a etapa: ${Object.keys(ETAPAS).join(', ')}.`);
  }
  if (!SENHA_ADMIN) throw new Error('Informe GIH_ADMIN_SENHA — ver o cabeçalho deste arquivo.');
  fs.mkdirSync(SAIDA, { recursive: true });

  const admin = await sessaoAdmin();
  const marca = `t${String(crypto.randomInt(100000)).padStart(5, '0')}`;
  const pessoas = {};
  const nomes = { GESTOR: 'Gestora', ANALISTA: 'Analista', ADMINISTRADOR: 'Administradora' };
  for (const perfil of Object.keys(nomes)) {
    const login = `${marca}.${perfil.toLowerCase()}`;
    const senha = crypto.randomBytes(18).toString('base64url');
    const criado = await admin('POST', '/api/usuarios', {
      login, nome: `${nomes[perfil]} da Captura`, senha, perfil,
    });
    if (criado.status !== 201) throw new Error(`Não criei o ${perfil} (${criado.status}).`);
    pessoas[perfil] = { login, senha, id: (await criado.json()).id };
  }

  const navegador = await puppeteer.launch({ headless: 'new' });
  try {
    const gestor = await paginaDe(navegador, pessoas.GESTOR.login, pessoas.GESTOR.senha);
    const analista = await paginaDe(navegador, pessoas.ANALISTA.login, pessoas.ANALISTA.senha);
    const administrador = await paginaDe(
      navegador, pessoas.ADMINISTRADOR.login, pessoas.ADMINISTRADOR.senha,
    );
    await ETAPAS[etapa]({ gestor, analista, administrador, pessoas, admin });
    for (const p of [gestor, analista, administrador]) {
      await p.evaluate(() => fetch('/api/sessao', { method: 'DELETE', credentials: 'same-origin' }));
    }
  } finally {
    await navegador.close();
    console.log(`\nlimpeza: ${limparExecucao(marca)}`);
    for (const { id } of Object.values(pessoas)) {
      await admin('PATCH', `/api/usuarios/${id}`, { ativo: false });
    }
    console.log('usuários da captura desativados');
  }
  console.log(`\ncapturas em docs/entrega/evidencias/sprint06/ — etapa "${etapa}"`);
}

main().catch((e) => {
  console.error(e.message);
  // `exitCode`, e não `process.exit()`: sair com o navegador ainda fechando
  // derruba o Node no Windows com uma asserção da libuv, que esconde o erro.
  process.exitCode = 1;
});
