/**
 * O que os roteiros de captura têm em comum, a partir da Sprint 07.
 *
 * Saiu do `capturar_sprint06.js`, que continua como está: ele gerou evidência
 * já entregue, e não se mexe em quem gerou o que foi entregue. Os roteiros
 * novos (`capturar_sprint07.js` em diante) partem daqui.
 *
 * **Nenhuma senha é digitada em formulário.** O roteiro cria, pela API, um
 * gestor, um analista e um administrador descartáveis, com senha aleatória que
 * nunca é impressa, e os autentica com `fetch` dentro da página. No fim, as
 * sessões são encerradas, os usuários desativados, e o que a captura gravou sai
 * pela limpeza da verificação de ponta a ponta (`api/e2e/limpeza.py`).
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
const RAIZ_API = path.join(__dirname, '..', '..', '..', 'api');

/* Os parâmetros de um plano viável na base de demonstração, os mesmos da
   verificação de ponta a ponta (`verificacao.py`, seção da campanha). */
const PARAMETROS = {
  orcamento: '5000.00',
  maximo_acoes: 30,
  cota_cauda_longa: '0.3',
  aplicacao_inicio: '2026-10-05',
  aplicacao_fim: '2026-10-11',
};

/* A janela de toda captura; o fator 2 é o que dá nitidez no PDF. */
const VISOR = { width: 1280, height: 900, deviceScaleFactor: 2 };

async function esperar(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/** Quebra nas palavras, para caber nas 96 colunas do documento, com o recuo nas seguintes. */
function quebrar(texto, recuo, largura = 94) {
  const margem = /^ */.exec(texto)[0];
  const linhas = [];
  let linha = '';
  for (const palavra of texto.slice(margem.length).split(' ')) {
    if (linha && linha.length + palavra.length + 1 > largura) {
      linhas.push(linha);
      linha = recuo + palavra;
    } else {
      linha = linha ? `${linha} ${palavra}` : margem + palavra;
    }
  }
  return [...linhas, linha].join('\n');
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

/** Cria o roteiro de uma entrega: as funções de foto gravam na pasta dela. */
function roteiro(saida) {
  async function fotografar(pagina, nome, opcoes = {}) {
    // O ponteiro fica onde foi o último clique, e a linha embaixo dele sairia realçada.
    await pagina.mouse.move(0, 0);
    await esperar(400); // transições de 180 ms terminadas
    await pagina.screenshot({ path: path.join(saida, `${nome}.png`), ...opcoes });
    console.log(`${nome.padEnd(36)} ok`);
  }

  /**
   * Só o elemento, com uma margem — a tela inteira dilui o que se quer mostrar.
   * `altura` corta o que passa dela: numa lista, as primeiras linhas já mostram as colunas.
   *
   * A caixa é medida **depois** de a página assentar. Medida antes, um elemento
   * que some acima dela a desloca, e o recorte pega o vizinho — foi o que
   * estragou uma figura da Sprint 06.
   */
  async function fotografarElemento(pagina, nome, seletor, margem = 16, altura = Infinity) {
    await pagina.$eval(seletor, (el) => el.scrollIntoView({ block: 'start' }));
    await pagina.mouse.move(0, 0);
    await esperar(600);
    const caixa = await pagina.$eval(seletor, (el) => {
      const r = el.getBoundingClientRect();
      return { x: r.x + window.scrollX, y: r.y + window.scrollY, width: r.width, height: r.height };
    });
    await fotografar(pagina, nome, recorte({ ...caixa, height: Math.min(caixa.height, altura) }, margem));
  }

  function gravar(nome, linhas) {
    fs.writeFileSync(path.join(saida, nome), `${linhas.join('\n')}\n`, 'utf8');
    console.log(`${nome.padEnd(36)} ok`);
  }

  return { fotografar, fotografarElemento, gravar };
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
  await pagina.setViewport(VISOR);
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

/** Uma chamada à API pela sessão da página, com o JSON de volta. */
async function pelaApi(pagina, metodo, caminho, corpo) {
  return pagina.evaluate(async (m, c, b) => {
    const r = await fetch(c, {
      method: m,
      credentials: 'same-origin',
      headers: b ? { 'Content-Type': 'application/json' } : undefined,
      body: b ? JSON.stringify(b) : undefined,
    });
    const texto = await r.text();
    let dados = null;
    try { dados = texto ? JSON.parse(texto) : null; } catch { dados = texto; }
    return { status: r.status, dados };
  }, metodo, caminho, corpo ?? null);
}

/** Um plano calculado pela página, com a sessão do gestor, e esperado até o fim. */
async function calcularPlano(pagina, parametros = PARAMETROS) {
  const pedido = await pelaApi(pagina, 'POST', '/api/otimizacoes', parametros);
  if (pedido.status !== 202) return { erro: `o cálculo respondeu ${pedido.status}` };
  const limite = Date.now() + 180000;
  for (;;) {
    const { dados } = await pelaApi(pagina, 'GET', `/api/otimizacoes/${pedido.dados.id}`);
    if (dados.situacao !== 'EM_ANDAMENTO') return dados;
    if (Date.now() > limite) return { erro: 'o cálculo não terminou em 3 minutos' };
    await esperar(1000);
  }
}

/**
 * Roda a etapa pedida na linha de comando, com as três pessoas descartáveis, e
 * desfaz tudo no fim — mesmo se a etapa estourar.
 */
async function executar(etapas, saida, entrega) {
  const etapa = process.argv[2];
  if (!etapas[etapa]) throw new Error(`Informe a etapa: ${Object.keys(etapas).join(', ')}.`);
  if (!SENHA_ADMIN) throw new Error('Informe GIH_ADMIN_SENHA — ver o cabeçalho de comum/captura.js.');
  fs.mkdirSync(saida, { recursive: true });

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
    await etapas[etapa]({ gestor, analista, administrador, pessoas, admin, marca, ...roteiro(saida) });
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
  console.log(`\ncapturas em docs/entrega/evidencias/${entrega}/ — etapa "${etapa}"`);
}

/** O `main` de um roteiro: o erro aparece inteiro, e o Node não cai com o navegador fechando. */
function principal(etapas, saida, entrega) {
  executar(etapas, saida, entrega).catch((e) => {
    console.error(e.message);
    // `exitCode`, e não `process.exit()`: sair com o navegador ainda fechando
    // derruba o Node no Windows com uma asserção da libuv, que esconde o erro.
    process.exitCode = 1;
  });
}

module.exports = { WEB, PARAMETROS, VISOR, esperar, quebrar, ir, pelaApi, calcularPlano, principal };
