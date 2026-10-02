/**
 * Parte VII do documento — Sprint 07 acadêmica: sistema quase completo.
 *
 * O enunciado pede seis entregas — dashboard, relatórios, pesquisas, filtros,
 * exportação e logs ou histórico de operações —, cada uma funcionando e com
 * evidência, mais a integração com os módulos anteriores, o link do
 * repositório, as dificuldades, os próximos passos e o registro do que mudou
 * no planejamento, na arquitetura e na modelagem. Como nas partes anteriores,
 * nenhum número é digitado aqui:
 *
 * - as conferências de cada entrega vêm das transcrições em
 *   `evidencias/sprint07/`, que os scripts de `api/e2e/` escrevem contra a
 *   aplicação no ar;
 * - o endereço de cada recorte, o que a tela e a API responderam nele e as
 *   páginas de cada PDF vêm dos registros da captura (`capturar_sprint07.js`);
 * - o tempo com a base grande e a medição das telas vêm de `painel-10000.md` e
 *   de `acessibilidade.md`, **na cópia de `evidencias/sprint07/medicoes/`**: as
 *   de `docs/medicoes/` são refeitas nas entregas seguintes, e esta parte,
 *   depois de entregue, não pode mudar com elas;
 * - as contagens de testes, bugs, commits e revisões vêm dos registros que os
 *   scripts geram a partir da suíte rodada, das issues, do git e dos Pull
 *   Requests.
 *
 * `aprovado()` recusa gerar se uma evidência registrar falha, e os leitores de
 * medida recusam se não acharem o número.
 *
 * **As figuras desta parte estão congeladas** em `diagramas/parte-vii/`, como
 * as das Partes II e VI: o diagrama vivo pode mudar depois desta entrega, e a
 * parte entregue não.
 */
const fs = require('fs');
const path = require('path');
const { AlignmentType } = require('docx');
const { p, rich, h1, h2, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { diagrama, evidencia, legenda } = require('../comum/figuras');
const { trecho, json } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';
const EVIDENCIAS = path.join(__dirname, '..', 'evidencias');
const PARTE_VII = 'parte-vii';

/*
 * Os poucos números que não saem de um arquivo de evidência, com a origem de
 * cada um. `null` é "ainda não medido", e a geração recusa.
 */
const MEDIDAS = {
  operacoes: 78, // app.openapi() no contêiner da API, 01/10 — eram 64 na Sprint 06
  tabelas: 20, // catálogo do banco no ar, 01/10 — as mesmas da Sprint 06: a migração desta entrega só cria índices
};

function medida(nome) {
  const valor = MEDIDAS[nome];
  if (valor === null || valor === undefined) {
    throw new Error(`Medida "${nome}" não preenchida em secoes/sprint07.js — meça antes de gerar.`);
  }
  return String(valor);
}

/** As linhas do arquivo como saíram do script, sem quebrar: para ler, e não para mostrar. */
function cruas(nome) {
  const arquivo = path.join(EVIDENCIAS, nome);
  if (!fs.existsSync(arquivo)) throw new Error(`Falta ${nome}. Rode os scripts de evidência.`);
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n').split('\n');
}

/** A linha de resultado da evidência, e a recusa se ela registrar alguma falha. */
function aprovado(arquivo, marcador) {
  // Do arquivo cru, e não do quebrado em colunas: a linha de resultado comprida
  // perderia o fim.
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
  const achadas = cruas('sprint07/testes.txt')
    .map((l) => /^\s{2}(\S.+?)\s{2,}(\d+) testes\s+(\d+) passaram\s+(\d+) falharam\s+(\d+) pulados\s+(\d+) s/.exec(l))
    .filter(Boolean)
    .map(([, nome, total, passaram, falharam, pulados, segundos]) => ({
      nome, total: Number(total), passaram: Number(passaram), falharam: Number(falharam), pulados: Number(pulados), segundos,
    }));
  if (achadas.length !== 4) throw new Error('O registro de testes não tem as quatro suítes.');
  return achadas;
}

// ------------------------------------------------------- as medições
/*
 * A cópia desta entrega, e não a medição viva de `docs/medicoes/` — ver o
 * cabeçalho. Ela é tirada junto das evidências, depois do último Pull Request
 * de código:
 *   cp docs/medicoes/acessibilidade.md docs/medicoes/painel-10000.md docs/entrega/evidencias/sprint07/medicoes/
 */
function medicao(nome) {
  const arquivo = path.join(EVIDENCIAS, 'sprint07', 'medicoes', nome);
  if (!fs.existsSync(arquivo)) {
    throw new Error(`Falta sprint07/medicoes/${nome}. Copie a medição de docs/medicoes/ antes de gerar.`);
  }
  return fs.readFileSync(arquivo, 'utf8').replace(/\r\n/g, '\n');
}

function achar(texto, regex, onde) {
  const m = regex.exec(texto);
  if (!m) throw new Error(`Não achei ${regex} em docs/medicoes/${onde} — meça de novo ou corrija o leitor.`);
  return m;
}

/** O texto de uma seção `## título` de um arquivo de medição. */
function secao(texto, titulo, onde) {
  const inicio = texto.indexOf(`## ${titulo}`);
  if (inicio < 0) throw new Error(`Sem a seção "${titulo}" em docs/medicoes/${onde}.`);
  const fim = texto.indexOf('\n## ', inicio + 3);
  return texto.slice(inicio, fim < 0 ? undefined : fim);
}

const comVirgula = (numero) => numero.replace('.', ',');

/**
 * O painel e os relatórios com 10.000 parceiros — e a recusa, se alguma
 * consulta passar do teto do RNF03.
 */
function medicaoDaBaseGrande() {
  const onde = 'painel-10000.md';
  const t = medicao(onde);
  const massa = achar(t, /^\| Massa \| ([^|]+) \|$/m, onde)[1].trim();
  const data = achar(t, /^\| Data \| ([^|]+) \|$/m, onde)[1].trim();
  const consultas = [...secao(t, 'Resultado', onde).matchAll(
    /^\| `([^`]+)` \| \d+ \| ([\d.]+) ms \| ([\d.]+) ms \| [^|]+ \| [^|]+ \| (sim|não) \|$/gm,
  )].map(([, nome, mediana, p95, dentro]) => ({ nome, mediana, p95, dentro }));
  if (!consultas.length) throw new Error(`Não li nenhuma consulta em docs/medicoes/${onde}.`);
  if (consultas.some((c) => c.dentro !== 'sim')) {
    throw new Error('A medição com a base grande tem consulta fora do teto de 2 s — corrija antes de gerar.');
  }
  const de = (nome) => {
    const c = consultas.find((x) => x.nome === nome);
    if (!c) throw new Error(`A consulta "${nome}" não está em docs/medicoes/${onde}.`);
    return `${comVirgula(c.mediana)} ms de mediana, ${comVirgula(c.p95)} ms no p95`;
  };
  const maisLenta = consultas.reduce((a, b) => (Number(b.p95) > Number(a.p95) ? b : a));
  return { massa, data, total: consultas.length, de, maisLenta };
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
  // A medição precisa ser de depois das telas desta entrega (a última, a H91,
  // ficou pronta em 01/10): a de antes delas não diz nada sobre elas.
  const [dia, mes, ano] = data.split(' ')[0].split('/');
  if (`${ano}-${mes}-${dia}` < '2026-10-01') {
    throw new Error(`A medição das telas é de ${data}, de antes das telas da Sprint 07 — rode scripts/medir_telas.py de novo.`);
  }
  return { pares, telas, medidas, auditorias, data };
}

/** Os autores e coautores do registro de commits. */
function autoria() {
  const linhas = cruas('sprint07/commits.txt');
  const ler = (tipo) => linhas
    .map((l) => new RegExp(`^\\s{2}${tipo}\\s+(.+?)\\s{2,}(\\d+)$`).exec(l))
    .filter(Boolean)
    .map(([, nome, n]) => ({ nome, n: Number(n) }));
  const autores = ler('autor');
  const coautores = ler('coautor');
  if (!autores.length) throw new Error('O registro de commits não traz a autoria.');
  return { autores, coautores };
}

// Os casos da seção dos relatórios, do painel e dos filtros na transcrição de
// validações, na ordem em que ela os provoca (api/e2e/validacoes.py). O
// resultado de cada um vem do arquivo.
const CASOS_DESTA_ENTREGA = [
  'O administrador abre o relatório de desempenho',
  'O analista abre o relatório de operações',
  'O analista exporta a trilha de auditoria',
  'O administrador pede a previsão e a campanha do painel',
  'Relatório de um período que não existe',
  'Painel de uma categoria que não existe',
  'Segmento fora da lista',
  'Chance de queda acima de 100%',
  'Resultado de execução fora da lista',
  'Série de um parceiro e de uma categoria ao mesmo tempo',
  'Relatório da campanha de uma execução sem plano',
  'CSV do plano de uma execução sem plano',
  'Relatório da campanha de uma execução que não existe',
  'Data inicial depois da final',
  'Data fora do formato',
  'Ação que a trilha não tem',
  'Histórico de um parceiro que não existe',
];

function validacoesDestaEntrega() {
  const linhas = cruas('sprint07/validacoes.txt');
  const inicio = linhas.findIndex((l) => l.includes('[2/9] Relatórios'));
  const fim = linhas.findIndex((l, i) => i > inicio && l.startsWith('Preparação'));
  if (inicio < 0 || fim < 0) throw new Error('Não achei a seção dos relatórios em validacoes.txt.');
  const resultados = linhas.slice(inicio, fim)
    .filter((l) => /^\s+ok\s+esperado:/.test(l))
    // As aspas simples da transcrição viram aspas tipográficas: o trecho esperado
    // pode ter aspas duplas dentro, como o JSON da resposta.
    .map((l) => l.replace(/^\s+ok\s+esperado:\s*/, '').replace(/'([^']*)'/g, '“$1”'));
  if (resultados.length !== CASOS_DESTA_ENTREGA.length) {
    throw new Error(`A seção dos relatórios em validacoes.txt tem ${resultados.length} conferências, e não ${CASOS_DESTA_ENTREGA.length}.`);
  }
  return CASOS_DESTA_ENTREGA.map((caso, i) => [caso, resultados[i]]);
}

function montar() {
  const c = [];
  const verificacao = aprovado('sprint07/verificacao.txt', 'verificações passaram');
  const transcricao = aprovado('sprint07/relatorios.txt', 'Resultado:');
  const persistencia = aprovado('sprint07/persistencia.txt', 'Resultado:');
  const validacoes = aprovado('sprint07/validacoes.txt', 'Resultado:');
  const registroTestes = aprovado('sprint07/testes.txt', 'Resultado:');
  const registroBugs = aprovado('sprint07/bugs.txt', 'Resultado:');
  const registroRevisoes = aprovado('sprint07/revisoes.txt', 'Resultado:');
  const [api, modelo, otimizador, interfaceWeb] = suites();
  const base = medicaoDaBaseGrande();
  const telas = medicaoDasTelas();
  const bugs = json('sprint07/bugs.json');
  const revisoes = json('sprint07/revisoes.json');
  const { autores, coautores } = autoria();

  const aprovadosNoGithub = revisoes.filter((r) => r.aprovado).length;
  const totalDeCommits = autores.reduce((s, a) => s + a.n, 0);
  const gpuDoRegistro = cruas('sprint07/testes.txt').find((l) => l.includes('GPU:'));
  if (!gpuDoRegistro) throw new Error('O registro de testes não diz em que placa o otimizador rodou.');
  const placa = gpuDoRegistro.split('GPU: ')[1].trim();

  c.push(quebra());
  c.push(h1('Parte VII — Sprint 07: Sistema Quase Completo'));

  c.push(p(
    'Com os três módulos funcionando e ligados entre si, esta entrega cuida do que faz o sistema ser usado no '
    + 'dia a dia sem sair da tela: escolher o recorte que o painel mostra, tirar um relatório, achar o que se '
    + 'procura, levar os números para fora e saber o que foi feito, quando e por quem. Nada disso é um módulo '
    + 'novo: cada item lê o que os três módulos já gravam, e é conferido contra eles.',
  ));
  c.push(p(
    'Cada item vem com execução real: transcrições e capturas geradas por scripts contra a aplicação no ar, '
    + 'sobre a base de demonstração, que é sintética. Os PDFs dos relatórios são os que o navegador imprime, e '
    + 'estão no repositório ao lado das capturas.',
  ));

  c.push(h2('As seis entregas, e onde estão'));
  c.push(table([700, 2700, 1900, 4338], [
    ['#', 'Entrega', 'Situação', 'Evidência neste documento'],
    ['1', 'Dashboard', 'Funcionando', 'Seção 1 — o recorte por período e categoria, e os três módulos num bloco'],
    ['2', 'Relatórios', 'Funcionando', 'Seção 2 — os quatro, na tela, cada um conferido contra a tela que resume'],
    ['3', 'Pesquisas', 'Funcionando', 'Seção 3 — parceiros, usuários e a trilha, sem maiúscula nem acento'],
    ['4', 'Filtros', 'Funcionando', 'Seção 3 — o endereço de cada recorte, e o que a tela e a API responderam'],
    ['5', 'Exportação', 'Funcionando', 'Seção 4 — o CSV de cada tela e o PDF pela impressão do navegador'],
    ['6', 'Logs e histórico de operações', 'Funcionando', 'Seção 5 — a trilha de auditoria na tela e o histórico no cadastro'],
    ['—', 'Integração com os módulos anteriores', 'Conferida', 'Seção 6 — o que cada item lê de cada módulo, e as conferências'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  c.push(h2('Números desta entrega'));
  c.push(table([6000, 3638], [
    ['Medida', 'Valor'],
    ['Histórias entregues', 'H82 a H91 — 38 pontos; o backlog foi de 402 para 440'],
    ['Requisitos novos', 'RF44 a RF53, e o caso de uso UC15'],
    ['Operações da API', `${medida('operacoes')} — eram 64 na Sprint 06`],
    ['Tabelas no banco', `${medida('tabelas')} — as mesmas; a migração desta entrega cria três índices na trilha`],
    ['Telas medidas no navegador', `${telas.telas} — eram 20 na Sprint 06`],
    ['Testes da API', `${api.total}, ${api.passaram} passando, ${api.pulados} pulados`],
    ['Testes da interface', `${interfaceWeb.total}, todos passando`],
    ['Verificação de ponta a ponta contra a aplicação no ar', verificacao.replace(/^As /, '').replace(/\.$/, '')],
  ], { zebra: true, boldCol: 0 }));

  // ================================================ 1. DASHBOARD
  c.push(quebra());
  c.push(h1('1. Dashboard'));
  c.push(p(
    'O painel existe desde a Parte III: seis indicadores, a série histórica, a distribuição por segmento e '
    + 'o ranking. Faltavam duas coisas. Ele abria sempre no período mais recente, sem como olhar outro — e o '
    + 'requisito fala em "período selecionado". E mostrava só o primeiro módulo: a previsão e a campanha '
    + 'ficavam cada uma na sua tela.',
  ));

  c.push(h2('1.1 O painel num recorte: período e categoria'));
  c.push(evidencia('sprint07/antes-painel-topo'));
  c.push(legenda('Antes: os indicadores do painel, sempre do período mais recente e da rede inteira.'));
  c.push(p(
    'Agora o período e a categoria se escolhem no alto do painel, e a escolha fica no endereço: o recorte pode '
    + 'ser guardado, recarregado e mandado para outra pessoa. Tudo o que o painel mostra passa a ser do recorte '
    + '— os indicadores, a série, a distribuição e o ranking —, e a comparação é com o período anterior, na '
    + 'mesma categoria. Duas coisas não mudam com o filtro, de propósito, e a tela diz as duas:',
  ));
  c.push(bullet('A posição no ranking continua a da rede inteira (RN02). Filtrar por Padaria mostra as padarias, cada uma na posição que ocupa entre todos os parceiros.'));
  c.push(bullet('A mobilidade do Top N é a da rede inteira: quem entrou e quem saiu do Top 15 não depende da categoria que se está olhando.'));

  c.push(quebra());
  c.push(evidencia('sprint07/depois-painel-recorte'));
  c.push(legenda('Depois: o painel de um período anterior, só na categoria Padaria, com a série e a distribuição do recorte.'));
  c.push(quebra());
  c.push(evidencia('sprint07/depois-painel-ranking-da-categoria'));
  c.push(legenda('O ranking da categoria: só as padarias, cada uma na posição da rede inteira.'));
  c.push(espaco(60));
  c.push(p('O endereço do recorte, o que a tela mostrou e o que a API respondeu nele:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/recortes.txt', 'Painel —', 'Execuções —').filter((l) => l.trim())));

  c.push(h2('1.2 Os três módulos num lugar só'));
  c.push(p(
    'O bloco novo põe, embaixo do que foi medido, o que o modelo prevê e o que a última campanha decidiu. O '
    + 'faturamento previsto vem ao lado do medido nos mesmos parceiros, para a comparação ser justa. Os '
    + 'parceiros de maior risco de queda são uma ordenação — os cinco primeiros —, e não um limiar novo: '
    + 'nenhuma regra de negócio foi inventada. O resumo da campanha leva ao plano. Tudo é marcado como '
    + 'estimativa, com a versão do modelo e até quando ele tem dados.',
  ));
  c.push(evidencia('sprint07/depois-painel-decisao'));
  c.push(legenda('A previsão e a campanha no painel: o previsto ao lado do medido, o maior risco de queda e o último plano.'));
  c.push(p(
    'Quem decide se o bloco aparece é a API, pelo perfil: o gestor e o analista o recebem; o administrador lê o '
    + 'painel, mas não a previsão por parceiro nem a campanha, que ele também não abre nas telas delas.',
    { size: 19 },
  ));

  c.push(h2('1.3 Com dados reais, conferido'));
  c.push(p(
    'A transcrição pede o painel pela API e confere cada número contra a origem dele: os indicadores do '
    + 'recorte contra a soma das métricas no banco, a posição contra o ranking da rede, o risco contra a '
    + 'previsão do cadastro e a campanha contra o plano que o gestor acabou de calcular.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint07/relatorios.txt', '[1/6] Dashboard', '[2/6]')));

  c.push(h2('1.4 O tempo, com 10.000 parceiros'));
  c.push(p(
    `O requisito pede resposta em até 2 segundos com 10.000 parceiros (RNF03, RNF04). A medição foi refeita `
    + `com as consultas novas, num banco separado, com ${base.massa}: as ${base.total} consultas do painel, dos `
    + `relatórios e da lista ficam dentro do teto, e a mais lenta (${base.maisLenta.nome}) leva `
    + `${comVirgula(base.maisLenta.p95)} ms no p95.`,
  ));
  c.push(table([4300, 1700, 3638], [
    ['Consulta', 'Teto', 'Medido'],
    ['Indicadores do painel, na categoria com mais parceiros', '2 s', base.de('indicadores-categoria')],
    ['Ranking da categoria, com a posição da rede', '2 s', base.de('ranking-categoria')],
    ['O bloco da previsão e da campanha', '2 s', base.de('decisao')],
    ['Relatório de desempenho', '2 s', base.de('relatorio-desempenho')],
    ['Relatório de parceiros em risco', '2 s', base.de('relatorio-risco')],
    ['Relatório da campanha', '2 s', base.de('relatorio-campanha')],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER], size: 17 }));
  c.push(p(`Lido da medição publicada no repositório (docs/medicoes/painel-10000.md), gerada por script em ${base.data}. O ranking, o bloco da previsão e os relatórios de desempenho e de risco têm teste que conta as consultas: nenhum faz uma por parceiro.`, { size: 17, italics: true }));

  // ================================================ 2. RELATÓRIOS
  c.push(quebra());
  c.push(h1('2. Relatórios'));
  c.push(p(
    'O sistema não tinha relatório nenhum. Agora tem quatro, um para cada pergunta que se leva para uma '
    + 'reunião: como a rede foi, quem vai cair, onde a verba foi e o que foi feito no sistema. Cada um tem '
    + 'filtros, que ficam no endereço, um total que se confere contra a tela que ele resume, o arquivo CSV e a '
    + 'impressão em PDF.',
  ));
  c.push(table([1900, 3700, 2300, 1738], [
    ['Relatório', 'O que traz', 'Filtros', 'Quem abre'],
    ['Desempenho por período', 'Por categoria e por segmento: parceiros, faturamento, pedidos, ticket médio e variação (RF44)', 'Período, categoria, segmento', 'Gestor, Analista'],
    ['Parceiros em risco', 'Parceiro a parceiro: segmento, variação, faturamento medido e previsto, chance de queda e a ação no último plano (RF45)', 'Categoria, segmento, chance mínima de queda', 'Gestor, Analista'],
    ['Campanha', 'Um plano, por ação, por categoria e por segmento: parceiros, custo e ganho esperado (RF46)', 'O plano — sem escolha, o último', 'Gestor, Analista'],
    ['Operações do sistema', 'O que foi registrado na trilha de auditoria, por tipo de ação, por pessoa e por dia (RF47)', 'Datas, pessoa, ação', 'Administrador'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(espaco(80));
  c.push(evidencia('sprint07/relatorios-lista', 560));
  c.push(legenda('A lista de relatórios do gestor. O de operações fica no menu da administração, e só o administrador o vê.'));

  c.push(quebra());
  c.push(h2('2.1 Desempenho por período'));
  c.push(evidencia('sprint07/relatorio-desempenho'));
  c.push(legenda('O relatório de desempenho: o total do recorte, por categoria e por segmento, com o CSV e a impressão.'));

  c.push(quebra());
  c.push(p(
    'O ticket médio é a razão dos totais, e não a média dos tickets (RN04). E a variação tem duas contas, que o '
    + 'próprio relatório explica embaixo de cada tabela. Por categoria, e no total, é a do painel: o faturamento '
    + 'do grupo contra o dele mesmo no período anterior. Por segmento, é a dos mesmos parceiros — o que os '
    + 'parceiros do grupo que venderam nos dois períodos faturaram agora, contra o que eles faturaram antes. O '
    + 'segmento muda de um período para o outro, e comparar o grupo de agora com o de antes mediria quem entrou '
    + 'e quem saiu dele, e não como ele foi (seção 10.1).',
  ));
  c.push(evidencia('sprint07/relatorio-desempenho-em-risco', 560));
  c.push(legenda('O mesmo relatório, filtrado pelo segmento Em risco: o total e as categorias passam a ser só desses parceiros.'));

  c.push(quebra());
  c.push(h2('2.2 Parceiros em risco'));
  c.push(p(
    'É o relatório que junta os três módulos numa linha por parceiro: o que ele faturou e como variou, do '
    + 'primeiro; o previsto e a chance de queda, do segundo; e a ação que o último plano reservou para ele, do '
    + 'terceiro. Vem do maior risco para o menor, e o filtro de chance mínima é uma escolha de quem lê, e não '
    + 'um limiar do sistema.',
  ));
  c.push(evidencia('sprint07/relatorio-risco'));
  c.push(legenda('Os parceiros com chance de queda a partir de 90%, com o medido, o previsto e a ação no último plano.'));
  c.push(espaco(40));
  c.push(p('Quem não tem previsão aparece com o motivo, e não com zero — zero seria lido como "sem risco" (RN09):', { size: 19 }));
  c.push(evidencia('sprint07/relatorio-risco-sem-previsao'));
  c.push(legenda('Os recém-chegados no relatório de risco: sem previsão, com o motivo que o cadastro deles também mostra.'));

  c.push(quebra());
  c.push(h2('2.3 Campanha'));
  c.push(evidencia('sprint07/relatorio-campanha'));
  c.push(legenda('O relatório de um plano de campanha: o total e os três agrupamentos, cada um somando o total.'));

  c.push(quebra());
  c.push(h2('2.4 Operações do sistema'));
  c.push(p(
    'O relatório do administrador resume a trilha de auditoria num intervalo — sem datas, os últimos trinta '
    + 'dias. As barras dão a proporção, e o número ao lado, o valor. Por pessoa, a tela lista as quinze que mais '
    + 'fizeram e soma as outras numa linha; o arquivo CSV traz todas. O link do total leva às mesmas operações '
    + 'na trilha, uma a uma.',
  ));
  c.push(evidencia('sprint07/relatorio-operacoes-topo', 560));
  c.push(legenda('O relatório de operações: o total do intervalo e as operações por tipo de ação.'));
  c.push(quebra());
  c.push(evidencia('sprint07/relatorio-operacoes-pessoas', 560));
  c.push(legenda('As operações por pessoa: as quinze que mais fizeram, e a linha das outras, que fecha a soma.'));
  c.push(p(
    'A base de demonstração tem centenas de usuários desativados, porque cada rodada de verificação e de captura '
    + 'cria os seus e os desativa no fim — a trilha aponta para eles, e por isso eles não são apagados. É o que '
    + 'aparece nesta tela.',
    { size: 17, italics: true },
  ));

  c.push(h2('2.5 Cada relatório, conferido contra a tela que ele resume'));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint07/relatorios.txt', '[2/6] Relatórios', '[3/6]')));

  // ======================================= 3. PESQUISAS E FILTROS
  c.push(quebra());
  c.push(h1('3. Pesquisas e filtros'));
  c.push(p(
    'A busca de parceiro e os filtros da lista vêm da Sprint 04. Esta entrega levou o mesmo desenho às telas '
    + 'que não tinham: o recorte fica no endereço, a busca ignora maiúscula e acento, mudar um filtro volta para '
    + 'a primeira página, e o recorte vazio diz que é o recorte que está vazio, e não a base.',
  ));
  c.push(table([2200, 4300, 3138], [
    ['Tela', 'Busca e filtros', 'Desde quando'],
    ['Parceiros', 'Busca por nome; categoria, segmento, status comercial e situação; ordenação, inclusive pelo risco', 'Sprints 04 e 06'],
    ['Painel', 'Período e categoria', 'Esta entrega (H82)'],
    ['Relatórios', 'Período, categoria, segmento, chance mínima de queda, plano, datas, pessoa e ação', 'Esta entrega (H84 a H87)'],
    ['Execuções', 'Resultado, modo em que rodou, quem calculou e datas', 'Esta entrega (H91, RF51)'],
    ['Usuários', 'Busca por nome ou login; perfil e situação', 'A busca, nesta entrega (H91, RF52)'],
    ['Auditoria', 'Busca por texto; ação, quem fez e datas', 'Esta entrega (H89, RF49)'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('3.1 O histórico de execuções'));
  c.push(evidencia('sprint07/antes-execucoes'));
  c.push(legenda('Antes: o histórico de execuções, sem filtro nenhum.'));
  c.push(espaco(40));
  c.push(evidencia('sprint07/depois-execucoes'));
  c.push(legenda('Depois: os filtros por resultado, modo, quem calculou e datas.'));
  c.push(quebra());
  c.push(evidencia('sprint07/depois-execucoes-inviaveis'));
  c.push(legenda('Só as execuções que terminaram sem plano viável, com a restrição que faltou.'));

  c.push(h2('3.2 A busca de usuários'));
  c.push(evidencia('sprint07/depois-usuarios-busca', 560));
  c.push(legenda('A busca por nome ou login, combinada com o filtro de situação.'));
  c.push(quebra());
  c.push(evidencia('sprint07/depois-usuarios-sem-acento', 560));
  c.push(legenda('"verificacao", sem cedilha nem til, acha quem se chama "Verificação".'));

  c.push(h2('3.3 O endereço de cada recorte, e o que voltou'));
  c.push(p(
    'A captura abre cada recorte pelo endereço, lê da tela quantos registros ela diz que achou e pede o mesmo '
    + 'recorte à API. Os dois números precisam ser o mesmo:',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/recortes.txt', 'Execuções — resultado=VIAVEL').filter((l, i, todasAs) => l.trim() || todasAs[i + 1]?.trim())));
  c.push(espaco(60));
  c.push(p('E as conferências da transcrição, pela API:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint07/relatorios.txt', '[3/6] Pesquisas', '[4/6]')));

  // ============================================== 4. EXPORTAÇÃO
  c.push(quebra());
  c.push(h1('4. Exportação'));
  c.push(p(
    'Dois formatos, e nenhuma biblioteca nova. O CSV é para quem vai trabalhar o número numa planilha; o PDF, '
    + 'para quem vai apresentar ou guardar. A lista de parceiros já exportava em CSV, desde a Sprint 04; agora '
    + 'exportam também os quatro relatórios, o plano de uma campanha e a trilha de auditoria.',
  ));
  c.push(table([2600, 1700, 5338], [
    ['O que se exporta', 'Formato', 'O que o arquivo traz'],
    ['Os quatro relatórios', 'CSV e PDF', 'O recorte da tela — os mesmos filtros, as mesmas linhas e o mesmo total'],
    ['O plano de uma campanha', 'CSV e PDF', 'Uma linha por parceiro do plano, na ordem da tela, e o total (RF53)'],
    ['A trilha de auditoria', 'CSV', 'Um registro por linha, com o recorte da busca e dos filtros (RF49)'],
    ['A lista de parceiros', 'CSV', 'O recorte da lista, como na Sprint 04 — com o risco, desde a Sprint 06'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('4.1 O CSV'));
  c.push(p(
    'O arquivo é a mesma consulta da tela: ponto e vírgula, vírgula decimal e a marca de UTF-8 no começo, que é '
    + 'o que a planilha em português abre sem ajuste. Texto que vem de usuário passa pela proteção contra '
    + 'fórmula — um nome começado por "=" não vira fórmula na planilha de quem exporta —, e número continua '
    + 'número, para a coluna somar. A exportação segue a permissão da tela.',
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/relatorios.txt', '$ GET /api/relatorios/risco/exportacao.csv', '$ GET /api/relatorios/campanha/exportacao.csv').filter((l) => l.trim())));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/relatorios.txt', '$ GET /api/otimizacoes/', '$ GET /api/relatorios/operacoes/exportacao.csv').filter((l) => l.trim())));
  c.push(espaco(60));
  c.push(p('Cada arquivo, conferido contra a tela de onde ele sai:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint07/relatorios.txt', '[4/6] Exportação', '[5/6]')));

  c.push(quebra());
  c.push(h2('4.2 O PDF, pela impressão do navegador'));
  c.push(p(
    '"Imprimir ou salvar em PDF" é a impressão do navegador, com uma folha de estilo própria: saem o menu, o '
    + 'cabeçalho, os filtros e os botões, e entram o título, o recorte aplicado por extenso — quem lê a folha '
    + 'não tem os filtros na frente — e a linha de quem gerou e quando. A tabela não é cortada entre duas '
    + 'páginas, o cabeçalho dela se repete em cada uma, e a folha sai sempre no tema claro, mesmo com a tela no '
    + 'escuro. As figuras abaixo são a primeira página de dois dos PDFs que a captura gerou.',
  ));
  c.push(evidencia('sprint07/relatorio-desempenho-folha', 400));
  c.push(legenda('A primeira página do PDF do relatório de desempenho.'));
  c.push(quebra());
  c.push(evidencia('sprint07/relatorio-risco-folha', 400));
  c.push(legenda('O PDF do relatório de parceiros em risco: as oito colunas na largura da folha.'));
  c.push(espaco(60));
  c.push(p('O endereço, o recorte que a folha diz, as páginas do PDF e o CSV de cada um:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/relatorios-em-pdf.txt', 'Desempenho por período').filter((l, i, todasAs) => l.trim() || todasAs[i + 1]?.trim())));
  c.push(espaco(60));
  c.push(p(
    'Os cinco PDFs estão no repositório, em docs/entrega/evidencias/sprint07/. A impressão é a do Chromium, que '
    + 'é o navegador da captura; em outro navegador, a paginação pode mudar.',
    { size: 17, italics: true },
  ));
  c.push(evidencia('sprint07/depois-execucao', 560));
  c.push(legenda('A execução aberta pelo histórico, com Exportar CSV e a impressão do plano.'));

  // ==================================== 5. LOGS E HISTÓRICO
  c.push(quebra());
  c.push(h1('5. Logs e histórico de operações'));
  c.push(p(
    'A trilha de auditoria existe desde a estrutura inicial, da Parte III, e todos os módulos gravam nela: quem entrou, quem foi '
    + 'recusado, o que foi importado, cadastrado, treinado, calculado, aprovado. Mas ela só se lia pela API — o '
    + 'caso de uso de auditar o sistema nunca tinha ganhado tela. Esta entrega dá a ela duas: a trilha inteira, '
    + 'para o administrador, e o histórico de um cadastro, no próprio cadastro.',
  ));

  c.push(h2('5.1 A trilha de auditoria, na tela'));
  c.push(p(
    'Cada registro diz quando, quem fez — o nome e o login —, a ação, em português, o que aconteceu, numa frase, '
    + 'e de onde veio. A frase é montada no servidor a partir do que foi gravado; quem quiser ver o registro cru '
    + 'abre "O que foi gravado" na linha. A trilha se filtra por ação, por pessoa e por datas, se busca por '
    + 'texto e se exporta em CSV com o mesmo recorte.',
  ));
  c.push(evidencia('sprint07/auditoria-tela'));
  c.push(legenda('A trilha de auditoria: quando, quem fez, a ação, o que aconteceu e a origem.'));
  c.push(quebra());
  c.push(evidencia('sprint07/auditoria-busca', 600));
  c.push(legenda('A busca na trilha pela marca da captura, com um registro aberto: a frase em cima, e o que foi gravado embaixo.'));
  c.push(quebra());
  c.push(evidencia('sprint07/auditoria-entradas-recusadas', 560));
  c.push(legenda('O filtro por ação: as entradas recusadas, com o login tentado — inclusive o que não existe.'));

  c.push(h2('5.2 O histórico, no cadastro do parceiro'));
  c.push(p(
    'O gestor e o analista não abrem a trilha inteira, que é do administrador. Mas, no cadastro de um parceiro, '
    + 'veem o que mudou nele, do mais recente ao mais antigo: o nome com o valor de antes e o de depois, e a '
    + 'categoria pelo nome que tinha na hora. O contato entra como "alterado", sem o valor: é dado de uma '
    + 'pessoa, e a trilha não o guarda.',
  ));
  c.push(evidencia('sprint07/historico-do-cadastro'));
  c.push(legenda('O histórico no cadastro: o que mudou, quando e por quem.'));

  c.push(quebra());
  c.push(h2('5.3 O que a tela e a API responderam'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/auditoria.txt', 'A trilha, buscando').filter((l, i, todasAs) => l.trim() || todasAs[i + 1]?.trim())));
  c.push(espaco(60));
  c.push(p('E as conferências da transcrição:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint07/relatorios.txt', '[5/6] Logs', '[6/6]')));

  // ============================================= 6. INTEGRAÇÃO
  c.push(quebra());
  c.push(h1('6. Integração com os módulos anteriores'));
  c.push(p(
    'Nada desta entrega calcula número novo: cada item lê o que um módulo anterior gravou, e por isso precisa '
    + 'dar o mesmo número que a tela daquele módulo. O relatório e o painel usam as mesmas consultas; o risco é '
    + 'o da previsão em uso; a campanha é o plano gravado. É isso que as conferências das seções 1 a 5 mostram, '
    + 'e é o que a tabela resume.',
  ));
  c.push(table([2700, 3300, 3638], [
    ['Item desta entrega', 'O que lê', 'Conferido contra'],
    ['Painel num recorte', 'As métricas e o ranking do módulo de análise', 'A soma das métricas no banco, e a posição no ranking da rede (RN02)'],
    ['Previsão e campanha no painel', 'A previsão do segundo módulo e o plano do terceiro', 'A previsão no cadastro do parceiro, e o plano que o gestor calculou'],
    ['Relatório de desempenho', 'As mesmas consultas do painel', 'O indicador do painel no mesmo período, categoria a categoria'],
    ['Relatório de parceiros em risco', 'O desempenho, a previsão em uso e o último plano', 'A previsão e o motivo de não haver previsão, no cadastro'],
    ['Relatório da campanha', 'O plano gravado pelo otimizador', 'A soma dos itens do plano; cada agrupamento soma o total'],
    ['Relatório de operações e a trilha', 'O que todos os módulos registram na auditoria', 'A contagem da trilha no mesmo intervalo'],
    ['Histórico do cadastro', 'Os registros da trilha daquele parceiro', 'A trilha, que traz os mesmos eventos com a origem'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('6.1 No banco'));
  c.push(p('A transcrição termina lendo o banco por SQL, só leitura, para mostrar que o relatório soma o que está gravado:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/relatorios.txt', '[6/6] No banco', 'Depois da limpeza').slice(1).filter((l) => !/^=+$/.test(l) && l.trim())));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado da transcrição: ', b: true, s: 19 }, { t: semRotulo(transcricao), s: 19 }]));

  c.push(h2('6.2 Depois de desligar e religar'));
  c.push(p(
    'O teste de persistência ganhou três conferências: depois do "docker compose down" e do "up", o histórico '
    + 'do cadastro, a trilha do parceiro e os relatórios voltam iguais.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint07/persistencia.txt', 'Conferências:')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(persistencia), s: 19 }]));

  c.push(quebra());
  c.push(h2('6.3 O mapa de navegação, com as telas novas'));
  c.push(p(
    'As telas desta entrega no mapa: os relatórios no grupo da análise, e a auditoria e as operações no da '
    + 'administração. Como na Parte VI, o mapa é largo demais para ser lido impresso numa página: a imagem está '
    + 'em alta resolução, para ampliar no PDF, e a versão vetorial está no repositório, em '
    + 'docs/09-sistema-visual.md.',
    { size: 19 },
  ));
  c.push(diagrama('navegacao-telas', undefined, PARTE_VII));
  c.push(legenda('O mapa de navegação, com os relatórios, a auditoria e as operações.'));

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

  c.push(h2('7.2 Os quatro tipos de teste, com exemplos desta entrega'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/testes.txt', 'Fluxos principais', 'Por arquivo')));

  c.push(quebra());
  c.push(h2('7.3 As validações negativas desta entrega'));
  c.push(p(
    'Provocadas contra a aplicação no ar, com o esperado de cada uma conferido contra o que voltou. Um link '
    + 'editado à mão, ou antigo, chega com um recorte que não existe: a recusa diz o que não existe, em vez de '
    + 'abrir a rede inteira no lugar do que foi pedido.',
    { size: 19 },
  ));
  c.push(table([3400, 6238], [
    ['Caso', 'Esperado, e o que voltou'],
    ...validacoesDestaEntrega(),
  ], { zebra: true, boldCol: 0, size: 16 }));
  c.push(espaco(80));
  c.push(rich([
    { t: 'Resultado da transcrição de validações, com as seções das Sprints 03 a 06: ', b: true, s: 19 },
    { t: semRotulo(validacoes), s: 19 },
  ]));

  c.push(h2('7.4 As telas, medidas no navegador'));
  c.push(p(
    `A medição foi refeita depois de cada Pull Request de tela, e a última é de ${telas.data}: as `
    + `${telas.telas} telas, cada uma a 768 e a 1.440 px e nos dois temas. ${telas.pares} pares de cor passam no `
    + `contraste; nenhuma das ${telas.medidas} medidas rola a página na horizontal ou corta conteúdo; e nenhuma `
    + `das ${telas.auditorias} auditorias do axe acusa violação.`,
  ));

  c.push(h2('7.5 Os bugs desta entrega'));
  c.push(p(
    'Todo defeito vira issue com o rótulo "fix" — o que apareceu, a causa, a correção e como foi encontrado — e '
    + 'é fechado pelo Pull Request que o corrige. O registro é gerado dessas issues: as abertas desde o PDF da '
    + 'Sprint 06, fora as que o registro dela já tinha.',
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
  c.push(espaco(60));
  c.push(p(
    'Fora do registro ficam os defeitos que apareceram enquanto as telas desta entrega eram construídas: foram '
    + 'corrigidos antes de o código entrar na branch principal, no mesmo Pull Request. O que as evidências e a '
    + 'medição no navegador acharam está na seção 10.',
    { size: 19 },
  ));

  // ============================== 8. REPOSITÓRIO, COMMITS E REVISÕES
  c.push(quebra());
  c.push(h1('8. Repositório, commits e revisões'));
  c.push(espaco(40));
  c.push(rich([{ t: 'Repositório: ', s: 21 }, { t: REPO, b: true, s: 21, c: '2C5B8F' }]));
  c.push(espaco(100));
  c.push(p(
    'Gerado do histórico do git, lido da branch principal do repositório remoto. A janela da Sprint 06 fecha no '
    + 'Pull Request do PDF dela (#195), e não no prazo: o trabalho que entrou depois dele é desta entrega.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/commits.txt', 'Totais', 'Por tipo')));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/commits.txt', 'Sprint 07 — ')));

  c.push(quebra());
  c.push(h2('8.1 Autoria e coautoria'));
  const coautoria = coautores.map((x) => `${x.nome.split(' ')[0]} ${x.n}`).join(', ');
  c.push(p(
    `Os ${totalDeCommits} commits têm o mesmo autor; os demais integrantes aparecem como coautores, pela área de `
    + `cada um (${coautoria}). A coautoria credita, mas não distribui a autoria: é a pendência da Pré-Banca, que `
    + 'continua como está (seção 11.1).',
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/commits.txt', 'Autoria e coautoria', 'Pull Requests incorporados, por')));

  c.push(h2('8.2 Revisões'));
  c.push(p(
    'O registro lista, para cada Pull Request incorporado desde o PDF da entrega anterior, quem abriu, quem foi '
    + 'convidado a revisar, quem revisou e com que resultado, e quem incorporou. Ele mostra a revisão como o '
    + 'GitHub a registrou.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint07/revisoes.txt', 'Resumo', 'Resultado:')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: semRotulo(registroRevisoes), s: 19 }]));

  // ====================================== 9. EXECUÇÃO E ROTEIRO
  c.push(quebra());
  c.push(h1('9. Execução e roteiro de demonstração'));
  c.push(p('O ambiente sobe com um comando, como nas entregas anteriores:'));
  c.push(espaco(40));
  c.push(...mono([
    'docker compose up -d                                     # sem GPU: a CPU paralela',
    'docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build   # com a GPU',
    'python scripts/resetar_banco.py --parceiros 500          # a base, segmentada e com o modelo',
  ]));
  c.push(espaco(120));
  c.push(h2('9.1 Roteiro para a orientação'));
  c.push(table([700, 8938], [
    ['#', 'Passo'],
    ['1', 'Entrar como gestor. No painel, escolher um período anterior e uma categoria: os indicadores, a série e o ranking mudam, e a posição continua a da rede'],
    ['2', 'Voltar ao período mais recente e descer até "Próximo período": o previsto ao lado do medido, o maior risco e a última campanha'],
    ['3', 'Relatórios → Desempenho por período: filtrar por um segmento, e ler a nota da variação'],
    ['4', 'Relatórios → Parceiros em risco: chance de queda a partir de 90%; "Imprimir ou salvar em PDF" e mostrar a folha'],
    ['5', 'No mesmo relatório, "Exportar CSV": abrir o arquivo na planilha, com as mesmas linhas da tela'],
    ['6', 'Campanha: calcular um plano. Execuções: filtrar pelo resultado; abrir a execução, exportar o plano em CSV e imprimir'],
    ['7', 'Parceiros: buscar por "praca", sem cedilha; abrir um parceiro, trocar a categoria e ver a linha nova no histórico do cadastro'],
    ['8', 'Entrar como administrador. Auditoria: buscar pelo nome do parceiro alterado, abrir "O que foi gravado", exportar o recorte'],
    ['9', 'Operações: o total do intervalo, por ação, por pessoa e por dia; o link que leva às mesmas operações na trilha'],
    ['10', 'Usuários: buscar por um trecho do login. Entrar como analista: o menu não tem Auditoria nem Operações'],
  ], { zebra: true, align: [AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(p(
    'Os roteiros das Sprints 04 a 06 continuam valendo. O Docker Desktop precisa estar aberto antes, e a '
    + 'verificação de ponta a ponta é a forma mais rápida de conferir que tudo subiu.',
    { size: 19 },
  ));

  // ============================================ 10. DIFICULDADES
  c.push(quebra());
  c.push(h1('10. Dificuldades encontradas'));
  const dificuldade = (titulo, causa, correcao) => {
    c.push(h2(titulo));
    c.push(p(causa));
    c.push(rich([{ t: 'O que foi feito: ', b: true, s: 19 }, { t: correcao, s: 19 }]));
  };
  dificuldade(
    '10.1 A variação por segmento contava quem mudou de segmento',
    'A primeira versão do relatório de desempenho comparava o faturamento do segmento agora com o do mesmo '
    + 'segmento no período anterior. O número saía certo na conta e errado no sentido: o segmento Em risco '
    + 'aparecia crescendo. O segmento muda a cada período: os parceiros que estão nele agora não são os que '
    + 'estavam antes, e a conta media essa troca, e não o desempenho deles.',
    'por segmento, a variação passou a ser a dos mesmos parceiros — os que venderam nos dois períodos. A regra '
    + 'foi para o requisito (RF44) antes do código, o relatório a explica embaixo da tabela, e há teste com o '
    + 'caso que enganava.',
  );
  dificuldade(
    '10.2 A folha impressa não é a tela, e o teste da tela não a vê',
    'O ambiente de teste da interface não desenha nem imprime. Os defeitos da folha só apareceram no PDF: a '
    + 'tela no tema escuro imprimia texto claro em papel branco; um bloco curto se dividia entre duas páginas; '
    + 'e a tabela de oito colunas do relatório de risco não cabia na largura da folha — o navegador encolhia a '
    + 'página inteira, e aquele PDF saía com a letra menor que a dos outros.',
    'a folha troca para o tema claro antes de imprimir e o devolve depois; os blocos curtos não se dividem; e, '
    + 'na folha, a tabela usa letra um passo menor e não reserva largura para o nome. A evidência é o PDF que a '
    + 'captura gera, olhado página a página, e a captura da primeira página de cada um.',
  );
  dificuldade(
    '10.3 Um relatório com centenas de linhas iguais',
    'O relatório de operações lista quem fez o quê. Na base de demonstração, que acumula os usuários de cada '
    + 'rodada de verificação, a tabela "por pessoa" passava de duzentas linhas — a maioria com meia dúzia de '
    + 'operações —, e a página virava uma lista que ninguém lê.',
    'a tela mostra as quinze pessoas que mais fizeram e soma as outras numa linha, para a tabela continuar '
    + 'fechando o total; o arquivo CSV traz todas. O limite é da apresentação, e não uma regra de negócio.',
  );
  dificuldade(
    '10.4 Filtrar o painel sem desmentir o ranking',
    'Filtrar por categoria pede uma decisão: a posição de uma padaria é entre as padarias ou entre todos? Se '
    + 'fosse entre as padarias, o mesmo parceiro teria duas posições no sistema, e a mobilidade do Top N deixaria '
    + 'de bater com o ranking — o erro que a RN02 existe para evitar.',
    'o filtro escolhe quem aparece, e a posição continua a da rede; a mobilidade não é filtrada. A tela diz as '
    + 'duas coisas, no ranking e no indicador, e a transcrição confere a posição contra o ranking da rede.',
  );
  dificuldade(
    '10.5 A trilha guardava códigos, e a tela precisa de frases',
    'A auditoria gravava a ação e os parâmetros como o sistema os usa: o código da ação, o identificador da '
    + 'categoria. Para a tela, "categoria 6 para 8" não diz nada. E o nome da categoria precisa ser o que ela '
    + 'tinha na hora da troca, e não o de hoje.',
    'a edição do cadastro passou a gravar o nome de antes e o de depois, e a categoria pelo nome; a frase é '
    + 'montada no servidor, com um rótulo em português para cada uma das ações — há teste de que nenhuma fica '
    + 'sem rótulo. O contato entra como "alterado", sem o valor.',
  );
  dificuldade(
    '10.6 Uma parte já entregue que mudava sozinha',
    'A Parte VI lia os números da medição das telas direto do arquivo que o script de medição escreve. Esta '
    + 'entrega mediu de novo, com seis telas a mais, e a parte entregue passou a dizer 26 telas onde o PDF da '
    + 'Sprint 06 diz 20 — sem erro e sem aviso. As evidências e as figuras de cada entrega já ficavam '
    + 'congeladas; as medições tinham ficado de fora (#208).',
    'cada parte passou a ler a cópia da medição da entrega dela, guardada junto das evidências. Quem achou foi '
    + 'a conferência do documento novo contra o entregue, parágrafo a parágrafo e figura a figura, feita antes '
    + 'de exportar o PDF.',
  );

  // ====================================== 11. AJUSTES
  c.push(quebra());
  c.push(h1('11. Ajustes no planejamento, na arquitetura e na modelagem'));
  c.push(table([2500, 3000, 4138], [
    ['O que mudou', 'De / para', 'Por quê'],
    ['Histórias H82 a H91', 'Backlog de 402 para 440 pontos', 'As seis entregas pedidas viraram dez histórias, com critério de aceite antes do código'],
    ['Requisitos', 'RF43 para RF53; o RF17 ganhou a categoria', 'Os relatórios, a exportação deles, a busca na trilha, o histórico do cadastro e os filtros que faltavam entraram no documento antes do código'],
    ['Casos de uso', '14 para 15', 'O UC15, consultar e exportar relatórios; o UC05 e o UC14 foram atualizados com o recorte do painel e a tela da trilha'],
    ['API', `64 para ${medida('operacoes')} operações`, 'O recorte do painel, os relatórios com a exportação de cada um, a busca e a exportação da trilha, o histórico do cadastro e o CSV do plano'],
    ['Modelo de dados', 'As mesmas 20 tabelas; três índices novos', 'A trilha só cresce e passou a ser filtrada na tela: índices por ação, por pessoa e pelo parceiro a que o registro se refere'],
    ['Registro da edição do cadastro', 'Identificadores para o valor de antes e o de depois', 'O histórico precisa dizer o que mudou sem depender do estado de hoje'],
    ['Exportação', 'Só CSV para CSV e PDF', 'O PDF é a impressão do navegador, com uma folha de estilo: nenhuma dependência nova'],
    ['Menu', 'Relatórios, Auditoria e Operações', 'Os itens continuam vindo do servidor, pelas permissões das rotas'],
    ['Medição das telas', `20 para ${telas.telas} telas`, 'A auditoria e as cinco de relatório, medidas depois de cada Pull Request de tela, e não só na entrega'],
    ['Janela da Sprint 06', 'Até 17/10 para até o PR do PDF (#195)', 'O trabalho que entrou depois do PDF é desta entrega'],
    ['Medições das partes entregues', 'Do arquivo vivo para a cópia da entrega', 'A medição é refeita a cada entrega, e a parte entregue não pode mudar com ela (#208)'],
    ['Figuras da Parte VII', 'Diagramas vivos para congelados', 'Como as das Partes II e VI: a parte entregue não muda quando o diagrama vivo mudar'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('11.1 As duas pendências da Pré-Banca, como estão'));
  // As três leituras do registro: todos aprovados, nenhum, ou parte deles.
  const semAprovacao = revisoes.length - aprovadosNoGithub;
  let situacaoDasRevisoes;
  if (!semAprovacao) {
    situacaoDasRevisoes = `os ${revisoes.length} têm aprovação registrada no GitHub. A pendência fecha se isso se `
      + 'mantiver até a entrega final';
  } else if (!aprovadosNoGithub) {
    situacaoDasRevisoes = 'nenhum tem aprovação registrada no GitHub: ela foi dada fora da plataforma, como na '
      + 'entrega anterior, e a pendência continua em aberto';
  } else {
    situacaoDasRevisoes = `${aprovadosNoGithub} têm aprovação registrada no GitHub; nos outros ${semAprovacao}, `
      + 'ela foi dada fora da plataforma, e a pendência continua em aberto';
  }
  c.push(bullet(
    `Revisão cruzada. Cada Pull Request desta entrega foi aberto convidando o dono de cada área a revisar, e `
    + `pedindo a aprovação no próprio PR. Dos ${revisoes.length} incorporados desde a entrega anterior, `
    + `${situacaoDasRevisoes}. O registro é gerado de novo a cada entrega.`,
  ));
  c.push(bullet(
    `Autoria. Os ${totalDeCommits} commits continuam com o mesmo autor, e os demais integrantes como coautores, `
    + 'pela área de cada um. Continua em aberto: o que cada integrante fizer até a entrega final — a decisão do '
    + 'limiar de recém-chegado (issue #59), o registro da validação do README (H72) — entra com a própria conta.',
  ));

  c.push(h2('11.2 Planejamento'));
  c.push(p(
    'As treze sprints internas terminaram antes do calendário, e a Sprint 07 da disciplina não corresponde a '
    + 'nenhuma delas: o enunciado pediu painel, relatórios, pesquisa, filtros, exportação e histórico, e o que '
    + 'faltava de cada um virou as histórias H82 a H91. A comunicação e o assistente, das Sprints 12 e 13, já '
    + 'estão construídos e ficam para as próximas entregas. A tabela de correspondência do cronograma foi '
    + 'atualizada.',
  ));

  // ========================================= 12. PRÓXIMOS PASSOS
  c.push(quebra());
  c.push(h1('12. Próximos passos'));
  c.push(table([2200, 7438], [
    ['Onde', 'O que entra'],
    ['Próximas entregas', 'A central de comunicação — mensagens por segmento, com aprovação humana obrigatória — e o assistente, que responde sobre dados já apurados ou se abstém; os dois já estão construídos'],
    ['Até a banca', 'A validação do README numa máquina limpa (H72), os dois vídeos (H74, H75) e a apresentação do núcleo à equipe, com as perguntas prováveis da banca (risco R4)'],
    ['No módulo de análise', 'O aval do Product Owner sobre o limiar do segmento Recém-chegado (issue #59)'],
    ['Congelamento', 'O código congela em 25/10, para sobrar tempo aos vídeos e ao ensaio'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(h2('12.1 No processo'));
  c.push(bullet('Revisão registrada no GitHub em todo Pull Request, antes do merge — a pendência da seção 11.1.'));
  c.push(bullet('Commits de autoria de cada integrante, com a própria conta, no que cada um fizer até a entrega final.'));
  c.push(bullet('Olhar o PDF impresso de toda tela que ganhar impressão: a folha não aparece em teste nenhum da interface.'));

  c.push(espaco(200));
  c.push(p(
    'Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa '
    + 'visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.',
    { italics: true, color: '5A6B7E', size: 18 },
  ));

  return c;
}

module.exports = { montar };
