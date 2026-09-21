/**
 * Captura o módulo da Sprint 04 funcionando — o fluxo e os erros, como o
 * usuário os vê.
 *
 * O enunciado pede evidência do módulo funcionando, das validações, das
 * mensagens de erro e da navegação. Cada captura aqui é da aplicação no ar,
 * sobre a base de demonstração, e cada erro é provocado de verdade pela tela —
 * nenhum é montado.
 *
 * **Nenhuma senha é digitada em formulário.** O script cria, pela API, um
 * analista descartável com senha aleatória que nunca é impressa, e o autentica
 * com `fetch` dentro da página. No fim, o analista é desativado.
 *
 * **A única gravação é a importação**, e ela é desfeita no `finally`, pela
 * mesma limpeza da verificação de ponta a ponta (`api/e2e/limpeza.py`). Os
 * erros provocados não gravam nada: é isso que eles demonstram. A importação
 * usa o período seguinte ao último da base e nomes que já existem nela — assim
 * nenhum parceiro novo é criado, e a limpeza tem só período, importação e
 * métricas a desfazer.
 *
 * A API e a interface precisam estar no ar (docker compose up -d):
 *   GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint04.js
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
const SAIDA = path.join(__dirname, 'evidencias', 'sprint04');
const RAIZ_API = path.join(__dirname, '..', '..', 'api');
const FORMULARIO = 'section[aria-labelledby="titulo-cadastro"]';

async function esperar(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ------------------------------------------------------------ API, pelo Node
/** Sessão do administrador, só para criar e desativar o analista descartável. */
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

/** Desfaz a importação pela limpeza da verificação, que recusa apagar dado alheio. */
function limparImportacao(marca) {
  const codigo = [
    'import sys',
    "sys.path.insert(0, '.')",
    'from e2e.limpeza import limpar_execucao',
    `print(limpar_execucao(${JSON.stringify(marca)}))`,
  ].join('; ');
  return execFileSync(python(), ['-c', codigo], { cwd: RAIZ_API, encoding: 'utf8' }).trim();
}

// ---------------------------------------------------------------- navegador
/** Preenche um campo controlado pelo React — ver `capturar_interface.js`. */
async function preencher(pagina, seletor, valor) {
  await pagina.$eval(
    seletor,
    (el, v) => {
      const proto = {
        TEXTAREA: HTMLTextAreaElement.prototype,
        SELECT: HTMLSelectElement.prototype,
      }[el.tagName] ?? HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
      el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
    },
    valor,
  );
}

/** Clica no botão com exatamente este texto — o texto é o que o usuário procura. */
async function clicar(pagina, texto, dentro = 'body') {
  const achou = await pagina.$eval(
    dentro,
    (raiz, t) => {
      const botao = [...raiz.querySelectorAll('button, a')].find(
        (b) => b.textContent.trim() === t && !b.disabled,
      );
      botao?.click();
      return Boolean(botao);
    },
    texto,
  );
  if (!achou) throw new Error(`Não achei o botão "${texto}".`);
}

async function fotografar(pagina, nome, opcoes = {}) {
  await esperar(400); // transições de 180 ms terminadas
  await pagina.screenshot({ path: path.join(SAIDA, `${nome}.png`), ...opcoes });
  console.log(`${nome.padEnd(32)} ok`);
}

/** Só o elemento, com uma margem — a tela inteira dilui o erro que se quer mostrar. */
async function fotografarElemento(pagina, nome, seletor, margem = 16) {
  const caixa = await pagina.$eval(seletor, (el) => {
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, width: r.width, height: r.height };
  });
  await fotografar(pagina, nome, {
    captureBeyondViewport: true,
    clip: {
      x: Math.max(0, caixa.x - margem),
      y: Math.max(0, caixa.y - margem),
      width: caixa.width + 2 * margem,
      height: caixa.height + 2 * margem,
    },
  });
}

/** Do topo de um elemento ao fim de outro: o resumo do erro e o formulário juntos. */
async function fotografarFaixa(pagina, nome, primeiro, ultimo, margem = 16) {
  const caixa = await pagina.evaluate((a, b) => {
    const [ra, rb] = [a, b].map((s) => document.querySelector(s).getBoundingClientRect());
    const esquerda = Math.min(ra.left, rb.left);
    return {
      x: esquerda + window.scrollX,
      y: ra.top + window.scrollY,
      width: Math.max(ra.right, rb.right) - esquerda,
      height: rb.bottom - ra.top,
    };
  }, primeiro, ultimo);
  await fotografar(pagina, nome, {
    captureBeyondViewport: true,
    clip: {
      x: Math.max(0, caixa.x - margem),
      y: Math.max(0, caixa.y - margem),
      width: caixa.width + 2 * margem,
      height: caixa.height + 2 * margem,
    },
  });
}

/** Até o fim da N-ésima linha da tabela — ver `capturar_interface.js`. */
async function fotografarAteLinha(pagina, nome, linhas) {
  const fim = await pagina.$$eval(
    '.tabela tbody tr',
    (trs, n) => Math.ceil(trs[Math.min(n, trs.length) - 1].getBoundingClientRect().bottom + window.scrollY),
    linhas,
  );
  const largura = await pagina.evaluate(() => document.documentElement.clientWidth);
  await fotografar(pagina, nome, {
    captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: largura, height: fim + 1 },
  });
}

async function ir(pagina, caminho, seletor) {
  await pagina.goto(`${WEB}${caminho}`, { waitUntil: 'networkidle0' });
  if (seletor) await pagina.waitForSelector(seletor, { timeout: 15000 });
}

// -------------------------------------------------------------------- roteiro
async function main() {
  if (!SENHA_ADMIN) throw new Error('Informe GIH_ADMIN_SENHA — ver o cabeçalho deste arquivo.');
  fs.mkdirSync(SAIDA, { recursive: true });

  const admin = await sessaoAdmin();
  const marca = `t${String(crypto.randomInt(100000)).padStart(5, '0')}`;
  const login = `${marca}.captura`;
  const senha = crypto.randomBytes(18).toString('base64url');
  const criado = await admin('POST', '/api/usuarios', {
    login, nome: 'Captura da Evidência', senha, perfil: 'ANALISTA',
  });
  if (criado.status !== 201) throw new Error(`Não criei o analista (${criado.status}).`);
  const idAnalista = (await criado.json()).id;

  const navegador = await puppeteer.launch({ headless: 'new' });
  let importou = false;
  try {
    const pagina = await navegador.newPage();
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

    // ------------------------------------------------------------- painel
    await pagina.setViewport({ width: 1280, height: 1180, deviceScaleFactor: 2 });
    await ir(pagina, '/', '.indicadores .indicador');
    await pagina.waitForSelector('.tabela tbody tr');
    await fotografarAteLinha(pagina, 'fluxo-1-painel', 8);

    // ------------------------------------------ lista: recorte pela URL
    await pagina.setViewport({ width: 1280, height: 900, deviceScaleFactor: 2 });
    await ir(pagina, '/parceiros?segmento=EM_RISCO&ordenar_por=variacao', '.tabela tbody tr');
    await fotografarAteLinha(pagina, 'fluxo-2-parceiros-em-risco', 10);

    // ------------------------------------------- cadastro, pela lista
    const nomeDoParceiro = await pagina.$eval('.tabela tbody tr .nome__link', (a) => a.textContent.trim());
    await pagina.click('.tabela tbody tr .nome__link');
    await pagina.waitForSelector('#titulo-desempenho', { timeout: 15000 });
    await pagina.waitForSelector('.grafico__linha', { timeout: 15000 });
    await fotografar(pagina, 'fluxo-3-cadastro-do-parceiro', { fullPage: true });

    // --------------------------- erro: campos inválidos, nada é gravado
    await preencher(pagina, '#campo-nome', '');
    await preencher(pagina, '#campo-contato', 'x'.repeat(121));
    await clicar(pagina, 'Salvar alterações');
    await pagina.waitForSelector('.campo__erro', { timeout: 15000 });
    await fotografarFaixa(pagina, 'erro-1-campos-do-cadastro', '.aviso[role="alert"]', FORMULARIO);

    // --------------------- erro: exclusão recusada, com a saída ao lado
    await ir(pagina, pagina.url().replace(WEB, ''), '#titulo-situacao');
    await clicar(pagina, 'Excluir parceiro', '.situacao__corpo');
    await clicar(pagina, 'Excluir', '.confirmacao');
    await pagina.waitForFunction(
      () => [...document.querySelectorAll('.situacao__corpo button')]
        .some((b) => b.textContent.includes('Desativar em vez de excluir')),
      { timeout: 15000 },
    );
    await fotografarElemento(pagina, 'erro-2-exclusao-recusada', 'section[aria-labelledby="titulo-situacao"]');

    // ------------------------ erro: nome em uso, com o link do existente
    await ir(pagina, '/parceiros/novo', '#campo-nome');
    await preencher(pagina, '#campo-nome', nomeDoParceiro);
    await clicar(pagina, 'Cadastrar parceiro');
    await pagina.waitForSelector('.aviso__acao a', { timeout: 15000 });
    await fotografarFaixa(pagina, 'erro-3-nome-em-uso', '.aviso[role="alert"]', FORMULARIO);

    // ------------------------------------------------ importação
    const ultimo = await pagina.evaluate(
      async () => (await (await fetch('/api/painel/indicadores', { credentials: 'same-origin' })).json()).periodo,
    );
    const inicio = new Date(`${ultimo.data_fim}T12:00:00Z`);
    inicio.setUTCDate(inicio.getUTCDate() + 1);
    const fim = new Date(inicio);
    fim.setUTCDate(fim.getUTCDate() + 6);
    const periodo = [inicio, fim].map((d) => d.toISOString().slice(0, 10));

    const existentes = await pagina.evaluate(
      async () => (await (await fetch('/api/parceiros?tamanho=3&ordenar_por=faturamento&descendente=true',
        { credentials: 'same-origin' })).json()).itens.map((p) => p.nome),
    );
    const relatorio = [
      'Parceiro;Faturamento;Pedidos',
      `${existentes[0]};18420,90;402`,
      `${existentes[1]};15310,00;351`,
      `${existentes[2]};abacaxi;290`,
    ].join('\n');

    await ir(pagina, '/importacao', '#texto');
    await preencher(pagina, '#inicio', periodo[0]);
    await preencher(pagina, '#fim', periodo[1]);
    await preencher(pagina, '#texto', relatorio);
    await clicar(pagina, 'Ver a prévia');
    await pagina.waitForSelector('#titulo-previa', { timeout: 15000 });
    await fotografar(pagina, 'fluxo-4-importacao-previa', { fullPage: true });

    importou = true; // a partir daqui, há o que desfazer mesmo se algo quebrar
    await clicar(pagina, 'Gravar 2 registros');
    await pagina.waitForSelector('.aviso--sucesso', { timeout: 30000 });
    await fotografarElemento(pagina, 'fluxo-5-importacao-concluida', '.aviso--sucesso');

    // ----------------------------- erro: o mesmo período de novo (RF12)
    await preencher(pagina, '#inicio', periodo[0]);
    await preencher(pagina, '#fim', periodo[1]);
    await preencher(pagina, '#texto', relatorio);
    await clicar(pagina, 'Ver a prévia');
    await pagina.waitForSelector('#titulo-previa', { timeout: 15000 });
    await clicar(pagina, 'Gravar 2 registros');
    await pagina.waitForSelector('.importacao__conflito', { timeout: 15000 });
    await fotografarElemento(pagina, 'erro-4-periodo-ja-importado', '.aviso[role="alert"]');

    await pagina.evaluate(() => fetch('/api/sessao', { method: 'DELETE', credentials: 'same-origin' }));
  } finally {
    await navegador.close();
    await admin('PATCH', `/api/usuarios/${idAnalista}`, { ativo: false });
    if (importou) console.log(`\nlimpeza: ${limparImportacao(marca)}`);
    console.log('analista da captura desativado');
  }
  console.log('\ncapturas em docs/entrega/evidencias/sprint04/');
}

main().catch((e) => {
  console.error(e.message);
  // `exitCode`, e não `process.exit()`: sair com o navegador ainda fechando
  // derruba o Node no Windows com uma asserção da libuv, que esconde o erro.
  process.exitCode = 1;
});
