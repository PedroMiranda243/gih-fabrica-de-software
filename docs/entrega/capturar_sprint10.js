/**
 * Captura as evidências da Sprint 10 — a Release Candidate — que nenhum outro
 * roteiro tira:
 *
 *   node docs/entrega/capturar_sprint10.js api      # a documentação da API no Swagger
 *   node docs/entrega/capturar_sprint10.js escuro   # a interface final no tema escuro
 *
 * O fluxo principal de ponta a ponta (importar, painel, modelo, campanha,
 * mensagens, aprovação, relatório) não está aqui: ele sai das capturas do
 * executor dos casos de teste (`scripts/testar_na_tela.py`), copiadas para a
 * pasta da sprint na rodada final. E a interface no tema claro, a 768 e a
 * 1440 px, sai do `scripts/medir_telas.py`.
 *
 * **A etapa `api` abre o Swagger como quem avalia o abre**: a visão geral, com a
 * versão e o que vale para toda rota; uma rota aberta, com os perfis, o exemplo
 * do corpo e as respostas de erro; e a sessão (o cadeado), que é como a API
 * reconhece quem chama. O Swagger carrega o próprio código de uma CDN: a máquina
 * precisa de internet.
 *
 * A API e a interface precisam estar no ar (docker compose up -d), com a base de
 * demonstração:
 *   GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint10.js <etapa>
 */
const fs = require('fs');
const path = require('path');
const { VISOR, esperar, ir, principal } = require('./comum/captura');

const SAIDA = path.join(__dirname, 'evidencias', 'sprint10');
const API = process.env.GIH_URL || 'http://localhost:8000';

/* A rota que a figura abre: tem corpo com exemplo, perfis e os erros de toda
   rota protegida — 401, 403, 409 e o 422 no formato da API. */
const ROTA = { metodo: 'post', caminho: '/api/parceiros' };

/** O Swagger, a visão geral, uma rota aberta e a sessão. */
async function api({ gestor, fotografar, fotografarElemento, gravar }) {
  const pagina = await gestor.browserContext().newPage();
  await pagina.setViewport(VISOR);
  await pagina.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }]);
  await pagina.goto(`${API}/api/docs`, { waitUntil: 'networkidle0' });
  await pagina.waitForSelector('.swagger-ui .information-container', { timeout: 30000 });
  await esperar(800);

  // 1. A visão geral: o título, a versão e a descrição — a sessão, os perfis, os erros.
  await fotografarElemento(pagina, 'api-1-visao-geral', '.swagger-ui .information-container', 12, 1300);
  const info = await pagina.$eval('.swagger-ui .info', (el) => el.innerText.split('\n').slice(0, 2).join(' · '));

  // 2. Uma rota aberta: os perfis na descrição, o exemplo do corpo e as respostas.
  /* O bloco da rota, achado pelo caminho: o Swagger redesenha o bloco ao abri-lo,
     e uma marca posta nele antes do clique se perderia. */
  const marcar = (s, c) => {
    const bloco = [...document.querySelectorAll(s)]
      .find((b) => b.querySelector('.opblock-summary-path')?.getAttribute('data-path') === c);
    if (bloco) bloco.id = 'rota-da-figura';
    return bloco ? bloco.querySelector('.opblock-summary-description')?.innerText ?? '' : null;
  };
  const seletor = `.opblock-${ROTA.metodo}`;
  const aberta = await pagina.evaluate(marcar, seletor, ROTA.caminho);
  if (aberta === null) throw new Error(`O Swagger não tem ${ROTA.metodo.toUpperCase()} ${ROTA.caminho}.`);
  // Quem abre e fecha a rota é o botão do resumo; o div em volta dele não faz nada.
  await pagina.click('#rota-da-figura .opblock-summary-control');
  await pagina.waitForFunction(
    (s, c) => [...document.querySelectorAll(`${s}.is-open`)]
      .some((b) => b.querySelector('.opblock-summary-path')?.getAttribute('data-path') === c
        && b.querySelector('.responses-wrapper')),
    { timeout: 15000 }, seletor, ROTA.caminho,
  );
  await pagina.evaluate(marcar, `${seletor}.is-open`, ROTA.caminho);
  await esperar(600);
  await fotografarElemento(pagina, 'api-2-rota-aberta', '#rota-da-figura', 8, 2600);
  const respostas = await pagina.$$eval(
    '#rota-da-figura .responses-table tr.response', (linhas) => linhas.map((l) => l.getAttribute('data-code')),
  );

  // 3. A sessão: o cadeado, com o cookie que a API lê.
  await pagina.click('.swagger-ui .auth-wrapper .authorize');
  await pagina.waitForSelector('.swagger-ui .dialog-ux .modal-ux', { timeout: 10000 });
  await esperar(500);
  await fotografarElemento(pagina, 'api-3-sessao', '.swagger-ui .dialog-ux .modal-ux', 8);
  const sessao = await pagina.$eval('.swagger-ui .dialog-ux .modal-ux-content', (el) => el.innerText.replace(/\s*\n\s*/g, ' · '));
  await pagina.close();

  gravar('api.txt', [
    'A documentação da API no Swagger — o que cada figura mostra',
    '',
    `endereço    ${API}/api/docs`,
    `visão geral ${info}`,
    `rota aberta ${ROTA.metodo.toUpperCase()} ${ROTA.caminho} — ${aberta}`,
    `respostas   ${respostas.join(', ')}`,
    `sessão      ${sessao}`,
  ]);
}

/* As telas da galeria no tema escuro: as que mais carregam o sistema visual. */
const ESCURAS = [
  ['escuro-painel', '/', 'section[aria-labelledby="titulo-indicadores"]'],
  ['escuro-campanha', '/campanha', 'section[aria-labelledby="t-restricoes"]'],
  ['escuro-relatorio-risco', '/relatorios/risco', 'article.folha'],
];

/** A interface final no tema escuro: o tema é o do sistema, e a pessoa escolhe. */
async function escuro({ gestor, fotografar }) {
  await gestor.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'dark' }]);
  for (const [nome, caminho, seletor] of ESCURAS) {
    await ir(gestor, caminho, seletor);
    await gestor.waitForFunction(() => !document.querySelector('[aria-busy="true"]'), { timeout: 30000 });
    await esperar(600);
    await fotografar(gestor, nome);
  }
}

fs.mkdirSync(SAIDA, { recursive: true });
principal({ api, escuro }, SAIDA, 'sprint10');
