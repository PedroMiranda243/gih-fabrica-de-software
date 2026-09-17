/**
 * Captura as telas do protótipo navegável para o documento de entrega.
 *
 * O protótipo é uma página só, com quatro seções alternadas pelo trilho lateral.
 * Este script abre a página, clica em cada tela e salva a captura — em vez de
 * alguém tirar print à mão e esquecer de refazer quando a tela mudar.
 *
 * Usa o Chromium que já veio com o `mermaid-cli`; nenhuma dependência nova.
 *
 * Uso:  node docs/entrega/capturar_prototipo.js
 */
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const RAIZ = path.join(__dirname, '..', '..');
const PROTOTIPO = path.join(RAIZ, 'docs', 'prototipo', 'index.html');
const SAIDA = path.join(RAIZ, 'docs', 'prototipo', 'telas');

// 1280 de largura é o desktop que o protótipo foi desenhado para ocupar; o
// `deviceScaleFactor` dobra a densidade para a captura aguentar impressão.
const JANELA = { width: 1280, height: 900, deviceScaleFactor: 2 };

const TELAS = [
  ['painel', 'Painel — indicadores, gráficos e ranking de parceiros'],
  ['importar', 'Importação — período obrigatório e prévia antes de gravar'],
  ['campanha', 'Campanha — restrições, benchmark e plano recomendado'],
  ['aprovacao', 'Aprovação — fila de mensagens pendentes de decisão humana'],
];

async function main() {
  if (!fs.existsSync(PROTOTIPO)) {
    console.error(`Protótipo não encontrado em ${PROTOTIPO}`);
    process.exit(1);
  }
  fs.mkdirSync(SAIDA, { recursive: true });

  const navegador = await puppeteer.launch({ headless: 'new' });
  try {
    const pagina = await navegador.newPage();
    await pagina.setViewport(JANELA);
    await pagina.goto(`file://${PROTOTIPO.replace(/\\/g, '/')}`, { waitUntil: 'networkidle0' });

    for (const [tela, descricao] of TELAS) {
      await pagina.click(`button[data-tela="${tela}"]`);

      // A troca de tela tem transição; capturar antes dela terminar pega a
      // seção anterior desaparecendo por cima da nova.
      await new Promise((r) => setTimeout(r, 400));

      // Confere que a seção certa está de fato visível. O atributo `hidden` tem
      // especificidade baixíssima em CSS e uma classe com `display` o anula —
      // já houve teste "passando" com a tela errada na frente do usuário.
      const visivel = await pagina.evaluate((id) => {
        const alvo = document.getElementById(id);
        return alvo ? getComputedStyle(alvo).display !== 'none' : false;
      }, tela);
      if (!visivel) {
        throw new Error(`A tela "${tela}" não ficou visível depois do clique.`);
      }

      const destino = path.join(SAIDA, `${tela}.png`);
      await pagina.screenshot({ path: destino, fullPage: true });
      console.log(`${tela.padEnd(10)} ${descricao}`);
    }
  } finally {
    await navegador.close();
  }

  console.log(`\n${TELAS.length} telas capturadas em docs/prototipo/telas/`);
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
