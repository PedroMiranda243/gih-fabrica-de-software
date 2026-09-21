/**
 * Captura a documentação interativa da API para o documento de entrega.
 *
 * A especificação do FastAPI em `/api/docs` é a superfície do sistema: mostra
 * todos os endereços, agrupados por assunto, com os corpos de entrada e saída.
 * Serve de evidência do que existe, e é por onde a demonstração acontece.
 *
 * Usa o Chromium que já veio com o `mermaid-cli`; nenhuma dependência nova.
 *
 * A API precisa estar no ar:  docker compose up -d
 *
 * Uso:  node docs/entrega/capturar_evidencias.js
 */
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const URL = process.env.GIH_URL || 'http://localhost:8000';
/* A Sprint 03 capturou estas telas, e a Parte III as lê daqui. Rodar de novo
   reescreve o retrato de uma entrega já feita — só faz sentido para corrigir a
   própria Parte III. Ver `comum/evidencias.js`. */
const SAIDA = path.join(__dirname, 'evidencias', 'sprint03');
const JANELA = { width: 1280, height: 900, deviceScaleFactor: 2 };

async function esperar(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function main() {
  fs.mkdirSync(SAIDA, { recursive: true });

  const navegador = await puppeteer.launch({ headless: 'new' });
  try {
    const pagina = await navegador.newPage();
    await pagina.setViewport(JANELA);

    try {
      await pagina.goto(`${URL}/api/docs`, { waitUntil: 'networkidle0', timeout: 20000 });
    } catch (e) {
      throw new Error(`A API não respondeu em ${URL}. Suba com: docker compose up -d`);
    }

    // O Swagger monta a lista depois de buscar a especificação; sem esperar por
    // um bloco de operação, a captura sai com a página ainda vazia.
    await pagina.waitForSelector('.opblock', { timeout: 20000 });
    await esperar(600);

    const operacoes = await pagina.$$eval('.opblock', (n) => n.length);
    if (!operacoes) throw new Error('A documentação carregou sem nenhuma operação.');

    // O bloco de esquemas dobra a altura da página e, reduzido para caber em
    // A4, deixaria a lista de endereços ilegível. O contrato de entrada e saída
    // aparece na captura seguinte, aberto e em tamanho de leitura.
    await pagina.evaluate(() => {
      const esquemas = document.querySelector('section.models');
      if (esquemas) esquemas.remove();
    });
    await esperar(200);

    await pagina.screenshot({ path: path.join(SAIDA, 'swagger-geral.png'), fullPage: true });
    console.log(`swagger-geral       ${operacoes} operações`);

    // Abre a primeira operação de parceiros, para a captura mostrar o contrato
    // de entrada e saída, e não apenas a lista de endereços.
    const abriu = await pagina.evaluate(() => {
      const alvo = [...document.querySelectorAll('.opblock-summary-path')]
        .find((e) => e.getAttribute('data-path') === '/api/parceiros');
      if (!alvo) return false;
      alvo.click();
      return true;
    });

    if (abriu) {
      await esperar(700);
      const bloco = await pagina.$('#operations-parceiros-listar_api_parceiros_get')
        || await pagina.$('.opblock.is-open');
      if (bloco) {
        await bloco.screenshot({ path: path.join(SAIDA, 'swagger-parceiros.png') });
        console.log('swagger-parceiros   contrato de listagem de parceiros');
      }
    } else {
      console.log('swagger-parceiros   não encontrei /api/parceiros na documentação');
    }
  } finally {
    await navegador.close();
  }

  console.log('\nevidências em docs/entrega/evidencias/sprint03/');
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
