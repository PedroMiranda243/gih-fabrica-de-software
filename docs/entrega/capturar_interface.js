/**
 * Captura as telas da interface para o documento de entrega.
 *
 * São evidência de funcionalidade **implementada**: cada tela aqui consome a
 * API real, sobre o banco real. O enunciado da Sprint 03 recusa "imagens de
 * telas de funcionalidades que ainda não foram implementadas" — por isso a
 * captura é da aplicação no ar, e não do protótipo.
 *
 * Usa o Chromium que já veio com o `mermaid-cli`; nenhuma dependência nova.
 *
 * **Nenhuma senha é digitada em formulário.** A tela de login é capturada vazia;
 * para as demais, o script autentica pela API, com `fetch` para `/api/sessao`
 * dentro da página — o mesmo caminho que a verificação de ponta a ponta usa.
 * As credenciais vêm do ambiente, de um usuário descartável:
 *
 *   docker compose exec -T -e GIH_SENHA_NOVA=... api \
 *       python -m app.cli criar-usuario --login captura --nome "..." --perfil GESTOR
 *   GIH_CAPTURA_LOGIN=captura GIH_CAPTURA_SENHA=... node docs/entrega/capturar_interface.js
 *
 * Captura em **modo claro**, que é o que imprime com contraste no PDF.
 */
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const URL = process.env.GIH_WEB_URL || 'http://localhost:5173';
const LOGIN = process.env.GIH_CAPTURA_LOGIN;
const SENHA = process.env.GIH_CAPTURA_SENHA;
/* A Sprint 03 capturou estas telas, e a Parte III as lê daqui. Rodar de novo
   reescreve o retrato de uma entrega já feita — só faz sentido para corrigir a
   própria Parte III. Ver `comum/evidencias.js`. */
const SAIDA = path.join(__dirname, 'evidencias', 'sprint03');

/* Termo que demonstra a busca sem acento **com os dados que o gerador produz**:
   "praca" acha "Casa da Praça". A primeira escolha foi "comercio", e o gerador
   não tem nenhum "Comércio" — a captura sairia no estado vazio. */
const BUSCA = 'praca';

/* Relatório sintético para a prévia, com uma linha ruim de propósito: é ela que
   mostra a rejeição com o motivo, que é o que a prévia existe para mostrar. */
const RELATORIO = [
  'Parceiro;Faturamento;Pedidos',
  'Casa da Praça;4210,55;98',
  'Espaço Azul;7730,10;140',
  'Empório Bom Prato;abacaxi;38',
  'Quiosque do Porto;1890,00;52',
].join('\n');

async function esperar(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Preenche um campo controlado pelo React.
 *
 * Atribuir `value` direto não dispara o `onChange` — o React guarda o valor
 * anterior e ignora a mudança. O setter nativo do protótipo, seguido de um
 * evento `input`, é o que o React escuta.
 */
async function preencher(pagina, seletor, valor) {
  await pagina.$eval(
    seletor,
    (el, v) => {
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    },
    valor,
  );
}

/**
 * Fotografa a página até o fim da N-ésima linha da tabela.
 *
 * Tabela longa inteira vira figura altíssima, que no PDF encolhe até ficar
 * ilegível; cortada na altura da janela, sai com uma linha pela metade, o que
 * no documento parece descuido. Cortar na borda de uma linha resolve os dois.
 */
async function fotografarAteLinha(pagina, nome, linhas) {
  const fim = await pagina.$$eval(
    '.tabela tbody tr',
    (trs, n) => {
      const alvo = trs[Math.min(n, trs.length) - 1];
      const caixa = alvo.getBoundingClientRect();
      return Math.ceil(caixa.bottom + window.scrollY);
    },
    linhas,
  );
  const largura = await pagina.evaluate(() => document.documentElement.clientWidth);
  /* `clip` e `fullPage` são mutuamente exclusivos no Puppeteer; o que deixa o
     recorte passar da janela visível é `captureBeyondViewport`. */
  await fotografar(pagina, nome, {
    captureBeyondViewport: true,
    // Um pixel, e não uma folga: qualquer sobra mostra o topo da linha
    // seguinte, que é justamente o que o recorte existe para evitar.
    clip: { x: 0, y: 0, width: largura, height: fim + 1 },
  });
}

async function fotografar(pagina, nome, opcoes = {}) {
  await esperar(400); // transições de 180 ms terminadas
  await pagina.screenshot({ path: path.join(SAIDA, `${nome}.png`), ...opcoes });
  console.log(`${nome.padEnd(24)} ok`);
}

async function main() {
  if (!LOGIN || !SENHA) {
    throw new Error('Informe GIH_CAPTURA_LOGIN e GIH_CAPTURA_SENHA — ver o cabeçalho deste arquivo.');
  }
  fs.mkdirSync(SAIDA, { recursive: true });

  const navegador = await puppeteer.launch({ headless: 'new' });
  try {
    const pagina = await navegador.newPage();
    await pagina.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }]);
    await pagina.setViewport({ width: 1280, height: 820, deviceScaleFactor: 2 });

    // ------------------------------------------------------------ login
    try {
      await pagina.goto(`${URL}/entrar`, { waitUntil: 'networkidle0', timeout: 30000 });
    } catch {
      throw new Error(`A interface não respondeu em ${URL}. Suba com: docker compose up -d`);
    }
    await pagina.waitForSelector('#login');
    await fotografar(pagina, 'interface-login');

    const status = await pagina.evaluate(
      async (login, senha) => {
        const r = await fetch('/api/sessao', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ login, senha }),
        });
        return r.status;
      },
      LOGIN,
      SENHA,
    );
    if (status !== 201) throw new Error(`A autenticação respondeu ${status}.`);

    // ------------------------------------------------------------ painel
    await pagina.setViewport({ width: 1280, height: 1180, deviceScaleFactor: 2 });
    await pagina.goto(`${URL}/`, { waitUntil: 'networkidle0' });
    await pagina.waitForSelector('.indicadores .indicador');
    await pagina.waitForSelector('.tabela tbody tr');
    await pagina.waitForSelector('.grafico__linha');
    await fotografarAteLinha(pagina, 'interface-painel', 8);

    // -------------------------------------------------------- importação
    await pagina.setViewport({ width: 1280, height: 900, deviceScaleFactor: 2 });
    await pagina.goto(`${URL}/importacao`, { waitUntil: 'networkidle0' });
    await pagina.waitForSelector('#texto');
    /* Período ainda não importado: a prévia não grava nada, e um período já
       existente mostraria outra coisa que não o fluxo principal. */
    await preencher(pagina, '#inicio', '2026-09-14');
    await preencher(pagina, '#fim', '2026-09-20');
    await preencher(pagina, '#texto', RELATORIO);
    await pagina.click('button[type=submit]');
    await pagina.waitForSelector('#titulo-previa', { timeout: 15000 });
    await fotografar(pagina, 'interface-importacao', { fullPage: true });

    // --------------------------------------------------------- parceiros
    await pagina.goto(`${URL}/parceiros?busca=${BUSCA}`, { waitUntil: 'networkidle0' });
    await pagina.waitForSelector('.tabela tbody tr', { timeout: 15000 });
    const linhas = await pagina.$$eval('.tabela tbody tr', (l) => l.length);
    if (!linhas) throw new Error(`A busca por "${BUSCA}" não encontrou nada.`);
    await fotografarAteLinha(pagina, 'interface-parceiros', 12);
    console.log(`  busca "${BUSCA}": ${linhas} parceiros`);

    await pagina.evaluate(() => fetch('/api/sessao', { method: 'DELETE', credentials: 'same-origin' }));
  } finally {
    await navegador.close();
  }
  console.log('\ncapturas em docs/entrega/evidencias/sprint03/');
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
