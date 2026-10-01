/**
 * Parte VI do documento — Sprint 06 acadêmica: aprimoramento do sistema.
 *
 * O enunciado pede as correções apontadas na Pré-Banca, o terceiro módulo
 * implementado, a integração entre os módulos, melhorias na interface e ajustes
 * de navegação — cada um com evidência —, mais o link do repositório, as
 * dificuldades, os próximos passos e o registro do que mudou no planejamento, na
 * arquitetura e na modelagem. Como nas partes anteriores, nenhum número é
 * digitado aqui:
 *
 * - os números do otimizador vêm de `docs/medicoes/nucleo.md` e
 *   `otimizador.md`, e os da interface de `docs/medicoes/acessibilidade.md` —
 *   os arquivos que os scripts de medição escrevem;
 * - as contagens de testes, bugs, commits e revisões vêm de
 *   `evidencias/sprint06/`, que os scripts de registro escrevem a partir da
 *   suíte rodada, das issues, do git e dos Pull Requests;
 * - os títulos das abas, antes e depois, vêm dos registros de navegação da
 *   captura (`capturar_sprint06.js`).
 *
 * `aprovado()` recusa gerar se uma evidência registrar falha, e os leitores de
 * medida recusam se não acharem o número.
 *
 * **As figuras desta parte estão congeladas** em `diagramas/parte-vi/`, como as
 * da Parte II: o diagrama vivo pode mudar depois desta entrega, e a parte
 * entregue não.
 */
const fs = require('fs');
const path = require('path');
const { AlignmentType } = require('docx');
const { p, rich, h1, h2, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { diagrama, evidencia, legenda } = require('../comum/figuras');
const { todas, trecho, json } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';
const EVIDENCIAS = path.join(__dirname, '..', 'evidencias');
const PARTE_VI = 'parte-vi';

/*
 * Os poucos números que não saem de um arquivo de evidência, com a origem de
 * cada um. `null` é "ainda não medido", e a geração recusa.
 */
const MEDIDAS = {
  operacoes: 64, // app.openapi() da main, 30/09 — eram 37 na Sprint 05
  tabelas: 20, // catálogo do banco no ar, 30/09 — docs/08, seção 6; eram 18
};

function medida(nome) {
  const valor = MEDIDAS[nome];
  if (valor === null || valor === undefined) {
    throw new Error(`Medida "${nome}" não preenchida em secoes/sprint06.js — meça antes de gerar.`);
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
  const linhas = todas(arquivo);
  const linha = linhas.find((l) => l.includes(marcador));
  if (!linha) throw new Error(`Sem a linha de resultado em ${arquivo}.`);
  const falhas = linhas.filter((l) => /\bFALHA\b/.test(l));
  if (falhas.length) {
    throw new Error(`${arquivo} registra ${falhas.length} falha(s) — corrija e gere a evidência de novo.`);
  }
  return linha.trim();
}

/** As linhas de um trecho, do marcador de início ao de fim, os dois incluídos. */
function bloco(nome, de, ate) {
  const linhas = trecho(nome, de);
  const fim = linhas.findIndex((l, i) => i > 0 && l.includes(ate));
  if (fim < 0) throw new Error(`Não achei ${JSON.stringify(ate)} depois de ${JSON.stringify(de)} em ${nome}.`);
  return linhas.slice(0, fim + 1);
}

/** As conferências (ok) de um trecho da evidência, sem as trocas em volta. */
function conferencias(nome, de, ate) {
  const linhas = cruas(nome);
  const inicio = linhas.findIndex((l) => l.includes(de));
  if (inicio < 0) throw new Error(`Não achei ${JSON.stringify(de)} em ${nome}.`);
  const resto = linhas.slice(inicio + 1);
  const fim = ate ? resto.findIndex((l) => l.includes(ate)) : -1;
  return (fim >= 0 ? resto.slice(0, fim) : resto).filter((l) => /^\s+ok\s/.test(l)).map((l) => l.trimEnd());
}

/** As quatro suítes, lidas do registro de testes. */
function suites() {
  const achadas = cruas('sprint06/testes.txt')
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
 * As medições como estavam no PDF entregue, em `evidencias/sprint06/medicoes/`,
 * e não as vivas de `docs/medicoes/`: a das telas é refeita a cada tela nova, e
 * ler a viva fez esta parte mudar sozinha na geração da Sprint 07 — passou a
 * dizer 26 telas onde o PDF entregue diz 20. A parte entregue é retrato.
 */
function medicao(nome) {
  return fs.readFileSync(path.join(EVIDENCIAS, 'sprint06', 'medicoes', nome), 'utf8').replace(/\r\n/g, '\n');
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

const sem = (t) => t.replace(/\*\*/g, '').trim();

function medicaoDoNucleo() {
  const t = medicao('nucleo.md');
  const rnf = (rotulo) => sem(achar(t, new RegExp(`^\\| ${rotulo} \\| [^|]+ \\| ([^|]+) \\| atende \\|$`, 'm'), 'nucleo.md')[1]);
  const busca = secao(t, 'A busca inteira na GPU', 'nucleo.md');
  const linhaDaGpu = (parceiros) => achar(
    busca, new RegExp(`^\\| ${parceiros.replace('.', '\\.')} \\|(.+)\\|$`, 'm'), 'nucleo.md',
  )[1].split('|').map(sem);
  const doisMil = secao(t, '2.000 parceiros', 'nucleo.md');
  const openmp8 = achar(doisMil, /^\| OpenMP \| 8 \|([^\n]+)\|$/m, 'nucleo.md')[1].split('|').map(sem);
  // As colunas depois dos parceiros: OpenMP, só o laço, laço contra o OpenMP,
  // contexto da GPU, a busca inteira, a busca inteira contra o OpenMP.
  const [, , lacoContraOpenmp2000, contexto2000, , buscaContraOpenmp2000] = linhaDaGpu('2.000');
  const [, , lacoContraOpenmp10000, , , buscaContraOpenmp10000] = linhaDaGpu('10.000');
  return {
    rnf01: rnf('RNF01, de ponta a ponta'),
    rnf02: rnf('RNF02, speedup sobre o Python'),
    uplift: rnf('RNF02, uplift'),
    // Depois das threads: tempo, faixa, ganho sobre o serial, faixa do ganho...
    openmp8: openmp8[2],
    lacoContraOpenmp2000,
    lacoContraOpenmp10000,
    contexto2000,
    buscaContraOpenmp2000,
    buscaContraOpenmp10000,
  };
}

function medicaoDoOtimizador() {
  const t = secao(medicao('otimizador.md'), '2.000 parceiros', 'otimizador.md');
  return {
    otimo: achar(t, /ótimo da enumeração em \*\*(\d+ de \d+)\*\*/, 'otimizador.md')[1],
    empates: achar(t, /empatou com o guloso\*\* em (\d+ de \d+) buscas/, 'otimizador.md')[1],
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
  // A medição precisa ser de depois das mudanças de interface desta entrega
  // (a H81 entrou em 30/09): a de antes delas não diz nada sobre elas.
  const [dia, mes, ano] = data.split(' ')[0].split('/');
  if (`${ano}-${mes}-${dia}` < '2026-09-30') {
    throw new Error(`A medição das telas é de ${data}, de antes da H79 a H81 — rode scripts/medir_telas.py de novo.`);
  }
  return { pares, telas, medidas, auditorias, data };
}

/** Cada endereço do registro de navegação da captura: título da aba, onde parou e trilha. */
function navegacao(etapa) {
  const campos = { 'título da aba': 'titulo', 'a página parou em': 'parou', trilha: 'trilha' };
  const visitas = [];
  for (const l of cruas(`sprint06/navegacao-${etapa}.txt`)) {
    if (l.startsWith('/')) {
      visitas.push({ endereco: l.trim() });
    } else if (visitas.length) {
      const m = /^\s{2}(título da aba|a página parou em|trilha): (.*)$/.exec(l);
      if (m) visitas[visitas.length - 1][campos[m[1]]] = m[2].trim();
    }
  }
  if (!visitas.length) throw new Error(`O registro navegacao-${etapa}.txt está vazio.`);
  return visitas;
}

/** Os autores e coautores do registro de commits. */
function autoria() {
  const linhas = cruas('sprint06/commits.txt');
  const ler = (tipo) => linhas
    .map((l) => new RegExp(`^\\s{2}${tipo}\\s+(.+?)\\s{2,}(\\d+)$`).exec(l))
    .filter(Boolean)
    .map(([, nome, n]) => ({ nome, n: Number(n) }));
  const autores = ler('autor');
  const coautores = ler('coautor');
  if (!autores.length) throw new Error('O registro de commits não traz a autoria.');
  return { autores, coautores };
}

// Os casos da seção da campanha na transcrição de validações, na ordem em que
// ela os provoca (api/e2e/validacoes.py). O resultado de cada um vem do arquivo.
const CASOS_DA_CAMPANHA = [
  'O analista pede o cálculo',
  'Orçamento zero',
  'Máximo de ações zero',
  'Cota da cauda longa acima de 100%',
  'Fim da aplicação antes do início',
  'Cota para categoria que não existe',
  'Orçamento de R$ 100,00 com 30% na cauda longa',
  'Execução que não existe',
];

function validacoesDaCampanha() {
  const linhas = cruas('sprint06/validacoes.txt');
  const inicio = linhas.findIndex((l) => l.includes('[1/8] Campanha'));
  const fim = linhas.findIndex((l, i) => i > inicio && l.startsWith('Preparação'));
  const resultados = linhas.slice(inicio, fim)
    .filter((l) => /^\s+ok\s+esperado:/.test(l))
    // As aspas simples da transcrição viram aspas tipográficas: o trecho esperado
    // pode ter aspas duplas dentro, como o JSON da resposta.
    .map((l) => l.replace(/^\s+ok\s+esperado:\s*/, '').replace(/'([^']*)'/g, '“$1”'));
  if (resultados.length !== CASOS_DA_CAMPANHA.length) {
    throw new Error(`A seção da campanha em validacoes.txt tem ${resultados.length} conferências, e não ${CASOS_DA_CAMPANHA.length}.`);
  }
  return CASOS_DA_CAMPANHA.map((caso, i) => [caso, resultados[i]]);
}

function montar() {
  const c = [];
  const verificacao = aprovado('sprint06/verificacao.txt', 'verificações passaram');
  const transcricao = aprovado('sprint06/campanha.txt', 'Resultado:');
  const persistencia = aprovado('sprint06/persistencia.txt', 'Resultado:');
  const validacoes = aprovado('sprint06/validacoes.txt', 'Resultado:');
  const registroTestes = aprovado('sprint06/testes.txt', 'Resultado:');
  const registroBugs = aprovado('sprint06/bugs.txt', 'Resultado:');
  const registroRevisoes = aprovado('sprint06/revisoes.txt', 'Resultado:');
  aprovado('sprint06/modulo.txt', 'o mesmo plano');
  aprovado('sprint06/integracao.txt', 'Conferência:');
  const [api, modelo, otimizador, interfaceWeb] = suites();
  const nucleo = medicaoDoNucleo();
  const busca = medicaoDoOtimizador();
  const telas = medicaoDasTelas();
  const bugs = json('sprint06/bugs.json');
  const revisoes = json('sprint06/revisoes.json');
  const { autores, coautores } = autoria();
  const antes = navegacao('antes');
  const depois = navegacao('depois');
  if (antes.length !== depois.length) throw new Error('Os registros de navegação não visitaram os mesmos endereços.');

  const aprovadosNoGithub = revisoes.filter((r) => r.aprovado).length;
  const totalDeCommits = autores.reduce((s, a) => s + a.n, 0);
  const corrigidos = bugs.filter((b) => b.situacao === 'corrigido').length;
  const gpuDoRegistro = cruas('sprint06/testes.txt').find((l) => l.includes('GPU:'));
  if (!gpuDoRegistro) throw new Error('O registro de testes não diz em que placa o otimizador rodou.');
  const placa = gpuDoRegistro.split('GPU: ')[1].trim();

  c.push(quebra());
  c.push(h1('Parte VI — Sprint 06: Aprimoramento do Sistema'));

  c.push(p(
    'Esta entrega junta o terceiro módulo aos dois primeiros e cuida do que a Pré-Banca apontou. O terceiro '
    + 'módulo é a Campanha: com a previsão e o risco de cada parceiro, que o segundo módulo calcula, e a '
    + 'posição no ranking, que o primeiro calcula, o sistema decide em quem investir a verba de uma campanha '
    + '— que ação dar a cada parceiro, dentro do orçamento, do número de ações que a equipe consegue executar e '
    + 'das cotas. É a pergunta "em quem investir?" do problema do produto, e é onde está o núcleo '
    + 'computacional: o mesmo otimizador em Python, em C++, em paralelo na CPU e na GPU.',
  ));
  c.push(p(
    'Cada item vem com execução real: transcrições e capturas geradas por scripts contra a aplicação no ar, '
    + 'com a GPU, e registros de testes, de bugs, de commits e de revisões gerados de fonte. Gerar essas '
    + 'evidências achou três defeitos da própria sprint, corrigidos antes desta entrega — seção 7.',
  ));

  c.push(h2('As cinco entregas, e onde estão'));
  c.push(table([700, 2900, 2200, 3838], [
    ['#', 'Entrega', 'Situação', 'Evidência neste documento'],
    ['1', 'Correções apontadas na Pré-Banca', 'Feitas, com duas pendências declaradas', 'Seção 1 — observação por observação'],
    ['2', 'Terceiro módulo implementado', 'Funcionando', 'Seções 2 e 3 — o problema, as quatro versões medidas, as telas e o banco'],
    ['3', 'Integração entre os módulos', 'Funcionando', 'Seção 4 — pelo dado e pela tela, conferida contra a aplicação no ar'],
    ['4', 'Melhorias na interface', 'Feitas e medidas', 'Seção 5 — antes e depois, e a medição no navegador'],
    ['5', 'Ajustes de navegação', 'Feitos', 'Seção 6 — o menu, o título das abas, a página que não existe e a trilha'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  // =============================================== 1. PRÉ-BANCA
  c.push(quebra());
  c.push(h1('1. Correções apontadas na Pré-Banca'));
  c.push(p(
    'As devolutivas das Sprints 01 a 04, observação por observação: o que foi feito e onde está a evidência. '
    + 'Duas continuam em aberto, e estão escritas como estão, com a medida que falta.',
  ));
  const preBanca = [
    ['01', 'Reduzir o escopo do MVP', 'O escopo foi priorizado, e não cortado: histórias Must, Should e Could, e o assistente como válvula de escape. O código fechou antes do calendário, e a válvula não precisou ser usada', 'docs/04; docs/05, risco R2', 'Resolvido de outro modo'],
    ['01', 'Definir os papéis da equipe', 'Product Owner, Scrum Master, Frontend, Banco de Dados e Backend/Núcleo, com o dono de cada diretório no CODEOWNERS, que convida o dono a revisar o PR', 'docs/06; .github/CODEOWNERS', 'Resolvido'],
    ['01', 'Sprints semanais', 'Treze sprints semanais desde 16/09; as histórias de 13 pontos foram quebradas', 'docs/05, seção 2', 'Resolvido'],
    ['02', 'Documentação acompanhando o código', 'Arquitetura, modelo de dados e classes reescritos como construídos; nesta entrega, cada PR atualizou o documento que mudou — o mapa de navegação, o fluxo entre os módulos', 'docs/07 versão 2.1; docs/09', 'Resolvido'],
    ['02', 'Controlar o escopo; pouca margem para atraso', 'A construção terminou antes do calendário, e o congelamento foi antecipado de 30/11 para 25/10, para sobrar tempo aos vídeos', 'docs/05, riscos R2 e R7', 'Resolvido'],
    ['02', 'Evidência objetiva de modelo, paralelismo e GPU', `Medições geradas por script; o mesmo plano nos quatro modos; o benchmark na tela; e, nesta entrega, os testes do otimizador rodando na placa (${placa.split(' (')[0]}), sem pular nenhum`, 'Seções 2, 3 e 7; docs/medicoes', 'Resolvido'],
    ['03', 'Tela de administração de usuários', 'Feita antes da Sprint 05: criar a conta, mudar o nome e o perfil, desativar e reativar, pela interface', 'Parte V, seção 10.1', 'Resolvido'],
    ['03', 'Levar à interface o rigor do backend', `O axe em todo teste da interface; as ${telas.telas} telas medidas no navegador, nos dois temas; e dois defeitos de interface achados pelas evidências e corrigidos (#190, #192)`, 'Seções 5 e 7; CLAUDE.md', 'Resolvido'],
    ['03', 'Ampliar as validações negativas', 'A transcrição de validações ganhou uma seção por entrega — importação, cadastro, limiares, acesso, modelo e, agora, a campanha', `Seção 7.3 — ${validacoes.replace(/^Resultado:\s*/, '').replace(/\.$/, '')}`, 'Resolvido'],
    ['03', 'Cronograma sincronizado com o antecipado', 'O cronograma registra o calendário real e a correspondência entre as duas numerações, atualizada a cada entrega', 'docs/05, seção 1', 'Resolvido'],
    ['04', 'Fechar as lacunas: limiares, histórico de importações, sugestão de categoria', 'As três foram feitas antes do segundo módulo', 'Parte V, seção 10.1', 'Resolvido'],
    ['04', 'Distribuir a autoria dos commits', `Cada commit leva como coautor o dono da área, que o GitHub credita. Mas o autor dos ${totalDeCommits} commits continua sendo o mesmo integrante`, 'Seção 8', 'Em aberto'],
    ['04', 'Revisão cruzada real dos Pull Requests', `Cada PR desta entrega foi aberto convidando o dono de cada área a revisar, e pedindo a aprovação no próprio PR — mas a aprovação foi dada fora da plataforma. Dos ${revisoes.length} PRs desde a entrega anterior, ${aprovadosNoGithub} têm aprovação registrada no GitHub`, 'Seção 8 — registro de revisões', 'Em aberto'],
  ];
  c.push(table([500, 1900, 3800, 1800, 1638], [
    ['Sprint', 'Observação', 'O que foi feito', 'Evidência', 'Situação'],
    ...preBanca,
  ], { zebra: true, align: [AlignmentType.CENTER, null, null, null, AlignmentType.CENTER], size: 16 }));
  c.push(espaco(80));
  const abertas = preBanca.filter((l) => l[4] === 'Em aberto').length;
  c.push(rich([
    { t: 'Resultado: ', b: true, s: 19 },
    { t: `${preBanca.length - abertas} de ${preBanca.length} observações resolvidas; ${abertas} em aberto.`, s: 19 },
  ]));

  c.push(h2('1.1 As duas em aberto, e o que falta'));
  c.push(bullet(
    `Revisão cruzada. A proteção da branch principal já exige uma aprovação antes do merge, e ela vinha sendo `
    + `contornada pela permissão de administrador. O que falta é a aprovação no GitHub — na aba "Files changed", `
    + `"Review changes" e "Approve" —, que é o que o registro mostra. Ele é gerado de novo a cada entrega.`,
  ));
  c.push(bullet(
    'Autoria. Os integrantes passam a commitar com a própria conta o que fizerem até a entrega final: a decisão '
    + 'do limiar de recém-chegado (issue #59, do Product Owner), o registro da validação do README numa máquina '
    + 'limpa (H72, do Scrum Master) e os ajustes pedidos nas revisões.',
  ));

  // ======================================== 2. O TERCEIRO MÓDULO
  c.push(quebra());
  c.push(h1('2. O terceiro módulo: Campanha e otimizador'));

  c.push(h2('2.1 O problema'));
  c.push(p(
    'O gestor tem uma verba e um catálogo de ações comerciais — cupom, destaque na vitrine, campanha de '
    + 'categoria, visita de relacionamento, frete subsidiado —, cada uma com custo e efeito estimado. O sistema '
    + 'escolhe, para cada parceiro, uma ação ou nenhuma, de modo que o ganho esperado da campanha seja o maior '
    + 'possível sem passar de nenhuma restrição. Com centenas de parceiros e cinco ações, as combinações são '
    + 'mais que os átomos do universo: é um problema de otimização combinatória, e é por isso que ele mora no '
    + 'núcleo computacional, e não numa planilha.',
  ));
  c.push(table([1500, 4700, 3438], [
    ['Regra', 'O que diz', 'Onde aparece'],
    ['RN10', 'O ganho de uma ação sai da previsão do parceiro: faturamento previsto × crescimento, mais previsto × risco de queda × retenção', 'O plano e o cadastro do parceiro, marcados como estimativa'],
    ['RN11', 'Recebe ação quem está ativo e tem previsão da versão em uso; a cauda longa é quem está fora do Top N do ranking', 'A tela da campanha diz quantos entram e quantos ficam fora, e por quê'],
    ['RN07, RF31', 'Campanha que não cabe não vira plano: é recusada antes da busca, dizendo a restrição e quanto falta', 'A execução inviável, registrada sem plano'],
    ['RF32, RNF06', 'O cálculo roda no modo escolhido ou no primeiro disponível — GPU, CPU paralela, serial —, e sem GPU o sistema funciona igual', 'O seletor de modo, com o porquê do que falta'],
    ['RF33 a RF35', 'Cada execução fica gravada, com autor, parâmetros, modo, tempo e plano; dois planos se comparam lado a lado', 'Execuções e comparação'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('2.2 O mesmo otimizador, em quatro versões'));
  c.push(p(
    'Um algoritmo genético, com os planos gulosos na população inicial, escrito quatro vezes: em Python, que é '
    + 'a referência; em C++; em C++ com OpenMP, nos núcleos do processador; e em CUDA, na placa de vídeo, com a '
    + 'população morando na GPU de uma geração para a outra. Com a mesma semente, as quatro dão o mesmo plano — '
    + 'é o que permite comparar o tempo de uma com o da outra, e é conferido em teste, no benchmark e na tela.',
  ));
  c.push(bullet(`Contra o ótimo: em recortes pequenos, onde dá para enumerar todos os planos, o genético chegou ao ótimo em ${busca.otimo}.`));
  c.push(bullet(`Contra a escolha gulosa, que é o que uma planilha faria: empatou em ${busca.empates} buscas com 2.000 parceiros e ficou acima nas demais — nunca abaixo, porque os planos gulosos estão na população inicial.`));

  c.push(h2('2.3 Os números, medidos'));
  c.push(p(
    'Lidos da medição publicada no repositório, no contêiner da API e na placa da equipe. O cenário de '
    + 'referência é o dos requisitos: 2.000 parceiros e 5 ações.',
    { size: 19 },
  ));
  c.push(table([4300, 1700, 3638], [
    ['Medida', 'Meta', 'Medido'],
    ['RNF01 — a campanha calculada, de ponta a ponta, na GPU', 'até 5 s', nucleo.rnf01],
    ['RNF02 — ganho da GPU sobre o Python', 'no mínimo 5x', nucleo.rnf02],
    ['RNF02 — o plano da GPU contra o do Python', 'dentro de 2%', nucleo.uplift],
    ['OpenMP, 8 threads, sobre o C++ serial — 2.000 parceiros', '—', nucleo.openmp8],
    ['O laço na GPU sobre o OpenMP — 2.000 e 10.000 parceiros', '—', `${nucleo.lacoContraOpenmp2000} e ${nucleo.lacoContraOpenmp10000}`],
    ['A busca inteira na GPU sobre o OpenMP — 2.000 e 10.000', '—', `${nucleo.buscaContraOpenmp2000} e ${nucleo.buscaContraOpenmp10000}`],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(p(
    `A última linha é a mais honesta da tabela. Antes de qualquer conta, a GPU paga o custo fixo de iniciar o `
    + `driver e criar o contexto da placa — ${nucleo.contexto2000} com 2.000 parceiros. O laço na GPU é o mais `
    + 'rápido dos modos, mas, com o contexto, a busca inteira perde do OpenMP até perto de 10.000 parceiros. '
    + 'O resultado está medido e explicado na própria tela do benchmark, e não escondido: é uma conclusão '
    + 'técnica válida sobre quando a GPU compensa.',
    { size: 19 },
  ));

  c.push(h2('2.4 Números do módulo'));
  c.push(table([6000, 3638], [
    ['Medida', 'Valor'],
    ['Testes da API', `${api.total}, ${api.passaram} passando, ${api.pulados} pulados`],
    ['Testes do otimizador, na placa', `${otimizador.total}, todos passando`],
    ['Testes do modelo preditivo', `${modelo.total}, todos passando`],
    ['Testes da interface', `${interfaceWeb.total}, todos passando`],
    ['Verificação de ponta a ponta contra a aplicação no ar', verificacao.replace(/^As /, '').replace(/\.$/, '')],
    ['Operações da API', `${medida('operacoes')} — eram 37 na Sprint 05`],
    ['Tabelas no banco', `${medida('tabelas')} — eram 18 na Sprint 05`],
  ], { zebra: true, boldCol: 0 }));

  // ========================================= 3. FUNCIONANDO
  c.push(quebra());
  c.push(h1('3. O módulo funcionando'));

  c.push(h2('3.1 Com o que a campanha vai trabalhar'));
  c.push(p(
    'Ao abrir a tela, o gestor vê de onde vêm as previsões, quantos parceiros podem receber ação e quantos '
    + 'ficam fora, e por quê. As restrições são o orçamento, o máximo de ações, a cota mínima da cauda longa e '
    + 'as cotas por categoria. O modo automático diz qual roda nesta instalação — aqui, a GPU.',
  ));
  c.push(evidencia('sprint06/modulo-campanha-restricoes'));
  c.push(legenda('As restrições da campanha, com os elegíveis e os excluídos (RN11) e o modo de execução (RF32).'));
  c.push(espaco(80));
  c.push(evidencia('sprint06/modulo-campanha-catalogo'));
  c.push(legenda('O catálogo de ações, que só o gestor edita, com a fórmula do ganho (RN10).'));

  c.push(quebra());
  c.push(h2('3.2 Calcular'));
  c.push(p(
    'O cálculo pede confirmação e roda fora da requisição: a tela acompanha o andamento e pode ser fechada. A '
    + 'captura abaixo é do modo serial, em Python, que demora o bastante para o andamento aparecer.',
  ));
  c.push(evidencia('sprint06/modulo-campanha-andamento'));
  c.push(legenda('O cálculo em andamento, no modo serial.'));
  c.push(espaco(80));
  c.push(evidencia('sprint06/modulo-campanha-plano'));
  c.push(legenda('O plano calculado na GPU: as ações, o custo, o ganho esperado, as cotas e a comparação com o plano guloso.'));
  c.push(espaco(60));
  c.push(p('O mesmo pedido, nos dois modos, pela tela:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(bloco('sprint06/modulo.txt', 'O mesmo pedido', 'o mesmo plano')));

  c.push(quebra());
  c.push(h2('3.3 A campanha que não cabe'));
  c.push(p(
    'Com R$ 100,00 e 30% das ações na cauda longa, nem a ação mais barata para cada parceiro que as cotas exigem '
    + 'cabe no orçamento. A execução é registrada sem plano, dizendo qual restrição falhou e quanto falta — e '
    + 'não com um plano que desrespeite o orçamento.',
  ));
  c.push(evidencia('sprint06/modulo-campanha-inviavel'));
  c.push(legenda('Campanha inviável: sem plano, com a restrição e o que falta (RN07).'));
  c.push(espaco(80));
  c.push(p('O analista consulta a campanha, mas não decide onde vai a verba: no lugar do botão, o porquê.'));
  c.push(evidencia('sprint06/modulo-campanha-analista'));
  c.push(legenda('A campanha aberta pelo analista.'));

  c.push(quebra());
  c.push(h2('3.4 O histórico e a comparação'));
  c.push(evidencia('sprint06/modulo-execucoes'));
  c.push(legenda('O histórico de execuções: quem, quando, com que parâmetros, em que modo, em quanto tempo e com que resultado (RF34).'));
  c.push(espaco(80));
  c.push(evidencia('sprint06/modulo-comparacao'));
  c.push(legenda('Dois planos lado a lado: só o orçamento mudou, e a comparação diz o que mudou parceiro a parceiro (RF35).'));

  c.push(quebra());
  c.push(h2('3.5 O benchmark'));
  c.push(p(
    'O mesmo problema sintético, com a mesma semente, em cada modo desta instalação, rodado pela tela. O plano é '
    + 'o mesmo nos quatro, e a tela explica quando a GPU não ganha.',
  ));
  c.push(evidencia('sprint06/modulo-benchmark-resultado'));
  c.push(legenda('O benchmark no cenário de referência: tempo, dispersão e ganho de cada modo, e o mesmo plano nos quatro.'));
  c.push(espaco(80));
  c.push(evidencia('sprint06/modulo-benchmark-escalabilidade'));
  c.push(legenda('A escalabilidade, em escalas logarítmicas: o tempo de cada modo pelo número de parceiros.'));

  c.push(quebra());
  c.push(h2('3.6 No banco'));
  c.push(p(
    'A execução, o plano e os itens ficam gravados, e é deles que as telas leem. O recorte do modelo de dados '
    + 'que o módulo usa:',
  ));
  c.push(diagrama('mer-campanha', 560, PARTE_VI));
  c.push(legenda('O recorte do modelo de dados da campanha e do benchmark.'));
  c.push(p(
    'A transcrição da campanha calcula dois planos pela API e termina lendo as linhas do banco por SQL — só '
    + 'leitura —, para mostrar o que ficou gravado de fato:',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint06/campanha.txt', '$ SQL, só leitura', 'Depois da limpeza').filter((l) => !/^=+$/.test(l))));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado da transcrição: ', b: true, s: 19 }, { t: transcricao.replace(/^Resultado:\s*/, ''), s: 19 }]));

  c.push(h2('3.7 Depois de desligar e religar'));
  c.push(p(
    'O teste de persistência passou a incluir a campanha: um plano calculado antes do "docker compose down" '
    + 'volta igual, item a item, depois do "up" — e o cadastro de um parceiro do plano mostra a mesma ação.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint06/persistencia.txt', 'O estado lido agora')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: persistencia.replace(/^Resultado:\s*/, ''), s: 19 }]));

  // ========================================== 4. INTEGRAÇÃO
  c.push(quebra());
  c.push(h1('4. A integração entre os módulos'));
  c.push(p(
    'Os três módulos não se chamam: cada um grava no banco o que produz, e o seguinte lê dali. A importação '
    + 'grava as métricas; a segmentação e o ranking saem delas; o treino grava a previsão de cada parceiro; e a '
    + 'campanha lê a previsão da versão em uso e a posição no ranking. Nenhum módulo recalcula o que o anterior '
    + 'gravou — por isso o risco da lista, o do cadastro e o que entra no ganho da campanha são o mesmo número.',
  ));
  c.push(diagrama('fluxo-entre-modulos', 520, PARTE_VI));
  c.push(legenda('O dado de um módulo para o outro, e as telas onde os três se encontram. Tracejados, os caminhos de clique.'));

  c.push(quebra());
  c.push(h2('4.1 Pelo dado, conferido'));
  c.push(p(
    'A transcrição da campanha confere a integração contra a aplicação no ar: o plano parte da previsão, a cauda '
    + 'longa é a do ranking do painel, o risco da lista é o da previsão, e o cadastro mostra a ação reservada.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint06/campanha.txt', '[3/5] Integração', '[4/5]')));
  c.push(espaco(40));
  c.push(...mono(conferencias('sprint06/campanha.txt', '[4/5] Atualizar', '[5/5]')));

  c.push(h2('4.2 Pela tela, por cliques'));
  c.push(p(
    'Do indicador do painel à lista de quem está em risco, ordenada pelo risco que o modelo estimou; dali ao '
    + 'cadastro de um parceiro, com o desempenho medido, a previsão e a ação no último plano; ao plano; e de volta '
    + 'ao parceiro. Ninguém passou pelo menu.',
  ));
  c.push(evidencia('sprint06/integracao-painel-indicador', 240));
  c.push(legenda('O indicador do painel, com o caminho para quem está em risco.'));
  c.push(espaco(60));
  c.push(evidencia('sprint06/integracao-lista-em-risco'));
  c.push(legenda('A lista filtrada pelo segmento Em risco, ordenada pelo risco de queda que o modelo estimou.'));

  c.push(quebra());
  c.push(evidencia('sprint06/integracao-cadastro', 300));
  c.push(legenda('O cadastro do parceiro: os três módulos lado a lado — o desempenho medido, a previsão e a ação no plano.'));
  c.push(espaco(60));
  c.push(evidencia('sprint06/integracao-trilha-do-plano', 220));
  c.push(legenda('Aberto a partir do plano, o cadastro volta para o plano, e não para a lista.'));

  c.push(quebra());
  c.push(p('O caminho, passo a passo, como a página o mostrou:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint06/integracao.txt', 'O último plano')));

  // ===================================== 5. MELHORIAS NA INTERFACE
  c.push(quebra());
  c.push(h1('5. Melhorias na interface'));
  c.push(p(
    'As capturas "antes" foram tiradas da branch principal antes de qualquer mudança, e as "depois", com as '
    + 'melhorias no ar, sobre a mesma base de demonstração.',
  ));

  c.push(h2('5.1 O risco de queda na lista de parceiros'));
  c.push(p(
    'A lista mostrava o desempenho medido, e o risco só aparecia parceiro a parceiro, no cadastro. A coluna nova '
    + 'traz a chance estimada de cada um, ordenável, com a nota de que é estimativa, de que versão do modelo e '
    + 'até quando ela tem dados; quem não tem previsão vai para o fim, e o leitor de tela ouve o porquê. Ela sai '
    + 'numa consulta só, sem uma por parceiro — há teste para isso —, e também vai para a exportação.',
  ));
  c.push(evidencia('sprint06/antes-parceiros-lista'));
  c.push(legenda('Antes: a lista de parceiros sem o risco.'));
  c.push(quebra());
  c.push(evidencia('sprint06/depois-parceiros-lista'));
  c.push(legenda('Depois: a lista ordenada pelo risco de queda, do maior para o menor, com a nota da estimativa.'));

  c.push(quebra());
  c.push(h2('5.2 O cadastro do parceiro, com os três módulos'));
  c.push(evidencia('sprint06/antes-parceiro-cadastro', 520));
  c.push(legenda('Antes: o cadastro com o desempenho e a previsão, sem ligação com a campanha.'));
  c.push(espaco(60));
  c.push(evidencia('sprint06/depois-parceiro-cadastro', 300));
  c.push(legenda('Depois: a coluna do cadastro termina com a ação do parceiro no último plano, e o caminho até ele.'));

  c.push(quebra());
  c.push(h2('5.3 Do painel para os outros módulos'));
  c.push(p(
    'O ranking e a distribuição por segmento eram só leitura. Agora o nome no ranking abre o cadastro, cada '
    + 'segmento da distribuição abre a lista filtrada por ele, e o indicador de Em risco leva a quem está em risco.',
  ));
  c.push(evidencia('sprint06/antes-painel-ranking'));
  c.push(legenda('Antes: o ranking do painel, sem caminho para o parceiro.'));

  c.push(h2('5.4 Acessibilidade e largura, medidas'));
  c.push(p(
    `A medição das telas foi refeita depois das mudanças, num navegador de verdade (${telas.data}): `
    + `as ${telas.telas} telas, cada uma a 768 e a 1.440 px e nos dois temas. ${telas.pares} pares de cor passam no `
    + `contraste; nenhuma das ${telas.medidas} medidas rola a página na horizontal ou corta conteúdo; e nenhuma `
    + `das ${telas.auditorias} auditorias do axe acusa violação.`,
  ));
  c.push(p(
    'A primeira medição refeita não passou: o menu agrupado e a coluna de risco faziam a página rolar a 768 px '
    + 'nas telas do gestor. O defeito foi registrado e corrigido antes desta entrega (#192, seção 7).',
    { size: 19 },
  ));

  // ====================================== 6. NAVEGAÇÃO
  c.push(quebra());
  c.push(h1('6. Ajustes de navegação'));

  c.push(h2('6.1 O menu, organizado pelos módulos'));
  c.push(p(
    'O menu tinha os itens soltos, fora da ordem do fluxo. Agora eles se agrupam pelos módulos, na ordem em que '
    + 'o produto é usado — Análise, Previsão, Otimização, Comunicação e Administração —, e cada perfil vê só os '
    + 'grupos que tem: os itens continuam vindo do servidor, pelas permissões das rotas.',
  ));
  c.push(evidencia('sprint06/antes-menu-gestor', 210));
  c.push(legenda('Antes: o menu do gestor, com os itens soltos.'));
  c.push(espaco(40));
  c.push(evidencia('sprint06/depois-menu-gestor', 210));
  c.push(legenda('Depois: o menu do gestor, agrupado pelos módulos.'));

  c.push(quebra());
  c.push(evidencia('sprint06/depois-menu-analista', 210));
  c.push(legenda('O menu do analista.'));
  c.push(espaco(40));
  c.push(evidencia('sprint06/depois-menu-administrador', 210));
  c.push(legenda('O menu do administrador: a administração por último, separada do resto.'));
  c.push(espaco(40));
  c.push(evidencia('sprint06/depois-menu-768'));
  c.push(legenda('A 768 px, o menu vira uma barra que rola na própria caixa, com um fio entre um módulo e outro.'));

  c.push(quebra());
  c.push(h2('6.2 O título da aba'));
  const iguais = new Set(antes.map((v) => v.titulo));
  c.push(p(
    iguais.size === 1
      ? `Antes, as ${antes.length} abas visitadas diziam o mesmo: "${[...iguais][0]}". Com várias abas abertas, `
        + 'não havia como saber qual era qual. Agora cada aba diz a tela e, nas de detalhe, o item aberto primeiro:'
      : 'Os títulos das abas, antes e depois:',
  ));
  const generico = (endereco) => endereco.replace(/\/\d+/g, '/{id}').replace(/=\d+/g, '={id}');
  c.push(table([3600, 6038], [
    ['Endereço', 'Título da aba, depois'],
    ...depois.map((v) => [generico(v.endereco), v.titulo]),
  ], { zebra: true, size: 16 }));
  c.push(p('Lidos da própria página pela captura, em cada endereço — o título fica fora de qualquer captura de tela.', { size: 17, italics: true }));

  c.push(quebra());
  c.push(h2('6.3 O endereço que não existe'));
  const invalidoAntes = antes.find((v) => v.endereco.includes('nao-existe'));
  const invalidoDepois = depois.find((v) => v.endereco.includes('nao-existe'));
  c.push(p(
    `Antes, um endereço inválido levava ao painel sem aviso — o registro diz que a página parou em `
    + `"${invalidoAntes.parou}". Agora ela fica no endereço pedido e diz que a página não existe, mostra o que `
    + `foi pedido e oferece a volta, com o menu no lugar — e a aba diz "${invalidoDepois.titulo}".`,
  ));
  c.push(evidencia('sprint06/antes-endereco-invalido', 520));
  c.push(legenda('Antes: o endereço inválido caía no painel, sem aviso.'));
  c.push(espaco(40));
  c.push(evidencia('sprint06/depois-endereco-invalido', 520));
  c.push(legenda('Depois: a página não encontrada, com o endereço pedido e os caminhos de volta.'));

  c.push(quebra());
  c.push(h2('6.4 A trilha, de volta para de onde se veio'));
  c.push(p(
    'As telas de detalhe já tinham trilha, e o registro "antes" mostra isso. O que mudou é para onde ela volta: '
    + 'o cadastro aberto do painel, de um plano ou da comparação volta para lá, e não para a lista de parceiros, '
    + 'que a pessoa nem tinha aberto.',
  ));
  c.push(evidencia('sprint06/depois-trilha-do-painel', 240));
  c.push(legenda('O cadastro aberto pelo ranking do painel: a trilha volta para o painel.'));

  c.push(quebra());
  c.push(h2('6.5 O mapa de navegação'));
  c.push(p(
    'O mapa completo, com todas as telas, os grupos do menu e os caminhos entre os módulos. Ele é largo demais '
    + 'para ser lido impresso numa página: a imagem está em alta resolução, para ampliar no PDF, e a versão '
    + 'vetorial está no repositório, em docs/09-sistema-visual.md.',
    { size: 19 },
  ));
  c.push(diagrama('navegacao-telas', undefined, PARTE_VI));
  c.push(legenda('O mapa de navegação, com os grupos do menu e os caminhos entre os módulos.'));

  // ============================================ 7. TESTES E BUGS
  c.push(quebra());
  c.push(h1('7. Testes e bugs'));

  c.push(h2('7.1 As quatro suítes'));
  c.push(p(
    'O registro foi gerado rodando as suítes, e não escrito à mão. A do otimizador passou a rodar na imagem do '
    + `núcleo compilado com CUDA, com a placa da máquina — ${placa.replace(/[()]/g, '').replace(' capacidade', ', capacidade')}. `
    + 'Na máquina de desenvolvimento, sem CUDA, os testes da GPU pulariam.',
  ));
  c.push(table([3900, 1150, 1150, 1150, 1100, 1188], [
    ['Suíte', 'Testes', 'Passaram', 'Falharam', 'Pulados', 'Tempo'],
    ...[api, modelo, otimizador, interfaceWeb].map((s) => [
      s.nome, String(s.total), String(s.passaram), String(s.falharam), String(s.pulados), `${s.segundos} s`,
    ]),
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: registroTestes.replace(/^Resultado:\s*/, ''), s: 19 }]));
  c.push(p('Os pulados são da suíte da API: os testes contra o modelo de linguagem de verdade, que pulam quando ele não está no ar. O assistente fica para as próximas entregas, e a medição dele contra o modelo está publicada à parte (docs/medicoes/assistente.md).', { size: 17 }));

  c.push(h2('7.2 Os quatro tipos de teste, com exemplos'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint06/testes.txt', 'Fluxos principais', 'Por arquivo')));

  c.push(quebra());
  c.push(h2('7.3 As validações negativas da campanha'));
  c.push(p(
    'Provocadas contra a aplicação no ar, com o esperado de cada uma conferido contra o que voltou. Cada campo '
    + 'recusado diz o limite, na língua de quem usa:',
    { size: 19 },
  ));
  c.push(table([3400, 6238], [
    ['Caso', 'Esperado, e o que voltou'],
    ...validacoesDaCampanha(),
  ], { zebra: true, boldCol: 0, size: 16 }));
  c.push(espaco(80));
  c.push(rich([
    { t: 'Resultado da transcrição de validações, com as seções das Sprints 03 a 05: ', b: true, s: 19 },
    { t: validacoes.replace(/^Resultado:\s*/, ''), s: 19 },
  ]));

  c.push(h2('7.4 Os bugs desta entrega'));
  c.push(p(
    'Todo defeito vira issue com o rótulo "fix" — o que apareceu, a causa, a correção e como foi encontrado — e '
    + 'é fechado pelo Pull Request que o corrige. O registro é gerado dessas issues: as abertas desde o PDF da '
    + 'Sprint 05, fora as que o registro dela já tinha.',
  ));
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
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: registroBugs.replace(/^Resultado:\s*/, ''), s: 19 }]));

  c.push(h2('7.5 Três defeitos que só as evidências pegaram'));
  c.push(p(
    `${corrigidos === bugs.length ? 'Todos foram corrigidos.' : 'O registro acima diz o que falta.'} Três vieram `
    + 'de gerar as evidências desta entrega, e nenhum deles os testes automáticos pegavam:',
    { size: 19 },
  ));
  const detalhe = (numero) => {
    const b = bugs.find((x) => x.numero === numero);
    if (!b) throw new Error(`A issue #${numero} não está no registro de bugs.`);
    c.push(rich([{ t: `#${b.numero} — ${b.titulo}`, b: true, s: 19 }]));
    const limpo = (t) => t.replace(/`/g, '').replace(/\*\*/g, '');
    c.push(p(`Apareceu: ${limpo(b.apareceu)}`, { size: 18 }));
    c.push(p(`Causa: ${limpo(b.causa)}`, { size: 18 }));
    c.push(p(`${b.situacao === 'corrigido' ? 'Correção' : 'O que fazer'}: ${limpo(b.correcao)}`, { size: 18 }));
    c.push(espaco(60));
  };
  detalhe(190);
  c.push(quebra());
  detalhe(192);
  detalhe(189);

  // ============================== 8. REPOSITÓRIO, COMMITS E REVISÕES
  c.push(quebra());
  c.push(h1('8. Repositório, commits e revisões'));
  c.push(espaco(40));
  c.push(rich([{ t: 'Repositório: ', s: 21 }, { t: REPO, b: true, s: 21, c: '2C5B8F' }]));
  c.push(espaco(100));
  c.push(p(
    'Gerado do histórico do git, lido da branch principal do repositório remoto. A janela da Sprint 05 fecha '
    + 'no Pull Request do PDF dela (#112), e não num dia: no mesmo 25/09, depois do PDF, já entrou trabalho desta '
    + 'entrega.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint06/commits.txt', 'Totais', 'Por tipo')));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint06/commits.txt', 'Sprint 06 — 25/09')));

  c.push(quebra());
  c.push(h2('8.1 Autoria e coautoria'));
  const coautoria = coautores.map((x) => `${x.nome.split(' ')[0]} ${x.n}`).join(', ');
  c.push(p(
    `Os ${totalDeCommits} commits têm o mesmo autor; os demais integrantes aparecem como coautores, pela área de `
    + `cada um (${coautoria}). É a pendência da seção 1: a coautoria credita, mas não distribui a autoria.`,
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint06/commits.txt', 'Autoria e coautoria', 'Pull Requests incorporados, por')));

  c.push(h2('8.2 Revisões'));
  c.push(p(
    'O registro novo lista, para cada Pull Request incorporado desde o PDF da entrega anterior, quem abriu, '
    + 'quem foi convidado a revisar, quem revisou e com que resultado, e quem incorporou. Ele mostra a revisão '
    + 'como o GitHub a registrou.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint06/revisoes.txt', 'Resumo', 'Resultado:')));
  c.push(espaco(60));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: registroRevisoes.replace(/^Resultado:\s*/, ''), s: 19 }]));

  // ====================================== 9. EXECUÇÃO E ROTEIRO
  c.push(quebra());
  c.push(h1('9. Execução e roteiro de demonstração'));
  c.push(p('O ambiente sobe com um comando; com a GPU, com o arquivo dela por cima:'));
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
    ['1', 'Entrar como gestor: o menu por módulo, e o título da aba mudando de tela em tela'],
    ['2', 'Painel → "Ver quem está em risco" → ordenar pelo risco → abrir um parceiro: o medido, o previsto e a ação no plano'],
    ['3', 'Campanha: os elegíveis e os excluídos; calcular com orçamento de R$ 5.000,00, 30 ações e 30% na cauda longa'],
    ['4', 'O mesmo pedido no modo serial: o mesmo plano, em segundos em vez de décimos'],
    ['5', 'Orçamento de R$ 100,00: a campanha inviável, com o que falta'],
    ['6', 'Execuções: marcar dois planos e comparar; abrir um parceiro do plano e voltar pela trilha'],
    ['7', 'Benchmark no cenário padrão: as quatro colunas, o mesmo plano e a explicação da GPU'],
    ['8', 'Entrar como analista: a campanha para consulta, com o porquê no lugar do botão'],
    ['9', 'Um endereço que não existe: a página não encontrada, com a volta'],
    ['10', 'Fechar com "docker compose down", subir de novo e mostrar o mesmo plano'],
  ], { zebra: true, align: [AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(p(
    'O roteiro das Sprints 04 e 05 continua valendo. O Docker Desktop precisa estar aberto antes, e a '
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
    '10.1 A GPU tem um custo fixo que o tamanho do problema não paga',
    'Iniciar o driver e criar o contexto da placa custa perto de dois décimos de segundo a cada cálculo, com '
    + '500 ou com 10.000 parceiros. Medindo só o laço, a GPU parecia a mais rápida em qualquer tamanho; medindo '
    + 'o processo inteiro, ela perde do OpenMP até perto de 10.000.',
    'o executável informa o contexto à parte, o benchmark mostra as duas coisas, e a tela explica quando a GPU '
    + 'não ganha. A população fica na GPU entre as gerações, que é o que faz o laço compensar.',
  );
  dificuldade(
    '10.2 Medir o Python sem medir a API junto',
    'O benchmark roda em segundo plano, no processo da API. Ali, o Python dividiria o interpretador com as '
    + 'requisições da própria tela, que consulta o andamento a cada dois segundos: sairia mais lento, e o ganho '
    + 'das outras versões sobre ele, maior do que é.',
    'o Python do benchmark roda num processo à parte desde a primeira versão, com teste que confere isso; a '
    + 'medição não depende de a tela estar aberta.',
  );
  dificuldade(
    '10.3 No contêiner, mais threads não é mais previsível',
    'Com as 16 threads lógicas, o OpenMP oscilava de uma medição para a outra — houve execução sem ganho nenhum: '
    + 'o contêiner disputa a CPU com o próprio sistema.',
    'o OpenMP usa uma thread por núcleo físico, e as medições reportam mediana e faixa, e não um número só.',
  );
  dificuldade(
    '10.4 Evidência que depende do "período mais recente"',
    'A transcrição de validações importa um período longe no futuro, para não tocar na base de demonstração. A '
    + 'campanha usa sempre o período mais recente — e, com o futuro gravado, ninguém tinha previsão nele: a seção '
    + 'da campanha deu errado pela ordem, e não pelo sistema.',
    'a seção da campanha roda antes da importação. É a mesma lição da Sprint 05, com o modelo: quando o '
    + 'resultado depende do período mais recente, a ordem das seções é parte do teste.',
  );
  dificuldade(
    '10.5 Testes passando, defeito na tela',
    'Dois defeitos desta entrega passavam em todos os testes. A tela da campanha lia um campo que a API nunca '
    + 'mandou, e o teste dela simulava uma API que o mandava (#190). E a página rolava a 768 px por causa de '
    + 'texto escondido, que o ambiente de teste não desenha (#192).',
    'os dois foram achados pelas capturas e pela medição no navegador. O contrato agora tem teste do lado da '
    + 'API, e a armadilha ficou escrita no guia do projeto, para quem vier depois.',
  );

  // ====================================== 11. AJUSTES
  c.push(quebra());
  c.push(h1('11. Ajustes no planejamento, na arquitetura e na modelagem'));
  c.push(table([2500, 3000, 4138], [
    ['O que mudou', 'De / para', 'Por quê'],
    ['Histórias H79, H80 e H81', 'Backlog de 389 para 402 pontos', 'As melhorias de interface e de navegação e a integração pela tela, pedidas por esta entrega, viraram histórias com critério de aceite antes do código'],
    ['Otimizador (ADR-011)', 'Metaheurística (ADR-002) para genético com partidas independentes', 'Restrições por viabilidade, aritmética inteira e os planos gulosos na população inicial: o mesmo plano em qualquer modo, e nunca abaixo do guloso'],
    ['Onde o núcleo roda (ADR-012)', 'Compilado no Windows para executável na imagem da API', 'Chamado por processo, e medido onde o sistema roda; a GPU entra por um arquivo à parte, para o sistema subir em máquina sem placa (RNF06)'],
    ['Modelo de dados', '18 para 20 tabelas', 'A execução do benchmark (H57) e o lote de mensagens (H60); a campanha ganhou os efeitos da ação e a execução em segundo plano'],
    ['Quem pode o quê na campanha', 'Da tela para a resposta da API', 'O estado da campanha passou a dizer, pelo perfil de quem pergunta, se ele calcula e se edita o catálogo (#190)'],
    ['Registro de testes', 'Três para quatro suítes', 'A do otimizador, na imagem do núcleo, com a GPU'],
    ['Registro de revisões', 'Nenhum para gerado', 'A revisão cruzada, cobrada na Sprint 04, passou a ser mostrada pelo que o GitHub registra'],
    ['Janela da Sprint 05', 'Até 03/10 para até o PR do PDF', 'O trabalho que entrou depois do PDF, no mesmo dia, é desta entrega'],
    ['Arquitetura, documentada', 'Versão 2.0 para 2.1', 'A seção do dado entre os módulos, com o diagrama do fluxo'],
    ['Figuras da Parte VI', 'Diagramas vivos para congelados', 'Como as da Parte II: a parte entregue não muda quando o diagrama vivo mudar'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('11.1 Planejamento'));
  c.push(p(
    'Esta entrega corresponde às Sprints 9 a 11 internas — o otimizador, o paralelismo em CPU e a GPU com o '
    + 'benchmark — mais as histórias H79 a H81. A comunicação e o assistente, das Sprints 12 e 13, já estão '
    + 'construídos e ficam para as próximas entregas. A tabela de correspondência do cronograma foi atualizada.',
  ));

  // ========================================= 12. PRÓXIMOS PASSOS
  c.push(quebra());
  c.push(h1('12. Próximos passos'));
  c.push(table([2200, 7438], [
    ['Onde', 'O que entra'],
    ['Próximas entregas', 'A central de comunicação — mensagens por segmento, com aprovação humana obrigatória — e o assistente, que responde sobre dados já apurados ou se abstém'],
    ['Até a banca', 'A validação do README numa máquina limpa (H72), os dois vídeos (H74, H75) e a apresentação do núcleo à equipe, com as perguntas prováveis da banca (risco R4)'],
    ['No módulo de análise', 'O aval do Product Owner sobre o limiar do segmento Recém-chegado (issue #59)'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(h2('12.1 No processo'));
  c.push(bullet('Revisão registrada no GitHub em todo Pull Request, antes do merge — a pendência da seção 1.'));
  c.push(bullet('Commits de autoria de cada integrante, com a própria conta, no que cada um fizer até a entrega final.'));
  c.push(bullet('Medir as telas no navegador junto de cada mudança de interface, e não só na entrega: o defeito da #192 entrou com a H79 e só a medição da entrega o achou.'));

  c.push(espaco(200));
  c.push(p(
    'Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa '
    + 'visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.',
    { italics: true, color: '5A6B7E', size: 18 },
  ));

  return c;
}

module.exports = { montar };
