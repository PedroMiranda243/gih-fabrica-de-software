/**
 * Parte IX do documento — Sprint 09 acadêmica: testes e correções.
 *
 * O enunciado pede a verificação completa do sistema — testes funcionais, a
 * correção dos bugs, testes de validação e de navegação — e a documentação
 * técnica atualizada, com os casos de teste, o esperado e o obtido, e a
 * evidência de cada um. Como nas partes anteriores, nenhum número é digitado
 * aqui:
 *
 * - os casos vêm de `casos.json`, que o `scripts/testar_na_tela.py` escreve
 *   executando o catálogo do `docs/12` num navegador de verdade, contra o
 *   sistema no ar — o esperado é o do catálogo, e o obtido, o que a tela mostrou;
 * - as conferências da API vêm das transcrições de `api/e2e/`, e as regras e as
 *   telas, das medições copiadas para `evidencias/sprint09/medicoes/`;
 * - os testes, os bugs, os commits e as revisões vêm dos registros que os
 *   scripts geram da suíte rodada, das issues, do git e dos Pull Requests;
 * - a campanha manual vem dos comentários de cada integrante na issue #256.
 *
 * `aprovado()` recusa gerar se uma evidência registrar falha, e `casos()` recusa
 * se um caso não tiver passado — inclusive o "não executado", que é o caso do
 * assistente sem o modelo de linguagem no ar. Para um rascunho com as
 * evidências ainda provisórias, `GIH_RASCUNHO=1` deixa gerar e marca a capa da
 * parte; o PDF entregue nunca sai assim.
 *
 * **As figuras desta parte estão congeladas** em `diagramas/parte-ix/`, e as
 * medições, em `evidencias/sprint09/medicoes/`: esta parte nunca lê o arquivo
 * vivo de `docs/`.
 */
const fs = require('fs');
const path = require('path');
const { AlignmentType, HeadingLevel, Paragraph, TextRun } = require('docx');
const { AZUL, p, rich, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { diagrama, evidencia, legenda } = require('../comum/figuras');
const { trecho, json } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';
const EVIDENCIAS = path.join(__dirname, '..', 'evidencias');
const S = 'sprint09';
const PARTE_IX = 'parte-ix';
const RASCUNHO = process.env.GIH_RASCUNHO === '1';

// Os integrantes pelo login do GitHub, para a campanha manual e as revisões.
const PESSOAS = {
  ingrydaraujob: { nome: 'Ingryd', area: 'Telas e navegação' },
  joaopfranca04: { nome: 'João Pedro', area: 'Importação, parceiros e categorias' },
  mihaeldatoman: { nome: 'Marcio', area: 'Painel, campanha e relatórios' },
  ThiagojFalcao: { nome: 'Thiago', area: 'Usuários, permissões, sessão e auditoria' },
  PedroMiranda243: { nome: 'Pedro', area: 'Modelo, benchmark, mensagens e assistente' },
};

// --------------------------------------------- títulos e figuras desta parte
const titulo = (nivel, tamanho, antes, depois) => (texto) => new Paragraph({
  heading: nivel,
  keepNext: true,
  spacing: { before: antes, after: depois },
  children: [new TextRun({ text: texto, bold: true, size: tamanho, color: AZUL, font: 'Calibri' })],
});
const h1 = titulo(HeadingLevel.HEADING_1, 30, 360, 180);
const h2 = titulo(HeadingLevel.HEADING_2, 24, 260, 120);

/** A figura e a legenda dela, juntas na mesma página. */
const figura = (nome, texto, largura) => [evidencia(`${S}/${nome}`, largura, true), legenda(texto)];

// ------------------------------------------------------------------ leitores
function cruas(nome) {
  const arquivo = path.join(EVIDENCIAS, S, nome);
  if (!fs.existsSync(arquivo)) throw new Error(`Falta ${S}/${nome}. Rode os scripts de evidência.`);
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n').split('\n');
}

/** A linha de resultado da evidência, e a recusa se ela registrar alguma falha. */
function aprovado(arquivo, marcador) {
  const linhas = cruas(arquivo);
  const linha = linhas.find((l) => l.includes(marcador));
  if (!linha) throw new Error(`Sem a linha de resultado em ${arquivo}.`);
  // `LOGIN_FALHA` é o nome de uma ação da trilha, e não uma falha: a palavra solta é a que reprova.
  const falhas = linhas.filter((l) => /\bFALHA\b/.test(l));
  if (falhas.length) throw new Error(`${arquivo} registra ${falhas.length} falha(s) — corrija e gere a evidência de novo.`);
  return linha.trim();
}

const semRotulo = (linha) => linha.replace(/^Resultado:\s*/, '');

function achar(texto, regex, onde) {
  const m = regex.exec(texto);
  if (!m) throw new Error(`Não achei ${regex} em ${onde} — gere de novo ou corrija o leitor.`);
  return m;
}

/*
 * A cópia desta entrega, e não o arquivo vivo de `docs/`. Tirada junto das
 * evidências, depois do último Pull Request de código:
 *   cp docs/medicoes/acessibilidade.md docs/medicoes/regras.md docs/entrega/evidencias/sprint09/medicoes/
 *   cp docs/11-rastreabilidade.md docs/entrega/evidencias/sprint09/medicoes/rastreabilidade.md
 */
function medicao(nome) {
  const arquivo = path.join(EVIDENCIAS, S, 'medicoes', nome);
  if (!fs.existsSync(arquivo)) throw new Error(`Falta ${S}/medicoes/${nome}. Copie o arquivo de docs/ antes de gerar.`);
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n');
}

/** Os casos de teste executados pela tela, e a recusa se algum não passou. */
function casos(arquivo = 'casos.json') {
  const registro = json(`${S}/${arquivo}`);
  const naoPassaram = registro.casos.filter((c) => c.situacao !== 'ok');
  if (naoPassaram.length && !RASCUNHO) {
    throw new Error(
      `${arquivo}: ${naoPassaram.map((c) => `${c.id} (${c.situacao})`).join(', ')} — os casos do assistente pedem o `
      + 'perfil assistente no ar; rode scripts/testar_na_tela.py de novo antes de gerar.',
    );
  }
  const [, data, hora] = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(registro.executado_em);
  const quando = `${data.split('-').reverse().join('/')} às ${hora}`;
  return { ...registro, quando, naoPassaram, porTipo: (letra) => registro.casos.filter((c) => c.id[3] === letra) };
}

/** As quatro suítes, lidas do registro de testes. */
function suites() {
  const achadas = cruas('testes.txt')
    .map((l) => /^\s{2}(\S.+?)\s{2,}(\d+) testes\s+(\d+) passaram\s+(\d+) falharam\s+(\d+) pulados\s+(\d+) s/.exec(l))
    .filter(Boolean)
    .map(([, nome, total, passaram, falharam, pulados, segundos]) => ({
      nome, total: Number(total), passaram: Number(passaram), falharam: Number(falharam), pulados: Number(pulados), segundos,
    }));
  if (achadas.length !== 4) throw new Error('O registro de testes não tem as quatro suítes.');
  return achadas;
}

/** A situação dos não funcionais, da cópia da matriz, conferida contra o resumo dela. */
function naoFuncionais() {
  const t = medicao('rastreabilidade.md');
  const linhas = [...t.matchAll(/^\| \*\*(RNF\d+)\*\* \| ([^|]+) \| .+ \| ([^|]+) \|$/gm)]
    .map(([, id, metrica, situacao]) => ({ id, metrica: metrica.trim(), situacao: situacao.trim() }));
  const [, total] = achar(t, /\*\*(\d+) requisitos não funcionais:/, 'rastreabilidade.md');
  if (linhas.length !== Number(total)) throw new Error(`A matriz lista ${linhas.length} não funcionais, e o resumo diz ${total}.`);
  return { linhas, pendentes: linhas.filter((r) => !r.situacao.startsWith('Atende')) };
}

/** A revisão das regras: o resultado, e as conferências de cada regra. */
function revisaoDasRegras() {
  const t = medicao('regras.md');
  const [, passaram, total, regras] = achar(
    t, /\*\*Resultado: (\d+) de (\d+) conferências passaram, nas (\d+) regras\.\*\*/, 'regras.md',
  );
  if (passaram !== total || /\bFALHA\b/.test(t)) {
    throw new Error('A revisão das regras registra falha — corrija e rode scripts/revisar_regras.py de novo.');
  }
  const linhas = [...t.matchAll(/^\| \*\*(RN\d+)\*\* — ([^|]+) \| (\d+) de (\d+) \| ok \|$/gm)]
    .map(([, codigo, nome, certas]) => ({ codigo, nome: nome.trim(), certas }));
  if (linhas.length !== Number(regras)) throw new Error('O resumo da revisão das regras não tem todas as regras.');
  return { passaram, total, linhas };
}

/** Os números da matriz perfil × rota, da transcrição das permissões. */
function matrizDePermissoes() {
  const linhas = cruas('permissoes.txt');
  const contar = (rotulo) => {
    const linha = linhas.find((l) => new RegExp(`^\\s+\\d+\\s+${rotulo}$`).test(l));
    if (!linha) throw new Error(`A transcrição das permissões não traz "${rotulo}".`);
    return linha.trim().split(/\s+/)[0];
  };
  const texto = linhas.join('\n');
  const negados = achar(texto, /recebeu (\d+) respostas 403; a trilha tem (\d+) registros/, 'permissoes.txt');
  return {
    rotas: achar(texto, /^(\d+) rotas, lidas das rotas registradas/m, 'permissoes.txt')[1],
    negacoes: contar('negações'),
    leituras: contar('leituras permitidas'),
    semSessao: contar('sem sessão'),
    escritas: contar('escritas permitidas, não exercitadas'),
    recebidos: negados[1],
    naTrilha: negados[2],
  };
}

/** A medição das telas no navegador — e a recusa, se alguma tela rolar ou violar o axe. */
function medicaoDasTelas() {
  const t = medicao('acessibilidade.md');
  const [, pares, totalPares] = achar(t, /\*\*(\d+) de (\d+) pares passam nos dois temas\.\*\*/, 'acessibilidade.md');
  const [, telas, rolando, medidas, axe, auditorias] = achar(
    t,
    /\*\*(\d+) telas\. Com a página rolando na horizontal ou conteúdo cortado: (\d+) das (\d+) medidas\. Com violação do axe no navegador: (\d+) das (\d+) auditorias\*\*/,
    'acessibilidade.md',
  );
  if (Number(rolando) || Number(axe) || pares !== totalPares) {
    throw new Error('A medição das telas registra defeito — corrija e meça de novo antes de gerar.');
  }
  const data = achar(t, /^\| Data \| ([^|]+) \|$/m, 'acessibilidade.md')[1].trim();
  // A medição precisa ser da interface v2, que entrou em 22/10 (H103).
  const [dia, mes, ano] = data.split(' ')[0].split('/');
  if (`${ano}-${mes}-${dia}` < '2026-10-22') {
    throw new Error(`A medição das telas é de ${data}, de antes da interface v2 — rode scripts/medir_telas.py de novo.`);
  }
  return { pares, telas, medidas, auditorias, data };
}

/** Os autores e coautores do registro de commits. */
function autoria() {
  const linhas = cruas('commits.txt');
  const ler = (tipo) => linhas
    .map((l) => new RegExp(`^\\s{2}${tipo}\\s+(.+?)\\s{2,}(\\d+)$`).exec(l))
    .filter(Boolean)
    .map(([, nome, n]) => ({ nome, n: Number(n) }));
  const autores = ler('autor');
  if (!autores.length) throw new Error('O registro de commits não traz a autoria.');
  return { autores, coautores: ler('coautor') };
}

/** Os títulos das seções de uma transcrição — as linhas que começam por "[". */
function secoesDe(nome) {
  const achadas = cruas(nome).filter((l) => /^\[[ \d+/]+\]/.test(l)).map((l) => l.trim());
  if (!achadas.length) throw new Error(`Sem seções em ${nome}.`);
  return achadas;
}

/**
 * A campanha manual: o comentário de cada integrante na issue #256, com o que
 * executou e o resultado. Quem não comentou aparece como não executado — a
 * tabela mostra os cinco, e não só quem testou.
 */
function campanhaManual() {
  const { comments: comentarios = [] } = json(`${S}/execucao-manual.json`);
  const campo = (corpo, rotulo) => {
    const m = new RegExp(`^\\s*${rotulo}:\\s*(.+)$`, 'im').exec(corpo);
    return m ? m[1].trim().replace(/`/g, '') : null;
  };
  const porPessoa = new Map();
  for (const c of comentarios) {
    const login = c.author?.login;
    const executei = campo(c.body ?? '', 'Executei');
    if (!PESSOAS[login] || !executei) continue;
    const lista = porPessoa.get(login) ?? [];
    lista.push({
      data: c.createdAt.slice(0, 10).split('-').reverse().join('/'),
      casos: executei,
      perfil: campo(c.body, 'Perfil') ?? '—',
      resultado: campo(c.body, 'Resultado') ?? '—',
    });
    porPessoa.set(login, lista);
  }
  return Object.entries(PESSOAS).map(([login, pessoa]) => ({ login, ...pessoa, execucoes: porPessoa.get(login) ?? [] }));
}

// ---------------------------------------------------------------- as tabelas
const MARCA = (c) => (c.situacao === 'ok' ? 'ok' : c.situacao.toUpperCase());

/** Uma tabela de casos: o caso, o que se fez, o esperado, o obtido e a situação. */
function tabelaDeCasos(lista) {
  return table([1150, 2250, 2300, 3338, 600], [
    ['Caso', 'Passos', 'Esperado', 'Obtido', ''],
    ...lista.map((c) => [`${c.id}||${c.modulo}`, c.passos.replace(/`/g, ''), c.esperado.replace(/`/g, ''), c.obtido, MARCA(c)]),
  ], { zebra: true, boldCol: 0, size: 14, align: [null, null, null, null, AlignmentType.CENTER] });
}

function montar() {
  const c = [];
  const tela = casos();
  const chrome = casos('casos-chrome.json');
  const verificacao = aprovado('verificacao.txt', 'verificações passaram');
  const validacoes = aprovado('validacoes.txt', 'Resultado:');
  const permissoes = aprovado('permissoes.txt', 'Resultado:');
  const registroTestes = aprovado('testes.txt', 'Resultado:');
  const registroBugs = aprovado('bugs.txt', 'Resultado:');
  const registroRevisoes = aprovado('revisoes.txt', 'Resultado:');
  const [api, modelo, otimizador, interfaceWeb] = suites();
  const rnf = naoFuncionais();
  const regras = revisaoDasRegras();
  const acesso = matrizDePermissoes();
  const telas = medicaoDasTelas();
  const bugs = json(`${S}/bugs.json`);
  const revisoes = json(`${S}/revisoes.json`);
  const manual = campanhaManual();
  const { autores, coautores } = autoria();

  const funcionais = tela.porTipo('F');
  const validacao = tela.porTipo('V');
  const navegacao = tela.porTipo('N');
  const passaram = (lista) => lista.filter((x) => x.situacao === 'ok').length;
  const navegacaoChrome = chrome.porTipo('N');
  const aprovadosNoGithub = revisoes.filter((r) => r.aprovado).length;
  const totalDeCommits = autores.reduce((s, a) => s + a.n, 0);
  const gpuDoRegistro = cruas('testes.txt').find((l) => l.includes('GPU:'));
  if (!gpuDoRegistro) throw new Error('O registro de testes não diz em que placa o otimizador rodou.');
  const placa = gpuDoRegistro.split('GPU: ')[1].trim();
  const corrigidos = bugs.filter((b) => b.situacao === 'corrigido');
  const pendentes = bugs.filter((b) => b.situacao !== 'corrigido');
  const daTroca = bugs.filter((b) => b.prs.includes(242));
  const testaram = manual.filter((m) => m.execucoes.length);
  if (navegacaoChrome.length !== navegacao.length) {
    throw new Error(`A execução no Chrome tem ${navegacaoChrome.length} casos de navegação, e a do Edge, ${navegacao.length}.`);
  }

  c.push(quebra());
  c.push(h1(`Parte IX — Sprint 09: Testes e Correções${RASCUNHO ? ' (RASCUNHO — evidências provisórias)' : ''}`));

  c.push(p(
    'As oito entregas anteriores construíram o sistema e conferiram, cada uma, o que a sua sprint pedia. Esta '
    + 'confere o sistema inteiro de uma vez, do jeito que quem o usa o vê: cada funcionalidade testada pela tela, '
    + 'com o resultado esperado escrito antes e o resultado obtido registrado pela própria execução.',
  ));
  c.push(p(
    `Os ${tela.casos.length} casos de teste desta parte não foram executados à mão e transcritos: o catálogo `
    + 'está no repositório (docs/12-plano-de-testes.md), e um script o executa num navegador de verdade, contra o '
    + 'sistema no ar, gravando o que a tela mostrou e uma captura de cada caso. Qualquer integrante roda de novo e '
    + 'vê o mesmo — e é assim que eles se demonstram na orientação (seção 8).',
  ));

  c.push(h2('As entregas do enunciado, e onde estão'));
  c.push(table([700, 3000, 5938], [
    ['#', 'Entrega', 'Evidência neste documento'],
    ['1', 'Testes funcionais', `Seções 1 e 2 — o plano de testes; ${funcionais.length} casos de cadastro, consulta, atualização, exclusão e autenticação, com o esperado e o obtido; a verificação de ponta a ponta; a campanha manual da equipe`],
    ['2', 'Correção de bugs', `Seção 5 — os ${bugs.length} defeitos registrados, com a causa, a correção e o Pull Request; e o que ficou pendente, com a ação prevista`],
    ['3', 'Testes de validação', `Seção 3 — ${validacao.length} casos pela tela, com a mensagem que a pessoa lê; as respostas da API a dado inválido; as regras de negócio`],
    ['4', 'Testes de navegação', `Seção 4 — ${navegacao.length} casos de menus, links, redirecionamentos, permissões e continuidade, em dois navegadores; a matriz de permissões do servidor`],
    ['5', 'Atualização da documentação', 'Seção 6 — o que mudou no sistema desde a Sprint 08, e cada documento revisado, com a versão'],
    ['—', 'Repositório, dificuldades e próximos passos', 'Seções 7, 9 e 10'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  c.push(h2('Números desta entrega'));
  c.push(table([6000, 3638], [
    ['Medida', 'Valor'],
    ['Casos de teste executados pela tela', `${passaram(tela.casos)} de ${tela.casos.length} como esperado`],
    ['— funcionais, de validação e de navegação', `${funcionais.length}, ${validacao.length} e ${navegacao.length}`],
    ['Casos de navegação também no Chrome', `${passaram(navegacaoChrome)} de ${navegacaoChrome.length}`],
    ['Verificação de ponta a ponta pela API', verificacao.replace(/^As /, '').replace(/\.$/, '')],
    ['Respostas da API a dado inválido', semRotulo(validacoes).replace(/\.$/, '')],
    ['Conferências de permissão', semRotulo(permissoes).replace(/\.$/, '')],
    ['Regras de negócio revisadas', `${regras.passaram} de ${regras.total} conferências, nas ${regras.linhas.length} regras`],
    ['Telas medidas no navegador', `${telas.telas} telas; nenhuma rolando nem com violação do axe`],
    ['Testes automatizados (as quatro suítes)', semRotulo(registroTestes).replace(/\.$/, '')],
    ['Defeitos registrados', `${bugs.length}: ${corrigidos.length} corrigidos, ${pendentes.length} pendentes`],
    ['Integrantes na campanha manual', `${testaram.length} de ${manual.length}`],
    ['Histórias da sprint', 'H104 a H106 — 11 pontos; o backlog foi de 484 para 495'],
  ], { zebra: true, boldCol: 0 }));

  // ============================================== 1. PLANO DE TESTES
  c.push(quebra());
  c.push(h1('1. O plano de testes'));
  c.push(p(
    'O plano está no repositório, em docs/12-plano-de-testes.md: os níveis de teste, o ambiente, os critérios de '
    + 'aprovação e o catálogo dos casos — para cada um, o requisito, o perfil, os passos e o resultado esperado. '
    + 'Ele foi escrito antes da execução, e é ele que o script executa.',
  ));

  c.push(h2('1.1 Os quatro níveis'));
  c.push(table([2000, 3300, 2700, 1638], [
    ['Nível', 'O que prova', 'Onde está', 'Quando roda'],
    ['Unidade e integração', 'Cada regra e cada rota da API, com o banco de teste; cada tela, com a API simulada e a acessibilidade conferida no fim', 'api/tests, web/src, nucleo/tests, modelo/tests', 'A cada Pull Request, na CI'],
    ['API de ponta a ponta', 'O sistema no ar responde como os requisitos dizem: fluxos, permissões e recusas', 'api/e2e', 'Antes de cada entrega'],
    ['Pela tela', 'O que a pessoa vê: os casos do catálogo, clicando como ela clica', 'scripts/testar_na_tela.py', 'Antes de cada entrega'],
    ['Medição', 'As telas a 768 e a 1.440 px, nos dois temas; as regras RN01 a RN11 numa base própria', 'scripts/medir_telas.py, scripts/revisar_regras.py', 'Antes de cada entrega'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(p(
    'Os dois primeiros níveis já existiam. O terceiro é desta sprint: até aqui, a tela só era testada com a API '
    + 'simulada, e teste com a API simulada não prova o contrato entre as duas.',
    { size: 19 },
  ));

  c.push(h2('1.2 O ambiente'));
  c.push(table([3200, 6438], [
    ['Item', 'Como foi'],
    ['O sistema', 'O mesmo do docker compose, no ar, com o perfil do modelo de linguagem'],
    ['A base', 'A de demonstração, com os dados do gerador sintético: nenhum dado real'],
    ['O navegador', `${tela.navegador}; a navegação também no ${chrome.navegador}`],
    ['A execução', `${tela.quando}, contra ${tela.web}`],
    ['As contas', 'Uma por perfil, criadas pela própria execução, com a marca dela no login e a senha só na memória do script'],
    ['O que fica na base', 'Nada: o que a execução grava sai no fim, e as contas são desativadas — não apagadas, porque a auditoria aponta para o autor'],
  ], { zebra: true, boldCol: 0, size: 18 }));

  c.push(h2('1.3 Como um caso é executado, e quando ele passa'));
  c.push(p(
    'O script lê o catálogo e recusa rodar se um caso do documento não tiver o código que o executa, ou o '
    + 'contrário. Cada caso abre um navegador limpo, faz os passos e registra o obtido. Ele só passa se a tela '
    + 'fizer o que o esperado diz e nada mais der errado no caminho: nenhuma resposta da API com erro que o caso '
    + 'não provocou de propósito, nenhum erro no console, nenhuma exceção na página. Um caso, como sai no registro:',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/casos.txt`, 'CT-F10  ', 'CT-F11  ').slice(0, -1)));

  c.push(h2('1.4 As suítes automatizadas'));
  c.push(p(
    `O registro foi gerado rodando as quatro suítes. A do otimizador roda na imagem do núcleo compilado com CUDA, com a placa da máquina — ${placa}.`,
    { size: 19 },
  ));
  c.push(table([3900, 1150, 1150, 1150, 1100, 1188], [
    ['Suíte', 'Testes', 'Passaram', 'Falharam', 'Pulados', 'Tempo'],
    ...[api, modelo, otimizador, interfaceWeb].map((s) => [
      s.nome, String(s.total), String(s.passaram), String(s.falharam), String(s.pulados), `${s.segundos} s`,
    ]),
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroTestes), s: 19 }]));

  // ============================================== 2. TESTES FUNCIONAIS
  c.push(quebra());
  c.push(h1('2. Testes funcionais'));
  c.push(p(
    `Os ${funcionais.length} casos funcionais cobrem cada módulo: o cadastro, a consulta, a atualização e a `
    + 'exclusão de usuários, de parceiros e das ações do catálogo; a autenticação; a importação; o painel; o '
    + 'modelo, a campanha e o benchmark; as mensagens e a aprovação; o assistente; os relatórios; a auditoria; a '
    + 'configuração; e o portal do parceiro. O esperado é o do catálogo; o obtido é o que a execução registrou.',
  ));
  c.push(espaco(40));
  c.push(tabelaDeCasos(funcionais));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: `${passaram(funcionais)} de ${funcionais.length} casos funcionais como esperado.`, s: 19 }]));

  c.push(quebra());
  c.push(h2('2.1 As evidências dos principais'));
  c.push(p('As capturas são as da própria execução, tiradas no fim de cada caso.', { size: 19 }));
  c.push(...figura('CT-F10', 'CT-F10 — o parceiro cadastrado, com a categoria sugerida pelo nome e aceita', 560));
  c.push(...figura('CT-F17', 'CT-F17 — a importação gravada: o período aparece em "Importações anteriores"', 560));
  c.push(...figura('CT-F22', 'CT-F22 — o plano de campanha calculado, com o ganho esperado marcado como estimativa', 560));
  c.push(...figura('CT-F28', 'CT-F28 — a fila de aprovação de uma geração de mensagens, depois de aprovar uma', 560));
  c.push(...figura('CT-F26', 'CT-F26 — o benchmark: o mesmo problema em cada modo de execução', 560));
  c.push(...figura('CT-F38', 'CT-F38 — o portal do parceiro: só os indicadores dele', 560));

  c.push(quebra());
  c.push(h2('2.2 A verificação de ponta a ponta, pela API'));
  c.push(p(
    'O roteiro de api/e2e/verificacao.py percorre o sistema inteiro pela API no ar — HTTP, cookie e banco de '
    + 'verdade —, agrupado pelos itens das entregas da disciplina. Ele importa numa semana do futuro e, no fim, '
    + 'confere que o banco voltou ao que era antes.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(secoesDe('verificacao.txt')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: verificacao, s: 19 }]));

  c.push(h2('2.3 A campanha manual da equipe'));
  c.push(p(
    'Além do script, cada integrante executou à mão um roteiro da sua área, no sistema no ar, olhando o que o '
    + 'script não vê: se o texto se entende, se a ordem dos passos faz sentido, se algo parece errado. O registro '
    + 'é o comentário de cada um, com a própria conta, na issue #256.',
    { size: 19 },
  ));
  c.push(table([1500, 2600, 1150, 2500, 1888], [
    ['Integrante', 'Área', 'Data', 'Casos executados', 'Resultado'],
    ...manual.flatMap((m) => (m.execucoes.length
      ? m.execucoes.map((e) => [m.nome, m.area, e.data, e.casos, e.resultado])
      : [[m.nome, m.area, '—', 'Não executado até a geração deste documento', '—']])),
  ], { zebra: true, boldCol: 0, size: 16 }));

  // ============================================== 3. VALIDAÇÃO
  c.push(quebra());
  c.push(h1('3. Testes de validação'));
  c.push(p(
    'O sistema recusa o que não pode aceitar e diz por quê, no lugar em que a pessoa está olhando: o campo '
    + 'obrigatório vazio, o formato errado, o valor fora da faixa e o pedido que fere uma regra de negócio. Em '
    + 'cada caso abaixo, o obtido é a mensagem que a tela mostrou.',
  ));
  c.push(espaco(40));
  c.push(tabelaDeCasos(validacao));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: `${passaram(validacao)} de ${validacao.length} casos de validação como esperado.`, s: 19 }]));

  c.push(quebra());
  c.push(h2('3.1 As mensagens, na tela'));
  c.push(...figura('CT-V03', 'CT-V03 — o formulário enviado vazio: uma mensagem embaixo de cada campo obrigatório', 560));
  c.push(...figura('CT-V08', 'CT-V08 — o nome que já existe: a recusa leva ao cadastro do parceiro existente', 560));
  c.push(...figura('CT-V10', 'CT-V10 — a importação sem o período, recusada na entrada (RN03)', 560));
  c.push(...figura('CT-V15', 'CT-V15 — a campanha que não cabe no orçamento: nenhum plano parcial, e quanto falta (RN07)', 560));

  c.push(quebra());
  c.push(h2('3.2 As respostas da API a dado inválido'));
  c.push(p(
    'Muitas recusas não têm tela que as provoque — um pedido malformado, um perfil chamando a rota de outro. A '
    + 'transcrição de api/e2e/validacoes.py as provoca contra a API no ar, com o esperado de cada uma conferido '
    + 'contra o que voltou, nestas seções:',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(secoesDe('validacoes.txt')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(validacoes), s: 19 }]));

  c.push(h2('3.3 As regras de negócio'));
  c.push(p(
    'As onze regras, cada uma contra um cenário desenhado para os ramos dela, numa base só da revisão '
    + '(scripts/revisar_regras.py).',
    { size: 19 },
  ));
  c.push(table([1300, 6300, 2038], [
    ['Regra', 'O que ela garante', 'Conferências'],
    ...regras.linhas.map((r) => [r.codigo, r.nome, `${r.certas} de ${r.certas}`]),
  ], { zebra: true, boldCol: 0, size: 17, align: [null, null, AlignmentType.CENTER] }));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: `${regras.passaram} de ${regras.total} conferências passaram.`, s: 19 }]));

  // ============================================== 4. NAVEGAÇÃO
  c.push(quebra());
  c.push(h1('4. Testes de navegação'));
  c.push(p(
    'Os menus de cada perfil, os redirecionamentos, os links entre as telas, as permissões e a continuidade dos '
    + `fluxos — a sessão que termina no meio, o formulário com alterações não salvas, o teclado, a tela estreita. Os ${navegacao.length} `
    + `casos rodaram no ${tela.navegador.split(' ').slice(0, 2).join(' ')} e, de novo, no ${chrome.navegador.split(' ').slice(0, 2).join(' ')}.`,
  ));
  c.push(espaco(40));
  c.push(tabelaDeCasos(navegacao));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, {
    t: `${passaram(navegacao)} de ${navegacao.length} no ${tela.navegador}; ${passaram(navegacaoChrome)} de ${navegacaoChrome.length} no ${chrome.navegador}.`,
    s: 19,
  }]));

  c.push(quebra());
  c.push(h2('4.1 O que a pessoa vê'));
  c.push(...figura('CT-N05', 'CT-N05 — o Analista pelo endereço do Modelo: o perfil, o endereço e nenhuma chamada à API', 560));
  c.push(...figura('CT-N07', 'CT-N07 — o endereço que não existe, mostrado como foi pedido, com o caminho de volta', 560));
  c.push(...figura('CT-N12', 'CT-N12 — o aviso de alterações não salvas, ao sair de um cadastro alterado', 560));
  c.push(...figura('CT-N15', 'CT-N15 — a 768 px, o menu vira gaveta, aberta pelo botão do cabeçalho', 360));

  c.push(quebra());
  c.push(h2('4.2 As permissões, no servidor'));
  c.push(p(
    'Esconder um item do menu não é controle de acesso: o servidor recusa sozinho. A transcrição de '
    + 'api/e2e/transcricao_permissoes.py exercita a matriz perfil × rota inteira contra a API no ar.',
    { size: 19 },
  ));
  c.push(table([6000, 3638], [
    ['Na matriz', 'Quantas'],
    ['Rotas da API, lidas das rotas registradas na aplicação', acesso.rotas],
    ['Combinações negadas, conferidas com 403', acesso.negacoes],
    ['Leituras permitidas, conferidas', acesso.leituras],
    ['Rotas que recusam quem não tem sessão', acesso.semSessao],
    ['Escritas permitidas, não exercitadas (gravariam na base)', acesso.escritas],
    ['Respostas 403 recebidas, e registros de acesso negado na trilha', `${acesso.recebidos} e ${acesso.naTrilha}`],
  ], { zebra: true, boldCol: 0 }));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(permissoes), s: 19 }]));

  c.push(h2('4.3 O mapa da navegação'));
  c.push(diagrama('navegacao-telas', 600, PARTE_IX));
  c.push(legenda('As telas e os caminhos entre elas, na interface v2 (docs/09)'));

  // ============================================== 5. BUGS
  c.push(quebra());
  c.push(h1('5. Registro de bugs e correções'));
  c.push(p(
    'Todo defeito vira issue com o rótulo "fix" — o que apareceu, a causa, a correção e como foi encontrado — e '
    + 'é fechado pelo Pull Request que o corrige; o que não é corrigido fica aberto, com a ação prevista. O '
    + 'registro é gerado dessas issues: as abertas desde o PDF da Sprint 08, fora as que o registro dela já tinha.',
  ));
  if (daTroca.length) {
    c.push(p(
      `${daTroca.length} dos ${bugs.length} foram achados na troca da interface (H103): pelo laboratório em que ela foi `
      + 'testada antes de entrar, pela medição oficial das telas e pela suíte de testes refeita. Foram corrigidos '
      + 'no próprio Pull Request da troca (#242), e registrados como issue depois da correção — o corpo de cada um '
      + 'diz quando ele foi achado.',
      { size: 19 },
    ));
  }
  c.push(table([900, 5300, 1500, 1938], [
    ['Issue', 'Defeito', 'Situação', 'Correção'],
    ...bugs.map((b) => [
      `#${b.numero}`, b.titulo, b.situacao === 'corrigido' ? 'Corrigido' : 'Pendente',
      b.prs.length ? b.prs.map((n) => `#${n}`).join(', ') : '—',
    ]),
  ], { zebra: true, align: [AlignmentType.CENTER, null, AlignmentType.CENTER, AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroBugs), s: 19 }]));
  const limpo = (t) => t.replace(/`/g, '').replace(/\*\*/g, '');
  for (const b of bugs) {
    c.push(espaco(60));
    c.push(rich([{ t: `#${b.numero} — ${b.titulo}`, b: true, s: 19 }]));
    c.push(p(`Apareceu: ${limpo(b.apareceu)}`, { size: 18 }));
    c.push(p(`Causa: ${limpo(b.causa)}`, { size: 18 }));
    c.push(p(`${b.situacao === 'corrigido' ? 'Correção' : 'O que fazer'}: ${limpo(b.correcao)}`, { size: 18 }));
    c.push(p(`Como foi encontrado: ${limpo(b.encontrado)}`, { size: 18 }));
  }

  // ============================================== 6. DOCUMENTAÇÃO
  c.push(quebra());
  c.push(h1('6. Atualização da documentação'));
  c.push(h2('6.1 O que mudou no sistema desde a Sprint 08'));
  c.push(p(
    'Duas histórias entraram depois do PDF da Sprint 08, e a documentação precisava dizer o sistema como ele '
    + 'ficou com elas:',
  ));
  c.push(bullet(
    'A interface refeita (H103, #242): a camada visual inteira, com a fonte, o menu como mapa de áreas e a '
    + 'estimativa marcada, sem mudar nenhuma tela de lugar nem nenhuma rota da API. Foi a única exceção ao '
    + 'congelamento de 25/10, aprovada pela equipe; a decisão está na ADR-015, e o sistema visual novo, no docs/09.',
  ));
  c.push(bullet(
    'O acesso de fora da máquina por rede privada (H102, #240): o sistema continua fora da internet, e os '
    + 'aparelhos da equipe chegam a ele por uma rede só deles (ADR-014).',
  ));
  c.push(...figura('interface-antes-painel', 'O painel na interface v1, como entrou no PDF da Sprint 08', 560));
  c.push(...figura('CT-F19', 'O mesmo painel na interface v2, na execução do caso CT-F19 desta entrega', 560));

  c.push(quebra());
  c.push(h2('6.2 Os documentos revisados'));
  c.push(p(
    'Cada documento foi conferido contra o sistema de hoje, e cada um subiu a versão, com a data. O que não '
    + 'aconteceu como estava escrito foi corrigido para dizer o que aconteceu — e não apagado.',
    { size: 19 },
  ));
  c.push(table([2300, 1300, 6038], [
    ['Documento', 'Versão', 'O que mudou'],
    ['12 — Plano de testes', 'nova, 1.0', 'Os quatro níveis, o ambiente, os critérios e o catálogo dos casos desta parte'],
    ['01 — Visão do produto', '1.0 → 1.1', 'Os requisitos citados pela numeração de hoje'],
    ['03 — Casos de uso', '2.3 → 2.4', 'O diagrama com os dezesseis casos (abaixo); as telas pela interface v2'],
    ['04 — Product backlog', '2.5 → 2.6', 'As histórias H104 a H106; o escopo em 495 pontos'],
    ['05 — Cronograma', '3.6 → 3.7', 'A Sprint 09 no mapeamento, no Gantt e nos marcos; a validação do README (H72) adiada, com data'],
    ['06 — Equipe e processo', '2.0 → 2.1', 'A estratégia de testes; a apresentação do núcleo remarcada; a programação em par do núcleo, que não aconteceu'],
    ['07 — Arquitetura', '2.3 → 2.4', 'A versão do Node; as operações da API contadas'],
    ['09 — Sistema visual', '2.0 → 2.1', 'O mapa de navegação da interface v2 renderizado de novo'],
    ['10 — Diagrama de classes', '2.0 → 2.1', 'Os serviços e as rotas dos relatórios, da auditoria e da ajuda; as tabelas e os testes contados'],
    ['11 — Rastreabilidade', '1.2 → 1.3', 'A navegação conferida também no Chrome'],
    ['README e validação do README', '—', 'Como rodar os testes da interface, os casos pela tela e as medições; o roteiro da H72 pela interface v2'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(espaco(60));
  c.push(p(
    'Os documentos 02 (requisitos) e 08 (modelo de dados) foram conferidos e não precisaram mudar: nenhum '
    + 'requisito e nenhuma tabela mudou desde a Sprint 08.',
    { size: 19 },
  ));
  c.push(h2('6.3 O diagrama de casos de uso'));
  c.push(diagrama('casos-de-uso-atual', 420, PARTE_IX));
  c.push(legenda('Os dezesseis casos de uso, agrupados pelas áreas do menu (docs/03)'));

  // ============================================== 7. REPOSITÓRIO
  c.push(quebra());
  c.push(h1('7. Repositório, commits e revisões'));
  c.push(espaco(40));
  c.push(rich([{ t: 'Repositório: ', s: 21 }, { t: REPO, b: true, s: 21, c: '2C5B8F' }]));
  c.push(espaco(100));
  c.push(p(
    'Gerado do histórico do git, lido da branch principal do repositório remoto. A janela da Sprint 08 fecha no '
    + 'Pull Request do PDF dela (#238); o que entrou depois dele é desta entrega.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/commits.txt`, 'Totais', 'Por tipo')));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/commits.txt`, 'Sprint 09 — ')));

  c.push(quebra());
  c.push(h2('7.1 Autoria e coautoria'));
  const coautoria = coautores.map((x) => `${x.nome.split(' ')[0]} ${x.n}`).join(', ');
  c.push(p(
    `Os ${totalDeCommits} commits do histórico têm ${autores.length === 1 ? 'o mesmo autor' : `${autores.length} autores`}; `
    + `os demais integrantes aparecem como coautores, pela área de cada um (${coautoria}).`,
  ));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/commits.txt`, 'Autoria e coautoria', 'Pull Requests incorporados, por')));

  c.push(h2('7.2 Revisões'));
  c.push(p(
    'Para cada Pull Request incorporado desde o PDF da Sprint 08: quem abriu, quem foi convidado a revisar, quem '
    + `revisou e com que resultado. ${aprovadosNoGithub} de ${revisoes.length} têm a aprovação de um colega registrada no `
    + 'GitHub; a pendência da Pré-Banca segue na seção 10.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/revisoes.txt`, 'Resumo', 'Resultado:')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroRevisoes), s: 19 }]));

  // ============================================== 8. EXECUÇÃO
  c.push(quebra());
  c.push(h1('8. Como executar e demonstrar os testes'));
  c.push(p('O sistema sobe com um comando; os testes rodam contra ele. A senha do administrador vai na variável GIH_ADMIN_SENHA.'));
  c.push(espaco(40));
  c.push(...mono([
    'docker compose --profile assistente up -d                  # o sistema, com o modelo de linguagem',
    'cd web && npm ci && npm run lint && npm test               # a suíte da interface',
    'cd api && pytest && ruff check .                           # a suíte da API',
    'api/.venv/Scripts/python scripts/testar_na_tela.py --saida <pasta>     # os casos pela tela',
    'api/.venv/Scripts/python scripts/testar_na_tela.py --navegador chrome --so CT-N   # a navegação no Chrome',
    'cd api && python e2e/verificacao.py                        # a verificação de ponta a ponta',
    'cd api && python e2e/validacoes.py                         # as respostas a dado inválido',
  ]));
  c.push(espaco(120));
  c.push(h2('8.1 Roteiro para a orientação'));
  c.push(table([700, 8938], [
    ['#', 'Passo'],
    ['1', 'Subir o sistema e abrir o docs/12 no GitHub: o catálogo, com o esperado de cada caso'],
    ['2', 'Rodar, com a janela aberta: testar_na_tela.py --ver --so CT-F01,CT-F02,CT-V08,CT-V10,CT-N05,CT-N13'],
    ['3', 'Acompanhar na tela: entrar e sair; o nome repetido recusado com o link para o existente; a importação sem período recusada; o Analista barrado no Modelo; a sessão que termina e volta ao mesmo lugar'],
    ['4', 'Abrir o casos.txt da execução: o esperado e o obtido de cada caso, e as capturas ao lado'],
    ['5', 'Mudar um caso no docs/12 sem mudar o script, e rodar de novo: o script recusa, porque o catálogo e o código divergem'],
    ['6', 'Abrir uma issue de defeito desta entrega (seção 5): o que apareceu, a causa, a correção e o Pull Request que a fechou, com o teste que reprova sem a correção'],
    ['7', 'Rodar a verificação de ponta a ponta e mostrar a última checagem: o banco voltou ao que era antes'],
  ], { zebra: true, align: [AlignmentType.CENTER], size: 17 }));

  // ============================================== 9. DIFICULDADES
  c.push(quebra());
  c.push(h1('9. Dificuldades encontradas'));
  const dificuldade = (nome, causa, correcao) => {
    c.push(h2(nome));
    c.push(p(causa));
    c.push(rich([{ t: 'O que foi feito: ', b: true, s: 19 }, { t: correcao, s: 19 }]));
  };
  dificuldade(
    '9.1 A interface nova quebrou as ferramentas de evidência',
    'Os roteiros de captura das entregas anteriores procuravam a tela pelos nomes da interface v1, e paravam já '
    + 'na entrada. E o modelo de issue de defeito não tinha as seções que o registro de bugs lê: o primeiro defeito '
    + 'aberto por ele faria o registro parar.',
    'O ponto comum da captura passou a usar os nomes da interface v2, e o modelo de defeito ganhou as quatro '
    + 'seções do registro, antes de qualquer teste da sprint (#257). As entregas já enviadas não mudam: elas leem '
    + 'as capturas e os registros guardados na pasta de cada uma.',
  );
  dificuldade(
    '9.2 Testar na base da equipe sem sujá-la',
    'Os testes pela tela gravam: cadastram, importam, calculam planos, mudam um limiar. Na primeira versão do '
    + 'script, um caso falhou no meio e deixou um limiar da segmentação alterado na base da equipe.',
    'O valor foi restaurado no mesmo dia, e o caso passou a devolvê-lo mesmo quando falha. Toda execução marca o '
    + 'que cria — o login das contas, o nome dos parceiros e das ações — e apaga tudo no fim, pela mesma limpeza '
    + 'da verificação de ponta a ponta, que ganhou as ações do catálogo.',
  );
  dificuldade(
    '9.3 O bloqueio de entrada não se testa pela tela',
    'Cinco tentativas erradas bloqueiam a entrada por origem. Provocá-las pela tela travaria, por quinze '
    + 'minutos, a entrada de todos na máquina — inclusive a de quem está usando o sistema.',
    'O script faz no máximo duas tentativas recusadas por execução, e o bloqueio fica no teste da API. O '
    + 'catálogo diz isso, na seção do que não roda pela tela.',
  );
  dificuldade(
    '9.4 O que parecia defeito e não era',
    'A campanha com orçamento de R$ 1,00 não deu "inviável": deu um plano sem nenhuma ação, explicado na tela. E '
    + 'a interface não tem como criar uma categoria nova.',
    'O primeiro é o comportamento certo — inviável é quando as restrições se contradizem, como cotas mínimas que '
    + 'custam mais que o orçamento, e é isso que o caso CT-V15 testa agora. O segundo é uma limitação registrada '
    + 'no docs/07: o caso de uso não pede essa tela, e as categorias vêm do gerador; criar uma nova é pela API.',
  );

  // ============================================== 10. PENDÊNCIAS E PRÓXIMOS PASSOS
  c.push(quebra());
  c.push(h1('10. Pendências e próximos passos'));
  c.push(p('O que não está concluído, por que, e como a equipe vai resolver:'));
  c.push(table([2600, 3000, 2800, 1238], [
    ['Pendência', 'Por que', 'Ação prevista', 'Quando'],
    ['Validação do README por quem não o escreveu (H72; RNF07, RNF27)', 'Precisa de uma máquina limpa e de um integrante que não escreveu o código', 'Thiago ou João Pedro seguem o docs/validacao-do-readme.md e registram na issue #164', 'Até 20/11'],
    ...pendentes.map((b) => [`Defeito #${b.numero}`, limpo(b.titulo), limpo(b.correcao), '—']),
    ['Aprovação dos Pull Requests registrada no GitHub (RNF25)', `${aprovadosNoGithub} de ${revisoes.length} desta entrega têm a aprovação de um colega`, 'Cada Pull Request aprovado por um integrante no GitHub antes da incorporação', 'A partir de agora'],
    ['O Firefox (RNF08)', 'Não está instalado na máquina de teste', 'Rodar os casos de navegação nele, com o mesmo script', 'Antes da entrega final'],
    ['Os 52 períodos (RNF04)', 'Medido com 10.000 parceiros e 12 períodos', 'Medir com a base de 52 períodos', 'Antes da entrega final'],
    ['O usuário novo observado (RNF20)', 'A interface está em português e tem ajuda; ninguém de fora foi observado usando', 'Uma sessão com alguém de fora da equipe, sem ajuda', 'Antes da gravação'],
    ['A transferência do núcleo (R4)', 'O núcleo foi construído por uma pessoa só', 'Apresentação à equipe, e as perguntas prováveis da banca em docs/banca.md', 'Até 08/11'],
    ['Os vídeos (H74, H75)', 'Ficam para depois do congelamento, com a interface que fica', 'Roteiro, base de demonstração final e gravação', '09/11 a 04/12'],
  ], { zebra: true, boldCol: 0, size: 16 }));
  c.push(espaco(80));
  c.push(h2('Próximos passos'));
  c.push(bullet('A base de demonstração final, recriada antes da gravação dos vídeos (09/11), com a rede, o modelo treinado, um plano, mensagens na fila e o benchmark com a GPU.'));
  c.push(bullet('Os casos de teste pela tela de novo antes de cada entrega e da banca: o catálogo é vivo, e caso novo entra no docs/12 junto do código que o executa.'));
  c.push(bullet(`Os não funcionais ainda em parte — ${rnf.pendentes.map((r) => r.id).join(', ')} — fechados ou explicados antes da entrega final, cada um com a ação da tabela acima.`));
  c.push(bullet('As entregas da disciplina que vierem, na ordem dos enunciados; o código continua congelado, e só entra correção.'));

  return c;
}

module.exports = { montar };
