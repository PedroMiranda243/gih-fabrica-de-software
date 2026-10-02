/**
 * Captura as evidências da Sprint 08 — as funcionalidades concluídas, o
 * controle de permissões e as melhorias de usabilidade, como o usuário os vê.
 *
 * O que muda numa tela que já existia só se mostra com o antes ao lado do
 * depois, e o antes precisa ser fotografado **antes** da mudança. Por isso o
 * roteiro tem etapas, rodadas em momentos diferentes:
 *
 *   node docs/entrega/capturar_sprint08.js antes       # a conta, o acesso negado e o cadastro de usuário, antes da H92 à H101
 *   node docs/entrega/capturar_sprint08.js fluxos      # do relatório importado à mensagem aprovada, e o assistente
 *   node docs/entrega/capturar_sprint08.js permissoes  # o que cada perfil vê, e o que lhe é negado
 *   node docs/entrega/capturar_sprint08.js depois      # as mesmas telas do antes, e as melhorias de usabilidade
 *
 * A etapa dos fluxos pede o modelo de linguagem no ar (`docker compose --profile
 * assistente up -d`): sem ele o sistema funciona igual, mas as mensagens saem do
 * modelo fixo e o assistente se diz indisponível — e a captura diz isso.
 *
 * Cada etapa grava em `evidencias/sprint08/` as capturas com o prefixo dela, e
 * um texto com o que uma captura não mostra: o endereço e o que a tela disse.
 *
 * O que é comum a todo roteiro — as três pessoas descartáveis, a foto depois de
 * a página assentar, a limpeza no fim — está em `comum/captura.js`.
 *
 * A API e a interface precisam estar no ar (docker compose up -d), com a base de
 * demonstração e o modelo treinado:
 *   GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint08.js <etapa>
 */
const path = require('path');

const {
  VISOR, WEB, calcularPlano, esperar, ir, pelaApi, principal, quebrar,
} = require('./comum/captura');

const SAIDA = path.join(__dirname, 'evidencias', 'sprint08');

/* O recuo das linhas de continuação nos textos: embaixo do valor, e não do rótulo. */
const RECUO = ' '.repeat(14);

/** As linhas de um registro em texto, quebradas nas 96 colunas do documento. */
const caber = (linhas) => linhas.flatMap((linha) => quebrar(linha, RECUO).split('\n'));

/**
 * O texto de um elemento da tela, como a pessoa o lê: `innerText` separa os
 * blocos, e o `textContent` os colaria ("Gestora da CapturaGESTOR").
 */
async function lerDaTela(pagina, seletor) {
  return pagina.$eval(seletor, (el) => el.innerText.replace(/\s*\n\s*/g, ' · ').replace(/\s+/g, ' ').trim())
    .catch(() => '(não está na tela)');
}

/**
 * O antes: o cabeçalho sem caminho para a conta (H92); o cadastro de um usuário
 * sem a redefinição de senha (H93) e sem o perfil Parceiro (H101); o analista
 * que abre pelo endereço uma tela que o perfil dele não tem (H94); e o login,
 * sem "mostrar a senha" (H96).
 */
async function antes({ gestor, analista, administrador, pessoas, fotografar, fotografarElemento, gravar }) {
  const linhas = ['O antes da Sprint 08 — o que a tela dizia em cada endereço', ''];

  await ir(gestor, '/', '.indicadores');
  await fotografarElemento(gestor, 'antes-cabecalho', 'header.cabecalho', 0);
  linhas.push('O cabeçalho, de qualquer tela');
  linhas.push(`  na tela     ${await lerDaTela(gestor, '.cabecalho__direita')} — e dois botões: o tema e a saída`);
  linhas.push('');

  // O analista não tem a trilha de auditoria (UC14). O endereço abre a casca da
  // tela, e o que aparece dentro é a recusa da API.
  await analista.goto(`${WEB}/auditoria`, { waitUntil: 'networkidle0' });
  await esperar(600);
  await fotografar(analista, 'antes-analista-em-auditoria');
  linhas.push('O analista abre /auditoria pelo endereço');
  linhas.push(`  título      ${await analista.title()}`);
  linhas.push(`  na tela     ${await lerDaTela(analista, 'main.pagina')}`);
  linhas.push('');

  await ir(administrador, '/usuarios/novo', '#campo-perfil');
  await fotografarElemento(administrador, 'antes-usuario-novo', 'main.pagina', 0);
  const perfis = await administrador.$$eval('#campo-perfil option', (os) => os.map((o) => o.textContent.trim()));
  linhas.push('O administrador cria um usuário');
  linhas.push('  endereço    /usuarios/novo');
  linhas.push(`  perfis      ${perfis.join(', ')}`);
  linhas.push('');

  await ir(administrador, `/usuarios/${pessoas.ANALISTA.id}`, '#campo-perfil');
  await fotografarElemento(administrador, 'antes-usuario-conta', 'main.pagina', 0);
  const blocos = await administrador.$$eval('main.pagina h2, main.pagina h3', (hs) => hs.map((h) => h.textContent.trim()));
  linhas.push('O administrador abre a conta de um usuário');
  linhas.push('  endereço    /usuarios/{id}');
  linhas.push(`  blocos      ${blocos.join(' · ')}`);
  linhas.push('');

  // O login, sem sessão: um contexto novo, que não divide o cookie com ninguém.
  const contexto = await gestor.browser().createBrowserContext();
  const visitante = await contexto.newPage();
  await visitante.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }]);
  await visitante.setViewport(VISOR);
  await ir(visitante, '/entrar', '#login');
  await fotografarElemento(visitante, 'antes-login', '.entrada__cartao', 24);
  await contexto.close();

  gravar('antes.txt', caber(linhas));
}

/* Um plano pequeno: oito mensagens mostram cada decisão, e o modelo de linguagem
   leva de 2 a 4 s em cada uma. */
const CAMPANHA = {
  orcamento: '1500.00',
  maximo_acoes: 8,
  cota_cauda_longa: '0.25',
  aplicacao_inicio: '2026-10-05',
  aplicacao_fim: '2026-10-11',
};

/* O relatório de uma semana que ainda não existe na base, para a prévia: três
   linhas reconhecidas e uma rejeitada. A prévia não grava nada. */
const RELATORIO = [
  'Parceiro;Faturamento;Pedidos',
  'Cantina Aurora;12500,40;312',
  'Pizzaria do Vale;8300,00;190',
  'Mercado Sol Nascente;21740,90;655',
  'Linha sem número;abc;10',
].join('\n');

/** Clica no botão pelo texto dele, dentro de um seletor. */
async function clicar(pagina, seletor, texto) {
  const achou = await pagina.evaluate((s, t) => {
    const botao = [...document.querySelectorAll(s)].find((b) => b.textContent.trim().startsWith(t));
    if (botao) botao.click();
    return Boolean(botao);
  }, seletor, texto);
  if (!achou) throw new Error(`Não achei "${texto}" em ${seletor}.`);
}

/**
 * Os fluxos principais, de ponta a ponta: o relatório na prévia da importação, o
 * painel, o modelo em uso, o plano de campanha, as mensagens do plano, a fila em
 * que o gestor decide, o histórico, o assistente e o relatório da campanha.
 */
async function fluxos({ gestor, analista, fotografar, fotografarElemento, gravar }) {
  const linhas = ['Os fluxos principais — o que cada tela disse', ''];

  // 1. A importação: o relatório na prévia, antes de gravar.
  await ir(analista, '/importacao', '#texto');
  await analista.type('#inicio', '26102026');
  await analista.type('#fim', '01112026');
  await analista.type('#texto', RELATORIO);
  await clicar(analista, 'form.importacao button[type="submit"]', '');
  await analista.waitForSelector('#titulo-previa', { timeout: 15000 });
  await esperar(500);
  await fotografar(analista, 'fluxo-1-importacao-previa', { fullPage: true });
  linhas.push('1. Importação — o analista confere a prévia antes de gravar');
  linhas.push(`  na tela     ${await lerDaTela(analista, 'section[aria-labelledby="titulo-previa"] .painel__cabecalho')}`);
  linhas.push('');

  // 2. O painel, com a base de demonstração.
  await ir(gestor, '/', '.indicadores');
  await esperar(600);
  await fotografar(gestor, 'fluxo-2-painel', { fullPage: true });
  linhas.push('2. Painel — os indicadores, o ranking e a distribuição por segmento');
  linhas.push(`  indicadores ${await lerDaTela(gestor, '.indicadores')}`);
  linhas.push('');

  // 3. O modelo de previsão em uso.
  await ir(gestor, '/modelo', 'section[aria-labelledby="titulo-versao"]');
  await esperar(400);
  await fotografarElemento(gestor, 'fluxo-3-modelo', 'section[aria-labelledby="titulo-versao"]', 16);
  const modelo = (await pelaApi(gestor, 'GET', '/api/modelo')).dados;
  linhas.push('3. Modelo — a versão que está prevendo');
  linhas.push(`  em uso      ${modelo.versao_em_uso} (${modelo.origem})`);
  linhas.push('');

  // 4. O plano de campanha, calculado pelo gestor.
  const execucao = await calcularPlano(gestor, CAMPANHA);
  if (execucao.erro) throw new Error(execucao.erro);
  await ir(gestor, '/campanha', 'section[aria-labelledby="titulo-plano"]');
  await esperar(500);
  await fotografarElemento(gestor, 'fluxo-4-campanha-plano', 'section[aria-labelledby="titulo-plano"]', 16, 1500);
  linhas.push('4. Campanha — o plano que o otimizador devolveu');
  linhas.push(`  plano       ${execucao.acoes} ações, custo de R$ ${execucao.custo_total}, ganho esperado de R$ ${execucao.uplift_total}, no modo ${execucao.modo}`);
  linhas.push('');

  // 5. As mensagens do plano, geradas pelo analista.
  const estado = (await pelaApi(analista, 'GET', '/api/mensagens/geracao')).dados;
  const noAr = Boolean(estado.assistente && estado.assistente.disponivel);
  await ir(analista, `/mensagens?plano=${execucao.id}`, 'section[aria-labelledby="titulo-publico"]');
  if (!(await analista.$('#titulo-previa'))) {
    await clicar(analista, 'section[aria-labelledby="titulo-publico"] button[type="submit"]', '');
  }
  await analista.waitForSelector('#titulo-previa', { timeout: 15000 });
  await clicar(analista, '.mensagens__acoes button', 'Gerar');
  await analista.waitForSelector('section[aria-labelledby="titulo-lote"]', { timeout: 30000 });
  const limite = Date.now() + 600000;
  for (;;) {
    const prontas = await analista.$$eval('.mensagens__lista > li', (itens) => itens.length);
    if (prontas >= execucao.acoes) break;
    if (Date.now() > limite) throw new Error('As mensagens não ficaram prontas em 10 minutos.');
    await esperar(1500);
  }
  await esperar(1500);
  await fotografar(analista, 'fluxo-5-mensagens-geradas', { fullPage: true });
  // O lote que a tela acabou de gerar: o último, e do analista desta captura.
  const ultimo = (await pelaApi(analista, 'GET', '/api/mensagens/geracao')).dados.ultimo;
  if (!ultimo || ultimo.total !== execucao.acoes) throw new Error('O último lote não é o desta captura.');
  const lote = ultimo.id;
  const pendentes = (await pelaApi(analista, 'GET', `/api/mensagens?lote_id=${lote}&tamanho=100`)).dados;
  const pelosRedatores = pendentes.itens.reduce((c, m) => ({ ...c, [m.redator]: (c[m.redator] || 0) + 1 }), {});
  linhas.push('5. Mensagens — uma para cada parceiro do plano, todas pendentes');
  linhas.push(`  modelo      ${noAr ? `no ar: ${estado.assistente.modelo}` : `fora do ar: ${estado.assistente && estado.assistente.motivo}`}`);
  linhas.push(`  geradas     ${pendentes.total}, por redator: ${JSON.stringify(pelosRedatores)}`);
  linhas.push(`  um texto    ${pendentes.itens[0].texto}`);
  linhas.push('');

  // 6. A fila: o gestor aprova uma, edita outra e rejeita uma terceira.
  await ir(gestor, `/aprovacao?lote=${lote}`, '.aprovacao__lista');
  await esperar(500);
  await fotografar(gestor, 'fluxo-6-aprovacao-fila');
  const [primeira, segunda, terceira] = pendentes.itens;
  await pelaApi(gestor, 'POST', `/api/mensagens/${primeira.id}/aprovacao`);
  await pelaApi(gestor, 'POST', `/api/mensagens/${segunda.id}/edicao`,
    { texto: `${segunda.texto} Nesta semana, 15% de desconto na taxa.` });
  await pelaApi(gestor, 'POST', `/api/mensagens/${terceira.id}/rejeicao`,
    { motivo: 'O tom não serve para este parceiro.' });
  await ir(gestor, `/aprovacao?lote=${lote}`, '.aprovacao__lista');
  await esperar(500);
  await fotografar(gestor, 'fluxo-6-aprovacao-editada');
  await pelaApi(gestor, 'POST', `/api/mensagens/${segunda.id}/aprovacao`);

  // 7. O histórico das aprovadas, de onde sai o arquivo para envio.
  await ir(gestor, `/aprovacao?estado=APROVADA&lote=${lote}`, '.aprovacao__lista');
  await esperar(500);
  await fotografar(gestor, 'fluxo-7-aprovacao-historico');
  const aprovadas = (await pelaApi(gestor, 'GET', `/api/mensagens?estado=APROVADA&lote_id=${lote}`)).dados;
  const restam = (await pelaApi(gestor, 'GET', `/api/mensagens?lote_id=${lote}`)).dados;
  linhas.push('6. Aprovação — o gestor aprova uma, edita e aprova outra, e rejeita uma terceira');
  linhas.push(`  aprovadas   ${aprovadas.total}, por ${aprovadas.itens[0].decidida_por}`);
  linhas.push(`  na fila     ${restam.total}: nenhuma sai sem a decisão de um gestor (RN06)`);
  linhas.push('');

  // 8. O assistente: uma pergunta respondida, com a fonte, e uma abstenção.
  await ir(gestor, '/assistente', '#campo-pergunta');
  const perguntas = ['Como foi a rede na última semana?', 'Qual a média de faturamento das pizzarias?'];
  linhas.push('7. Assistente — a resposta com a fonte, e a abstenção');
  if (noAr) {
    for (const [i, pergunta] of perguntas.entries()) {
      await gestor.type('#campo-pergunta', pergunta);
      await clicar(gestor, 'form.assistente__formulario button[type="submit"]', '');
      await gestor.waitForFunction(
        (n) => document.querySelectorAll('.resposta:not(.resposta--aguardando)').length >= n,
        { timeout: 240000 }, i + 1,
      );
      await esperar(600);
    }
    await fotografar(gestor, 'fluxo-8-assistente', { fullPage: true });
    const respostas = await gestor.$$eval('.resposta', (rs) => rs.map((r) => r.innerText.replace(/\s*\n\s*/g, ' · ')));
    respostas.forEach((r) => linhas.push(`  na tela     ${r}`));
  } else {
    await esperar(600);
    await fotografar(gestor, 'fluxo-8-assistente', { fullPage: true });
    linhas.push(`  na tela     ${await lerDaTela(gestor, 'main.pagina')}`);
  }
  linhas.push('');

  // 9. O relatório da campanha, que resume o plano.
  await ir(gestor, '/relatorios/campanha', 'main.pagina table');
  await esperar(500);
  await fotografar(gestor, 'fluxo-9-relatorio-campanha', { fullPage: true });
  linhas.push('8. Relatório da campanha — o plano resumido por ação, categoria e segmento');
  linhas.push(`  resumo      ${await lerDaTela(gestor, '.relatorio__resumo')}`);

  gravar('fluxos.txt', caber(linhas));
}

/**
 * O que cada perfil vê, e o que lhe é negado: os quatro menus, a página "Sem
 * acesso", a campanha e a fila do analista, o painel do administrador e o
 * portal e a ajuda do parceiro.
 */
async function permissoes({ gestor, analista, administrador, admin, outraPessoa, fotografar, fotografarElemento, gravar }) {
  const linhas = ['O controle de permissões — o que cada perfil vê na tela', ''];

  // A conta de perfil Parceiro, do parceiro de maior faturamento.
  const maior = (await pelaApi(analista, 'GET', '/api/parceiros?ordenar_por=faturamento&descendente=true&tamanho=1')).dados.itens[0];
  const parceiro = await outraPessoa('parceiro', 'PARCEIRO', 'Parceiro da Captura', { parceiro_id: maior.id });

  const perfis = [
    ['administrador', administrador, '/'],
    ['gestor', gestor, '/'],
    ['analista', analista, '/'],
    ['parceiro', parceiro, '/meu-desempenho'],
  ];
  linhas.push('O menu de cada perfil — só o que ele abre');
  for (const [nome, pagina, inicio] of perfis) {
    await ir(pagina, inicio, 'nav.trilho');
    await esperar(400);
    await fotografarElemento(pagina, `permissoes-menu-${nome}`, 'nav.trilho', 0);
    const itens = await pagina.$$eval('nav.trilho a.trilho__item', (as) => as.map((a) => a.textContent.trim()));
    linhas.push(`  ${nome.padEnd(14)}${itens.join(', ')}`);
  }
  linhas.push('');

  // O endereço de uma tela de outro perfil.
  const negados = [
    ['analista', analista, '/auditoria'],
    ['administrador', administrador, '/parceiros'],
    ['parceiro', parceiro, '/parceiros'],
    ['gestor', gestor, '/usuarios'],
  ];
  linhas.push('O endereço de uma tela que o perfil não abre — a página "Sem acesso"');
  for (const [nome, pagina, endereco] of negados) {
    await pagina.goto(`${WEB}${endereco}`, { waitUntil: 'networkidle0' });
    await esperar(500);
    await fotografar(pagina, `permissoes-sem-acesso-${nome}`);
    linhas.push(`  ${nome.padEnd(14)}${endereco.padEnd(12)} ${await lerDaTela(pagina, 'section[aria-label="Sem acesso"]')}`);
  }
  linhas.push('');

  // O que o perfil vê e não faz.
  await ir(gestor, '/campanha', 'section[aria-labelledby="titulo-restricoes"]');
  await esperar(400);
  await fotografarElemento(gestor, 'permissoes-campanha-gestor', 'section[aria-labelledby="titulo-restricoes"]', 16);
  await ir(analista, '/campanha', 'section[aria-labelledby="titulo-restricoes"]');
  await esperar(400);
  await fotografarElemento(analista, 'permissoes-campanha-analista', 'section[aria-labelledby="titulo-restricoes"]', 16);
  linhas.push('A campanha — o gestor calcula; o analista consulta');
  linhas.push(`  gestor        ${await lerDaTela(gestor, '.campanha__acoes')}`);
  linhas.push(`  analista      ${await lerDaTela(analista, '.campanha__bloqueio')}`);
  linhas.push('');

  // Três mensagens na fila, geradas pelo analista: com a base limpa, ela estaria vazia.
  const tres = (await pelaApi(analista, 'GET', '/api/parceiros?ordenar_por=faturamento&descendente=true&tamanho=3')).dados.itens;
  const pedido = await pelaApi(analista, 'POST', '/api/mensagens/lotes', { tipo: 'SELECAO', parceiros: tres.map((p) => p.id) });
  if (pedido.status !== 202) throw new Error(`A geração das mensagens respondeu ${pedido.status}.`);
  const prazo = Date.now() + 300000;
  for (;;) {
    const { dados } = await pelaApi(analista, 'GET', `/api/mensagens/lotes/${pedido.dados.id}`);
    if (dados.situacao !== 'EM_ANDAMENTO') break;
    if (Date.now() > prazo) throw new Error('As mensagens não ficaram prontas em 5 minutos.');
    await esperar(1500);
  }

  await ir(gestor, '/aprovacao', 'main.pagina');
  await esperar(600);
  await fotografar(gestor, 'permissoes-aprovacao-gestor');
  await ir(analista, '/aprovacao', 'main.pagina');
  await esperar(600);
  await fotografar(analista, 'permissoes-aprovacao-analista');
  const botoes = async (pagina) => pagina.$$eval('.aprovacao__lista li:first-child .aprovacao__acoes button', (bs) => bs.map((b) => b.textContent.trim()));
  linhas.push('A fila de aprovação — o analista vê; só o gestor decide (RN06)');
  linhas.push(`  gestor        os botões da primeira mensagem: ${(await botoes(gestor)).join(', ') || '(a fila está vazia)'}`);
  linhas.push(`  analista      os botões da primeira mensagem: ${(await botoes(analista)).join(', ') || 'nenhum'}`);
  linhas.push('');

  await ir(administrador, '/', '.indicadores');
  await esperar(600);
  await fotografar(administrador, 'permissoes-painel-administrador', { fullPage: true });
  linhas.push('O painel do administrador — só leitura, sem a previsão nem a campanha');
  linhas.push(`  blocos        ${(await administrador.$$eval('main.pagina h2', (hs) => hs.map((h) => h.textContent.trim()))).join(' · ')}`);
  linhas.push('');

  await ir(parceiro, '/meu-desempenho', '.indicadores');
  await esperar(600);
  await fotografar(parceiro, 'permissoes-portal-parceiro', { fullPage: true });
  await ir(parceiro, '/ajuda', '#portal');
  await esperar(400);
  await fotografar(parceiro, 'permissoes-ajuda-parceiro');
  linhas.push('O portal do parceiro — o histórico dele, e nada da rede (RF26)');
  linhas.push(`  de quem       ${maior.nome}`);
  linhas.push(`  ajuda         ${(await parceiro.$$eval('main.pagina h2', (hs) => hs.map((h) => h.textContent.trim()))).join(' · ')}`);
  linhas.push('');

  // O que a API registrou das quatro tentativas negadas — nenhuma: a página "Sem
  // acesso" não pede nada. A trilha mostra isso.
  const trilha = await (await admin('GET', '/api/auditoria?acao=ACESSO_NEGADO&tamanho=1')).json();
  linhas.push('A página "Sem acesso" não faz nenhuma chamada à API: quem decide o acesso continua');
  linhas.push(`sendo o servidor, a cada requisição. A trilha tem ${trilha.total} acessos negados registrados,`);
  linhas.push('de quem chamou a rota — a transcrição das permissões os provoca e os conta.');

  gravar('permissoes-na-tela.txt', caber(linhas));
}

/**
 * O depois: as mesmas telas do antes, e as melhorias de usabilidade — o caminho
 * para a conta e para a ajuda, a página "Sem acesso", a redefinição de senha, a
 * conta de perfil Parceiro, o link de pular, o foco, a sessão terminada e o
 * aviso de alterações não salvas.
 */
async function depois({ gestor, analista, administrador, pessoas, admin, fotografar, fotografarElemento, gravar }) {
  const linhas = ['O depois da Sprint 08 — o que a tela diz em cada endereço', ''];

  await ir(gestor, '/', '.indicadores');
  await fotografarElemento(gestor, 'depois-cabecalho', 'header.cabecalho', 0);
  linhas.push('O cabeçalho, de qualquer tela');
  linhas.push(`  na tela     ${await lerDaTela(gestor, '.cabecalho__direita')} — o nome leva à conta, e há o botão da ajuda`);
  linhas.push('');

  await analista.goto(`${WEB}/auditoria`, { waitUntil: 'networkidle0' });
  await esperar(600);
  await fotografar(analista, 'depois-analista-em-auditoria');
  linhas.push('O analista abre /auditoria pelo endereço');
  linhas.push(`  título      ${await analista.title()}`);
  linhas.push(`  na tela     ${await lerDaTela(analista, 'main.pagina')}`);
  linhas.push('');

  // O perfil Parceiro, com a busca do parceiro pelo nome (H101).
  const umParceiro = (await pelaApi(analista, 'GET', '/api/parceiros?ordenar_por=faturamento&descendente=true&tamanho=1')).dados.itens[0];
  await ir(administrador, '/usuarios/novo', '#campo-perfil');
  await administrador.select('#campo-perfil', 'PARCEIRO');
  await administrador.waitForSelector('#campo-parceiro_id', { timeout: 15000 });
  await administrador.type('#campo-parceiro_id', umParceiro.nome.slice(0, 5));
  await administrador.waitForSelector('ul[aria-label="Parceiros encontrados"] button', { timeout: 15000 });
  await esperar(400);
  await fotografarElemento(administrador, 'depois-usuario-novo', 'main.pagina', 0);
  const perfis = await administrador.$$eval('#campo-perfil option', (os) => os.map((o) => o.textContent.trim()));
  linhas.push('O administrador cria um usuário');
  linhas.push('  endereço    /usuarios/novo');
  linhas.push(`  perfis      ${perfis.join(', ')}`);
  linhas.push('  parceiro    com o perfil Parceiro, a busca pelo nome, que devolve só o nome e a situação');
  linhas.push('');

  await ir(administrador, `/usuarios/${pessoas.ANALISTA.id}`, '#campo-perfil');
  await fotografarElemento(administrador, 'depois-usuario-conta', 'main.pagina', 0);
  const blocos = await administrador.$$eval('main.pagina h2, main.pagina h3', (hs) => hs.map((h) => h.textContent.trim()));
  linhas.push('O administrador abre a conta de um usuário');
  linhas.push('  endereço    /usuarios/{id}');
  linhas.push(`  blocos      ${blocos.join(' · ')}`);
  linhas.push('');

  // A Minha conta, pelo nome no cabeçalho (H92).
  await ir(gestor, '/conta', '#campo-senha_atual');
  await gestor.type('#campo-senha_nova', 'curta');
  await gestor.type('#campo-confirmacao', 'curta');
  await gestor.type('#campo-senha_atual', 'a-senha-de-agora');
  await clicar(gestor, 'section[aria-labelledby="titulo-senha"] button[type="submit"]', '');
  await gestor.waitForSelector('#campo-senha_atual[aria-invalid="true"], #campo-senha_nova[aria-invalid="true"]', { timeout: 15000 });
  await esperar(400);
  await fotografar(gestor, 'depois-minha-conta', { fullPage: true });
  linhas.push('A Minha conta — os dados e a troca da senha, com o erro embaixo do campo');
  linhas.push(`  na tela     ${await lerDaTela(gestor, 'section[aria-labelledby="titulo-senha"] .campo__erro')}`);
  linhas.push('');

  // O primeiro Tab de qualquer tela, e o foco que segue a troca de tela (H96).
  await ir(gestor, '/parceiros', 'table');
  await gestor.keyboard.press('Tab');
  await esperar(300);
  await fotografar(gestor, 'depois-pular-para-o-conteudo');
  await gestor.keyboard.press('Tab');
  await gestor.keyboard.press('Enter');
  await esperar(900);
  const foco = await gestor.evaluate(() => `${document.activeElement.tagName.toLowerCase()}#${document.activeElement.id}: "${document.activeElement.textContent}"`);
  linhas.push('O teclado — o primeiro Tab, e o Enter no primeiro item do menu');
  linhas.push('  1º Tab      o link "Pular para o conteúdo", que só aparece com o foco');
  linhas.push(`  foco        depois de trocar de tela: ${foco}`);
  linhas.push('');

  // O aviso de alterações não salvas (H97): um campo alterado, e o clique no menu.
  await ir(gestor, '/parceiros', 'table tbody a');
  await gestor.click('table tbody a');
  await gestor.waitForSelector('#campo-contato', { timeout: 15000 });
  await gestor.type('#campo-contato', ' ');
  await gestor.evaluate(() => [...document.querySelectorAll('nav.trilho a')].find((a) => a.textContent.trim() === 'Relatórios').click());
  await gestor.waitForSelector('[role="alert"] .confirmacao', { timeout: 15000 });
  await esperar(400);
  await fotografar(gestor, 'depois-alteracoes-nao-salvas');
  linhas.push('O aviso de alterações não salvas — um campo mudado, e o clique em outro item do menu');
  linhas.push(`  na tela     ${await lerDaTela(gestor, '[role="alert"] .confirmacao')}`);
  linhas.push(`  endereço    continua em ${new URL(gestor.url()).pathname.replace(/\d+$/, '{id}')}`);
  linhas.push('');
  await clicar(gestor, '[role="alert"] .confirmacao button', 'Sair sem salvar');
  await esperar(600);

  // A ajuda (H95), inteira.
  await ir(gestor, '/ajuda', '#ganho');
  await esperar(400);
  await fotografar(gestor, 'depois-ajuda', { fullPage: true });
  const segmentos = await gestor.$$eval('.ajuda__segmentos > li', (ls) => ls.map((li) => li.firstElementChild.textContent.trim()));
  linhas.push('A ajuda — o que o perfil faz, os segmentos, a estimativa e o ganho esperado');
  linhas.push(`  segmentos   na ordem da regra: ${segmentos.join(', ')}`);
  linhas.push('');

  // A sessão que o servidor encerra: o administrador redefine a senha do gestor,
  // e a tela descobre na ação seguinte (H96).
  await ir(gestor, '/conta', '#campo-senha_atual');
  const novaSenha = require('crypto').randomBytes(18).toString('base64url');
  await admin('POST', `/api/usuarios/${pessoas.GESTOR.id}/senha`, { senha_nova: novaSenha });
  await gestor.type('#campo-senha_atual', 'qualquer-coisa');
  await gestor.type('#campo-senha_nova', 'uma-senha-nova-bem-longa');
  await gestor.type('#campo-confirmacao', 'uma-senha-nova-bem-longa');
  await clicar(gestor, 'section[aria-labelledby="titulo-senha"] button[type="submit"]', '');
  await gestor.waitForSelector('#login', { timeout: 15000 });
  await gestor.type('#senha', 'uma-senha');
  await gestor.click('.senha__botao');
  await esperar(400);
  await fotografarElemento(gestor, 'depois-login', '.entrada__cartao', 24);
  linhas.push('O login, depois de o servidor encerrar a sessão');
  linhas.push(`  na tela     ${await lerDaTela(gestor, '.entrada__cartao [role="status"]')}`);
  linhas.push('  a senha     com "Mostrar" e "Ocultar" no campo');
  // A sessão do gestor caiu de verdade: a página volta a ter uma, para o roteiro encerrar.
  await gestor.evaluate(async (l, s) => {
    await fetch('/api/sessao', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login: l, senha: s }),
    });
  }, pessoas.GESTOR.login, novaSenha);

  gravar('depois.txt', caber(linhas));
}

principal({ antes, fluxos, permissoes, depois }, SAIDA, 'sprint08');
