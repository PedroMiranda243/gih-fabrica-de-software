/**
 * Parte VIII do documento — Sprint 08 acadêmica: funcionalidades concluídas.
 *
 * O enunciado pede quatro entregas — todas as funcionalidades implementadas, o
 * controle de permissões, as melhorias de usabilidade e a revisão geral das
 * regras de negócio —, cada uma com evidência, mais as alterações de escopo com
 * a justificativa, o link do repositório, as dificuldades e os próximos passos.
 * Como nas partes anteriores, nenhum número é digitado aqui:
 *
 * - "todas as funcionalidades implementadas" sai da matriz de rastreabilidade
 *   (`docs/11`), **na cópia de `evidencias/sprint08/medicoes/`**, que um teste
 *   confere contra as rotas, as telas e os testes que ela cita;
 * - as conferências dos fluxos e das permissões vêm das transcrições em
 *   `evidencias/sprint08/`, que os scripts de `api/e2e/` escrevem contra a
 *   aplicação no ar;
 * - o que cada tela disse vem dos registros da captura (`capturar_sprint08.js`);
 * - a revisão das regras vem do relatório de `scripts/revisar_regras.py`, e a
 *   medição das telas, de `acessibilidade.md` — as duas na cópia desta entrega;
 * - as contagens de testes, bugs, commits e revisões vêm dos registros que os
 *   scripts geram a partir da suíte rodada, das issues, do git e dos Pull
 *   Requests.
 *
 * `aprovado()` recusa gerar se uma evidência registrar falha, e os leitores de
 * medida recusam se não acharem o número.
 *
 * **As figuras desta parte estão congeladas** em `diagramas/parte-viii/`, como
 * as das Partes II, VI e VII.
 *
 * **Os títulos desta parte ficam com o que vem depois deles.** Na Sprint 07, um
 * título caiu sozinho no pé da página duas vezes, e o PDF precisou de três
 * exportações. Os títulos daqui saem com "manter com o próximo", e a figura,
 * com a legenda dela — em auxiliares próprios, sem tocar nos das partes
 * entregues.
 */
const fs = require('fs');
const path = require('path');
const { AlignmentType, HeadingLevel, Paragraph, TextRun } = require('docx');
const { AZUL, p, rich, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { diagrama, evidencia, legenda } = require('../comum/figuras');
const { trecho, json } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';
const EVIDENCIAS = path.join(__dirname, '..', 'evidencias');
const PARTE_VIII = 'parte-viii';

/*
 * Os poucos números que não saem de um arquivo de evidência, com a origem de
 * cada um. `null` é "ainda não medido", e a geração recusa.
 */
const MEDIDAS = {
  tabelas: 20, // catálogo do banco no ar, 02/10 — as mesmas da Sprint 07: nenhuma migração nesta entrega
};

function medida(nome) {
  const valor = MEDIDAS[nome];
  if (valor === null || valor === undefined) {
    throw new Error(`Medida "${nome}" não preenchida em secoes/sprint08.js — meça antes de gerar.`);
  }
  return String(valor);
}

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
const figura = (nome, texto, largura) => [evidencia(nome, largura, true), legenda(texto)];

// ------------------------------------------------------------------ leitores
/** As linhas do arquivo como saíram do script, sem quebrar: para ler, e não para mostrar. */
function cruas(nome) {
  const arquivo = path.join(EVIDENCIAS, nome);
  if (!fs.existsSync(arquivo)) throw new Error(`Falta ${nome}. Rode os scripts de evidência.`);
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n').split('\n');
}

/** A linha de resultado da evidência, e a recusa se ela registrar alguma falha. */
function aprovado(arquivo, marcador) {
  const linhas = cruas(arquivo);
  const linha = linhas.find((l) => l.includes(marcador));
  if (!linha) throw new Error(`Sem a linha de resultado em ${arquivo}.`);
  // `LOGIN_FALHA` é o nome de uma ação da trilha, e não uma falha: o `\b` não
  // separa o sublinhado da letra, e a palavra solta é a que reprova.
  const falhas = linhas.filter((l) => /\bFALHA\b/.test(l));
  if (falhas.length) {
    throw new Error(`${arquivo} registra ${falhas.length} falha(s) — corrija e gere a evidência de novo.`);
  }
  return linha.trim();
}

const semRotulo = (linha) => linha.replace(/^Resultado:\s*/, '');

/** As conferências (ok) de um trecho da evidência, sem as trocas em volta. */
function conferencias(nome, de, ate) {
  const linhas = cruas(nome);
  const inicio = linhas.findIndex((l) => l.includes(de));
  if (inicio < 0) throw new Error(`Não achei ${JSON.stringify(de)} em ${nome}.`);
  const resto = linhas.slice(inicio + 1);
  const fim = ate ? resto.findIndex((l) => l.includes(ate)) : -1;
  const achadas = (fim >= 0 ? resto.slice(0, fim) : resto)
    .filter((l) => /^\s+ok\s/.test(l))
    .map((l) => l.trimEnd());
  if (!achadas.length) throw new Error(`Nenhuma conferência entre ${JSON.stringify(de)} e ${JSON.stringify(ate)} em ${nome}.`);
  return achadas;
}

/** As quatro suítes, lidas do registro de testes. */
function suites() {
  const achadas = cruas('sprint08/testes.txt')
    .map((l) => /^\s{2}(\S.+?)\s{2,}(\d+) testes\s+(\d+) passaram\s+(\d+) falharam\s+(\d+) pulados\s+(\d+) s/.exec(l))
    .filter(Boolean)
    .map(([, nome, total, passaram, falharam, pulados, segundos]) => ({
      nome, total: Number(total), passaram: Number(passaram), falharam: Number(falharam), pulados: Number(pulados), segundos,
    }));
  if (achadas.length !== 4) throw new Error('O registro de testes não tem as quatro suítes.');
  return achadas;
}

/*
 * A cópia desta entrega, e não o arquivo vivo de `docs/` — ver o cabeçalho. Ela
 * é tirada junto das evidências, depois do último Pull Request de código:
 *   cp docs/medicoes/acessibilidade.md docs/medicoes/regras.md docs/entrega/evidencias/sprint08/medicoes/
 *   cp docs/11-rastreabilidade.md docs/entrega/evidencias/sprint08/medicoes/rastreabilidade.md
 */
function medicao(nome) {
  const arquivo = path.join(EVIDENCIAS, 'sprint08', 'medicoes', nome);
  if (!fs.existsSync(arquivo)) {
    throw new Error(`Falta sprint08/medicoes/${nome}. Copie o arquivo de docs/ antes de gerar.`);
  }
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n');
}

function achar(texto, regex, onde) {
  const m = regex.exec(texto);
  if (!m) throw new Error(`Não achei ${regex} em ${onde} — gere de novo ou corrija o leitor.`);
  return m;
}

/** A matriz de rastreabilidade: os requisitos por módulo e a situação dos não funcionais. */
function rastreabilidade() {
  const t = medicao('rastreabilidade.md');
  const modulos = [];
  let atual = null;
  for (const linha of t.split('\n')) {
    const modulo = /^### (Módulo \d+) — (.+)$/.exec(linha);
    if (modulo) {
      atual = { numero: modulo[1], nome: modulo[2], requisitos: [], fora: 0 };
      modulos.push(atual);
    }
    const rf = /^\| \*\*(RF\d+)\*\* \|/.exec(linha);
    if (rf && atual) {
      const celulas = linha.split(' | ');
      atual.requisitos.push(rf[1]);
      if (!celulas[celulas.length - 1].startsWith('Implementado')) atual.fora += 1;
    }
  }
  const naoFuncionais = [...t.matchAll(/^\| \*\*(RNF\d+)\*\* \| ([^|]+) \| .+ \| ([^|]+) \|$/gm)]
    .map(([, id, metrica, situacao]) => ({ id, metrica: metrica.trim(), situacao: situacao.trim() }));
  const total = modulos.reduce((s, m) => s + m.requisitos.length, 0);
  const fora = modulos.reduce((s, m) => s + m.fora, 0);
  if (!total || naoFuncionais.length !== 29) throw new Error('Não li a matriz de rastreabilidade inteira.');
  if (fora) throw new Error(`A matriz traz ${fora} requisito(s) funcional(is) não implementado(s) — o texto desta parte não vale.`);
  const pendentes = naoFuncionais.filter((r) => !r.situacao.startsWith('Atende'));
  return { modulos, total, naoFuncionais, pendentes };
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
  const data = achar(t, /^\| Data \| ([^|]+) \|$/m, 'regras.md')[1].trim();
  return { passaram, total, linhas, data };
}

/** As conferências de uma regra, do relatório da revisão: o que se confere, o esperado e o que voltou. */
function conferenciasDaRegra(codigo) {
  const t = medicao('regras.md');
  const inicio = t.indexOf(`\n## ${codigo} — `);
  if (inicio < 0) throw new Error(`Sem a seção da ${codigo} em regras.md.`);
  const fim = t.indexOf('\n## ', inicio + 4);
  return [...t.slice(inicio, fim < 0 ? undefined : fim).matchAll(/^\| (.+) \| (.+) \| (.+) \| ok \|$/gm)]
    .map(([, oQue, esperado, voltou]) => [oQue, esperado, voltou]);
}

/** Os números da matriz perfil × rota, da transcrição das permissões. */
function matrizDePermissoes() {
  const linhas = cruas('sprint08/permissoes.txt');
  const contar = (rotulo) => {
    const linha = linhas.find((l) => new RegExp(`^\\s+\\d+\\s+${rotulo}$`).test(l));
    if (!linha) throw new Error(`A transcrição das permissões não traz "${rotulo}".`);
    return linha.trim().split(/\s+/)[0];
  };
  const rotas = achar(linhas.join('\n'), /^(\d+) rotas, lidas das rotas registradas/m, 'permissoes.txt')[1];
  const negados = achar(linhas.join('\n'), /recebeu (\d+) respostas 403; a trilha tem (\d+) registros/, 'permissoes.txt');
  return {
    rotas,
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
  // A medição precisa ser de depois das telas desta entrega: a ajuda, a última, é de 02/10.
  const [dia, mes, ano] = data.split(' ')[0].split('/');
  if (`${ano}-${mes}-${dia}` < '2026-10-02') {
    throw new Error(`A medição das telas é de ${data}, de antes das telas da Sprint 08 — rode scripts/medir_telas.py de novo.`);
  }
  return { pares, telas, medidas, auditorias, data };
}

/** Os autores e coautores do registro de commits. */
function autoria() {
  const linhas = cruas('sprint08/commits.txt');
  const ler = (tipo) => linhas
    .map((l) => new RegExp(`^\\s{2}${tipo}\\s+(.+?)\\s{2,}(\\d+)$`).exec(l))
    .filter(Boolean)
    .map(([, nome, n]) => ({ nome, n: Number(n) }));
  const autores = ler('autor');
  const coautores = ler('coautor');
  if (!autores.length) throw new Error('O registro de commits não traz a autoria.');
  return { autores, coautores };
}

/** As recusas da seção da conta, na transcrição de validações, com o que cada uma esperava. */
const CASOS_DESTA_ENTREGA = [
  'A pessoa troca a própria senha e erra a atual',
  'Acerta a atual, e a nova é curta demais',
  'O administrador redefine a senha de alguém com uma fraca',
  'O administrador tenta redefinir a própria senha',
  'O analista tenta redefinir a senha de alguém',
  'Conta de perfil Parceiro sem parceiro',
  'Conta de perfil Parceiro com um parceiro que não existe',
  'Busca de parceiro com uma letra só',
];

function validacoesDestaEntrega() {
  const linhas = cruas('sprint08/validacoes.txt');
  const inicio = linhas.findIndex((l) => l.includes('[9/10] Conta'));
  const fim = linhas.findIndex((l, i) => i > inicio && (l.includes('[10/10]') || l.startsWith('Resultado:')));
  if (inicio < 0 || fim < 0) throw new Error('Não achei a seção da conta em validacoes.txt.');
  const resultados = linhas.slice(inicio, fim)
    .filter((l) => /^\s+ok\s+esperado:/.test(l))
    .map((l) => l.replace(/^\s+ok\s+esperado:\s*/, '').replace(/'([^']*)'/g, '“$1”'));
  if (resultados.length !== CASOS_DESTA_ENTREGA.length) {
    throw new Error(`A seção da conta em validacoes.txt tem ${resultados.length} conferências, e não ${CASOS_DESTA_ENTREGA.length}.`);
  }
  return CASOS_DESTA_ENTREGA.map((caso, i) => [caso, resultados[i]]);
}

/** As linhas de um bloco da captura: do rótulo dele até a linha em branco seguinte. */
function daCaptura(arquivo, rotulo) {
  const linhas = trecho(arquivo, rotulo);
  const fim = linhas.findIndex((l, i) => i > 0 && !l.trim());
  return fim > 0 ? linhas.slice(0, fim) : linhas;
}

function montar() {
  const c = [];
  const verificacao = aprovado('sprint08/verificacao.txt', 'verificações passaram');
  const permissoes = aprovado('sprint08/permissoes.txt', 'Resultado:');
  const comunicacao = aprovado('sprint08/comunicacao.txt', 'Resultado:');
  const validacoes = aprovado('sprint08/validacoes.txt', 'Resultado:');
  const registroTestes = aprovado('sprint08/testes.txt', 'Resultado:');
  const registroBugs = aprovado('sprint08/bugs.txt', 'Resultado:');
  const registroRevisoes = aprovado('sprint08/revisoes.txt', 'Resultado:');
  const [api, modelo, otimizador, interfaceWeb] = suites();
  const matriz = rastreabilidade();
  const regras = revisaoDasRegras();
  const acesso = matrizDePermissoes();
  const telas = medicaoDasTelas();
  const bugs = json('sprint08/bugs.json');
  const revisoes = json('sprint08/revisoes.json');
  const { autores, coautores } = autoria();

  const aprovadosNoGithub = revisoes.filter((r) => r.aprovado).length;
  const totalDeCommits = autores.reduce((s, a) => s + a.n, 0);
  const gpuDoRegistro = cruas('sprint08/testes.txt').find((l) => l.includes('GPU:'));
  if (!gpuDoRegistro) throw new Error('O registro de testes não diz em que placa o otimizador rodou.');
  const placa = gpuDoRegistro.split('GPU: ')[1].trim();
  const modeloDeLinguagem = cruas('sprint08/comunicacao.txt').find((l) => l.includes('O modelo de linguagem'));
  if (!modeloDeLinguagem) throw new Error('A transcrição da comunicação não diz se o modelo de linguagem estava no ar.');
  const comOModelo = modeloDeLinguagem.includes('está no ar');
  const atendidos = matriz.naoFuncionais.length - matriz.pendentes.length;

  c.push(quebra());
  c.push(h1('Parte VIII — Sprint 08: Funcionalidades Concluídas'));

  c.push(p(
    'As sete entregas anteriores construíram o sistema módulo a módulo. Esta fecha o que faltava para ele ser '
    + 'usado inteiro, só pela tela, por qualquer um dos quatro perfis — e confere, de três jeitos, que o que '
    + 'está escrito é o que o sistema faz: requisito por requisito, permissão por permissão e regra por regra.',
  ));
  c.push(p(
    'Cada item vem com execução real: transcrições e capturas geradas por scripts contra a aplicação no ar, '
    + 'sobre a base de demonstração, que é sintética. Onde o que se confere é um documento — a matriz de '
    + 'rastreabilidade, as regras de negócio —, quem confere é um teste ou um roteiro, e não uma leitura.',
  ));

  c.push(h2('As quatro entregas, e onde estão'));
  c.push(table([700, 2900, 1700, 4338], [
    ['#', 'Entrega', 'Situação', 'Evidência neste documento'],
    ['1', 'Todas as funcionalidades implementadas', 'Concluída', `Seções 1 e 2 — os ${matriz.total} requisitos funcionais com rota, tela e teste, e os fluxos de ponta a ponta`],
    ['2', 'Controle de permissões', 'Conferido', 'Seção 3 — a matriz perfil × rota exercitada, um acesso permitido e um negado por caso de uso, por objeto e por sessão'],
    ['3', 'Melhorias de usabilidade', 'Entregues', 'Seção 4 — o antes e o depois de cada uma, por heurística, e a medição das telas'],
    ['4', 'Revisão geral das regras de negócio', 'Feita', `Seção 5 — as ${regras.linhas.length} regras contra um cenário desenhado para cada ramo, e o que a revisão ajustou`],
    ['—', 'Alterações no escopo', 'Registradas', 'Seção 6 — o que mudou desde a Sprint 01, com a justificativa'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  c.push(h2('Números desta entrega'));
  c.push(table([6000, 3638], [
    ['Medida', 'Valor'],
    ['Histórias entregues', 'H92 a H101 — 33 pontos; o backlog foi de 440 para 473'],
    ['Requisitos novos', 'RF54 a RF56, e o caso de uso UC16'],
    ['Requisitos funcionais com rota, tela e teste conferidos', `${matriz.total} de ${matriz.total}`],
    ['Operações da API', `${acesso.rotas} — eram 78 na Sprint 07`],
    ['Tabelas no banco', `${medida('tabelas')} — as mesmas; nenhuma migração nesta entrega`],
    ['Telas medidas no navegador', `${telas.telas} — eram 26 na Sprint 07`],
    ['Testes da API', `${api.total}, ${api.passaram} passando, ${api.pulados} pulados`],
    ['Testes da interface', `${interfaceWeb.total}, todos passando`],
    ['Verificação de ponta a ponta contra a aplicação no ar', verificacao.replace(/^As /, '').replace(/\.$/, '')],
    ['Revisão das regras de negócio', `${regras.passaram} de ${regras.total} conferências, nas ${regras.linhas.length} regras`],
  ], { zebra: true, boldCol: 0 }));

  // ==================================== 1. FUNCIONALIDADES CONCLUÍDAS
  c.push(quebra());
  c.push(h1('1. Funcionalidades concluídas'));
  c.push(p(
    '"Todas as funcionalidades implementadas" é uma frase que qualquer documento escreve. Para ela valer alguma '
    + 'coisa, o levantamento desta entrega percorreu os requisitos um a um, procurando onde cada um está no '
    + 'sistema. Achou três que não se alcançavam pela tela, e fechou os três; e deixou a conferência '
    + 'automática, para a frase não envelhecer.',
  ));

  c.push(h2('1.1 O que faltava, e foi fechado'));
  c.push(table([2300, 3500, 3838], [
    ['Lacuna', 'Como estava', 'Como ficou'],
    ['Trocar a própria senha (RF07)', 'Existia na API desde a Sprint 04, sem tela', 'A Minha conta, pelo nome no cabeçalho, para os quatro perfis; o erro volta embaixo do campo'],
    ['Quem esquecia a senha', 'Não tinha como voltar: a saída era criar outra conta', 'O administrador redefine a senha de outro usuário (RF54, novo): todas as sessões da conta caem, e o evento entra na trilha, sem a senha'],
    ['A conta de perfil Parceiro (RF04)', 'Só se criava pela API: a tela não oferecia o perfil, porque o administrador não lista parceiros', 'A tela oferece o perfil, com uma busca do parceiro só pelo nome (RF56, novo), que devolve o nome e a situação, e nada mais'],
    ['Ajuda', 'Não havia: "Em risco", "Estimativa" e "ganho esperado" sem nenhum lugar que os explicasse', 'A tela de Ajuda (RF55, novo), com o que o perfil faz, os segmentos na ordem da regra, a estimativa e o ganho esperado'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(espaco(80));
  c.push(p(
    'Os três requisitos novos entraram no documento de requisitos antes do código, com o caso de uso da ajuda '
    + '(UC16) e os fluxos de senha nos casos de uso de autenticação e de usuários.',
    { size: 19 },
  ));

  c.push(h2('1.2 A matriz de rastreabilidade'));
  c.push(p(
    `Um documento novo, docs/11-rastreabilidade.md, diz para cada um dos ${matriz.total} requisitos funcionais `
    + 'o caso de uso que o exercita, as rotas da API que o atendem, as telas em que aparece e um teste que o '
    + 'cobra, pelo nome. Um teste da suíte lê esse documento a cada execução e reprova quando:',
  ));
  c.push(bullet('um requisito não está na matriz, ou o caso de uso citado não é o que a documentação associa a ele;'));
  c.push(bullet('uma rota citada não existe — ou uma rota da aplicação não está no documento;'));
  c.push(bullet('os perfis do requisito não são os das rotas dele: a união dos perfis que as rotas aceitam precisa ser exatamente a coluna Perfis do requisito;'));
  c.push(bullet('uma tela citada não é um endereço da interface, ou um teste citado não existe.'));
  c.push(espaco(60));
  c.push(table([1500, 4200, 1900, 2038], [
    ['Módulo', 'O que cobre', 'Requisitos', 'Implementados'],
    ...matriz.modulos.map((m) => [
      m.numero, m.nome, `${m.requisitos[0]} a ${m.requisitos[m.requisitos.length - 1]}`,
      `${m.requisitos.length - m.fora} de ${m.requisitos.length}`,
    ]),
    ['Total', '', '', `${matriz.total} de ${matriz.total}`],
  ], { zebra: true, boldCol: 0, align: [null, null, AlignmentType.CENTER, AlignmentType.CENTER] }));
  c.push(espaco(80));
  c.push(p(
    'Dois requisitos não têm rota nem tela próprias, e a matriz diz por quê: o registro na trilha de auditoria '
    + '(RF06) acontece dentro de cada operação sensível, e o gerador de dados sintéticos (RF16) é do terminal. '
    + 'Os dois têm teste.',
    { size: 19 },
  ));

  c.push(h2('1.3 O que a primeira conferência achou'));
  c.push(p(
    'Na primeira execução, o teste reprovou sete requisitos: a coluna Perfis deles dizia menos do que a matriz '
    + 'de permissões dos casos de uso e do que a API faz desde a Sprint 01. O administrador lê o painel — os '
    + 'indicadores, o ranking, a série, a distribuição por segmento e a mobilidade (RF17, RF18, RF19, RF20 e '
    + 'RF22) —, e o analista consulta o histórico das execuções e compara planos (RF34 e RF35). A coluna foi '
    + 'corrigida; nenhuma permissão mudou. É o tipo de divergência que uma leitura não acha, porque cada '
    + 'documento, sozinho, parecia certo.',
  ));

  c.push(h2('1.4 Os requisitos não funcionais'));
  c.push(p(
    `A mesma matriz diz, para cada um dos ${matriz.naoFuncionais.length} requisitos não funcionais, onde a `
    + `métrica de aceitação é conferida — por teste, por medição registrada ou por configuração do repositório. `
    + `${atendidos} estão atendidos. Os outros ${matriz.pendentes.length} não dependem de código novo: são `
    + 'medições e validações, e ficam declarados.',
  ));
  c.push(table([1100, 3000, 5538], [
    ['Requisito', 'Métrica de aceitação', 'Como está'],
    ...matriz.pendentes.map((r) => [r.id, r.metrica.replace(/`/g, ''), r.situacao.replace(/`/g, '')]),
  ], { zebra: true, boldCol: 0, size: 17 }));

  // ======================================= 2. PRINCIPAIS FLUXOS
  c.push(quebra());
  c.push(h1('2. Os principais fluxos em funcionamento'));
  c.push(p(
    'O fluxo que o produto promete vai do relatório importado à mensagem pronta para envio: importar, analisar, '
    + 'prever, otimizar, comunicar. As entregas anteriores mostraram os três primeiros módulos. Esta mostra o '
    + 'caminho inteiro, com os dois que nenhuma entrega tinha apresentado — a central de comunicação e o '
    + 'assistente — e o portal do parceiro.',
  ));
  c.push(p(
    comOModelo
      ? 'As capturas e a transcrição foram tiradas com o modelo de linguagem no ar, rodando na própria máquina. '
        + 'Ele redige as mensagens e as respostas; os números vêm do sistema, e a guarda numérica confere cada texto.'
      : 'As capturas e a transcrição foram tiradas sem o modelo de linguagem no ar: as mensagens saem do modelo '
        + 'fixo e o assistente se diz indisponível, que é o que o sistema faz sem ele.',
    { size: 19 },
  ));

  c.push(h2('2.1 Importar e analisar'));
  c.push(...figura('sprint08/fluxo-1-importacao-previa', 'A prévia da importação: o que foi reconhecido e o que foi rejeitado, com o motivo, antes de gravar.'));
  c.push(...mono(daCaptura('sprint08/fluxos.txt', '1. Importação')));
  c.push(quebra());
  c.push(...figura('sprint08/fluxo-2-painel', 'O painel da rede: os indicadores, a série, a distribuição por segmento e o ranking.'));
  c.push(...mono(daCaptura('sprint08/fluxos.txt', '2. Painel')));

  c.push(quebra());
  c.push(h2('2.2 Prever e otimizar'));
  c.push(...figura('sprint08/fluxo-3-modelo', 'O modelo de previsão em uso, com as métricas dele contra as referências.', 560));
  c.push(...mono(daCaptura('sprint08/fluxos.txt', '3. Modelo')));
  c.push(espaco(80));
  c.push(...figura('sprint08/fluxo-4-campanha-plano', 'O plano de campanha que o otimizador devolveu, com o custo, o ganho esperado e as cotas.'));
  c.push(...mono(daCaptura('sprint08/fluxos.txt', '4. Campanha')));

  c.push(quebra());
  c.push(h2('2.3 Comunicar: das mensagens à aprovação'));
  c.push(p(
    'O analista gera uma mensagem para cada parceiro do plano, com a ação que o plano lhe deu. Todas nascem '
    + 'pendentes. Só um gestor decide — aprova, edita ou rejeita —, e só a aprovada vai para o arquivo de envio: '
    + 'o sistema não envia nada (RN06).',
  ));
  c.push(...figura('sprint08/fluxo-5-mensagens-geradas', 'As mensagens do plano, geradas uma a uma, com o redator de cada uma.'));
  c.push(...mono(daCaptura('sprint08/fluxos.txt', '5. Mensagens')));
  c.push(quebra());
  c.push(...figura('sprint08/fluxo-6-aprovacao-fila', 'A fila de aprovação do gestor: cada mensagem com os dados de onde ela saiu e os três botões.'));
  c.push(quebra());
  c.push(...figura('sprint08/fluxo-6-aprovacao-editada', 'Depois de aprovar uma, editar outra e rejeitar uma terceira: a editada aponta o número que não veio dos dados.'));
  c.push(...figura('sprint08/fluxo-7-aprovacao-historico', 'O histórico das aprovadas, com quem decidiu e quando, e o caminho para o arquivo de envio.'));
  c.push(...mono(daCaptura('sprint08/fluxos.txt', '6. Aprovação')));

  c.push(quebra());
  c.push(h2('2.4 Perguntar: o assistente'));
  c.push(p(
    'O assistente responde sobre o que o sistema já calculou, e diz de onde veio. O que ele não sabe, ele diz '
    + 'que não sabe: a pergunta que pede uma conta e a pergunta fora do catálogo recebem a abstenção, e não um '
    + 'palpite (RN08).',
  ));
  c.push(...figura('sprint08/fluxo-8-assistente', 'Uma abstenção e uma resposta: a pergunta que pede conta, e a rede na última semana, com a fonte.', 520));
  c.push(quebra());
  c.push(h2('2.5 O relatório, e o portal do parceiro'));
  c.push(...figura('sprint08/fluxo-9-relatorio-campanha', 'O relatório da campanha: o plano resumido por ação, por categoria e por segmento.', 560));
  c.push(...figura('sprint08/permissoes-portal-parceiro', 'O portal do parceiro: o histórico dele, e nada da rede.', 560));

  c.push(quebra());
  c.push(h2('2.6 Conferido contra a aplicação no ar'));
  c.push(p(
    'A transcrição refaz o caminho pela API e confere cada passo: as mensagens contra o plano e contra os '
    + 'fatos, as decisões contra o que ficou no banco, a resposta do assistente contra o número da tela, e o '
    + 'portal contra a lista de parceiros.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint08/comunicacao.txt', '1. Gerar', '2. Decidir')));
  c.push(...mono(conferencias('sprint08/comunicacao.txt', '2. Decidir', '3. Histórico')));
  c.push(...mono(conferencias('sprint08/comunicacao.txt', '3. Histórico', '4. No banco')));
  c.push(...mono(conferencias('sprint08/comunicacao.txt', '4. No banco', '5. Assistente')));
  c.push(...mono(conferencias('sprint08/comunicacao.txt', '5. Assistente', '6. Portal')));
  c.push(...mono(conferencias('sprint08/comunicacao.txt', '6. Portal', 'Depois da limpeza')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(comunicacao), s: 19 }]));

  // ===================================== 3. CONTROLE DE PERMISSÕES
  c.push(quebra());
  c.push(h1('3. Controle de permissões'));
  c.push(p(
    'O sistema tem quatro perfis — Administrador, Gestor, Analista e Parceiro —, e a regra é uma só: quem '
    + 'decide o acesso é o servidor, a cada requisição. A interface mostra a cada perfil só o que ele abre, mas '
    + 'esconder um botão não é controle de acesso. Esta seção mostra as duas coisas: o que cada perfil vê, e o '
    + 'que o servidor responde quando alguém tenta o que não pode.',
  ));

  c.push(h2('3.1 O que cada perfil vê'));
  c.push(p(
    'O menu de cada perfil vem do servidor, que o lê das permissões das próprias rotas: não há uma segunda '
    + 'lista para discordar da primeira.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(daCaptura('sprint08/permissoes-na-tela.txt', 'O menu de cada perfil')));
  c.push(espaco(80));
  c.push(...figura('sprint08/permissoes-menus', 'O menu de cada um dos quatro perfis, na mesma altura: o vazio é o que o perfil não abre.'));

  c.push(quebra());
  c.push(h2('3.2 O endereço de uma tela que o perfil não abre'));
  c.push(p(
    'Até a Sprint 07, digitar o endereço de uma tela de outro perfil montava a tela assim mesmo, com a recusa '
    + 'da API no meio. Estava seguro, mas não dava para saber se era defeito ou falta de permissão. Agora a '
    + 'página diz o que aconteceu, com o perfil de quem está usando e a volta. Ela não faz nenhuma chamada à '
    + 'API: a interface só deixa de pedir o que já sabe que vai ser recusado.',
  ));
  c.push(...figura('sprint08/permissoes-sem-acesso-administrador', 'O Administrador no endereço da lista de parceiros: a página "Sem acesso", com o menu dele ao lado.'));
  c.push(...mono(daCaptura('sprint08/permissoes-na-tela.txt', 'O endereço de uma tela que o perfil não abre')));

  c.push(quebra());
  c.push(h2('3.3 O que o perfil vê e não faz'));
  c.push(p(
    'Dois casos em que o perfil abre a tela e não executa a ação dela. O Analista consulta a campanha, e não a '
    + 'calcula. E vê a fila de aprovação, e não decide. Quem diz isso à tela é a API, pelo perfil de quem '
    + 'pergunta; e quem tenta assim mesmo é recusado.',
  ));
  // A 560, a última linha das transcrições abaixo caía sozinha na página seguinte.
  c.push(...figura('sprint08/permissoes-campanha-analista', 'A campanha para o Analista: no lugar do botão de calcular, o motivo.', 520));
  c.push(...figura('sprint08/permissoes-aprovacao-analista', 'A fila de aprovação para o Analista: as mensagens, sem os botões de decidir.', 520));
  c.push(...mono(daCaptura('sprint08/permissoes-na-tela.txt', 'A campanha —')));
  c.push(...mono(daCaptura('sprint08/permissoes-na-tela.txt', 'A fila de aprovação —')));

  c.push(quebra());
  c.push(h2('3.4 A matriz perfil × rota, tirada do código e exercitada'));
  c.push(p(
    `A transcrição lê as ${acesso.rotas} rotas da aplicação, com os perfis que cada uma aceita — tirados da `
    + 'dependência de autorização da própria rota, que é de onde a decisão sai —, e entra com os quatro perfis '
    + 'na aplicação no ar. Cada combinação é exercitada: a negada tem de responder 403; a leitura permitida tem '
    + 'de passar; e, sem sessão, toda rota protegida responde 401.',
  ));
  c.push(table([6200, 3438], [
    ['O que foi exercitado', 'Quantas'],
    ['Combinações de rota e perfil que a matriz nega — todas responderam 403', acesso.negacoes],
    ['Leituras que a matriz permite — todas passaram pela autorização', acesso.leituras],
    ['Rotas protegidas, sem sessão — todas responderam 401', acesso.semSessao],
    ['Escritas permitidas, não exercitadas aqui', acesso.escritas],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER] }));
  c.push(espaco(60));
  c.push(p(
    'A escrita permitida não é exercitada na matriz: um envio de corpo vazio poderia gravar. Ela é exercitada '
    + 'com dado de verdade nas outras seções desta transcrição, e a matriz inteira roda no banco de testes, a '
    + 'cada Pull Request.',
    { size: 18 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/permissoes.txt', 'Cada célula é o que a aplicação respondeu', 'negações').filter((l) => l.trim())));

  // Sem quebra: a matriz deixa mais da metade da página livre, e o bloco dos
  // casos de uso, uma página e uma linha, deixaria a última linha sozinha.
  c.push(espaco(160));
  c.push(h2('3.5 Por caso de uso: um acesso permitido e um negado'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/permissoes.txt', 'UC02 Gerenciar usuários', '3. Por capacidade')
    .filter((l) => l.trim() && !/^=+$/.test(l.trim()))));

  c.push(quebra());
  c.push(h2('3.6 Por capacidade, por objeto e por sessão'));
  c.push(p(
    'Três recortes que a matriz por rota não mostra. A capacidade: o que o perfil vê e não faz. O objeto: duas '
    + 'contas de perfil Parceiro, cada uma de um parceiro, e nenhuma vê o histórico da outra nem nada da rede '
    + '(RF26). E a sessão: sem ela, forjada, e derrubada pela troca de senha, pela redefinição e pela '
    + 'desativação da conta.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint08/permissoes.txt', '3. Por capacidade', '4. Por objeto')));
  c.push(...mono(conferencias('sprint08/permissoes.txt', '4. Por objeto', '5. A sessão')));
  c.push(...mono(conferencias('sprint08/permissoes.txt', '5. A sessão', '6. A trilha')));
  c.push(espaco(80));
  c.push(p(
    `Cada acesso negado fica na trilha de auditoria. A transcrição recebeu ${acesso.recebidos} respostas 403, e `
    + `a trilha tem ${acesso.naTrilha} registros de acesso negado das contas dela — um para cada.`,
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/permissoes.txt', '$ SQL, só leitura', 'A transcrição recebeu').filter((l) => l.trim())));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(permissoes), s: 19 }]));
  c.push(p(
    'Duas regras não são provocadas contra a aplicação no ar, e têm teste automatizado: o bloqueio depois de '
    + 'cinco falhas de login, que é por origem e travaria a entrada de todos nesta máquina; e a proteção do '
    + 'último administrador ativo, que só aparece quando resta um.',
    { size: 18 },
  ));

  // ==================================== 4. MELHORIAS DE USABILIDADE
  c.push(quebra());
  c.push(h1('4. Melhorias de usabilidade'));
  c.push(p(
    'O levantamento desta entrega procurou, tela a tela, onde a pessoa ficava sem saber o que tinha acontecido, '
    + 'ou perdia o que tinha feito. O que ele achou virou as histórias H92 a H97, cada uma com critério de aceite '
    + 'antes do código. A tabela organiza os achados pelas heurísticas de usabilidade de Nielsen.',
  ));
  c.push(table([2900, 3300, 3438], [
    ['Heurística', 'O que a revisão achou', 'O que mudou'],
    ['Visibilidade do estado do sistema', 'A sessão que expirava jogava a pessoa na tela de entrada, sem dizer por quê', 'O login diz "A sua sessão terminou" e, depois de entrar, devolve a pessoa para onde ela estava'],
    ['Controle e liberdade do usuário', 'Quem mudava um campo e clicava no menu perdia o que tinha digitado', 'O aviso de alterações não salvas: sair sem salvar ou continuar editando'],
    ['Prevenção de erros', 'A senha era digitada às cegas, na entrada, na criação de conta e na troca', '"Mostrar" e "Ocultar" em todo campo de senha; na troca, a senha nova é digitada duas vezes'],
    ['Reconhecer, diagnosticar e recuperar erros', 'O endereço de uma tela de outro perfil mostrava a tela vazia, com a recusa da API', 'A página "Sem acesso", com o perfil, o endereço e a volta. Na troca de senha, o erro embaixo do campo'],
    ['Ajuda e documentação', 'Nenhuma: os termos do sistema não eram explicados em lugar nenhum', 'A Ajuda, no cabeçalho, e um link do termo até a explicação dele'],
    ['Reconhecimento em vez de memorização', 'A conta da pessoa não tinha caminho: o nome no cabeçalho era só texto', 'O nome leva à Minha conta; a ajuda diz o que o perfil faz, com o caminho até cada tela'],
    ['Correspondência com o mundo real', 'O segmento se chamava "Top 15" mesmo com o tamanho do Top em outro valor', 'O rótulo é "Top"; o número em vigor aparece onde importa'],
    ['Flexibilidade e eficiência de uso', 'Quem usa o teclado atravessava o menu inteiro a cada tela', '"Pular para o conteúdo", e o foco no título da tela ao trocar de tela'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(quebra());
  c.push(h2('4.1 A conta e a ajuda, no cabeçalho'));
  c.push(...figura('sprint08/antes-cabecalho', 'Antes: o nome de quem está usando era só texto, e não havia ajuda.', 600));
  c.push(...figura('sprint08/depois-cabecalho', 'Depois: o nome leva à Minha conta, e ao lado dele há o botão da Ajuda.', 600));
  c.push(...figura('sprint08/depois-minha-conta', 'A Minha conta: os dados da pessoa e a troca da senha, com o erro embaixo do campo a que pertence.', 520));

  c.push(quebra());
  c.push(h2('4.2 A tela que o perfil não abre'));
  c.push(...figura('sprint08/antes-analista-em-auditoria', 'Antes: o analista no endereço da Auditoria via a tela montada, com a recusa da API dentro.', 520));
  c.push(...figura('sprint08/depois-analista-em-auditoria', 'Depois: a página diz que o perfil não abre aquela tela, e oferece a volta.', 520));

  c.push(quebra());
  c.push(h2('4.3 A senha de quem esqueceu, e a conta do parceiro'));
  c.push(...figura('sprint08/antes-usuario-conta', 'Antes: a conta de um usuário, sem como redefinir a senha.', 520));
  c.push(...figura('sprint08/depois-usuario-conta', 'Depois: o bloco Senha, com a confirmação e o aviso de que as sessões da pessoa caem.', 520));
  c.push(quebra());
  c.push(...figura('sprint08/antes-usuario-novo', 'Antes: o cadastro de usuário oferecia três perfis.', 520));
  c.push(...figura('sprint08/depois-usuario-novo', 'Depois: o perfil Parceiro, com a busca do parceiro pelo nome.', 520));

  c.push(quebra());
  c.push(h2('4.4 A sessão que termina, e a senha que dá para conferir'));
  c.push(...figura('sprint08/antes-login', 'Antes: a tela de entrada.', 300));
  c.push(...figura('sprint08/depois-login', 'Depois: o aviso de que a sessão terminou, e o campo de senha com "Mostrar" e "Ocultar".', 300));

  c.push(quebra());
  c.push(h2('4.5 O teclado, e o que não foi salvo'));
  c.push(...figura('sprint08/depois-pular-para-o-conteudo', 'O primeiro Tab de qualquer tela: "Pular para o conteúdo".', 560));
  c.push(...mono(daCaptura('sprint08/depois.txt', 'O teclado —')));
  c.push(espaco(80));
  c.push(...figura('sprint08/depois-alteracoes-nao-salvas', 'Um campo alterado e o clique no menu: a pergunta, na própria página, com o foco nela.', 560));
  c.push(...mono(daCaptura('sprint08/depois.txt', 'O aviso de alterações não salvas —')));
  c.push(espaco(60));
  c.push(p(
    'O aviso intercepta o clique num link que leva a outra tela; fechar a aba ou recarregar passa pelo aviso do '
    + 'próprio navegador. O botão voltar do navegador e "Encerrar sessão" não avisam: bloquear a navegação '
    + 'inteira exigiria trocar o roteador da aplicação. A limitação está dita no código e na documentação.',
    { size: 18 },
  ));

  c.push(quebra());
  c.push(h2('4.6 A ajuda'));
  c.push(p(
    'A ajuda diz o que o perfil de quem lê pode fazer — a partir das telas que o servidor deu na sessão, as '
    + 'mesmas do menu —, o que é cada segmento, o que é estimativa e como se chega ao ganho esperado. Nenhum '
    + 'número de regra está escrito na tela: o tamanho do Top, os períodos de tendência e o histórico que o '
    + 'modelo pede vêm da API, como estão valendo; mudar um limiar muda a ajuda. O Parceiro lê só a ajuda do '
    + 'portal dele.',
  ));
  c.push(...figura('sprint08/depois-ajuda', 'A Ajuda do Gestor: o que ele pode fazer, os segmentos na ordem em que a regra decide, a estimativa e o ganho esperado.', 400));

  c.push(quebra());
  c.push(h2('4.7 As telas, medidas, e o mapa de navegação'));
  c.push(p(
    `A medição foi refeita depois de cada Pull Request de tela, e a última é de ${telas.data}: as `
    + `${telas.telas} telas, cada uma a 768 e a 1.440 px e nos dois temas. ${telas.pares} pares de cor passam no `
    + `contraste; nenhuma das ${telas.medidas} medidas rola a página na horizontal ou corta conteúdo; e nenhuma `
    + `das ${telas.auditorias} auditorias do axe acusa violação. As telas novas — a Minha conta, a página "Sem `
    + 'acesso" e as duas da Ajuda — entraram na medição no mesmo Pull Request que as criou.',
  ));
  c.push(diagrama('navegacao-telas', undefined, PARTE_VIII));
  c.push(legenda('O mapa de navegação, com a Minha conta, a Ajuda e a página "Sem acesso".'));

  // ============================== 5. REVISÃO DAS REGRAS DE NEGÓCIO
  c.push(quebra());
  c.push(h1('5. Revisão geral das regras de negócio'));
  c.push(p(
    `O sistema tem ${regras.linhas.length} regras de negócio escritas, da RN01 à RN11. A revisão não foi uma `
    + 'leitura: foi um roteiro executável, que monta um cenário pequeno, desenhado à mão para cair em cada ramo '
    + 'de cada regra, passa-o pela aplicação de verdade — a importação, o treino, a campanha, as mensagens — e '
    + 'compara o que voltou com o que a regra escrita manda.',
  ));
  c.push(p(
    'O esperado está escrito no roteiro, deduzido da regra, e não sai do código que se revisa: se o roteiro '
    + 'chamasse a função da segmentação para saber o segmento esperado, ele só provaria que a função concorda '
    + 'consigo mesma. O cenário roda num banco só dele, recriado a cada execução; a base de demonstração não é '
    + 'tocada.',
  ));

  c.push(h2('5.1 O cenário'));
  c.push(p(
    'Vinte e dois parceiros e oito semanas. As três últimas semanas decidem a tendência, e a última, o '
    + 'ranking. Cada linha abaixo é um parceiro desenhado para um ramo — e cinco deles satisfazem mais de um '
    + 'critério ao mesmo tempo, que é onde a ordem de precedência decide.',
    { size: 19 },
  ));
  c.push(table([1700, 5500, 2438], [
    ['Parceiro', 'O que foi desenhado', 'Segmento que a regra manda'],
    ['Loja 14', 'Marcada como prospecção, entre os 15 maiores e em queda há duas semanas', 'Prospecção'],
    ['Loja 20', 'Só aparece nas duas últimas semanas', 'Recém-chegado'],
    ['Loja 02', 'A 3ª do ranking, em queda há duas semanas', 'Em Risco — vence Top'],
    ['Loja 19', 'Fora dos 15 maiores, em queda há duas semanas', 'Em Risco'],
    ['Loja 03', 'A 2ª do ranking, subindo há duas semanas', 'Top — vence Em Ascensão'],
    ['Loja 16', 'Era a 16ª e passa a 15ª na última semana, com uma alta só', 'Top'],
    ['Loja 18', 'Fora dos 15 maiores, subindo há duas semanas', 'Em Ascensão'],
    ['Loja 15', 'Era a 15ª e cai para a 16ª, com uma queda só', 'Estável — uma queda não é tendência'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('5.2 O resultado, regra a regra'));
  c.push(table([1100, 5900, 1500, 1138], [
    ['Regra', 'O que ela diz', 'Conferências', 'Resultado'],
    ...regras.linhas.map((r) => [r.codigo, r.nome, r.certas, 'ok']),
    ['Total', '', regras.total, `${regras.passaram} ok`],
  ], { zebra: true, boldCol: 0, align: [null, null, AlignmentType.CENTER, AlignmentType.CENTER] }));
  c.push(espaco(60));
  c.push(p(`Revisão de ${regras.data}. O relatório inteiro, com o cenário, o esperado e o que voltou em cada conferência, está em docs/medicoes/regras.md.`, { size: 18 }));

  c.push(quebra());
  c.push(h2('5.3 A segmentação e a mobilidade, de perto'));
  c.push(p(
    'As duas regras mais fáceis de errar. A RN01 diz que Em Risco vence Top, de propósito: é o que deixa o '
    + 'painel responder quem está prestes a sair do Top. E a RN02 diz que a mobilidade do Top lê o ranking, e '
    + 'não o segmento gravado: a Loja 02 está em 3º e gravada como Em Risco — lida do segmento, ela apareceria '
    + 'como saída, e continua lá.',
    { size: 19 },
  ));
  c.push(table([4600, 2519, 2519], [
    ['RN01 — o que se confere', 'Esperado', 'Voltou'],
    ...conferenciasDaRegra('RN01').filter(([oQue]) => !oQue.startsWith('os 22 parceiros')),
  ], { zebra: true, size: 16 }));
  c.push(espaco(80));
  c.push(table([4600, 2519, 2519], [
    ['RN02 — o que se confere', 'Esperado', 'Voltou'],
    ...conferenciasDaRegra('RN02').filter(([oQue]) => !oQue.startsWith('o ranking da última semana')),
  ], { zebra: true, size: 16 }));

  c.push(quebra());
  c.push(h2('5.4 O ganho esperado e as cotas'));
  c.push(table([4600, 2519, 2519], [
    ['RN10 e RN11 — o que se confere', 'Esperado', 'Voltou'],
    ...conferenciasDaRegra('RN10'),
    ...conferenciasDaRegra('RN11').filter(([oQue]) => !oQue.startsWith('a cauda longa de cada item')),
  ], { zebra: true, size: 16 }));

  c.push(h2('5.5 O que a revisão achou, e ajustou'));
  c.push(table([2600, 3500, 3538], [
    ['O que estava incoerente', 'Como estava', 'O ajuste'],
    ['A RN01 não dizia o limiar de recém-chegado', 'A regra dizia só "o limiar configurado"; o valor, 3 períodos, estava no código (issue #59)', 'A RN01 passou a trazer os três limiares, o valor de fábrica de cada um e de onde ele vem'],
    ['A RN01 e a RN09 escreviam "2 períodos" como número fixo', 'O limiar é configurável desde a Sprint 04', 'As duas dizem "o limiar de tendência", com o 2 como valor de fábrica'],
    ['O rótulo "Top 15" era fixo', 'Com o limiar em 10, o sistema classificava dez parceiros e chamava o segmento de "Top 15" — na tela, nos arquivos e nas respostas do assistente (issue #229)', 'O rótulo passou a ser "Top"; um teste de cada lado reprova o rótulo de segmento que trouxer número'],
    ['A coluna Perfis de sete requisitos', 'Dizia menos do que a matriz de permissões e a API (seção 1.3)', 'Corrigida, e conferida por teste a cada execução da suíte'],
    ['O contrato do projeto listava cinco segmentos', 'Faltava a Prospecção, que a RN01 tem', 'Os seis, na ordem de precedência'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(espaco(80));
  c.push(p(
    `Nenhuma regra foi achada com o comportamento errado: as ${regras.total} conferências passaram. E o roteiro `
    + 'acusa regra quebrada — com a precedência de Em Risco e Top invertida de propósito no código, quatro '
    + 'conferências da RN01 e da RN02 falharam, e o roteiro saiu com erro. Um instrumento que nunca reprova não '
    + 'prova nada.',
  ));

  // ========================================== 6. ALTERAÇÕES NO ESCOPO
  c.push(quebra());
  c.push(h1('6. Alterações no escopo, e a justificativa de cada uma'));
  c.push(p(
    'O que mudou no escopo desde o planejamento da Sprint 01. Os seis módulos previstos foram entregues; nada '
    + 'que estava dentro do escopo saiu. O que mudou foi para mais, e cada acréscimo entrou primeiro no '
    + 'documento de requisitos e no backlog, com critério de aceite, e só depois no código.',
  ));
  c.push(table([2300, 2700, 4638], [
    ['O que mudou', 'De / para', 'Justificativa'],
    ['Requisitos funcionais', `43 para ${matriz.total}`, 'A Sprint 07 da disciplina pediu relatórios, exportação, busca e histórico: dez requisitos (RF44 a RF53). Esta pediu todas as funcionalidades implementadas, e o levantamento achou três que faltavam (RF54 a RF56)'],
    ['Módulos', '6 para 8', 'O módulo 7 — relatórios, consulta e acompanhamento — e o módulo 8 — conta, ajuda e vínculo do parceiro. Nenhum traz regra de negócio nova: leem o que os seis primeiros gravam'],
    ['Casos de uso', '14 para 16', 'Consultar e exportar relatórios (UC15) e consultar a ajuda (UC16)'],
    ['Regras de negócio', '8 para 11', 'A da previsão (RN09), a do ganho esperado (RN10) e a de quem recebe ação e como as cotas contam (RN11): o código precisava delas, e foram decididas em issue antes de implementar'],
    ['Backlog', '389 para 473 pontos', 'Três grupos de histórias, um por pedido de entrega: interface e navegação (H79 a H81), relatórios e histórico (H82 a H91) e conta, permissões, usabilidade e revisões (H92 a H101)'],
    ['Exportação', 'Só CSV para CSV e PDF', 'O PDF é a impressão do navegador, com uma folha de estilo: nenhuma dependência nova'],
    ['Redefinição de senha', 'Fora para dentro', 'Sem ela, quem esquecia a senha não voltava ao sistema. É do administrador, e não por e-mail: o sistema não envia mensagem nenhuma'],
    ['Ajuda', 'Fora para dentro', 'O requisito de usabilidade pede o sistema operável sem treinamento, e não havia onde os termos fossem explicados'],
    ['Assistente analítico', 'Primeiro a sair, se o prazo apertasse; ficou', 'Era a válvula de escape do cronograma. As treze sprints internas terminaram antes do calendário, e ele foi construído'],
    ['Envio das mensagens', 'Fora, e continua fora', 'Exige dados de contato reais e conta habilitada. O sistema entrega a mensagem aprovada, num arquivo pronto para envio'],
    ['Integração com plataformas, aplicativo móvel, várias unidades', 'Fora, e continuam fora', 'Como no planejamento: dependem de terceiros ou ampliariam o modelo além do prazo'],
    ['Cadência das sprints', 'Quinzenal para semanal', 'Pedido na avaliação da Sprint 01: o atraso passa a aparecer na primeira semana'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  // ============================================ 7. TESTES E BUGS
  c.push(quebra());
  c.push(h1('7. Testes e bugs'));

  c.push(h2('7.1 As quatro suítes'));
  c.push(p(
    'O registro foi gerado rodando as suítes, e não escrito à mão. A do otimizador roda na imagem do núcleo '
    + `compilado com CUDA, com a placa da máquina — ${placa.replace(/[()]/g, '').replace(' capacidade', ', capacidade')}.`,
  ));
  c.push(table([3900, 1150, 1150, 1150, 1100, 1188], [
    ['Suíte', 'Testes', 'Passaram', 'Falharam', 'Pulados', 'Tempo'],
    ...[api, modelo, otimizador, interfaceWeb].map((s) => [
      s.nome, String(s.total), String(s.passaram), String(s.falharam), String(s.pulados), `${s.segundos} s`,
    ]),
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroTestes), s: 19 }]));
  c.push(p('Os pulados são da suíte da API: os testes contra o modelo de linguagem de verdade, que pulam quando ele não está no ar.', { size: 17 }));

  c.push(h2('7.2 Os tipos de teste, com exemplos desta entrega'));
  c.push(p('Os quatro tipos das entregas anteriores, e um quinto — permissões —, que é o que esta entrega pede.', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/testes.txt', 'Fluxos principais', 'Por arquivo')));

  c.push(quebra());
  c.push(h2('7.3 As validações negativas desta entrega'));
  c.push(p(
    'Provocadas contra a aplicação no ar, com o esperado de cada uma conferido contra o que voltou. Em todas, '
    + 'o erro volta no campo a que pertence, e é embaixo dele que a tela o mostra.',
    { size: 19 },
  ));
  c.push(table([3400, 6238], [
    ['Caso', 'Esperado, e o que voltou'],
    ...validacoesDestaEntrega(),
  ], { zebra: true, boldCol: 0, size: 16 }));
  c.push(espaco(80));
  c.push(rich([
    { t: 'Resultado da transcrição de validações, com as seções das Sprints 03 a 07 e a desta: ', b: true, s: 19 },
    { t: semRotulo(validacoes), s: 19 },
  ]));

  c.push(h2('7.4 Os bugs desta entrega'));
  c.push(p(
    'Todo defeito vira issue com o rótulo "fix" — o que apareceu, a causa, a correção e como foi encontrado — e '
    + 'é fechado pelo Pull Request que o corrige. O registro é gerado dessas issues: as abertas desde o PDF da '
    + 'Sprint 07, fora as que o registro dela já tinha.',
  ));
  if (bugs.length) {
    c.push(table([900, 5300, 1500, 1938], [
      ['Issue', 'Defeito', 'Situação', 'Correção'],
      ...bugs.map((b) => [
        `#${b.numero}`,
        b.titulo,
        b.situacao === 'corrigido' ? 'Corrigido' : 'Pendente',
        b.prs.length ? b.prs.map((n) => `#${n}`).join(', ') : '—',
      ]),
    ], { zebra: true, align: [AlignmentType.CENTER, null, AlignmentType.CENTER, AlignmentType.CENTER], size: 17 }));
    c.push(espaco(80));
  }
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroBugs), s: 19 }]));
  const limpo = (t) => t.replace(/`/g, '').replace(/\*\*/g, '');
  for (const b of bugs) {
    c.push(espaco(60));
    c.push(rich([{ t: `#${b.numero} — ${b.titulo}`, b: true, s: 19 }]));
    c.push(p(`Apareceu: ${limpo(b.apareceu)}`, { size: 18 }));
    c.push(p(`Causa: ${limpo(b.causa)}`, { size: 18 }));
    c.push(p(`${b.situacao === 'corrigido' ? 'Correção' : 'O que fazer'}: ${limpo(b.correcao)}`, { size: 18 }));
  }
  if (bugs.length === 3) {
    c.push(espaco(60));
    c.push(p(
      'Os três apareceram do jeito que esta entrega procurava defeito: um ao levantar o que faltava para uma '
      + 'funcionalidade chegar à tela; outro ao escrever a ajuda, que mostrou lado a lado o número em vigor e o '
      + 'número escrito no rótulo; e o terceiro na rodada final das evidências, ao conferir a figura do '
      + 'assistente contra o painel.',
      { size: 19 },
    ));
  }

  // ============================== 8. REPOSITÓRIO, COMMITS E REVISÕES
  c.push(quebra());
  c.push(h1('8. Repositório, commits e revisões'));
  c.push(espaco(40));
  c.push(rich([{ t: 'Repositório: ', s: 21 }, { t: REPO, b: true, s: 21, c: '2C5B8F' }]));
  c.push(espaco(100));
  c.push(p(
    'Gerado do histórico do git, lido da branch principal do repositório remoto. A janela da Sprint 07 fecha no '
    + 'Pull Request do PDF dela (#215), e não no prazo: o trabalho que entrou depois dele é desta entrega.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/commits.txt', 'Totais', 'Por tipo')));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/commits.txt', 'Sprint 08 — ')));

  c.push(quebra());
  c.push(h2('8.1 Autoria e coautoria'));
  const coautoria = coautores.map((x) => `${x.nome.split(' ')[0]} ${x.n}`).join(', ');
  c.push(p(
    `Os ${totalDeCommits} commits têm o mesmo autor; os demais integrantes aparecem como coautores, pela área de `
    + `cada um (${coautoria}). A coautoria credita, mas não distribui a autoria: é a pendência da Pré-Banca, que `
    + 'continua como está (seção 11.1).',
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/commits.txt', 'Autoria e coautoria', 'Pull Requests incorporados, por')));

  c.push(h2('8.2 Revisões'));
  c.push(p(
    'O registro lista, para cada Pull Request incorporado desde o PDF da entrega anterior, quem abriu, quem foi '
    + 'convidado a revisar, quem revisou e com que resultado, e quem incorporou. Ele mostra a revisão como o '
    + 'GitHub a registrou.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint08/revisoes.txt', 'Resumo', 'Resultado:')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroRevisoes), s: 19 }]));

  // ====================================== 9. EXECUÇÃO E ROTEIRO
  c.push(quebra());
  c.push(h1('9. Execução e roteiro de demonstração'));
  c.push(p('O ambiente sobe com um comando, como nas entregas anteriores. O modelo de linguagem é um perfil à parte: sem ele, o sistema funciona igual.'));
  c.push(espaco(40));
  c.push(...mono([
    'docker compose up -d                                     # sem GPU: a CPU paralela',
    'docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build   # com a GPU',
    'docker compose --profile assistente up -d                # com o modelo de linguagem',
    'python scripts/resetar_banco.py --parceiros 500          # a base, segmentada e com o modelo',
    'python scripts/revisar_regras.py                         # a revisão das regras, num banco só dela',
  ]));
  c.push(espaco(120));
  c.push(h2('9.1 Roteiro para a orientação'));
  c.push(table([700, 8938], [
    ['#', 'Passo'],
    ['1', 'Entrar como administrador. Usuários → Novo usuário: escolher o perfil Parceiro, digitar duas letras do nome de um parceiro e criar a conta'],
    ['2', 'Abrir a conta de outra pessoa e redefinir a senha: a confirmação diz que as sessões dela caem'],
    ['3', 'Entrar com a conta do parceiro criada: o menu tem só "Meu desempenho". Digitar o endereço /parceiros: a página "Sem acesso"'],
    ['4', 'Entrar como analista. Importação: colar um relatório e ver a prévia. Campanha: no lugar do botão de calcular, o motivo'],
    ['5', 'Entrar como gestor. Campanha: calcular um plano. Mensagens: gerar as do plano'],
    ['6', 'Aprovação: aprovar uma, editar outra escrevendo um desconto — o número fica apontado — e rejeitar uma terceira. Voltar como analista: a fila, sem os botões'],
    ['7', 'Assistente: "Como foi a rede na última semana?", com a fonte; e "Qual a média de faturamento das pizzarias?", que recebe a abstenção'],
    ['8', 'Ajuda, pelo botão do cabeçalho: o que o perfil faz, e os segmentos na ordem da regra. No painel, "O que é cada segmento?" leva ao mesmo bloco'],
    ['9', 'Abrir um parceiro, mudar o contato e clicar em outro item do menu: o aviso de alterações não salvas'],
    ['10', 'Como administrador, Configuração: mudar o tamanho do Top para 10 e salvar. A Ajuda e a mobilidade do painel passam a dizer 10; o rótulo do segmento continua "Top". Voltar para 15'],
    ['11', 'Clicar no nome, no cabeçalho: a Minha conta. Trocar a senha errando a atual: o erro embaixo do campo'],
    ['12', 'Apertar Tab numa tela qualquer: "Pular para o conteúdo". Trocar de tela pelo teclado: o foco vai para o título'],
  ], { zebra: true, align: [AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(p(
    'Os roteiros das Sprints 04 a 07 continuam valendo. O Docker Desktop precisa estar aberto antes, e a '
    + 'verificação de ponta a ponta é a forma mais rápida de conferir que tudo subiu.',
    { size: 19 },
  ));

  // ============================================ 10. DIFICULDADES
  c.push(quebra());
  c.push(h1('10. Dificuldades encontradas'));
  const dificuldade = (nome, causa, correcao) => {
    c.push(h2(nome));
    c.push(p(causa));
    c.push(rich([{ t: 'O que foi feito: ', b: true, s: 19 }, { t: correcao, s: 19 }]));
  };
  dificuldade(
    '10.1 Sete requisitos diziam uma coisa, e a API fazia outra',
    'A coluna de perfis de sete requisitos estava desatualizada desde a Sprint 01, e ninguém tinha visto: cada '
    + 'documento, lido sozinho, parecia certo. O requisito dizia "Gestor e Analista"; a matriz de permissões dos '
    + 'casos de uso dava a leitura também ao Administrador; e a API seguia a matriz.',
    'A matriz de rastreabilidade cruza os três, e um teste a confere a cada execução da suíte. A divergência '
    + 'apareceu na primeira execução. A coluna foi corrigida, e uma rota nova que não entre na matriz reprova o '
    + 'Pull Request.',
  );
  dificuldade(
    '10.2 O número escrito num rótulo',
    'O segmento se chamava "Top 15" em toda a interface, nos arquivos exportados e nas respostas do '
    + 'assistente. O tamanho do Top é configurável desde a Sprint 04, e o rótulo continuava dizendo 15 com o '
    + 'limiar em outro valor. Só apareceu quando a tela de ajuda mostrou, lado a lado, o número em vigor e o '
    + 'rótulo.',
    'O rótulo passou a ser "Top", e um teste em cada lado reprova o rótulo de segmento que trouxer número. A '
    + 'regra ficou escrita: nenhum texto de tela ou de arquivo traz o limiar.',
  );
  dificuldade(
    '10.3 O aviso de alterações não salvas, sem trocar o roteador',
    'O bloqueio de navegação da biblioteca de rotas só existe num tipo de roteador que a aplicação não usa. '
    + 'Trocar o roteador por causa de um aviso mexeria em todas as rotas, a três semanas do congelamento do '
    + 'código.',
    'O aviso intercepta o clique no link — o menu, a trilha, o "Voltar" —, que é por onde se sai de um '
    + 'formulário, e o aviso do navegador cobre fechar a aba e recarregar. O botão voltar do navegador não '
    + 'avisa, e isso está dito no código, na documentação e na seção 4.5.',
  );
  dificuldade(
    '10.4 O que não se provoca contra a aplicação no ar',
    'A transcrição das permissões roda contra a aplicação de verdade, e duas regras não podem ser provocadas '
    + 'nela. O bloqueio por tentativas de login é por origem: provocá-lo travaria a entrada de todos na máquina. '
    + 'E a proteção do último administrador só aparece quando resta um. Pelo mesmo motivo, a escrita permitida, '
    + 'de corpo vazio, poderia começar um treino.',
    'A matriz exercita toda negação e toda leitura permitida; a escrita permitida é exercitada com dado de '
    + 'verdade, caso a caso; e as duas regras ficam com os testes automatizados, que a transcrição cita pelo '
    + 'nome.',
  );
  dificuldade(
    '10.5 A limpeza que parou no primeiro usuário',
    'Os roteiros de captura criam contas descartáveis e as desativam no fim. Numa execução, a conexão com a API '
    + 'caiu na primeira chamada da limpeza, depois de minutos sem uso, e as outras contas ficaram ativas. E, com '
    + 'o aviso de alterações não salvas, um roteiro que deixasse um formulário alterado e navegasse ficaria '
    + 'esperando o aviso do navegador para sempre.',
    'A chamada do administrador tenta de novo quando a conexão cai, e as páginas dos roteiros aceitam o aviso '
    + 'do navegador. As contas que tinham ficado ativas foram desativadas na hora.',
  );
  dificuldade(
    '10.6 "Semana passada", "última semana" e uma conferência branda demais',
    'Na primeira transcrição do assistente, a conferência que esperava a semana mais recente reprovou "Como foi '
    + 'a rede na semana passada?" — e a resposta estava certa: a semana passada é a anterior à mais recente. A '
    + 'conferência foi abrandada para comparar a resposta com o período que a própria fonte cita, e foi isso que '
    + 'deixou passar o defeito seguinte. Nas capturas finais, "na última semana" saiu como a semana anterior, com '
    + 'o número certo da semana errada (#235). Quem lia a semana era o modelo de linguagem, e ele às vezes troca '
    + 'as duas.',
    'A semana dita pelo nome passou a ser lida pelo código, das datas da base, e não mais pelo modelo. A '
    + 'conferência cobra as duas coisas: que o período da resposta seja o mais recente, o que o painel abre, e '
    + 'que o número seja o do painel nesse período.',
  );

  // =============================================== 11. AJUSTES
  c.push(quebra());
  c.push(h1('11. Ajustes no planejamento, na arquitetura e na modelagem'));
  c.push(table([2500, 3000, 4138], [
    ['O que mudou', 'De / para', 'Por quê'],
    ['Histórias H92 a H101', 'Backlog de 440 para 473 pontos', 'As quatro entregas pedidas viraram dez histórias, com critério de aceite antes do código'],
    ['Requisitos', `RF53 para RF${matriz.total}`, 'A redefinição de senha, a ajuda e a busca do parceiro para o vínculo entraram no documento antes do código'],
    ['Casos de uso', '15 para 16', 'O UC16, consultar a ajuda; os de autenticação e de usuários ganharam os fluxos de senha e a conta do parceiro'],
    ['API', `78 para ${acesso.rotas} operações`, 'A redefinição de senha, a busca de parceiros do administrador e as regras em vigor para a ajuda'],
    ['Modelo de dados', `As mesmas ${medida('tabelas')} tabelas, sem migração`, 'A ação nova da trilha de auditoria é texto; nada do que entrou precisou de tabela nem de coluna'],
    ['Sessão', 'Duas capacidades novas', 'A sessão passou a dizer se o perfil calcula a campanha e se recebe as regras da ajuda: a tela pergunta, em vez de decidir pelo perfil'],
    ['Menu e rotas da interface', 'Duas listas para uma tabela só', 'O item que o menu esconde é a tela que o endereço não monta'],
    ['Documentação', '10 para 11 documentos', 'A matriz de rastreabilidade, conferida por teste'],
    ['Regras de negócio', 'A RN01 com os três limiares e o valor de fábrica', 'A revisão das regras; fecha a issue #59'],
    ['Requisitos', 'A coluna Perfis de sete requisitos', 'Passou a dizer o que a matriz de permissões e a API dizem'],
    ['Medição das telas', `26 para ${telas.telas} telas`, 'A Minha conta, a página "Sem acesso" e as duas da Ajuda'],
    ['Janela da Sprint 07', 'Até 24/10 para até o PR do PDF (#215)', 'O trabalho que entrou depois do PDF é desta entrega'],
    ['Títulos desta parte', 'Soltos para "manter com o próximo"', 'Na Sprint 07, um título sozinho no pé da página custou três exportações do PDF'],
    ['Figuras da Parte VIII', 'Diagramas vivos para congelados', 'Como as das Partes II, VI e VII: a parte entregue não muda quando o diagrama vivo mudar'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('11.1 As duas pendências da Pré-Banca, como estão'));
  const semAprovacao = revisoes.length - aprovadosNoGithub;
  let situacaoDasRevisoes;
  if (!semAprovacao) {
    situacaoDasRevisoes = `os ${revisoes.length} têm aprovação registrada no GitHub. A pendência fecha se isso se `
      + 'mantiver até a entrega final';
  } else if (!aprovadosNoGithub) {
    situacaoDasRevisoes = 'nenhum tem aprovação registrada no GitHub: ela foi dada fora da plataforma, como nas '
      + 'entregas anteriores, e a pendência continua em aberto';
  } else {
    situacaoDasRevisoes = `${aprovadosNoGithub} têm aprovação registrada no GitHub; nos outros ${semAprovacao}, `
      + 'ela foi dada fora da plataforma, e a pendência continua em aberto';
  }
  c.push(bullet(
    'Revisão cruzada. Cada Pull Request desta entrega foi aberto convidando o dono de cada área a revisar, e '
    + `pedindo a aprovação no próprio PR. Dos ${revisoes.length} incorporados desde a entrega anterior, `
    + `${situacaoDasRevisoes}. O registro é gerado de novo a cada entrega.`,
  ));
  c.push(bullet(
    `Autoria. Os ${totalDeCommits} commits continuam com o mesmo autor, e os demais integrantes como coautores, `
    + 'pela área de cada um. Continua em aberto: o que cada integrante fizer até a entrega final — o registro '
    + 'da validação do README (H72), os vídeos — entra com a própria conta.',
  ));
  c.push(p(
    'As duas ficam declaradas, e não disfarçadas: a equipe decidiu seguir como está e dizer isso, em vez de '
    + 'reescrever o histórico para parecer outra coisa.',
    { size: 19 },
  ));

  c.push(h2('11.2 Devolutivas das entregas anteriores'));
  c.push(p(
    'Até a data deste documento, a equipe não tinha recebido a devolutiva das Sprints 06 e 07. O que chegar '
    + 'entra na entrega seguinte, como as da Pré-Banca entraram na Parte VI: cada apontamento com a correção e '
    + 'a evidência dela.',
  ));

  c.push(h2('11.3 Planejamento'));
  c.push(p(
    'A Sprint 08 da disciplina também não corresponde a nenhuma das treze sprints internas, que terminaram '
    + 'antes do calendário: o enunciado pediu as funcionalidades concluídas, as permissões, a usabilidade e a '
    + 'revisão das regras, e o que faltava de cada um virou as histórias H92 a H101. A central de comunicação e '
    + 'o assistente, construídos nas Sprints 12 e 13, ficaram para esta entrega, e estão na seção 2. A tabela de '
    + 'correspondência do cronograma foi atualizada.',
  ));

  // ========================================= 12. PRÓXIMOS PASSOS
  // Sem quebra: a seção 11 enche a página até o pé, e a quebra caía sozinha na
  // seguinte, deixando uma página em branco.
  c.push(h1('12. Próximos passos'));
  c.push(table([2200, 7438], [
    ['Onde', 'O que entra'],
    ['Até a banca', 'A validação do README numa máquina limpa (H72), os dois vídeos (H74, H75) e a apresentação do núcleo à equipe, com as perguntas prováveis da banca (risco R4)'],
    ['Requisitos não funcionais', 'As medições e validações que a matriz declara em parte ou em aberto (seção 1.4): a carga com 52 períodos, os outros dois navegadores e o fluxo observado com um usuário novo'],
    ['Devolutivas', 'O que os professores apontarem nas Sprints 06, 07 e 08, com a correção e a evidência'],
    ['Congelamento', 'O código congela em 25/10, para sobrar tempo aos vídeos e ao ensaio'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(h2('12.1 No processo'));
  c.push(bullet('Revisão registrada no GitHub em todo Pull Request, antes do merge — a pendência da seção 11.1.'));
  c.push(bullet('Commits de autoria de cada integrante, com a própria conta, no que cada um fizer até a entrega final.'));
  c.push(bullet('Rota nova entra na matriz de rastreabilidade no mesmo Pull Request: o teste cobra.'));
  c.push(bullet('Rodar a revisão das regras antes de cada entrega: é um comando, e acusa regra quebrada.'));

  c.push(espaco(200));
  c.push(p(
    'Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa '
    + 'visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.',
    { italics: true, color: '5A6B7E', size: 18 },
  ));

  return c;
}

module.exports = { montar };
