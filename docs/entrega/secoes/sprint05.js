/**
 * Parte V do documento — Sprint 05 acadêmica: segundo módulo funcionando.
 *
 * O enunciado pede o segundo módulo completo e integrado ao banco, as regras de
 * negócio atualizadas e justificadas, os testes com os resultados registrados, e
 * o registro dos bugs e das correções. Como nas Partes III e IV, cada item traz
 * execução real, lida dos arquivos que os scripts geraram — nenhum número é
 * digitado aqui:
 *
 * - os resultados do modelo vêm de `docs/medicoes/modelo.md`, que o
 *   `scripts/medir_modelo.py` escreve;
 * - as contagens de testes vêm de `evidencias/sprint05/testes.txt`, que o
 *   `scripts/registrar_testes.py` escreve rodando as três suítes;
 * - o registro de bugs vem de `evidencias/sprint05/bugs.json`, que o
 *   `scripts/registrar_bugs.py` escreve a partir das issues do GitHub.
 *
 * `aprovado()` recusa gerar se uma evidência registrar falha, e os leitores de
 * medida recusam se não acharem o número: um documento que afirma o que o
 * arquivo não diz é pior que um documento que não gera.
 */
const fs = require('fs');
const path = require('path');
const { AlignmentType } = require('docx');
const { p, rich, h1, h2, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { diagrama, evidencia, legenda } = require('../comum/figuras');
const { todas, trecho, json } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';
const RAIZ = path.join(__dirname, '..', '..', '..');

/*
 * Os poucos números que não saem de um arquivo de evidência, com a origem de
 * cada um. `null` é "ainda não medido", e a geração recusa.
 */
const MEDIDAS = {
  operacoes: 37, // app.openapi() da main, 25/09 — eram 31 na Sprint 04
  tabelas: 18, // catálogo do banco no ar, 24/09 — docs/08, seção 6
  imagemAntes: '326 MB', // docker image ls, a imagem da API antes do PyTorch — PR #95
  imagemDepois: '1,6 GB', // idem, depois; o PyTorch da roda CPU ocupa 773 MB dela
};

function medida(nome) {
  const valor = MEDIDAS[nome];
  if (valor === null || valor === undefined) {
    throw new Error(`Medida "${nome}" não preenchida em secoes/sprint05.js — meça antes de gerar.`);
  }
  return String(valor);
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

/** As três suítes, lidas do registro de testes. */
function suites() {
  const linhas = todas('sprint05/testes.txt');
  const achadas = linhas
    .map((l) => /^\s{2}(\S.+?)\s{2,}(\d+) testes\s+(\d+) passaram\s+(\d+) falharam\s+(\d+) s/.exec(l))
    .filter(Boolean)
    .map(([, nome, total, passaram, falharam, segundos]) => ({
      nome, total: Number(total), passaram: Number(passaram), falharam: Number(falharam), segundos,
    }));
  if (achadas.length !== 3) throw new Error('O registro de testes não tem as três suítes.');
  return achadas;
}

/**
 * O resumo da medição do modelo, lido de `docs/medicoes/modelo.md` — o arquivo
 * que o script de medição escreve. Cada tamanho de rede tem a sua seção.
 */
function medicaoDoModelo() {
  const texto = fs.readFileSync(path.join(RAIZ, 'docs', 'medicoes', 'modelo.md'), 'utf8')
    .replace(/\r\n/g, '\n');
  const secoes = {};
  for (const bloco of texto.split(/^## /m).slice(1)) {
    const titulo = bloco.split('\n')[0].trim();
    const m = /^([\d.]+) parceiros$/.exec(titulo);
    if (!m) continue;
    const celulas = (rotulo) => {
      const linha = bloco.split('\n').find((l) => l.startsWith(`| ${rotulo} |`));
      if (!linha) throw new Error(`Falta a linha "${rotulo}" na seção ${titulo} de docs/medicoes/modelo.md.`);
      // A mediana é o primeiro número de cada célula; a faixa vem entre parênteses.
      return linha.split('|').slice(2, -1).map((c) => c.replace(/\*\*/g, '').trim().split(' (')[0]);
    };
    const supera = /Supera as referências nas duas saídas \(UC07-A1\): (\d+ de \d+) treinos/.exec(bloco);
    const tempo = /Tempo de treino: mediana de ([\d,]+ s)/.exec(bloco);
    const vantagem = /melhor referência de cada treino: mediana de ([\d,]+ pontos? percentua(?:l|is))/.exec(bloco);
    if (!supera || !tempo || !vantagem) throw new Error(`Seção ${titulo} de docs/medicoes/modelo.md incompleta.`);
    secoes[m[1]] = {
      mape: celulas('MAPE do faturamento'),
      brier: celulas('Brier do risco'),
      calibracao: celulas('Erro de calibração'),
      supera: supera[1],
      tempo: tempo[1],
      vantagem: vantagem[1],
    };
  }
  if (!secoes['500'] || !secoes['5.000']) {
    throw new Error('docs/medicoes/modelo.md sem as seções de 500 e de 5.000 parceiros.');
  }
  return secoes;
}

function montar() {
  const c = [];
  const verificacao = aprovado('sprint05/verificacao.txt', 'verificações passaram');
  const integracao = aprovado('sprint05/modelo.txt', 'Resultado:');
  const persistencia = aprovado('sprint05/persistencia.txt', 'Resultado:');
  const validacoes = aprovado('sprint05/validacoes.txt', 'Resultado:');
  const registroTestes = aprovado('sprint05/testes.txt', 'Resultado:');
  const registroBugs = aprovado('sprint05/bugs.txt', 'Resultado:');
  const [api, modelo, interfaceWeb] = suites();
  const medicao = medicaoDoModelo();
  const bugs = json('sprint05/bugs.json');

  c.push(quebra());
  c.push(h1('Parte V — Sprint 05: Segundo Módulo Funcionando'));

  c.push(p(
    'O segundo módulo é o de Previsão — a parte preditiva do módulo M4 do escopo, anunciada como próximo '
    + 'passo na Parte IV. A partir do histórico que o primeiro módulo grava, o sistema treina uma rede '
    + 'neural, mede o erro dela contra contas simples no mesmo conjunto de teste, põe em uso a versão só '
    + 'se ela for melhor, e mostra, no cadastro de cada parceiro, o faturamento previsto para o próximo '
    + 'período e a chance de ele entrar em risco. É a pergunta "quem vai cair?" do problema do produto, '
    + 'respondida com número medido.',
  ));
  c.push(p(
    'Cada item desta parte vem com execução real: transcrições geradas por scripts contra a aplicação no '
    + 'ar, capturas da interface sobre a base de demonstração, e registros de testes, de bugs e de commits '
    + 'gerados de fonte — a suíte rodada, as issues do GitHub, o próprio histórico do git.',
  ));

  c.push(h2('As cinco entregas, e onde estão'));
  c.push(table([700, 2900, 2200, 3838], [
    ['#', 'Entrega', 'Situação', 'Evidência neste documento'],
    ['1', 'Segundo módulo completo, com fluxo real', 'Funcionando', 'Seções 1 e 2 — o fluxo, o modelo medido e as telas'],
    ['2', 'Integração com o banco', 'Funcionando', 'Seção 3 — armazenar, consultar, atualizar, e depois de religar'],
    ['3', 'Regras de negócio atualizadas', 'Registradas', 'Seção 4 — a regra nova e as que mudaram, com o porquê'],
    ['4', 'Testes das funcionalidades', 'Todos passando', 'Seção 5 — as três suítes e os quatro tipos que o enunciado pede'],
    ['5', 'Correção dos bugs', `${bugs.filter((b) => b.situacao === 'corrigido').length} de ${bugs.length} corrigidos`, 'Seção 6 — o registro, gerado das issues'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  // ====================================================== 1. O MÓDULO
  c.push(quebra());
  c.push(h1('1. O segundo módulo: Previsão'));

  c.push(h2('1.1 O fluxo'));
  c.push(p(
    'Um gestor abre a tela Modelo, vê a versão em uso e as métricas dela, e dispara um treino. O treino '
    + 'roda fora da requisição — a tela acompanha o andamento e anuncia o resultado —, e as previsões '
    + 'passam a aparecer no cadastro de cada parceiro. Uma importação nova deixa a previsão "com dados '
    + 'até" um período antigo, e um novo treino a atualiza.',
  ));
  c.push(table([1700, 4600, 1500, 1838], [
    ['Etapa', 'O que o sistema faz', 'Requisito', 'Tela'],
    ['Consultar', 'Mostra a versão em uso, com data, período-base, volume e métricas, e se dá para treinar agora', 'UC07, RF27', 'Modelo'],
    ['Treinar', 'Grava o treino em andamento e o executa em segundo plano; um por vez, travado pelo banco', 'UC07, H45', 'Modelo'],
    ['Separar', 'Monta a janela dos 4 períodos de cada parceiro e separa treino, validação e teste pelo tempo', 'H41, RN09', '—'],
    ['Medir', 'Treina a rede e mede o erro dela e o de três referências no mesmo conjunto de teste', 'H42, H43, H46', 'Modelo'],
    ['Decidir', 'Põe a versão em uso só se ela superar as referências nas duas saídas; senão fica a anterior', 'UC07-A1', 'Modelo'],
    ['Prever', 'Grava a previsão do próximo período e o risco de cada parceiro, com a versão que a produziu', 'RF27, UC07-A2', '—'],
    ['Mostrar', 'Exibe previsão e risco no cadastro do parceiro, marcados como estimativa, ou o motivo de não haver', 'RF28, H44', 'Parceiro'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('1.2 O modelo, e contra o que ele se mede'));
  c.push(p(
    'Uma rede neural pequena, escrita em PyTorch, com duas saídas: o faturamento do próximo período e a '
    + 'chance de o parceiro estar Em Risco nele. Ela olha os quatro últimos períodos de cada parceiro — '
    + 'faturamento e pedidos, ticket médio, tendência, posição no ranking do período, categoria e tempo '
    + 'de casa — e aprende com o histórico inteiro da rede. O último período da base testa, o penúltimo '
    + 'valida, e os anteriores treinam: embaralhar os períodos vazaria o futuro para dentro do treino e '
    + 'daria uma métrica boa e falsa.',
  ));
  c.push(p(
    'Uma rede que não bate uma conta de cabeça não agrega nada, e por isso ela é medida contra três '
    + 'referências: repetir o último período, a média móvel dos últimos quatro, e — para o risco — a '
    + 'taxa observada no treino, separada por "caiu no último período". A tabela abaixo é a medição '
    + 'publicada no repositório: três redes geradas, cinco sementes de treino em cada uma, mediana dos '
    + 'quinze treinos.',
    { size: 19 },
  ));
  const m500 = medicao['500'];
  const m5000 = medicao['5.000'];
  c.push(table([3000, 1650, 1650, 1650, 1688], [
    ['Medida (mediana de 15 treinos)', 'Rede', 'Repetir o último', 'Média móvel', 'Taxa observada'],
    ['Erro no faturamento (MAPE), 500 parceiros', m500.mape[0], m500.mape[1], m500.mape[2], '—'],
    ['Erro no faturamento (MAPE), 5.000 parceiros', m5000.mape[0], m5000.mape[1], m5000.mape[2], '—'],
    ['Erro no risco (Brier), 500 parceiros', m500.brier[0], '—', '—', m500.brier[1]],
    ['Erro no risco (Brier), 5.000 parceiros', m5000.brier[0], '—', '—', m5000.brier[1]],
    ['Erro de calibração do risco, 500 parceiros', m500.calibracao[0], '—', '—', m500.calibracao[1]],
    ['Erro de calibração do risco, 5.000 parceiros', m5000.calibracao[0], '—', '—', m5000.calibracao[1]],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(bullet(`A rede superou as referências nas duas saídas em ${m500.supera} treinos com 500 parceiros e em ${m5000.supera} com 5.000.`));
  c.push(bullet(`A vantagem no faturamento é pequena: mediana de ${m500.vantagem} sobre a melhor referência de cada treino, com 500 parceiros, e de ${m5000.vantagem} com 5.000. Está registrada como é.`));
  c.push(bullet('O risco da rede separa melhor quem cai de quem não cai — Brier menor —, mas é menos calibrado que a taxa observada, que é calibrada por construção: é a própria frequência, em dois grupos. A rede ganha no Brier porque distingue os parceiros dentro de cada grupo.'));
  c.push(bullet(`Tempo de treino: mediana de ${m500.tempo} com 500 parceiros e ${m5000.tempo} com 5.000, numa thread — medido, e é o que permite treinar em segundo plano no próprio processo da API.`));
  c.push(espaco(60));
  c.push(p(
    'Se a rede não superasse as referências, o módulo funcionaria do mesmo jeito: a versão não entraria '
    + 'em uso, e as previsões sairiam da referência, identificadas assim na tela. Conclusão negativa bem '
    + 'medida é resultado válido — a arquitetura registrou isso antes de a rede existir.',
    { size: 19 },
  ));

  c.push(h2('1.3 Números do módulo'));
  c.push(table([6000, 3638], [
    ['Medida', 'Valor'],
    ['Testes da API', `${api.total}, todos passando`],
    ['Testes do modelo preditivo', `${modelo.total}, todos passando`],
    ['Testes da interface', `${interfaceWeb.total}, todos passando`],
    ['Verificação de ponta a ponta contra a aplicação no ar', verificacao.replace(/^As /, '').replace(/\.$/, '')],
    ['Operações da API', `${medida('operacoes')} — eram 31 na Sprint 04`],
    ['Tabelas no banco', `${medida('tabelas')} — a do treino do modelo é a nova`],
    ['Imagem da API, com o PyTorch da roda CPU', `${medida('imagemAntes')} → ${medida('imagemDepois')}`],
  ], { zebra: true, boldCol: 0 }));

  // ============================================ 2. FUNCIONANDO
  c.push(quebra());
  c.push(h1('2. O módulo funcionando'));

  c.push(h2('2.1 A tela do modelo'));
  c.push(p(
    'Para Administrador e Gestor, pelo menu — que vem do servidor, a partir das permissões das próprias '
    + 'rotas. À esquerda, os fatos da versão em uso; à direita, o erro da rede ao lado do erro das '
    + 'referências, um gráfico por métrica. A rede na cor dos gráficos, as referências em cinza: o '
    + 'gráfico existe para responder uma pergunta só — a rede erra menos que a conta simples? A barra '
    + 'começa no zero, e o número vem escrito na ponta.',
  ));
  c.push(evidencia('sprint05/fluxo-1-versao-em-uso'));
  c.push(legenda('A versão em uso, com a comparação contra as referências no mesmo conjunto de teste.'));

  c.push(quebra());
  c.push(h2('2.2 Treinar'));
  c.push(p(
    'O treino pede confirmação, que diz o que vai acontecer: roda em segundo plano, e a versão nova só '
    + 'entra em uso se errar menos que as referências nas duas saídas.',
  ));
  c.push(evidencia('sprint05/fluxo-2-confirmacao'));
  c.push(legenda('A confirmação antes do treino.'));
  c.push(espaco(120));
  c.push(p(
    'A requisição volta na hora, com o treino gravado em andamento. A tela consulta o estado a cada dois '
    + 'segundos; quem sair e voltar reencontra o andamento, porque ele vem do servidor e não da memória '
    + 'da página. A barra corre sem porcentagem, porque não há como sabê-la — a parada antecipada decide '
    + 'quando o treino acaba.',
  ));
  c.push(evidencia('sprint05/fluxo-3-treinando'));
  c.push(legenda('O treino em andamento, com o botão desligado até ele terminar.'));

  c.push(quebra());
  c.push(p(
    'Ao terminar, o resultado é anunciado — a versão nova entrou em uso, ou ficou a anterior, com o '
    + 'motivo escrito pela API. Um leitor de tela ouve o mesmo anúncio.',
  ));
  c.push(evidencia('sprint05/fluxo-4-resultado-do-treino'));
  c.push(legenda('Treino concluído: a versão nova entrou em uso, com as métricas dela.'));
  c.push(espaco(120));
  c.push(evidencia('sprint05/fluxo-5-historico-de-treinos'));
  c.push(legenda('O histórico de treinos: quando, por quem, o erro da rede e das referências, e o que cada um deixou.'));

  c.push(quebra());
  c.push(h2('2.3 A previsão no cadastro do parceiro'));
  c.push(p(
    'Abaixo do desempenho medido, o bloco "Próximo período", com a etiqueta Estimativa: o faturamento '
    + 'previsto, a chance de estar em risco, a data dos dados de onde a previsão parte e a versão que a '
    + 'produziu. Número previsto ao lado de número medido, sem marca, seria lido como medição.',
  ));
  c.push(evidencia('sprint05/fluxo-6-previsao-no-cadastro', 360));
  c.push(legenda('O desempenho do período mais recente e, embaixo, a previsão do próximo, marcada como estimativa.'));
  c.push(espaco(120));
  c.push(p(
    'Na série do parceiro, o trecho até o próximo período é tracejado, com marcador vazado, e a legenda '
    + 'diz qual é qual. Cor diferente sozinha não bastaria: quem não a distingue leria a previsão como '
    + 'medição.',
  ));
  c.push(evidencia('sprint05/fluxo-7-serie-com-estimativa'));
  c.push(legenda('A série histórica com a estimativa do próximo período, tracejada.'));

  c.push(quebra());
  c.push(h2('2.4 Verificação de ponta a ponta'));
  c.push(p(
    'A verificação roda contra a aplicação no ar e ganhou a seção do modelo — que roda antes de qualquer '
    + 'importação da própria verificação, porque ela grava semanas no futuro e o treino parte do período '
    + 'mais recente. Os blocos das sprints anteriores continuam passando na mesma execução.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/verificacao.txt', 'Modelo preditivo', '[5/6]')));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/verificacao.txt', 'Limpeza', 'verificações passaram')));
  c.push(espaco(80));
  c.push(rich([
    { t: 'Resultado: ', b: true, s: 19 },
    { t: `${verificacao} O treino da verificação sai na limpeza, e a versão em uso volta a ser a de antes — conferido.`, s: 19 },
  ]));

  // ================================================= 3. BANCO
  c.push(quebra());
  c.push(h1('3. Integração com o banco'));

  c.push(p(
    'O módulo grava, consulta e atualiza no mesmo banco do primeiro, e a transcrição abaixo mostra as '
    + 'três coisas contra a aplicação no ar. Ela termina lendo as linhas do banco por SQL — só leitura —, '
    + 'para mostrar o que ficou gravado de fato, e não o que a API diz que gravou.',
  ));
  c.push(diagrama('mer-previsao', 520));
  c.push(legenda('O recorte do modelo de dados que o módulo usa. A ligação tracejada não é chave estrangeira: vem da versão, pelo nome.'));

  c.push(quebra());
  c.push(h2('3.1 Armazenar — o treino gravado'));
  c.push(p(
    'O gestor dispara o treino. A resposta já traz o registro gravado em andamento, com o autor e o '
    + 'período-base; o volume e as métricas chegam na mesma linha quando o treino termina.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/modelo.txt', '$ POST /api/modelo/treinos', 'O registro gravado')));

  c.push(quebra());
  c.push(h2('3.2 Consultar — a previsão no cadastro'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/modelo.txt', 'O analista abre o cadastro', '=====')));

  c.push(h2('3.3 Atualizar — um novo treino muda a versão em uso'));
  c.push(p(
    'Um segundo treino grava uma versão nova, e o mesmo cadastro, lido de novo, passa a mostrar a '
    + 'previsão dela:',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/modelo.txt', 'de novo:', '=====')));

  c.push(quebra());
  c.push(h2('3.4 No banco'));
  c.push(p(
    'Os dois treinos, com os pesos da rede na própria linha — poucos KB, o que dispensa arquivo em volume '
    + 'e faz a versão em uso sobreviver a reinício —, e as previsões das duas versões sobre o mesmo '
    + 'período: elas coexistem, e é isso que permite comparar versões sobre o mesmo histórico.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/modelo.txt', '$ SQL, só leitura', '=====')));
  c.push(espaco(60));
  c.push(rich([
    { t: 'Resultado da transcrição: ', b: true, s: 19 },
    { t: integracao.replace(/^Resultado:\s*/, ''), s: 19 },
  ]));

  c.push(h2('3.5 Depois de desligar e religar'));
  c.push(p(
    'O teste de persistência da Sprint 04 — "docker compose down", que remove os contêineres, e "up", '
    + 'que cria outros — passou a conferir também o modelo: a versão em uso, com as mesmas métricas, e a '
    + 'previsão de um parceiro, lidas antes e depois. Se algo do modelo morasse na memória do processo, '
    + 'teria morrido com ele.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/persistencia.txt', 'O estado anotado', '=====')));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/persistencia.txt', 'O estado lido agora', '=====')));
  c.push(espaco(60));
  c.push(rich([
    { t: 'Resultado: ', b: true, s: 19 },
    { t: persistencia.replace(/^Resultado:\s*/, ''), s: 19 },
  ]));

  // ========================================= 4. REGRAS DE NEGÓCIO
  c.push(quebra());
  c.push(h1('4. Regras de negócio implementadas e atualizadas'));

  c.push(h2('4.1 A regra nova: RN09'));
  c.push(p(
    'O caso de uso de treino e a história do risco falavam em "probabilidade de queda" e em "mínimo de '
    + 'períodos", e nenhum dos dois estava definido na especificação. A regra do projeto manda perguntar '
    + 'antes de escolher: a pergunta foi registrada na issue #85, decidida, e virou a RN09.',
  ));
  c.push(table([500, 4600, 4538], [
    ['#', 'A regra', 'Por quê'],
    ['1', 'Queda prevista é estar Em Risco no período seguinte, pelo critério da RN01 — quedas seguidas até o limiar configurado', 'O rótulo do treino sai da mesma função que classifica o segmento: modelo e segmentação nunca discordam, e mudar o limiar muda os dois'],
    ['2', 'O treino exige 8 períodos na base; abaixo disso, é recusado dizendo quantos faltam', 'Quatro de janela, dois para treinar, um para validar e um para testar — sem isso não há como separar no tempo'],
    ['3', 'Parceiro com menos de 4 períodos, ou fora do período mais recente, não recebe previsão — e a tela diz por quê', 'A janela é de 4 períodos, e a previsão parte do período mais recente'],
    ['4', 'Versão que não supera a referência não entra em uso; sem versão anterior, vale a referência', 'Substituir por um modelo pior não é conteúdo técnico; resultado negativo bem medido é'],
    ['5', 'Previsão é estimativa e aparece como tal, com o período-base e a versão', 'Critério de aceite da história H44'],
  ], { zebra: true, align: [AlignmentType.CENTER], size: 17 }));

  c.push(h2('4.2 O que mudou desde a Sprint 04'));
  c.push(table([2400, 3300, 3938], [
    ['Regra ou documento', 'O que mudou', 'Por quê'],
    ['RN05 — categoria sugerida', 'Passou a dizer como a categoria é inferida: palavra inteira, exatamente uma categoria, só se existe e está ativa', 'A sugestão pelo nome foi implementada (RF15); regra aprovada na issue #35, e escrita antes do código'],
    ['"Pendente de classificação"', 'É quem não tem categoria confirmada — em branco ou só sugerida', 'Com a sugestão automática, "sem categoria" deixaria de fora quem tem só palpite'],
    ['UC03 — histórico de importações', 'O Administrador passa a ler o histórico', 'O caso de uso contradizia o RF13, que dá o histórico a ele; prevaleceu o requisito'],
    ['UC07 — treino do modelo', 'O mínimo do fluxo de exceção passou a ser o da RN09, e a nota diz como o caso aparece na interface', 'O mínimo não estava definido'],
    ['Modo de execução, no modelo de dados', 'SERIAL, CPU_PARALELO e GPU — os valores que o banco tem', 'O documento dizia outros, desde a Sprint 2 — issue #106'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('4.3 Onde as regras são decididas'));
  c.push(bullet('No servidor, sempre: a tela recebe "pode treinar" e o porquê, o motivo de não haver previsão, e o que o treino deixou — ela não compara erro com erro para concluir nada.'));
  c.push(bullet('O modelo preditivo é um pacote à parte, que prevê e não decide: recebe números e devolve números. Quem diz o que é queda e se uma versão entra em uso é a API.'));
  c.push(bullet('A autorização também é regra: treinar é de Administrador e Gestor; a previsão no cadastro é de Gestor e Analista. A matriz de permissões é testada rota por rota, perfil por perfil.'));

  // ============================================= 5. TESTES
  c.push(quebra());
  c.push(h1('5. Testes realizados e resultados'));

  c.push(p(
    'O registro abaixo foi gerado rodando as três suítes — a da API contra um banco PostgreSQL de '
    + 'verdade, separado do de trabalho —, e não escrito à mão. Os defeitos de comportamento corrigidos '
    + 'nesta entrega vieram com teste — o da tela que seguia oferecendo treino reprova no código antigo —; '
    + 'os de documento e de estilo foram conferidos no próprio documento e nas capturas.',
  ));
  c.push(table([4200, 1400, 1400, 1300, 1338], [
    ['Suíte', 'Testes', 'Passaram', 'Falharam', 'Tempo'],
    ...[api, modelo, interfaceWeb].map((s) => [s.nome, String(s.total), String(s.passaram), String(s.falharam), `${s.segundos} s`]),
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }));
  c.push(espaco(80));
  c.push(rich([{ t: 'Resultado: ', b: true, s: 19 }, { t: registroTestes.replace(/^Resultado:\s*/, ''), s: 19 }]));

  c.push(h2('5.1 Os quatro tipos que o enunciado pede'));
  c.push(p(
    'Fluxos principais, operações com o banco, validações e situações de erro — com exemplos nomeados, '
    + 'conferidos contra a execução: se um exemplo deixasse de existir, o registro recusaria em vez de '
    + 'publicar um teste que não rodou.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/testes.txt', 'Fluxos principais', 'Por arquivo')));

  c.push(quebra());
  c.push(h2('5.2 As situações de erro, na aplicação no ar'));
  c.push(p(
    'Os testes automáticos cobrem os casos; a transcrição abaixo mostra os mesmos erros contra a '
    + 'aplicação no ar, com o esperado de cada troca ao pé dela. O período-base décadas à frente é o da '
    + 'própria transcrição: ela importa um relatório numa semana sorteada no futuro, para não tocar na '
    + 'base de demonstração, e desfaz tudo no fim.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/validacoes.txt', 'O analista lê a previsão no cadastro', '=====')));
  c.push(espaco(60));
  c.push(rich([
    { t: 'Resultado da transcrição de validações e erros, com as seções das Sprints 03 e 04: ', b: true, s: 19 },
    { t: validacoes.replace(/^Resultado:\s*/, ''), s: 19 },
  ]));

  c.push(quebra());
  c.push(h2('5.3 Os mesmos erros, na tela'));
  c.push(p(
    'Um treino pedido enquanto outro roda — disparado em outra aba — é recusado, e a tela passa a '
    + 'acompanhar o treino que já roda, com o botão desligado. Esta captura achou um defeito: na primeira '
    + 'versão, a tela recusava e seguia oferecendo "Treinar agora" (issue #108, seção 6).',
  ));
  c.push(evidencia('sprint05/erro-1-treino-ja-em-andamento'));
  c.push(legenda('Treino recusado porque outro já roda: a recusa com a ajuda, e o botão acompanhando o treino em curso.'));
  c.push(espaco(120));
  c.push(p('O Analista lê a previsão no cadastro, mas não treina — e a tela do modelo, aberta pelo endereço, recusa:'));
  c.push(evidencia('sprint05/erro-2-analista-sem-acesso'));
  c.push(legenda('O Analista na tela do modelo: a rota recusa, e o menu dele nem oferece a tela.'));
  c.push(espaco(120));
  c.push(p('Parceiro com histórico curto demais: o cadastro não inventa previsão, e diz por quê.'));
  c.push(evidencia('sprint05/erro-3-parceiro-sem-historico', 360));
  c.push(legenda('Sem previsão para um parceiro recém-chegado, com o motivo da RN09.'));

  // ================================================ 6. BUGS
  c.push(quebra());
  c.push(h1('6. Bugs identificados e correções'));

  c.push(p(
    'A partir desta sprint, todo defeito vira issue com o rótulo "fix", com o que apareceu, a causa, a '
    + 'correção e como foi encontrado, e é fechado pelo Pull Request que o corrige. O registro abaixo é '
    + 'gerado dessas issues. Os nove defeitos achados entre a entrega da Sprint 04 e o início desta foram '
    + 'registrados assim depois de corrigidos — as issues dizem isso —, para que o registro começasse '
    + 'completo.',
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

  c.push(h2('6.1 Como foram encontrados'));
  c.push(p(
    'Quase nenhum pelo usuário final: a maior parte veio das ferramentas de verificação, que é para isso '
    + 'que elas existem.',
    { size: 19 },
  ));
  c.push(bullet('Capturas de tela em duas larguras e dois temas acharam o menu solto a 768 px, a regra de estilo sem efeito e a probabilidade exibida como certeza.'));
  c.push(bullet('As próprias evidências desta entrega acharam a tela que seguia oferecendo treino depois da recusa, e a verificação no ar que treinava a partir de uma semana de teste.'));
  c.push(bullet('Revisar a especificação contra o código achou o caso de uso que contradizia o requisito, e o modelo de dados com valores que o banco não tem.'));

  c.push(h2('6.2 Dois defeitos em detalhe'));
  const detalhe = (numero) => {
    const b = bugs.find((x) => x.numero === numero);
    if (!b) throw new Error(`A issue #${numero} não está no registro de bugs.`);
    c.push(rich([{ t: `#${b.numero} — ${b.titulo}`, b: true, s: 19 }]));
    // O corpo da issue é Markdown; no documento, a crase sairia literal.
    const limpo = (t) => t.replace(/`/g, '');
    c.push(p(`Apareceu: ${limpo(b.apareceu)}`, { size: 18 }));
    c.push(p(`Causa: ${limpo(b.causa)}`, { size: 18 }));
    c.push(p(`${b.situacao === 'corrigido' ? 'Correção' : 'O que fazer'}: ${limpo(b.correcao)}`, { size: 18 }));
    c.push(espaco(60));
  };
  detalhe(105);
  detalhe(108);

  // ============================================ 7. REPOSITÓRIO
  c.push(quebra());
  c.push(h1('7. Repositório e commits'));

  c.push(espaco(40));
  c.push(rich([
    { t: 'Repositório: ', s: 21 },
    { t: REPO, b: true, s: 21, c: '2C5B8F' },
  ]));
  c.push(espaco(100));
  c.push(p(
    'O registro é gerado do histórico do git, lido da branch principal do repositório remoto. A janela '
    + 'da Sprint 04 fecha no dia em que o PDF dela foi gerado, 21/09: o trabalho de 22/09 em diante é o '
    + 'desta entrega.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/commits.txt', 'Totais', 'Por semana')));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/commits.txt', 'Sprint 05 — 22/09')));

  c.push(h2('7.1 Autoria e coautoria'));
  c.push(p(
    'Como na Sprint 04, o registro mostra a autoria como ela é: todos os commits têm o mesmo integrante '
    + 'como autor, e os demais aparecem como coautores, pela área de responsabilidade de cada um. Os Pull '
    + 'Requests também foram abertos e incorporados pelo mesmo integrante — a revisão cruzada no GitHub, '
    + 'posta como ponto a corrigir na Sprint 04, ainda não acontece, e continua nos próximos passos.',
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint05/commits.txt', 'Autoria e coautoria', 'Pull Requests incorporados, por')));

  // ====================================== 8. EXECUÇÃO E ROTEIRO
  c.push(quebra());
  c.push(h1('8. Execução e roteiro de demonstração'));

  c.push(p(
    'O ambiente sobe com um comando, e a base de demonstração é gerada já segmentada e com o modelo '
    + 'treinado:',
  ));
  c.push(espaco(40));
  c.push(...mono([
    'docker compose up -d',
    'python scripts/resetar_banco.py --parceiros 500     # segmenta e treina o modelo',
    'docker compose exec api python -m app.cli treinar-modelo    # o treino, pelo terminal',
  ]));
  c.push(espaco(120));
  c.push(h2('8.1 Roteiro para a orientação'));
  c.push(table([700, 8938], [
    ['#', 'Passo'],
    ['1', 'Entrar como Gestor e abrir Modelo: a versão em uso, os fatos e a comparação com as referências'],
    ['2', 'Treinar agora: a confirmação, o andamento e o resultado anunciado; o histórico ganha uma linha'],
    ['3', 'Abrir um parceiro grande: o desempenho medido, a previsão marcada como estimativa, e a série tracejada'],
    ['4', 'Abrir um parceiro recém-chegado: sem previsão, e o motivo'],
    ['5', 'Importar um período novo e voltar a Modelo: o aviso de que há período mais novo que as previsões'],
    ['6', 'Treinar de novo e abrir um parceiro que está no relatório importado: a previsão parte do período novo — quem não está nele fica sem, e a tela diz por quê'],
    ['7', 'Abrir Modelo em duas abas e treinar nas duas: a recusa, e a segunda aba acompanhando o treino da primeira'],
    ['8', 'Fechar a aplicação com "docker compose down", subir de novo e mostrar a mesma versão em uso e a mesma previsão'],
  ], { zebra: true, align: [AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(p(
    'O roteiro da Sprint 04 continua valendo e foi ensaiado de novo com o módulo novo no ar. O Docker '
    + 'Desktop precisa estar aberto antes, e a verificação de ponta a ponta é a forma mais rápida de '
    + 'conferir que tudo subiu.',
    { size: 19 },
  ));

  // ============================================ 9. DIFICULDADES
  c.push(quebra());
  c.push(h1('9. Dificuldades encontradas'));

  const dificuldade = (titulo, causa, correcao) => {
    c.push(h2(titulo));
    c.push(p(causa));
    c.push(rich([{ t: 'O que foi feito: ', b: true, s: 19 }, { t: correcao, s: 19 }]));
  };

  dificuldade(
    '9.1 Saber se a rede agrega, e não só se ela treina',
    'Uma rede sempre treina e sempre devolve um número. A pergunta que importa é se ela erra menos que '
    + 'uma conta de cabeça — e, com a massa sintética, a vantagem sobre a média móvel saiu pequena. Uma '
    + 'medição de um treino só não diria se ela se sustenta.',
    'a medição usa três redes geradas e cinco sementes de treino em cada uma, com mediana e faixa, nas '
    + 'bases de 500 e de 5.000 parceiros, e está publicada no repositório. A vantagem se sustentou em todos '
    + 'os treinos; o relatório diz que ela é pequena, e que o risco da rede é menos calibrado que a '
    + 'referência.',
  );
  dificuldade(
    '9.2 Treinar sem segurar a requisição, e sem dois treinos ao mesmo tempo',
    'A arquitetura proíbe cálculo pesado dentro da requisição. Tirar o treino dela abre duas portas: dois '
    + 'pedidos ao mesmo tempo gravando versões cruzadas, e um treino interrompido por reinício que '
    + 'ficaria "em andamento" para sempre.',
    'o treino roda em segundo plano, com o estado gravado no banco; um índice único parcial deixa haver só '
    + 'um em andamento — trava do banco, e não da memória do processo —; e a subida da API marca como '
    + 'falho o treino que um reinício interrompeu. Cada caso tem teste.',
  );
  dificuldade(
    '9.3 O PyTorch pesa',
    `A imagem da API foi de ${medida('imagemAntes')} para ${medida('imagemDepois')}, mesmo com a roda CPU do PyTorch, a menor que existe — a roda padrão traria as bibliotecas do CUDA junto. E importar o PyTorch na subida da API custaria segundos e memória a um processo que, na maior parte do tempo, só serve telas.`,
    'a roda CPU, com o tamanho medido e registrado; e o pacote do modelo só carrega o PyTorch quando se '
    + 'treina ou prevê — um teste confere que importar o pacote não o carrega.',
  );
  dificuldade(
    '9.4 Duas execuções da suíte no mesmo banco de teste',
    'Durante o desenvolvimento, a suíte da API foi rodada duas vezes ao mesmo tempo. As duas usam o mesmo '
    + 'banco de teste e esvaziam as tabelas entre um teste e outro — uma apagava os dados da outra, e o '
    + 'resultado não valia nada.',
    'a execução foi descartada e refeita sozinha, e o gerador do registro de testes diz, no cabeçalho, '
    + 'que não pode rodar em paralelo.',
  );
  dificuldade(
    '9.5 Evidência que parte de dado de teste',
    'A verificação de ponta a ponta grava semanas no futuro para não colidir com a base de demonstração. '
    + 'A seção do modelo rodou depois de uma dessas gravações, e o treino partiu de uma semana de teste '
    + 'com dois parceiros: o maior parceiro do período não tinha previsão.',
    'a seção do modelo roda antes de qualquer gravação da verificação (issue #103). A lição vale para as '
    + 'próximas: quando o resultado depende do "período mais recente", a ordem das seções é parte do teste.',
  );

  // ====================================== 10. AJUSTES
  c.push(quebra());
  c.push(h1('10. Ajustes no planejamento, na arquitetura e na modelagem'));

  c.push(table([2500, 3000, 4138], [
    ['O que mudou', 'De / para', 'Por quê'],
    ['História H45 — retreino pela tela', 'Sprint 9 interna para a 8', 'Sem disparar o treino, o módulo não teria fluxo de uso: o usuário só leria números prontos. A Sprint 9 fica com o otimizador'],
    ['Pacote do modelo preditivo', 'Nenhum para modelo/, próprio', 'Prevê e não decide: sem banco, sem FastAPI, testável por linha de comando — o mesmo desenho do núcleo em C++ (decisão ADR-010)'],
    ['Onde o treino roda', 'Requisição para segundo plano', 'A arquitetura proíbe cálculo pesado na requisição; fila de tarefas traria um serviço a mais para um treino de segundos (ADR-010)'],
    ['Onde ficam os pesos', 'Nenhum lugar para a linha do treino', 'Poucos KB: a versão em uso sobrevive a reinício sem volume de arquivo (ADR-010)'],
    ['Tabela treino_modelo', '17 para 18 tabelas', 'O RF27 pede data, volume e métricas de cada treino; a versão em uso fica na própria linha, sem uma segunda fonte que possa discordar'],
    ['Imagem da API', 'Contexto único para contexto adicional', 'O modelo mora fora da API; levar a raiz inteira para o build traria a interface e a documentação junto'],
    ['Integração contínua', 'Três para quatro trabalhos', 'O pacote do modelo tem suíte própria, e o piso de cobertura do núcleo passou a cobrar a previsão'],
    ['Regras de negócio', 'RN01–RN08 para RN01–RN09', 'Seção 4'],
    ['Figuras da Parte II', 'Diagramas vivos para figuras entregues', 'Renderizada de novo, a Parte II mudaria uma entrega já feita; a modelagem nova aparece na seção 3 desta parte'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('10.1 As lacunas da Parte IV, fechadas'));
  c.push(p(
    'A Parte IV declarou quatro lacunas em vez de omiti-las. As quatro foram fechadas antes do módulo '
    + 'novo: a tela dos limiares da segmentação, o histórico de importações na interface, a sugestão de '
    + 'categoria pelo nome do parceiro — com a regra escrita antes do código — e a tela de administração '
    + 'de usuários. O menu passou a vir do servidor, com as telas que cada perfil abre.',
  ));

  c.push(h2('10.2 Planejamento'));
  c.push(p(
    'A equipe segue à frente do calendário interno: a Sprint 8 — modelo preditivo — estava prevista para '
    + '26/10 a 30/10. A tabela de equivalência do cronograma foi atualizada: esta entrega '
    + 'corresponde à Sprint 8 interna mais a H45 da 9. A folga continua sendo margem para o núcleo em GPU.',
  ));

  // ========================================= 11. PRÓXIMOS PASSOS
  c.push(quebra());
  c.push(h1('11. Próximos passos'));

  c.push(table([1400, 3600, 4638], [
    ['Sprint', 'Tema', 'O que entra'],
    ['9 a 11', 'Núcleo computacional', 'Otimizador serial, paralelo em CPU e paralelo em GPU, alimentado pela previsão e pelo risco deste módulo, com o comparativo de desempenho'],
    ['12', 'Central de comunicação', 'Geração de mensagens por segmento, com aprovação humana obrigatória'],
    ['13', 'Assistente e fechamento', 'Perguntas em linguagem natural sobre dados já apurados, e a entrega final'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('11.1 No módulo de previsão'));
  c.push(bullet('A coluna de risco na lista de parceiros, com ordenação por ela — a pergunta "em quem investir?" feita à rede inteira de uma vez.'));
  c.push(bullet('O risco calibrado de novo à medida que a base crescer: com poucas semanas, a rede separa melhor, mas erra mais a proporção que a taxa observada.'));
  c.push(bullet('O aval do Product Owner sobre o limiar de recém-chegado, na issue #59.'));

  c.push(h2('11.2 No processo'));
  c.push(bullet('Revisão cruzada nos Pull Requests: cada um revisado pelo dono da área antes de entrar, e não só pelo autor — ponto posto na Sprint 04 e ainda aberto.'));
  c.push(bullet('Todo defeito como issue com o rótulo "fix", desde o primeiro minuto — o registro desta entrega só começou completo porque os anteriores foram registrados depois.'));

  c.push(espaco(200));
  c.push(p(
    'Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa '
    + 'visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.',
    { italics: true, color: '5A6B7E', size: 18 },
  ));

  return c;
}

module.exports = { montar };
