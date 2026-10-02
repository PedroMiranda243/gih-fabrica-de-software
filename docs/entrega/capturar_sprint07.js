/**
 * Captura as evidências da Sprint 07 — o painel com filtros, os relatórios, as
 * pesquisas, a exportação e a trilha de auditoria, como o usuário os vê.
 *
 * O que muda numa tela que já existia só se mostra com o antes ao lado do
 * depois, e o antes precisa ser fotografado **antes** da mudança. Por isso o
 * roteiro tem etapas, rodadas em momentos diferentes:
 *
 *   node docs/entrega/capturar_sprint07.js antes   # o painel, as execuções e os usuários, antes da H82 e da H91
 *
 * As outras etapas entram com as telas delas.
 *
 * O que é comum a todo roteiro — as três pessoas descartáveis, a foto depois de
 * a página assentar, a limpeza no fim — está em `comum/captura.js`.
 *
 * A API e a interface precisam estar no ar (docker compose up -d), com a base de
 * demonstração e o modelo treinado:
 *   GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint07.js <etapa>
 */
const path = require('path');

const { PARAMETROS, VISOR, calcularPlano, ir, principal } = require('./comum/captura');

const SAIDA = path.join(__dirname, 'evidencias', 'sprint07');

/* Três orçamentos, três planos diferentes: o histórico com mais de uma linha. */
const ORCAMENTOS = ['5000.00', '8000.00', '3000.00'];

/**
 * O antes: o painel que abre sempre no período mais recente, sem escolha de
 * período nem de categoria (H82) e só com o módulo 1 (H83); o histórico de
 * execuções e a lista de usuários sem filtro nem busca (H91).
 */
async function antes({ gestor, administrador, fotografar, fotografarElemento }) {
  await ir(gestor, '/', 'section[aria-labelledby="titulo-ranking"] table');
  await fotografar(gestor, 'antes-painel', { fullPage: true });
  await fotografarElemento(gestor, 'antes-painel-topo', '.indicadores', 16);

  // Três execuções do gestor da captura, para o histórico não depender do que já há na base.
  for (const orcamento of ORCAMENTOS) {
    const plano = await calcularPlano(gestor, { ...PARAMETROS, orcamento });
    if (plano.erro) throw new Error(`O plano da captura não saiu: ${plano.erro}.`);
  }
  // A tabela tem sete colunas, e a 1.280 px a última fica atrás da rolagem dela.
  await gestor.setViewport({ ...VISOR, width: 1600 });
  await ir(gestor, '/execucoes', 'section[aria-labelledby="titulo-execucoes"] table');
  await fotografarElemento(gestor, 'antes-execucoes', 'main.pagina', 0);
  await gestor.setViewport(VISOR);

  /* Os desativados: são as contas que as verificações deixam, e é nessa lista,
     que só cresce, que a busca faz falta. A conta de quem usa a base de
     demonstração na máquina fica de fora da figura. */
  await ir(administrador, '/usuarios?ativo=false', 'section[aria-labelledby="titulo-usuarios"] table');
  await fotografarElemento(administrador, 'antes-usuarios', 'main.pagina', 0, 640);
}

principal({ antes }, SAIDA, 'sprint07');
