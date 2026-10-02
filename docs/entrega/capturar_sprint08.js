/**
 * Captura as evidências da Sprint 08 — as funcionalidades concluídas, o
 * controle de permissões e as melhorias de usabilidade, como o usuário os vê.
 *
 * O que muda numa tela que já existia só se mostra com o antes ao lado do
 * depois, e o antes precisa ser fotografado **antes** da mudança. Por isso o
 * roteiro tem etapas, rodadas em momentos diferentes:
 *
 *   node docs/entrega/capturar_sprint08.js antes   # a conta, o acesso negado e o cadastro de usuário, antes da H92 à H101
 *
 * As etapas do depois — os fluxos, as permissões e a usabilidade — entram com
 * as evidências da entrega, depois do último Pull Request de código.
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

const { VISOR, WEB, esperar, ir, principal, quebrar } = require('./comum/captura');

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

principal({ antes }, SAIDA, 'sprint08');
