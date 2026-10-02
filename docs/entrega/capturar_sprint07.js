/**
 * Captura as evidências da Sprint 07 — o painel com filtros, os relatórios, as
 * pesquisas, a exportação e a trilha de auditoria, como o usuário os vê.
 *
 * O que muda numa tela que já existia só se mostra com o antes ao lado do
 * depois, e o antes precisa ser fotografado **antes** da mudança. Por isso o
 * roteiro tem etapas, rodadas em momentos diferentes:
 *
 *   node docs/entrega/capturar_sprint07.js antes       # o painel, as execuções e os usuários, antes da H82 e da H91
 *   node docs/entrega/capturar_sprint07.js depois      # as mesmas telas, com o recorte, os filtros e a busca
 *   node docs/entrega/capturar_sprint07.js relatorios  # os quatro relatórios, na tela e em PDF
 *   node docs/entrega/capturar_sprint07.js auditoria   # a trilha de auditoria e o histórico do cadastro
 *
 * Cada etapa grava em `evidencias/sprint07/` as capturas com o prefixo dela, e
 * um texto com o que uma captura não mostra: o endereço de cada recorte e o que
 * a tela e a API responderam nele.
 *
 * **O PDF é o da impressão do navegador** (RF48): a etapa `relatorios` chama
 * `page.pdf()`, que imprime a página com a folha `web/src/estilos/impressao.css`,
 * como o "Imprimir ou salvar em PDF" da tela. O arquivo fica em
 * `evidencias/sprint07/`, e a captura `…-folha.png` mostra a primeira página dele.
 *
 * O que é comum a todo roteiro — as três pessoas descartáveis, a foto depois de
 * a página assentar, a limpeza no fim — está em `comum/captura.js`.
 *
 * A API e a interface precisam estar no ar (docker compose up -d), com a base de
 * demonstração e o modelo treinado:
 *   GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint07.js <etapa>
 */
const fs = require('fs');
const path = require('path');

const {
  PARAMETROS, VISOR, calcularPlano, esperar, ir, pelaApi, principal, quebrar,
} = require('./comum/captura');

const SAIDA = path.join(__dirname, 'evidencias', 'sprint07');

/* Três orçamentos, três planos diferentes: o histórico com mais de uma linha. */
const ORCAMENTOS = ['5000.00', '8000.00', '3000.00'];

/* A folha A4 a 96 pontos por polegada, que é como o navegador a mede. */
const FOLHA = { width: 794, height: 1123 };

async function planos(gestor, orcamentos = ORCAMENTOS) {
  const calculados = [];
  for (const orcamento of orcamentos) {
    const plano = await calcularPlano(gestor, { ...PARAMETROS, orcamento });
    if (plano.erro) throw new Error(`O plano da captura não saiu: ${plano.erro}.`);
    calculados.push(plano);
  }
  return calculados;
}

/* O recuo das linhas de continuação nos textos: embaixo do valor, e não do rótulo. */
const RECUO = ' '.repeat(14);

/** As linhas de um registro em texto, quebradas nas 96 colunas do documento. */
const caber = (linhas) => linhas.flatMap((linha) => quebrar(linha, RECUO).split('\n'));

/** O texto de um elemento da tela, sem as quebras — o que a pessoa lê nele. */
async function lerDaTela(pagina, seletor) {
  return pagina.$eval(seletor, (el) => el.textContent.replace(/\s+/g, ' ').trim()).catch(() => '(não está na tela)');
}

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
  await planos(gestor);
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

/**
 * O depois das mesmas telas: o painel com o recorte e com a previsão e a
 * campanha (H82, H83), o histórico de execuções com os filtros e a lista de
 * usuários com a busca (H91), e o plano com as duas saídas.
 */
async function depois({ gestor, administrador, fotografar, fotografarElemento, gravar }) {
  const [primeiro] = await planos(gestor);
  // Uma inviável, para o filtro de resultado ter o que separar.
  await calcularPlano(gestor, { ...PARAMETROS, orcamento: '10.00', cota_cauda_longa: '1' });
  const linhas = ['Pesquisas e filtros — o endereço de cada recorte, e o que a tela e a API responderam', ''];
  const anotar = (texto) => linhas.push(texto);

  await ir(gestor, '/', 'section[aria-labelledby="titulo-proximo-periodo"] table');
  await fotografar(gestor, 'depois-painel', { fullPage: true });
  await fotografarElemento(gestor, 'depois-painel-decisao', '.painel-duplo:has(#titulo-proximo-periodo)');

  // O recorte: um período que não é o mais recente, numa categoria.
  const recortes = (await pelaApi(gestor, 'GET', '/api/painel/recortes')).dados;
  const periodo = recortes.periodos[3];
  const categoria = recortes.categorias.find((c) => c.nome === 'Padaria') ?? recortes.categorias[0];
  const endereco = `/?periodo=${periodo.id}&categoria=${categoria.id}`;
  await ir(gestor, endereco, 'section[aria-labelledby="titulo-ranking"] table');
  await fotografarElemento(gestor, 'depois-painel-recorte', 'main.pagina', 0, 1180);
  await fotografarElemento(gestor, 'depois-painel-ranking-da-categoria', 'section[aria-labelledby="titulo-ranking"]', 16, 420);
  const indicadores = (await pelaApi(gestor, 'GET',
    `/api/painel/indicadores?periodo_id=${periodo.id}&categoria_id=${categoria.id}`)).dados;
  anotar(`Painel — período de ${periodo.data_inicio} a ${periodo.data_fim}, categoria ${categoria.nome}`);
  anotar(`  endereço    ${endereco}`);
  anotar(`  na tela     ${await lerDaTela(gestor, '.recorte__nota')}`);
  anotar(`              ranking: ${await lerDaTela(gestor, 'section[aria-labelledby="titulo-ranking"] .painel__nota')}`);
  anotar(`  na API      faturamento ${indicadores.faturamento} · ${indicadores.pedidos} pedidos · `
    + `${indicadores.parceiros_ativos} parceiros · categoria ${indicadores.categoria.nome}`);
  anotar('');

  await gestor.setViewport({ ...VISOR, width: 1600 });
  await ir(gestor, '/execucoes', 'section[aria-labelledby="titulo-execucoes"] table');
  await fotografarElemento(gestor, 'depois-execucoes', 'main.pagina', 0);
  for (const [nome, consulta] of [
    ['depois-execucoes-viaveis', 'resultado=VIAVEL'],
    ['depois-execucoes-inviaveis', 'resultado=INVIAVEL'],
  ]) {
    await ir(gestor, `/execucoes?${consulta}`, 'section[aria-labelledby="titulo-execucoes"] table');
    await fotografarElemento(gestor, nome, 'main.pagina', 0);
    const lista = (await pelaApi(gestor, 'GET', `/api/otimizacoes?${consulta}&tamanho=50`)).dados;
    anotar(`Execuções — ${consulta}`);
    anotar(`  endereço    /execucoes?${consulta}`);
    anotar(`  na tela     ${await lerDaTela(gestor, 'section[aria-labelledby="titulo-execucoes"] .painel__nota')}`);
    anotar(`  na API      ${lista.total} execuções; viáveis: ${lista.itens.filter((e) => e.viavel === true).length}, `
      + `inviáveis: ${lista.itens.filter((e) => e.viavel === false).length}`);
    anotar('');
  }
  await gestor.setViewport(VISOR);

  await ir(gestor, `/execucoes/${primeiro.id}`, 'section[aria-labelledby="titulo-pedido"]');
  await fotografarElemento(gestor, 'depois-execucao', 'main.pagina', 0, 560);

  for (const [nome, consulta, altura] of [
    ['depois-usuarios-busca', 'ativo=false&busca=captura', 560],
    ['depois-usuarios-sem-acento', 'ativo=todas&busca=verificacao', 460],
  ]) {
    await ir(administrador, `/usuarios?${consulta}`, 'section[aria-labelledby="titulo-usuarios"] table');
    await fotografarElemento(administrador, nome, 'main.pagina', 0, altura);
    const busca = new URLSearchParams(consulta);
    const ativo = busca.get('ativo') === 'todas' ? '' : `&ativo=${busca.get('ativo')}`;
    const lista = (await pelaApi(administrador, 'GET', `/api/usuarios?busca=${busca.get('busca')}${ativo}`)).dados;
    anotar(`Usuários — ${consulta}`);
    anotar(`  endereço    /usuarios?${consulta}`);
    anotar(`  na tela     ${await lerDaTela(administrador, 'section[aria-labelledby="titulo-usuarios"] .painel__nota')}`);
    anotar(`  na API      ${lista.length} usuários; o primeiro: ${lista[0]?.nome ?? '—'}`);
    anotar('');
  }

  gravar('recortes.txt', caber(linhas));
}

/** Quantas páginas tem um PDF gerado pelo navegador: uma por objeto de página. */
function paginasDoPdf(arquivo) {
  return (fs.readFileSync(arquivo, 'latin1').match(/\/Type\s*\/Page\b(?!s)/g) ?? []).length;
}

/**
 * O relatório como a tela o mostra, o PDF que a impressão do navegador gera, e
 * a primeira página dele.
 */
async function relatorioEmPdf(pagina, nome, { fotografar, anotar }) {
  await fotografar(pagina, nome, { fullPage: true });

  const arquivo = path.join(SAIDA, `${nome}.pdf`);
  await pagina.pdf({ path: arquivo, format: 'A4' });
  const csv = await pagina.$eval('a[download]', (a) => a.getAttribute('href')).catch(() => null);
  anotar(`${await lerDaTela(pagina, '.relatorio__titulo')}`);
  anotar(`  endereço    ${new URL(pagina.url()).pathname}${new URL(pagina.url()).search}`);
  anotar(`  recorte     ${await lerDaTela(pagina, '.relatorio__recorte')}`);
  anotar(`  PDF         ${nome}.pdf — ${paginasDoPdf(arquivo)} página(s), `
    + `${Math.round(fs.statSync(arquivo).size / 1024)} kB, pela impressão do navegador`);
  if (csv) {
    const baixado = await pagina.evaluate(async (c) => {
      const r = await fetch(c, { credentials: 'same-origin' });
      return { status: r.status, nome: r.headers.get('content-disposition'), linhas: (await r.text()).trim().split('\r\n').length };
    }, csv);
    anotar(`  CSV         ${csv}`);
    anotar(`              ${baixado.status} · ${baixado.nome} · ${baixado.linhas - 1} linhas além do cabeçalho`);
  }

  /* A folha: a mesma página, com a mídia de impressão, na largura do A4 e com as
     margens do `@page` — é o que o PDF tem na primeira página. Uma captura não
     dispara o evento de impressão, que é quem põe a folha no tema claro
     (`web/src/temas/impressao.js`). E, no Puppeteer, emular a mídia desfaz a
     emulação do tema, e emular o tema desfaz a da mídia: a primeira versão
     desta figura saiu no tema escuro da máquina, e a segunda, com o menu da
     tela. As duas vão juntas, num comando só do protocolo do navegador. */
  const protocolo = await pagina.createCDPSession();
  const emular = (media) => protocolo.send('Emulation.setEmulatedMedia', {
    media, features: [{ name: 'prefers-color-scheme', value: 'light' }],
  });
  await emular('print');
  await pagina.addStyleTag({ content: '@media print { body { padding: 14mm 12mm !important; } }' });
  await pagina.setViewport({ ...FOLHA, deviceScaleFactor: 2 });
  await esperar(300);
  await pagina.screenshot({
    path: path.join(SAIDA, `${nome}-folha.png`),
    clip: { x: 0, y: 0, width: FOLHA.width, height: FOLHA.height },
  });
  console.log(`${`${nome}-folha`.padEnd(36)} ok`);
  await emular('');
  await protocolo.detach();
  await pagina.setViewport(VISOR);
  anotar('');
}

/**
 * Os quatro relatórios (H84 a H88): a lista, cada um na tela, o PDF de cada um
 * e o CSV que o link da tela baixa.
 */
async function relatorios({ gestor, administrador, fotografar, fotografarElemento, gravar }) {
  const [plano] = await planos(gestor, ['5000.00']);
  const linhas = ['Relatórios — o endereço, o recorte que a folha diz, o PDF e o CSV de cada um', ''];
  const contexto = { fotografar, anotar: (texto) => linhas.push(texto) };

  await ir(gestor, '/relatorios', '.relatorios');
  await fotografarElemento(gestor, 'relatorios-lista', 'main.pagina', 0);

  await ir(gestor, '/relatorios/desempenho', '#titulo-por-segmento');
  await relatorioEmPdf(gestor, 'relatorio-desempenho', contexto);

  // Filtrado pelo segmento: o total e as categorias passam a ser dos mesmos parceiros.
  await ir(gestor, '/relatorios/desempenho?segmento=EM_RISCO', '#titulo-por-segmento');
  await fotografarElemento(gestor, 'relatorio-desempenho-em-risco', 'main.pagina', 0, 900);

  // A partir de 90%: cabe numa página, e mostra a ação de quem está no plano.
  await ir(gestor, '/relatorios/risco?risco_minimo=90', '#titulo-parceiros-risco');
  await relatorioEmPdf(gestor, 'relatorio-risco', contexto);

  // Os recém-chegados: quem não tem previsão aparece com o motivo (RN09).
  await ir(gestor, '/relatorios/risco?segmento=RECEM_CHEGADO', '#titulo-parceiros-risco');
  await fotografarElemento(gestor, 'relatorio-risco-sem-previsao', 'section[aria-labelledby="titulo-parceiros-risco"]', 16, 420);

  await ir(gestor, `/relatorios/campanha?execucao=${plano.id}`, '#titulo-por-segmento');
  await relatorioEmPdf(gestor, 'relatorio-campanha', contexto);

  await ir(administrador, '/relatorios/operacoes', '#titulo-por-dia');
  // A página inteira tem mais de duas telas de altura: no documento, ela ficaria
  // do tamanho de um selo. Os dois recortes são o que se lê — o começo, com o
  // total, e as pessoas, com a linha das outras.
  await fotografarElemento(administrador, 'relatorio-operacoes-topo', 'main.pagina', 0, 900);
  await fotografarElemento(administrador, 'relatorio-operacoes-pessoas', 'section[aria-labelledby="titulo-por-usuario"]');
  await relatorioEmPdf(administrador, 'relatorio-operacoes', contexto);

  /* O plano de uma execução, pela mesma folha (H91). */
  await ir(gestor, `/execucoes/${plano.id}`, 'section[aria-labelledby="titulo-pedido"]');
  const arquivo = path.join(SAIDA, 'plano.pdf');
  await gestor.pdf({ path: arquivo, format: 'A4' });
  linhas.push('Plano de campanha, pela execução');
  linhas.push(`  endereço    /execucoes/${plano.id}`);
  linhas.push(`  PDF         plano.pdf — ${paginasDoPdf(arquivo)} página(s), pela impressão do navegador`);
  linhas.push(`  CSV         /api/otimizacoes/${plano.id}/exportacao.csv — ${plano.itens.length} itens e o total`);
  console.log(`${'plano.pdf'.padEnd(36)} ok`);

  gravar('relatorios-em-pdf.txt', caber(linhas));
}

/**
 * A trilha de auditoria na tela (H89) e o histórico no cadastro do parceiro
 * (H90). Um gestor cadastra e altera um parceiro; o administrador o acha na
 * trilha pela busca.
 */
async function auditoria({ gestor, administrador, marca, fotografar, fotografarElemento, gravar }) {
  await ir(gestor, '/parceiros', 'table');
  const categorias = (await pelaApi(gestor, 'GET', '/api/categorias')).dados;
  const criado = await pelaApi(gestor, 'POST', '/api/parceiros', {
    nome: `Empório ${marca}`, categoria_id: categorias[0].id, contato: 'contato@exemplo.test',
  });
  if (criado.status !== 201) throw new Error(`O parceiro da captura não foi criado (${criado.status}).`);
  const { id } = criado.dados;
  for (const corpo of [
    { nome: `Empório Central ${marca}`, contato: 'compras@exemplo.test' },
    { categoria_id: categorias[1].id },
    { ativo: false },
    { ativo: true },
  ]) {
    const r = await pelaApi(gestor, 'PATCH', `/api/parceiros/${id}`, corpo);
    if (r.status !== 200) throw new Error(`A alteração do parceiro respondeu ${r.status}.`);
  }

  await ir(gestor, `/parceiros/${id}`, 'section[aria-labelledby="titulo-historico-cadastro"] li');
  await fotografarElemento(gestor, 'historico-do-cadastro', 'section[aria-labelledby="titulo-historico-cadastro"]');

  await ir(administrador, '/auditoria', 'table');
  await fotografar(administrador, 'auditoria-tela');

  // A busca pela marca desta captura: o que as três pessoas dela fizeram.
  const busca = `/auditoria?busca=${marca}`;
  await ir(administrador, busca, 'table');
  await administrador.click('details.auditoria__gravado summary');
  await fotografar(administrador, 'auditoria-busca', { fullPage: true });

  await ir(administrador, '/auditoria?acao=LOGIN_FALHA', 'main.pagina');
  await esperar(600);
  await fotografarElemento(administrador, 'auditoria-entradas-recusadas', 'main.pagina', 0, 760);

  const lista = (await pelaApi(administrador, 'GET', `/api/auditoria?busca=${marca}`)).dados;
  const historico = (await pelaApi(gestor, 'GET', `/api/parceiros/${id}/historico`)).dados;
  const linhas = [
    'Trilha de auditoria e histórico do cadastro — o que a tela e a API responderam',
    '',
    'A trilha, buscando pela marca desta captura',
    `  endereço    ${busca}`,
    `  na API      ${lista.total} registros`,
    ...lista.itens.map((r) => `              ${r.rotulo} · ${r.autor} · ${r.resumo || '—'}`),
    '',
    'O histórico, no cadastro do parceiro',
    `  endereço    /parceiros/${id}`,
    `  na API      ${historico.length} eventos, do mais recente ao mais antigo`,
    ...historico.map((e) => `              ${e.rotulo} · por ${e.autor}${e.resumo ? ` · ${e.resumo}` : ''}`),
  ];
  gravar('auditoria.txt', caber(linhas));
}

principal({ antes, depois, relatorios, auditoria }, SAIDA, 'sprint07');
