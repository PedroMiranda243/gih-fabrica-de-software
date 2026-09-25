/**
 * Captura o módulo de previsão da Sprint 05 funcionando — o fluxo e os erros,
 * como o usuário os vê.
 *
 * O enunciado pede evidência das funcionalidades do segundo módulo e testes das
 * situações de erro. Cada captura aqui é da aplicação no ar, sobre a base de
 * demonstração, e cada erro é provocado de verdade pela tela — nenhum é montado.
 *
 * **Nenhuma senha é digitada em formulário.** O script cria, pela API, um
 * gestor e um analista descartáveis, com senha aleatória que nunca é impressa,
 * e os autentica com `fetch` dentro da página. No fim, os dois são desativados.
 *
 * **A única gravação é o treino**, e ele sai no fim pela mesma limpeza da
 * verificação de ponta a ponta (`api/e2e/limpeza.py`): os treinos do gestor da
 * captura, com as previsões deles. A versão em uso volta a ser a de antes.
 *
 * A API e a interface precisam estar no ar (docker compose up -d), com o
 * modelo já treinado uma vez na base — `resetar_banco.py` faz isso:
 *   GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint05.js
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
const SAIDA = path.join(__dirname, 'evidencias', 'sprint05');
const RAIZ_API = path.join(__dirname, '..', '..', 'api');
const VERSAO = 'section[aria-labelledby="titulo-versao"]';

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

/** Os treinos da captura saem pela limpeza da verificação, que recusa dado alheio. */
function limparExecucao(marca) {
  const codigo = [
    'import sys',
    "sys.path.insert(0, '.')",
    'from e2e.limpeza import limpar_execucao',
    `print(limpar_execucao(${JSON.stringify(marca)}))`,
  ].join('; ');
  return execFileSync(python(), ['-c', codigo], { cwd: RAIZ_API, encoding: 'utf8' }).trim();
}

/** Espera todo treino em andamento terminar — a limpeza não pode apagar um que grava. */
async function esperarTreinos(admin) {
  const limite = Date.now() + 180000;
  while (Date.now() < limite) {
    const estado = await (await admin('GET', '/api/modelo')).json();
    if (!estado.em_andamento) return;
    await esperar(1000);
  }
  throw new Error('Um treino não terminou em 3 minutos.');
}

// ------------------------------------------------------------ na página
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

/** Só o elemento, com uma margem — a tela inteira dilui o que se quer mostrar. */
async function fotografarElemento(pagina, nome, seletor, margem = 16) {
  const caixa = await pagina.$eval(seletor, (el) => {
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, width: r.width, height: r.height };
  });
  await fotografar(pagina, nome, recorte(caixa, margem));
}

/** Do topo de um elemento ao fim de outro: o aviso e o que ele comenta, juntos. */
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
  await fotografar(pagina, nome, recorte(caixa, margem));
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
  await pagina.setViewport({ width: 1280, height: 1000, deviceScaleFactor: 2 });
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

// -------------------------------------------------------------------- roteiro
async function main() {
  if (!SENHA_ADMIN) throw new Error('Informe GIH_ADMIN_SENHA — ver o cabeçalho deste arquivo.');
  fs.mkdirSync(SAIDA, { recursive: true });

  const admin = await sessaoAdmin();
  const antes = (await (await admin('GET', '/api/modelo')).json()).versao_em_uso;
  if (!antes) throw new Error('O modelo nunca foi treinado nesta base — rode resetar_banco.py.');

  const marca = `t${String(crypto.randomInt(100000)).padStart(5, '0')}`;
  const pessoas = {};
  for (const perfil of ['GESTOR', 'ANALISTA']) {
    const login = `${marca}.${perfil.toLowerCase()}`;
    const senha = crypto.randomBytes(18).toString('base64url');
    const criado = await admin('POST', '/api/usuarios', {
      login, nome: `${perfil === 'GESTOR' ? 'Gestora' : 'Analista'} da Captura`, senha, perfil,
    });
    if (criado.status !== 201) throw new Error(`Não criei o ${perfil} (${criado.status}).`);
    pessoas[perfil] = { login, senha, id: (await criado.json()).id };
  }

  const navegador = await puppeteer.launch({ headless: 'new' });
  try {
    const gestor = await paginaDe(navegador, pessoas.GESTOR.login, pessoas.GESTOR.senha);

    // --------------------------------------------------- a versão em uso
    await ir(gestor, '/modelo', `${VERSAO} .comparacao`);
    await fotografarElemento(gestor, 'fluxo-1-versao-em-uso', VERSAO);

    // ------------------------ o treino: confirmação, andamento, resultado
    /* Uma segunda aba, aberta antes do treino, é "a outra pessoa" do erro 1:
       quando ela pedir, o treino desta já estará rodando. */
    const outraAba = await paginaDe(navegador, pessoas.GESTOR.login, pessoas.GESTOR.senha);
    await ir(outraAba, '/modelo', VERSAO);
    /* A confirmação da outra aba abre antes: o pedido dela sai um clique depois
       do desta, dentro do tempo em que o treino ainda roda (~1 s). */
    await clicar(outraAba, 'Treinar agora');
    await outraAba.waitForSelector('.confirmacao');

    await clicar(gestor, 'Treinar agora');
    await gestor.waitForSelector('.confirmacao');
    await fotografarFaixa(gestor, 'fluxo-2-confirmacao', `${VERSAO} .painel__cabecalho`, '.confirmacao');
    await clicar(gestor, 'Treinar', '.confirmacao');
    await gestor.waitForSelector('.modelo__andamento');
    await clicar(outraAba, 'Treinar', '.confirmacao');
    await outraAba.waitForSelector('.aviso[role="alert"]', { timeout: 15000 });

    await fotografarFaixa(gestor, 'fluxo-3-treinando', '.modelo__andamento', `${VERSAO} .painel__cabecalho`);
    await fotografarFaixa(outraAba, 'erro-1-treino-ja-em-andamento', '.aviso[role="alert"]', `${VERSAO} .painel__cabecalho`);

    await gestor.waitForFunction(() => !document.querySelector('.modelo__andamento'), { timeout: 180000 });
    await gestor.waitForSelector(`${VERSAO} .comparacao`);
    const aviso = (await gestor.$('.aviso--sucesso')) ? '.aviso--sucesso' : '.aviso--informativo';
    await fotografarFaixa(gestor, 'fluxo-4-resultado-do-treino', aviso, VERSAO);
    await fotografarElemento(gestor, 'fluxo-5-historico-de-treinos', 'section.historico-treinos');

    // ------------------------------------------------ previsão no parceiro
    const maior = await gestor.evaluate(async () => {
      const r = await fetch('/api/parceiros?tamanho=1&ordenar_por=faturamento&descendente=true', {
        credentials: 'same-origin',
      });
      return (await r.json()).itens[0].id;
    });
    await gestor.setViewport({ width: 1280, height: 1400, deviceScaleFactor: 2 });
    await ir(gestor, `/parceiros/${maior}`, 'section[aria-labelledby="titulo-previsao"]');
    await gestor.waitForSelector('.grafico__linha--prevista');
    await fotografarElemento(gestor, 'fluxo-6-previsao-no-cadastro', '.cadastro__lateral');
    await fotografarElemento(gestor, 'fluxo-7-serie-com-estimativa', 'section[aria-labelledby="titulo-serie-parceiro"]');

    const curto = await gestor.evaluate(async () => {
      const r = await fetch('/api/parceiros?tamanho=1&segmento=RECEM_CHEGADO', { credentials: 'same-origin' });
      return (await r.json()).itens[0]?.id;
    });
    if (!curto) throw new Error('A base não tem parceiro recém-chegado para o erro 3.');
    await ir(gestor, `/parceiros/${curto}`, 'section[aria-labelledby="titulo-previsao"] .vazio');
    await fotografarElemento(gestor, 'erro-3-parceiro-sem-historico', 'section[aria-labelledby="titulo-previsao"]');

    // ------------------------------------ o analista não abre a tela do modelo
    const analista = await paginaDe(navegador, pessoas.ANALISTA.login, pessoas.ANALISTA.senha);
    await ir(analista, '/modelo', '.aviso[role="alert"]');
    await fotografarElemento(analista, 'erro-2-analista-sem-acesso', '.aviso[role="alert"]');

    for (const p of [gestor, outraAba, analista]) {
      await p.evaluate(() => fetch('/api/sessao', { method: 'DELETE', credentials: 'same-origin' }));
    }
  } finally {
    await navegador.close();
    await esperarTreinos(admin);
    console.log(`\nlimpeza: ${limparExecucao(marca)}`);
    for (const { id } of Object.values(pessoas)) {
      await admin('PATCH', `/api/usuarios/${id}`, { ativo: false });
    }
    const depois = (await (await admin('GET', '/api/modelo')).json()).versao_em_uso;
    console.log(`usuários da captura desativados; versão em uso: ${depois} (antes: ${antes})`);
    if (depois !== antes) process.exitCode = 1;
  }
  console.log('\ncapturas em docs/entrega/evidencias/sprint05/');
}

main().catch((e) => {
  console.error(e.message);
  // `exitCode`, e não `process.exit()`: sair com o navegador ainda fechando
  // derruba o Node no Windows com uma asserção da libuv, que esconde o erro.
  process.exitCode = 1;
});
