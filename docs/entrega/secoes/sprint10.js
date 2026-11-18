/**
 * Parte X do documento — Sprint 10 acadêmica: a Release Candidate.
 *
 * O enunciado pede a versão candidata à entrega final por cinco lados: o
 * sistema estável, a interface final, o banco de dados final, as APIs
 * documentadas e o README atualizado. Como nas partes anteriores, nenhum número
 * é digitado aqui:
 *
 * - a versão vem do `openapi.json` congelado, e a tag é conferida no git;
 * - a estabilidade vem das transcrições contra o sistema no ar — a verificação
 *   de ponta a ponta, a instalação do zero (`scripts/instalar_do_zero.py`) e a
 *   persistência —, do registro das suítes e dos casos executados pela tela;
 * - a interface vem da medição das telas e das capturas, nos dois temas;
 * - o banco vem do `banco.txt`, que o `scripts/descrever_banco.py` lê do
 *   catálogo do PostgreSQL, e dos diagramas congelados em `diagramas/parte-x/`;
 * - a API vem da cópia do `openapi.json` e das capturas do Swagger;
 * - o README vem da cópia dele, e a parte recusa gerar se faltar um dos nove
 *   itens do enunciado;
 * - os bugs, os commits e as revisões vêm dos registros, pelo marco da Sprint 10.
 *
 * `aprovado()` recusa gerar se uma evidência registrar falha. Para um rascunho
 * com as evidências provisórias, `GIH_RASCUNHO=1` deixa gerar e marca a parte;
 * o PDF entregue nunca sai assim.
 *
 * As evidências desta parte, tiradas na rodada final, depois do último Pull
 * Request de código, com a base de demonstração final:
 *   api/.venv/Scripts/python scripts/testar_na_tela.py --saida docs/entrega/evidencias/sprint10
 *   cd api && python e2e/verificacao.py  > ../docs/entrega/evidencias/sprint10/verificacao.txt
 *   cd api && python e2e/transcricao_permissoes.py > ../docs/entrega/evidencias/sprint10/permissoes.txt
 *   cd api && python e2e/persistencia.py > ../docs/entrega/evidencias/sprint10/persistencia.txt
 *   api/.venv/Scripts/python scripts/registrar_testes.py --saida docs/entrega/evidencias/sprint10
 *   api/.venv/Scripts/python scripts/descrever_banco.py --saida docs/entrega/evidencias/sprint10/banco.txt
 *   api/.venv/Scripts/python scripts/medir_telas.py    (e a cópia: medicoes/ e telas/)
 *   node docs/entrega/capturar_sprint10.js api ; node docs/entrega/capturar_sprint10.js escuro
 *   cp docs/api/openapi.json README.md docs/entrega/evidencias/sprint10/
 *   python scripts/registrar_bugs.py --desde 2026-10-03 --marco "Sprint 10 acadêmica" --saida ...
 *   python scripts/registrar_revisoes.py --depois-do-pr 238 --marco "Sprint 10 acadêmica" --saida ...
 *   node docs/entrega/registrar_commits.js > docs/entrega/evidencias/sprint10/commits.txt
 *   docker compose stop ; api/.venv/Scripts/python scripts/instalar_do_zero.py --ref v1.0.0-rc.1 --sem-cache \
 *       > docs/entrega/evidencias/sprint10/instalacao.txt ; docker compose up -d
 * E os diagramas do banco, congelados: os `mer-*` de docs/diagramas/ (SVG) e de
 * docs/entrega/diagramas/ (PNG) copiados para docs/entrega/diagramas/parte-x/.
 */
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { AlignmentType, HeadingLevel, ImageRun, Paragraph, TextRun } = require('docx');
const { AZUL, p, rich, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { diagrama, evidencia, legenda } = require('../comum/figuras');
const { trecho, json } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';
const EVIDENCIAS = path.join(__dirname, '..', 'evidencias');
const S = 'sprint10';
const PARTE_X = 'parte-x';
const RASCUNHO = process.env.GIH_RASCUNHO === '1';

// Os diagramas do banco, na ordem do docs/08: o conceitual e um por área.
const MER = [
  ['mer-conceitual', 'O modelo conceitual: as entidades e os relacionamentos que carregam regra de negócio'],
  ['mer-acesso', 'Acesso e auditoria: os usuários, as sessões e a trilha'],
  ['mer-desempenho', 'Parceiros e desempenho: as importações, os períodos, as métricas e os segmentos'],
  ['mer-previsao', 'A previsão: os treinos do modelo e a previsão de cada parceiro'],
  ['mer-campanha', 'O núcleo computacional: o catálogo de ações, as execuções do otimizador e os planos'],
  ['mer-comunicacao', 'A comunicação: os lotes de mensagens e cada mensagem, com a decisão'],
];

// Os nove itens do enunciado, na ordem dele, e o título da seção do README que responde a cada um.
const ITENS_DO_README = [
  ['Nome do projeto e descrição', null],
  ['Objetivo do sistema', 'Objetivo'],
  ['Tecnologias utilizadas', 'Tecnologias'],
  ['Requisitos para execução', 'Requisitos'],
  ['Instalação e configuração', 'Instalação e configuração'],
  ['Configuração do banco de dados', 'Banco de dados'],
  ['Como executar o sistema', 'Como executar'],
  ['Estrutura do projeto', 'Estrutura do projeto'],
  ['Integrantes da equipe', 'Equipe'],
];

// A galeria da interface final, das capturas do medir_telas (tema claro).
const GALERIA = [
  ['painel-1440', 'O Painel: os indicadores do período, a série, os segmentos e o ranking'],
  ['parceiro-1440', 'O cadastro de um parceiro: o desempenho, a previsão marcada como estimativa e os dados'],
  ['campanha-1440', 'A Campanha: as restrições do otimizador e o último plano, lacrado'],
  ['mensagens-1440', 'Mensagens: os três passos — para quem, quem entra e gerar'],
  ['aprovacao-1440', 'A Aprovação: a fila de mensagens pendentes'],
  ['relatorio-risco-1440', 'O relatório Parceiros em risco, pronto para imprimir'],
  ['meu-desempenho-1440', 'O portal do Parceiro: só os números dele'],
];
const ESCURAS = [
  ['escuro-painel', 'O Painel no tema escuro'],
  ['escuro-campanha', 'A Campanha no tema escuro'],
  ['escuro-relatorio-risco', 'O relatório Parceiros em risco no tema escuro'],
];
// O fluxo principal de ponta a ponta, nas capturas do executor dos casos.
const FLUXO = [
  ['CT-F16', 'Importação: o relatório na prévia, com a linha sem sentido recusada antes de gravar'],
  ['CT-F17', 'Importação gravada: o período em "Importações anteriores"'],
  ['CT-F19', 'O Painel com o período importado'],
  ['CT-F21', 'O Modelo treinado de novo, com o erro de cada versão'],
  ['CT-F22', 'A Campanha: o plano calculado, com o ganho esperado como estimativa'],
  ['CT-F27', 'Mensagens: uma para cada parceiro do plano, todas pendentes'],
  ['CT-F28', 'A Aprovação: a fila da geração, depois de aprovar uma'],
  ['CT-F33', 'Os relatórios: o desempenho, o risco e a campanha'],
];

// --------------------------------------------- títulos e figuras desta parte
const titulo = (nivel, tamanho, antes, depois) => (texto) => new Paragraph({
  heading: nivel,
  keepNext: true,
  spacing: { before: antes, after: depois },
  children: [new TextRun({ text: texto, bold: true, size: tamanho, color: AZUL, font: 'Calibri' })],
});
const h1 = titulo(HeadingLevel.HEADING_1, 30, 360, 180);
const h2 = titulo(HeadingLevel.HEADING_2, 24, 260, 120);

const figura = (nome, texto, largura) => [evidencia(`${S}/${nome}`, largura, true), legenda(texto)];

/** As dimensões de um JPEG, do marcador de início do quadro (SOF). */
function tamanhoDoJpeg(dados) {
  for (let i = 2; i < dados.length - 9;) {
    if (dados[i] !== 0xff) { i += 1; continue; }
    const marcador = dados[i + 1];
    if (marcador >= 0xc0 && marcador <= 0xc3) return { altura: dados.readUInt16BE(i + 5), largura: dados.readUInt16BE(i + 7) };
    i += 2 + dados.readUInt16BE(i + 2);
  }
  throw new Error('JPEG sem o marcador de tamanho.');
}

/** As capturas do medir_telas são JPEG: a figura delas, com a legenda junto. */
function capturaDaTela(nome, texto, limite = 560) {
  const arquivo = path.join(EVIDENCIAS, S, 'telas', `${nome}.jpg`);
  if (!fs.existsSync(arquivo)) throw new Error(`Falta ${S}/telas/${nome}.jpg. Copie as capturas do medir_telas.`);
  const dados = fs.readFileSync(arquivo);
  const { largura, altura } = tamanhoDoJpeg(dados);
  const w = Math.min(limite, 642);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      keepNext: true,
      spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: 'jpg', data: dados, transformation: { width: w, height: Math.round(w * altura / largura) } })],
    }),
    legenda(texto),
  ];
}

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
  const falhas = linhas.filter((l) => /\bFALHA\b/.test(l));
  if (falhas.length) throw new Error(`${arquivo} registra ${falhas.length} falha(s) — corrija e gere a evidência de novo.`);
  return linha.trim();
}

const semRotulo = (linha) => linha.replace(/^Resultado:\s*/, '');
const semPonto = (linha) => linha.replace(/\.$/, '');

function achar(texto, regex, onde) {
  const m = regex.exec(texto);
  if (!m) throw new Error(`Não achei ${regex} em ${onde} — gere de novo ou corrija o leitor.`);
  return m;
}

/** A cópia desta entrega, e não o arquivo vivo de `docs/`. */
function medicao(nome) {
  const arquivo = path.join(EVIDENCIAS, S, 'medicoes', nome);
  if (!fs.existsSync(arquivo)) throw new Error(`Falta ${S}/medicoes/${nome}. Copie o arquivo de docs/ antes de gerar.`);
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n');
}

/** Os casos executados pela tela, e a recusa se algum não passou. */
function casos() {
  const registro = json(`${S}/casos.json`);
  const naoPassaram = registro.casos.filter((c) => c.situacao !== 'ok');
  if (naoPassaram.length && !RASCUNHO) {
    throw new Error(`casos.json: ${naoPassaram.map((c) => `${c.id} (${c.situacao})`).join(', ')} — rode scripts/testar_na_tela.py de novo.`);
  }
  return { ...registro, passaram: registro.casos.length - naoPassaram.length };
}

/** As quatro suítes, lidas do registro de testes. */
function suites() {
  const achadas = cruas('testes.txt')
    .map((l) => /^\s{2}(\S.+?)\s{2,}(\d+) testes\s+(\d+) passaram\s+(\d+) falharam\s+(\d+) pulados\s+(\d+) s/.exec(l))
    .filter(Boolean)
    .map(([, nome, total, passaram, falharam, pulados, segundos]) => ({ nome, total, passaram, falharam, pulados, segundos }));
  if (achadas.length !== 4) throw new Error('O registro de testes não tem as quatro suítes.');
  return achadas;
}

/** A medição das telas no navegador — e a recusa, se alguma tela rolar, cortar ou violar o axe. */
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
  const navegador = achar(t, /^\| Navegador \| ([^|]+) \|$/m, 'acessibilidade.md')[1].trim();
  const axeVersao = achar(t, /^\| axe-core \| ([^|]+) \|$/m, 'acessibilidade.md')[1].trim();
  return { pares, telas, medidas, auditorias, data, navegador, axeVersao };
}

/** As conferências de uma transcrição — as linhas "ok" do fim —, e a linha do resultado. */
function conferencias(nome) {
  const linhas = cruas(nome);
  const inicio = linhas.findIndex((l) => /^Conferências:/.test(l.trim()));
  if (inicio < 0) throw new Error(`Sem a lista de conferências em ${nome}.`);
  return linhas.slice(inicio + 1).filter((l) => /^\s+ok\s/.test(l)).map((l) => l.trim().replace(/^ok\s+/, ''));
}

/** O que a instalação do zero diz da máquina, da referência, da versão e do tempo. */
function instalacao() {
  const t = cruas('instalacao.txt').join('\n');
  return {
    resultado: aprovado('instalacao.txt', 'Resultado:'),
    maquina: achar(t, /^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} · (.+)$/m, 'instalacao.txt')[1],
    quando: achar(t, /^(\d{2}\/\d{2}\/\d{4}) \d{2}:\d{2} · /m, 'instalacao.txt')[1],
    ferramentas: achar(t, /^(Docker .+) · projeto do ensaio/m, 'instalacao.txt')[1],
    clone: achar(t, /^\$ git clone --depth 1 --branch (\S+)/m, 'instalacao.txt')[1],
    commit: achar(t, /^\s+commit: (\S+)/m, 'instalacao.txt')[1],
    versao: achar(t, /"versao": "([^"]+)"/, 'instalacao.txt')[1],
    semCache: /as imagens foram construídas sem o cache/.test(t),
    lista: conferencias('instalacao.txt'),
  };
}

/** A estrutura do banco, como o catálogo a respondeu. */
function banco() {
  const linhas = cruas('banco.txt');
  const texto = linhas.join('\n');
  const [, lidoEm, postgres, migracao] = achar(
    texto, /^Lida do catálogo em (.+?); PostgreSQL (\S+); migração aplicada: (\S+)$/m, 'banco.txt',
  );
  const resumo = achar(texto, /^Resumo\n\s+(.+)$/m, 'banco.txt')[1].trim();
  const extensoes = achar(texto, /^Extensões: (.+)$/m, 'banco.txt')[1].trim();
  const tabelas = [];
  let atual = null;
  for (const l of linhas) {
    const t = /^(\w+)\s+\((\d+) linhas?\)$/.exec(l);
    if (t) {
      atual = { nome: t[1], linhas: Number(t[2]), colunas: 0, fks: [], unique: 0, check: 0, indices: 0, pk: '' };
      tabelas.push(atual);
      continue;
    }
    if (!atual || !/^\s{4}\S/.test(l)) continue;
    const r = /^\s{4}(PK|FK|UNIQUE|CHECK|índice)\s+\S+: (.*)$/.exec(l);
    if (!r) { atual.colunas += 1; continue; }
    const [, tipo, corpo] = r;
    if (tipo === 'PK') atual.pk = (/\(([^)]+)\)/.exec(corpo) || [, ''])[1];
    if (tipo === 'FK') atual.fks.push(achar(corpo, /REFERENCES (\w+)\(/, 'banco.txt')[1]);
    if (tipo === 'UNIQUE') atual.unique += 1;
    if (tipo === 'CHECK') atual.check += 1;
    if (tipo === 'índice') atual.indices += 1;
  }
  const [, nTabelas] = achar(resumo, /^(\d+) tabelas/, 'o resumo do banco.txt');
  if (tabelas.length !== Number(nTabelas)) throw new Error(`O banco.txt lista ${tabelas.length} tabelas, e o resumo diz ${nTabelas}.`);
  const enums = linhas.slice(linhas.findIndex((l) => l.startsWith('Tipos ENUM')) + 1).filter((l) => /^\s{4}\w+:/.test(l)).map((l) => l.trim());
  return { lidoEm, postgres, migracao, resumo, extensoes, tabelas, enums };
}

/** O que o documento da API traz, contado do `openapi.json` congelado. */
function documentoDaApi() {
  const e = json(`${S}/openapi.json`);
  const ops = Object.entries(e.paths).flatMap(([caminho, metodos]) => Object.entries(metodos).map(([metodo, op]) => ({ caminho, metodo, ...op })));
  // O corpo em JSON tem exemplo; o arquivo da importação (multipart) é um arquivo, e não tem.
  const comCorpo = ops.filter((o) => o.requestBody?.content?.['application/json']);
  const comArquivo = ops.filter((o) => o.requestBody?.content?.['multipart/form-data']);
  const comExemplo = comCorpo.filter((o) => {
    const m = o.requestBody.content['application/json'];
    return m.example !== undefined || m.examples || m.schema?.example;
  });
  const parametros = ops.flatMap((o) => o.parameters || []);
  const porTag = e.tags.map((t) => ({ ...t, n: ops.filter((o) => (o.tags || []).includes(t.name)).length }));
  const exemplo = (caminho, metodo) => {
    const c = e.paths[caminho][metodo].requestBody.content['application/json'];
    return c.example ?? Object.values(c.examples ?? {})[0]?.value;
  };
  return {
    versao: e.info.version,
    titulo: e.info.title,
    ops,
    protegidas: ops.filter((o) => (o.security || []).length),
    comPerfis: ops.filter((o) => /Quem pode/.test(o.description || '')),
    comCorpo,
    comArquivo,
    comExemplo,
    parametros,
    parametrosDescritos: parametros.filter((x) => x.description),
    erros: [...new Set(ops.flatMap((o) => Object.keys(o.responses || {}).filter((c) => c >= '400')))].sort(),
    porTag,
    sessao: e.components.securitySchemes.sessao,
    exemploEntrada: exemplo('/api/sessao', 'post'),
    exemploParceiro: exemplo('/api/parceiros', 'post'),
  };
}

/** Os títulos do README entregue, e a recusa se faltar um dos nove itens. */
function readme() {
  const linhas = cruas('README.md');
  const nome = linhas.find((l) => /^# /.test(l));
  if (!nome) throw new Error('O README não tem o título de nível 1 — o nome do projeto.');
  const secoes = linhas.filter((l) => /^## /.test(l)).map((l) => l.slice(3).trim());
  const itens = ITENS_DO_README.map(([item, secao]) => {
    if (secao && !secoes.includes(secao)) throw new Error(`O README não tem a seção "${secao}" (${item}).`);
    return { item, secao: secao ?? `${nome.slice(2).trim()} — o título e a descrição, no topo` };
  });
  return { itens, secoes, linhas: linhas.length };
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

/** A versão tem tag no repositório? Sem ela, a Release Candidate não existe. */
function tagNoGit(tag) {
  try {
    return execFileSync('git', ['tag', '--list', tag], { encoding: 'utf8' }).trim() === tag;
  } catch {
    return false;
  }
}

function montar() {
  const c = [];
  const api = documentoDaApi();
  const tag = `v${api.versao}`;
  if (!tagNoGit(tag) && !RASCUNHO) throw new Error(`A tag ${tag} não existe no git: crie a Release Candidate antes de gerar.`);
  const verificacao = aprovado('verificacao.txt', 'verificações passaram');
  const permissoes = aprovado('permissoes.txt', 'Resultado:');
  const persistencia = aprovado('persistencia.txt', 'Resultado:');
  const listaDaPersistencia = conferencias('persistencia.txt');
  const inst = instalacao();
  if (inst.versao !== api.versao) throw new Error(`A instalação do zero subiu a ${inst.versao}, e o documento da API é da ${api.versao}.`);
  const registroTestes = aprovado('testes.txt', 'Resultado:');
  const registroBugs = aprovado('bugs.txt', 'Resultado:');
  const registroRevisoes = aprovado('revisoes.txt', 'Resultado:');
  const quatro = suites();
  const tela = casos();
  const telas = medicaoDasTelas();
  const bd = banco();
  const leiame = readme();
  const bugs = json(`${S}/bugs.json`);
  const revisoes = json(`${S}/revisoes.json`);
  const { autores, coautores } = autoria();
  const corrigidos = bugs.filter((b) => b.situacao === 'corrigido');
  const pendentes = bugs.filter((b) => b.situacao !== 'corrigido');
  const daRevisaoDaInterface = bugs.filter((b) => /revisão de consistência da interface/.test(b.encontrado));
  const doEnsaio = bugs.filter((b) => /ensaio da instalação do zero|capturas do Swagger/.test(b.encontrado));
  const aprovadosNoGithub = revisoes.filter((r) => r.aprovado).length;
  const totalDeCommits = autores.reduce((s, a) => s + a.n, 0);
  const limpo = (t) => t.replace(/`/g, '').replace(/\*\*/g, '');

  c.push(quebra());
  c.push(h1(`Parte X — Sprint 10: Release Candidate${RASCUNHO ? ' (RASCUNHO — evidências provisórias)' : ''}`));
  c.push(p(
    'A Release Candidate é a versão candidata à entrega final: o sistema com tudo o que a entrega final terá, '
    + 'parado para que, daqui em diante, só entre correção. Esta parte mostra essa versão pelos cinco lados que o '
    + `enunciado pede — o sistema estável, a interface final, o banco final, as APIs documentadas e o README —, e ela tem nome: a versão ${api.versao}, com a tag ${tag} no repositório.`,
  ));
  c.push(p(
    'Como nas partes anteriores, nenhum número desta parte foi digitado: cada um sai de uma execução contra o '
    + 'sistema no ar, de um registro gerado por script ou de uma cópia congelada do que foi entregue.',
  ));

  c.push(h2('As entregas do enunciado, e onde estão'));
  c.push(table([700, 2700, 6238], [
    ['#', 'Entrega', 'Evidência neste documento'],
    ['1', 'Versão estável e funcional', `Seções 1 e 2 — a versão e a tag; a verificação de ponta a ponta; a instalação do zero, seguindo o README num clone novo; a persistência; as quatro suítes; os ${tela.casos.length} casos pela tela e o fluxo principal em capturas`],
    ['2', 'Interface final', `Seção 3 — o sistema visual; a revisão das ${telas.telas} telas, com as ${daRevisaoDaInterface.length} correções; a galeria nos dois temas; a medição no navegador`],
    ['3', 'Banco de dados final', `Seção 4 — os diagramas; as ${bd.tabelas.length} tabelas lidas do catálogo, com as chaves, as restrições e os índices; as migrações; o teste que confere o documento contra o banco`],
    ['4', 'APIs documentadas', `Seção 5 — as ${api.ops.length} operações no Swagger e no docs/13: o método, a rota, os perfis, os parâmetros, o corpo com exemplo, as respostas e os erros; a autenticação`],
    ['5', 'README atualizado', `Seção 6 — os ${ITENS_DO_README.length} itens do enunciado, cada um numa seção do README`],
    ['—', 'Correções, repositório e próximos passos', 'Seções 7, 8 e 9'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  c.push(h2('Números desta entrega'));
  c.push(table([5600, 4038], [
    ['Medida', 'Valor'],
    ['A versão', `${api.versao} — tag ${tag}`],
    ['Verificação de ponta a ponta pela API', semPonto(verificacao.replace(/^As /, ''))],
    ['Instalação do zero, seguindo o README', semPonto(semRotulo(inst.resultado))],
    ['Persistência: desligar, religar e conferir', semPonto(semRotulo(persistencia))],
    ['Testes automatizados (as quatro suítes)', semPonto(semRotulo(registroTestes))],
    ['Casos de teste executados pela tela', `${tela.passaram} de ${tela.casos.length} como esperado`],
    ['Conferências de permissão', semPonto(semRotulo(permissoes))],
    ['Telas medidas no navegador', `${telas.telas} telas, nos dois temas; nenhuma rolando, cortando ou com violação do axe`],
    ['O banco', bd.resumo],
    ['A API', `${api.ops.length} operações; ${api.protegidas.length} pedem sessão; ${api.comExemplo.length} de ${api.comCorpo.length} com corpo em JSON têm exemplo`],
    ['Defeitos registrados nesta entrega', `${bugs.length}: ${corrigidos.length} corrigidos, ${pendentes.length} pendentes`],
    ['Pull Requests incorporados nesta entrega', `${revisoes.length}`],
  ], { zebra: true, boldCol: 0 }));

  // ============================================== 1. A VERSÃO
  c.push(quebra());
  c.push(h1('1. A versão Release Candidate'));
  c.push(p(
    'Desde 25/10, o código está congelado: só entra correção, documentação e o que os vídeos precisam (docs/05). A '
    + 'Release Candidate é o retrato desse código com as correções desta sprint — a versão que seria entregue, se a '
    + 'entrega final fosse hoje. O que falta até 05/12 não é funcionalidade: é a validação do README por quem não o '
    + 'escreveu, os vídeos e a banca (seção 9).',
  ));
  c.push(h2('1.1 A versão e onde ela aparece'));
  c.push(table([3000, 6638], [
    ['O quê', 'Onde'],
    ['A versão', `${api.versao} — a mesma na API, no documento da API e na interface`],
    ['A tag no repositório', `${tag} — ${REPO}/releases/tag/${tag}`],
    ['O commit instalado do zero', `${inst.commit}, clonado pela tag (${inst.clone})`],
    ['Onde a pessoa a vê', `/api/health ("versao") e o topo do Swagger (/api/docs)`],
  ], { zebra: true, boldCol: 0, size: 18 }));
  c.push(h2('1.2 O que entrou desde a Sprint 08'));
  c.push(p(
    'A Sprint 09 (Parte IX) testou o sistema inteiro e corrigiu o que achou. Esta sprint fechou o que a entrega final '
    + 'pede além disso: a documentação da API, o banco descrito e conferido, a configuração que não fazia o que dizia, '
    + 'a tela que faltava, a revisão da interface, o README e a instalação do zero. Os Pull Requests desta janela, '
    + 'lidos do histórico do git:',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/commits.txt`, 'Sprint 10 — ', 'depois da última janela')));

  // ============================================== 2. SISTEMA ESTÁVEL
  c.push(quebra());
  c.push(h1('2. O sistema estável'));
  c.push(p(
    'Estável quer dizer três coisas, e cada uma tem a sua prova: o sistema faz o que deve, do começo ao fim, contra o '
    + 'banco de verdade; ele se instala do zero, seguindo só o README; e o que ele grava continua lá depois de '
    + 'desligado e religado.',
  ));
  c.push(h2('2.1 A verificação de ponta a ponta'));
  c.push(p(
    'O roteiro de api/e2e/verificacao.py percorre o sistema pela API no ar — HTTP, cookie e banco de verdade —, '
    + 'agrupado pelos itens das entregas da disciplina, e no fim confere que o banco voltou ao que era.',
    { size: 19 },
  ));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: verificacao, s: 19 }]));

  c.push(h2('2.2 A instalação do zero'));
  c.push(p(
    `O scripts/instalar_do_zero.py faz o que o README manda, num clone novo de ${inst.clone}, num projeto à parte do `
    + `Docker (gih-rc), e transcreve cada passo. Rodado em ${inst.quando}, em ${inst.maquina}, com ${inst.ferramentas}`
    + `${inst.semCache ? ', e com as imagens construídas sem o cache do Docker' : ''}. A senha do administrador sai do log, `
    + 'como o README ensina, e não vai para o registro. O que ele conferiu:',
    { size: 19 },
  ));
  inst.lista.forEach((x) => c.push(bullet(x)));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(inst.resultado), s: 19 }]));
  c.push(p(
    'O ensaio não substitui a validação do README por quem não o escreveu (H72): quem roda o script, em geral, '
    + 'escreveu o código. Ela segue o docs/validacao-do-readme.md (seção 9).',
    { size: 18 },
  ));

  c.push(h2('2.3 A persistência'));
  c.push(p(
    'O api/e2e/persistencia.py grava, derruba os contêineres — remove, e não pausa —, sobe outros e lê tudo de novo, '
    + 'com o mesmo cookie de antes:',
    { size: 19 },
  ));
  listaDaPersistencia.forEach((x) => c.push(bullet(x)));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(persistencia), s: 19 }]));

  c.push(h2('2.4 As suítes automatizadas e os casos pela tela'));
  c.push(table([3600, 1300, 1300, 1300, 1100, 1038], [
    ['Suíte', 'Testes', 'Passaram', 'Falharam', 'Pulados', 'Tempo'],
    ...quatro.map((x) => [x.nome, x.total, x.passaram, x.falharam, x.pulados, `${x.segundos} s`]),
  ], { zebra: true, boldCol: 0, size: 18, align: [null, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT] }));
  c.push(espaco(60));
  c.push(p(
    `E os ${tela.casos.length} casos do catálogo (docs/12), executados num navegador de verdade pelo `
    + `scripts/testar_na_tela.py: ${tela.passaram} como esperado. O catálogo e o esperado de cada caso estão na Parte IX.`,
    { size: 19 },
  ));

  c.push(quebra());
  c.push(h2('2.5 O fluxo principal, de ponta a ponta'));
  c.push(p(
    'Do relatório da semana à mensagem aprovada e ao relatório para levar para fora, nas capturas da própria '
    + 'execução dos casos de teste:',
    { size: 19 },
  ));
  for (const [nome, texto] of FLUXO) c.push(...figura(nome, `${nome} — ${texto}`, 520));

  // ============================================== 3. INTERFACE FINAL
  c.push(quebra());
  c.push(h1('3. A interface final'));
  c.push(p(
    'A interface final é a "Etiqueta e Lacre" (H103), que entrou em 26/10 (#242) no lugar da primeira e foi aprovada '
    + 'pela equipe (ADR-015). O sistema visual está no docs/09, com as três regras que não se negociam: cada cor tem '
    + 'um trabalho só — a de ação significa "responde ao seu clique", e nada mais; o que foi medido sai lacrado, e o '
    + 'que é estimativa sai tracejado, com a etiqueta; e a hierarquia vem do tamanho do número, e não do contraste.',
  ));
  c.push(h2('3.1 A revisão de consistência'));
  c.push(p(
    `As ${telas.telas} telas foram revistas uma a uma, nos dois temas, a 768 e a 1440 px, contra uma lista: o título `
    + 'e a volta, o rótulo da mesma ação, a posição dos botões, os estados vazio, carregando e erro, a confirmação do '
    + 'irreversível e a formatação de número, data e dinheiro. O essencial já era coerente — o título e a trilha vêm '
    + 'de um componente só, a formatação de um módulo só, e o irreversível passa sempre pela mesma confirmação. O que '
    + `apareceu foram ${daRevisaoDaInterface.length} defeitos pequenos, cada um numa issue, corrigido com o teste que o `
    + 'reprova (#285):',
    { size: 19 },
  ));
  daRevisaoDaInterface.forEach((b) => c.push(bullet(`#${b.numero} — ${limpo(b.titulo)}`)));
  c.push(p(
    'O que era gosto, e não defeito — o título longo descendo para a segunda linha do cabeçalho, por exemplo —, '
    + 'ficou numa lista à parte, para a decisão de quem cuida da interface, e não foi mudado.',
    { size: 18 },
  ));

  c.push(h2('3.2 A medição no navegador'));
  c.push(p(
    `O scripts/medir_telas.py abre cada tela pelo perfil que a usa, no ${telas.navegador}, a 768 e a 1440 px: nenhuma `
    + 'página rola na horizontal, nenhum conteúdo fica cortado — nem o seletor estreito demais para o que está '
    + `escolhido nele —, e o axe-core ${telas.axeVersao} não acusa nada, nos dois temas.`,
    { size: 19 },
  ));
  c.push(table([5600, 4038], [
    ['Medida', 'Resultado'],
    ['Telas', telas.telas],
    ['Medidas sem rolagem e sem corte (768 e 1440 px)', `${telas.medidas} de ${telas.medidas}`],
    ['Auditorias do axe sem violação (dois temas)', `${telas.auditorias} de ${telas.auditorias}`],
    ['Pares de cor que passam no contraste, nos dois temas', `${telas.pares} de ${telas.pares}`],
    ['Data da medição', telas.data],
  ], { zebra: true, boldCol: 0, size: 18 }));

  c.push(quebra());
  c.push(h2('3.3 A galeria'));
  c.push(p('As telas principais, no tema claro, a 1440 px:', { size: 19 }));
  for (const [nome, texto] of GALERIA) c.push(...capturaDaTela(nome, texto, 520));
  c.push(p('E no tema escuro, que segue o do sistema operacional, e que a pessoa troca no cabeçalho:', { size: 19 }));
  for (const [nome, texto] of ESCURAS) c.push(...figura(nome, texto, 520));

  // ============================================== 4. BANCO FINAL
  c.push(quebra());
  c.push(h1('4. O banco de dados final'));
  c.push(p(
    `O banco é o PostgreSQL ${bd.postgres}, com a estrutura criada pelas migrações do Alembic (api/migrations/), que a `
    + `API aplica sozinha a cada subida. A migração em vigor é a ${bd.migracao}. O docs/08 descreve o banco — os `
    + 'diagramas, cada entidade, as restrições, os índices e a política de exclusão —, e esta seção mostra o banco '
    + 'como o catálogo do PostgreSQL o responde, lido pelo scripts/descrever_banco.py.',
  ));
  c.push(rich([{ t: 'A estrutura, contada do catálogo: ', b: true, s: 19 }, { t: `${bd.resumo}. Extensões: ${bd.extensoes}.`, s: 19 }]));

  c.push(h2('4.1 Os diagramas'));
  for (const [nome, texto] of MER) {
    c.push(diagrama(nome, 600, PARTE_X));
    c.push(legenda(texto));
  }

  c.push(quebra());
  c.push(h2('4.2 As tabelas'));
  c.push(p(
    `Cada uma das ${bd.tabelas.length} tabelas, como o catálogo a respondeu em ${bd.lidoEm}: as colunas, a chave `
    + 'primária, as tabelas para onde apontam as chaves estrangeiras, as restrições e os índices, e quantas linhas a '
    + 'base de demonstração tem nela. A descrição de cada coluna está no banco.txt desta entrega e no docs/08.',
    { size: 19 },
  ));
  c.push(table([2500, 900, 1200, 2338, 700, 700, 700, 600], [
    ['Tabela', 'Colunas', 'Chave', 'Aponta para', 'UNIQUE', 'CHECK', 'Índices', 'Linhas'],
    ...bd.tabelas.map((t) => [t.nome, t.colunas, t.pk, [...new Set(t.fks)].join(', ') || '—', t.unique, t.check, t.indices, t.linhas]),
  ], { zebra: true, boldCol: 0, size: 15, align: [null, AlignmentType.RIGHT, null, null, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT] }));
  c.push(espaco(60));
  c.push(rich([{ t: 'Os tipos enumerados: ', b: true, s: 18 }, { t: bd.enums.join(' · '), s: 18 }]));

  c.push(h2('4.3 A integridade e a exclusão'));
  c.push(p(
    'O que o banco garante sozinho — e não só o código — está no docs/08, seção 5: a chave estrangeira de cada '
    + 'relacionamento, o UNIQUE onde a regra pede um só, o CHECK nos valores que têm faixa, e o índice nas consultas '
    + 'do painel e da trilha. Nenhuma chave estrangeira apaga em cascata: a auditoria e o histórico não se apagam, e '
    + 'quem sai do sistema é desativado, e não excluído. Só o parceiro sem histórico pode ser excluído (seção 5.1).',
    { size: 19 },
  ));
  c.push(h2('4.4 O documento conferido contra o banco'));
  c.push(p(
    'O api/tests/test_modelo_de_dados.py roda a cada Pull Request, contra o banco migrado da CI, e reprova quando o '
    + 'documento, as migrações e o banco discordam:',
    { size: 19 },
  ));
  c.push(bullet('as migrações criam o que os modelos do código descrevem (o compare_metadata do Alembic, sem diferença);'));
  c.push(bullet('toda tabela e toda coluna do docs/08 existem no banco, e o banco não tem nenhuma a mais;'));
  c.push(bullet('as chaves estrangeiras do documento são as do banco, e a cardinalidade dos diagramas é a da chave (a que aceita nulo é opcional);'));
  c.push(bullet('cada entidade do banco está na tabela de entidades e nos diagramas;'));
  c.push(bullet('as contagens do documento — chaves, restrições e índices — são as do catálogo.'));

  // ============================================== 5. APIs
  c.push(quebra());
  c.push(h1('5. As APIs documentadas'));
  c.push(p(
    `A API tem ${api.ops.length} operações, e a documentação delas sai das próprias rotas: o FastAPI gera o documento, `
    + 'e o api/app/documentacao_api.py o completa com o resumo de cada rota, os perfis que podem chamá-la, a sessão, '
    + 'os formatos de erro e os exemplos. Ela está em dois lugares:',
  ));
  c.push(bullet('com o sistema no ar, em /api/docs (Swagger, para experimentar) e /api/redoc (para ler);'));
  c.push(bullet('no repositório, sem subir nada: docs/13-api.md, a referência por área, com um exemplo de uso de ponta a ponta, e docs/api/openapi.json.'));
  c.push(p(
    'Um teste (api/tests/test_documentacao_api.py) reprova a rota sem resumo, sem descrição, sem os perfis, sem '
    + 'exemplo do corpo ou com parâmetro sem descrição; o exemplo que o próprio esquema recusaria; e o docs/13 e o '
    + 'openapi.json versionados quando deixam de ser o que a API gera. Rota nova sem documentação não entra.',
    { size: 19 },
  ));
  c.push(table([5600, 4038], [
    ['O que o documento traz', 'Quantas'],
    ['Operações (método e rota)', `${api.ops.length}`],
    ['Com os perfis que podem chamá-las, na descrição', `${api.comPerfis.length} de ${api.ops.length}`],
    ['Que pedem a sessão (o cadeado)', `${api.protegidas.length} de ${api.ops.length}; as outras são a entrada e a saúde`],
    ['Com corpo em JSON, e com exemplo do corpo', `${api.comExemplo.length} de ${api.comCorpo.length}`],
    ['Que recebem um arquivo (o CSV da importação)', `${api.comArquivo.length}`],
    ['Parâmetros, com descrição', `${api.parametrosDescritos.length} de ${api.parametros.length}`],
    ['Códigos de erro documentados', api.erros.join(', ')],
    ['Áreas (tags), cada uma com a sua descrição', `${api.porTag.length}`],
  ], { zebra: true, boldCol: 0, size: 18 }));

  c.push(h2('5.1 A autenticação'));
  c.push(p(
    `A sessão vive num cookie (${api.sessao.name}, HttpOnly), e não num token que o cliente guarda: POST /api/sessao `
    + 'abre a sessão e devolve o cookie; as chamadas seguintes o mandam de volta; DELETE /api/sessao a encerra no '
    + 'servidor. A permissão de cada rota é conferida no servidor, em toda chamada, pelo perfil da sessão. Um exemplo, '
    + 'com os corpos do próprio documento:',
    { size: 19 },
  ));
  c.push(...mono([
    'import httpx',
    'api = httpx.Client(base_url="http://localhost:8000")          # o cliente guarda o cookie',
    `api.post("/api/sessao", json=${JSON.stringify(api.exemploEntrada).replace(/"senha":"[^"]*"/, '"senha":"..."')})`,
    `api.post("/api/parceiros", json=${JSON.stringify(api.exemploParceiro)})`,
    'api.get("/api/parceiros", params={"segmento": "EM_RISCO", "pagina": 1})',
    'api.delete("/api/sessao")                                    # encerra no servidor',
  ]));

  c.push(h2('5.2 As áreas'));
  c.push(table([2200, 900, 6538], [
    ['Área', 'Rotas', 'O que reúne'],
    ...api.porTag.map((t) => [t.name, t.n, limpo(t.description || '—')]),
  ], { zebra: true, boldCol: 0, size: 16, align: [null, AlignmentType.CENTER] }));

  c.push(quebra());
  c.push(h2('5.3 No Swagger'));
  c.push(...figura('api-1-visao-geral', `A visão geral: a versão ${api.versao}, a autenticação, os perfis, os erros e as convenções`, 560));
  c.push(...figura('api-2-rota-aberta', 'Uma rota aberta: quem pode, o corpo com exemplo e cada resposta, com o formato do erro', 460));
  c.push(...figura('api-3-sessao', 'A sessão (o cadeado): o cookie que a entrada devolve', 460));

  // ============================================== 6. README
  c.push(quebra());
  c.push(h1('6. O README'));
  c.push(p(
    `O README (${REPO}#readme) é o que quem avalia lê primeiro, e o que ele precisa para instalar e usar o sistema. `
    + `Ele segue os ${ITENS_DO_README.length} itens do enunciado, na ordem dele;`
    + ' o que só a equipe usa — desenvolver fora do contêiner, os '
    + 'testes, as medições, a administração pelo terminal e como gerar as entregas — foi para o guia de operação '
    + '(docs/14), a um link de distância. A instalação do zero (seção 2.2) é ele seguido ao pé da letra.',
  ));
  c.push(table([4000, 5638], [
    ['Item do enunciado', 'Onde está no README'],
    ...leiame.itens.map((x) => [x.item, x.secao]),
  ], { zebra: true, boldCol: 0, size: 18 }));
  c.push(espaco(60));
  c.push(p(`As seções do README entregue, na ordem: ${leiame.secoes.join(' · ')}.`, { size: 18 }));

  // ============================================== 7. CORREÇÕES
  c.push(quebra());
  c.push(h1('7. Correções e ajustes'));
  c.push(p(
    'Cada defeito desta sprint virou uma issue com o que apareceu, a causa, a correção e como foi encontrado, e foi '
    + `corrigido num Pull Request com o teste que o reprova. ${doEnsaio.length} deles só apareceram fazendo o que quem `
    + 'avalia vai fazer: instalando do zero pelo README e abrindo o Swagger.',
  ));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroBugs), s: 19 }]));
  for (const b of bugs) {
    c.push(espaco(60));
    c.push(rich([{ t: `#${b.numero} — ${limpo(b.titulo)}`, b: true, s: 19 }]));
    c.push(p(`Apareceu: ${limpo(b.apareceu)}`, { size: 18 }));
    c.push(p(`Causa: ${limpo(b.causa)}`, { size: 18 }));
    c.push(p(`${b.situacao === 'corrigido' ? 'Correção' : 'O que fazer'}: ${limpo(b.correcao)}`, { size: 18 }));
    c.push(p(`Como foi encontrado: ${limpo(b.encontrado)}`, { size: 18 }));
  }

  // ============================================== 8. REPOSITÓRIO
  c.push(quebra());
  c.push(h1('8. Repositório, commits e revisões'));
  c.push(rich([{ t: 'Repositório: ', s: 21 }, { t: REPO, b: true, s: 21, c: '2C5B8F' }]));
  c.push(espaco(80));
  const coautoria = coautores.map((x) => `${x.nome.split(' ')[0]} ${x.n}`).join(', ');
  c.push(p(
    `Os ${totalDeCommits} commits do histórico têm ${autores.length === 1 ? 'o mesmo autor' : `${autores.length} autores`}; `
    + `os demais integrantes aparecem como coautores, pela área de cada um (${coautoria}).`,
  ));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/commits.txt`, 'Autoria e coautoria', 'Pull Requests incorporados, por')));
  c.push(h2('8.1 Revisões'));
  c.push(p(
    'Para cada Pull Request desta sprint: quem abriu, quem foi convidado a revisar, quem revisou e com que resultado. '
    + `${aprovadosNoGithub} de ${revisoes.length} têm a aprovação de um colega registrada no GitHub; a pendência segue na seção 9.`,
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho(`${S}/revisoes.txt`, 'Resumo', 'Resultado:')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroRevisoes), s: 19 }]));

  // ============================================== 9. PENDÊNCIAS
  c.push(quebra());
  c.push(h1('9. Pendências e próximos passos'));
  c.push(p('O que não está concluído, por que, e como a equipe vai resolver até a entrega final, em 05/12:'));
  c.push(table([2600, 3000, 2800, 1238], [
    ['Pendência', 'Por que', 'Ação prevista', 'Quando'],
    ['Validação do README por quem não o escreveu (H72; RNF07, RNF27)', 'Precisa de uma máquina limpa e de um integrante que não escreveu o código', 'Thiago ou João Pedro seguem o docs/validacao-do-readme.md e registram na issue #164', 'Antes da entrega final'],
    ...pendentes.map((b) => [`Defeito #${b.numero}`, limpo(b.titulo), limpo(b.correcao), '—']),
    ['Aprovação dos Pull Requests registrada no GitHub (RNF25)', `${aprovadosNoGithub} de ${revisoes.length} desta entrega têm a aprovação de um colega`, 'Cada Pull Request aprovado por um integrante no GitHub antes da incorporação', 'A partir de agora'],
    ['O Firefox (RNF08)', 'Não está instalado na máquina de teste', 'Rodar os casos de navegação nele, com o mesmo script', 'Antes da entrega final'],
    ['Os 52 períodos (RNF04)', 'Medido com 10.000 parceiros e 12 períodos', 'Medir com a base de 52 períodos', 'Antes da entrega final'],
    ['O usuário novo observado (RNF20)', 'Ninguém de fora da equipe foi observado usando o sistema', 'Uma sessão com alguém de fora, sem ajuda', 'Antes da gravação'],
    ['A transferência do núcleo (R4)', 'O núcleo foi construído por uma pessoa só', 'Apresentação à equipe, e as perguntas prováveis da banca em docs/banca.md', 'Antes da gravação'],
    ['Os vídeos (H74, H75)', 'Ficam para depois da Release Candidate, com a interface e a base que ficam', 'Roteiro e gravação, com a base de demonstração final', 'Até 04/12'],
  ], { zebra: true, boldCol: 0, size: 16 }));
  c.push(espaco(80));
  c.push(h2('Próximos passos'));
  c.push(bullet(`Daqui à entrega final, só correção: cada defeito numa issue e num Pull Request com o teste, e a versão sobe de ${api.versao} para a 1.0.0 sem funcionalidade nova.`));
  c.push(bullet('A base de demonstração desta Release Candidate é a da gravação dos vídeos e da banca.'));
  c.push(bullet('A instalação do zero, a verificação de ponta a ponta e os casos pela tela de novo antes da entrega final, contra a versão 1.0.0.'));

  return c;
}

module.exports = { montar };
