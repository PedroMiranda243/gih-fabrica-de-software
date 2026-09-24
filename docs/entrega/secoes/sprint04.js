/**
 * Parte IV do documento — Sprint 04 acadêmica: primeiro módulo completo.
 *
 * O enunciado pede um módulo **completo e integrado**, e avisa que tela sem
 * funcionalidade por trás não conta. Por isso, como na Parte III, cada item
 * traz execução real: transcrições, capturas da aplicação no ar e a saída dos
 * scripts — lidas dos arquivos que eles geraram, e nunca transcritas à mão.
 *
 * Dois guardas impedem o documento de afirmar o que não foi visto:
 * `medida()` recusa número não preenchido, e `aprovado()` recusa gerar se a
 * própria evidência registrar uma falha. Um documento que diz "todas as
 * conferências passaram" em cima de uma transcrição com FALHA é pior que não
 * ter a transcrição.
 */
const { AlignmentType } = require('docx');
const { p, rich, h1, h2, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { evidencia, legenda } = require('../comum/figuras');
const { todas, trecho } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';

/*
 * Números medidos contra a versão entregue. `null` é "ainda não medido", e a
 * geração recusa: um documento com número estimado não é evidência.
 */
const MEDIDAS = {
  testesApi: 475, // pytest --collect-only -q, na main, 21/09
  testesInterface: 64, // npm test, na main, 21/09
  coberturaNucleo: '99%', // o portão da CI: servico_segmentacao, ranking, rotas/painel, calculos
  verificacoes: 68, // e2e/verificacao.py contra a API no ar — evidencias/sprint04/verificacao.txt
  operacoes: 31, // app.openapi(), lido da própria aplicação
  tabelas: 17, // pg_tables do schema public, sem alembic_version
  painelPiorMediana: '32,3 ms', // docs/medicoes/painel-5000.md, 21/09 — ranking de 200
  painelPiorP95: '36,4 ms', // idem
};

function medida(nome) {
  const valor = MEDIDAS[nome];
  if (valor === null || valor === undefined) {
    throw new Error(`Medida "${nome}" não preenchida em secoes/sprint04.js — meça antes de gerar.`);
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

function montar() {
  const c = [];
  const persistencia = aprovado('sprint04/persistencia.txt', 'Resultado:');
  const validacoes = aprovado('sprint04/validacoes.txt', 'Resultado:');
  const verificacao = aprovado('sprint04/verificacao.txt', 'verificações passaram');

  c.push(quebra());
  c.push(h1('Parte IV — Sprint 04: Primeiro Módulo Completo'));

  c.push(p(
    'O módulo entregue é o de Ingestão e Inteligência de Negócio — os módulos M2 e M3 do escopo, que na '
    + 'prática são um fluxo só: o relatório do período entra, é validado, persiste, cada parceiro é '
    + 'segmentado, e o resultado aparece no painel e na lista de parceiros, onde pode ser recortado e '
    + 'exportado. A autenticação, entregue na Sprint 03, é o que protege esse fluxo; o núcleo de '
    + 'otimização e o modelo preditivo vêm nas próximas sprints.',
  ));
  c.push(p(
    'Cada item desta parte vem com execução real. As transcrições foram geradas por scripts contra a '
    + 'aplicação no ar, e cada troca vem com o resultado que se esperava dela — uma evidência que só mostra '
    + 'respostas não diz se elas estão certas. As capturas são da aplicação no ar, sobre a base de '
    + 'demonstração, e cada erro mostrado foi provocado pela própria tela.',
  ));

  c.push(h2('As seis entregas, e onde estão'));
  c.push(table([700, 2700, 2400, 3838], [
    ['#', 'Entrega', 'Situação', 'Evidência neste documento'],
    ['1', 'Módulo funcional', 'Funcionando', 'Seções 1 e 2 — as funcionalidades, a verificação de ponta a ponta e as telas'],
    ['2', 'Persistência', 'Funcionando', 'Seção 3 — os dados depois de desligar e religar a aplicação'],
    ['3', 'Validações', 'Funcionando', 'Seção 4 — cada regra provocada, na API e na tela'],
    ['4', 'Mensagens de erro', 'Funcionando', 'Seção 5 — o contrato das mensagens e a falha inesperada'],
    ['5', 'Navegação entre telas', 'Funcionando', 'Seção 6 — o mapa das telas e o percurso'],
    ['6', 'Commits organizados', 'Funcionando', 'Seção 7 — o histórico, gerado do próprio repositório'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  c.push(espaco(80));
  c.push(p(
    'Quatro lacunas estão declaradas em vez de omitidas, e aparecem com essas palavras nas seções 1 e 11: '
    + 'os limiares da segmentação se configuram pela API e pelo terminal, mas ainda não têm tela; o '
    + 'histórico de importações existe na API e não na interface; a sugestão automática de categoria '
    + 'ainda não foi feita; e a administração de usuários, lacuna já declarada na Sprint 03, continua sem '
    + 'tela.',
  ));

  // ====================================================== 1. O MÓDULO
  c.push(quebra());
  c.push(h1('1. O módulo e suas funcionalidades'));

  c.push(h2('1.1 O fluxo'));
  c.push(p(
    'O gestor recebe da plataforma de delivery um relatório de faturamento por parceiro, em texto, sem '
    + 'data nenhuma. O módulo transforma esse texto em série histórica e em classificação — quem está no '
    + 'topo, quem está subindo, quem está caindo — e deixa o gestor recortar a rede por qualquer um '
    + 'desses critérios.',
  ));
  c.push(table([2200, 4400, 1300, 1738], [
    ['Etapa', 'O que o sistema faz', 'Requisito', 'Tela'],
    ['Importar', 'Recebe o relatório colado ou em arquivo CSV, com o período obrigatório', 'RF09, RF10', 'Importação'],
    ['Validar', 'Mostra a prévia antes de gravar: linhas reconhecidas, rejeitadas com o motivo, parceiros novos', 'RF11', 'Importação'],
    ['Persistir', 'Grava na mesma transação as métricas e a segmentação — ou nada; período repetido só com substituição explícita', 'RF12, RF13', 'Importação'],
    ['Segmentar', 'Classifica cada parceiro em exatamente um segmento, por regra determinística com precedência', 'RF20, RF21', 'Painel e lista'],
    ['Analisar', 'Indicadores do período, série histórica, distribuição por segmento, ranking e mobilidade do Top N', 'RF17 a RF19, RF22', 'Painel'],
    ['Recortar', 'Busca sem diferenciar acento, filtros, ordenação por qualquer medida e exportação do recorte', 'RF23 a RF25', 'Parceiros'],
    ['Cadastrar', 'Cadastro, edição, desativação e exclusão de parceiro, com o desempenho e a série individual', 'RF14, RF19', 'Cadastro'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('1.2 As regras de negócio que o módulo aplica'));
  c.push(p(
    'Todas estão escritas na especificação de requisitos, e todas são decididas no servidor. A interface '
    + 'exibe e coleta; nenhum cálculo de negócio acontece no navegador.',
    { size: 19 },
  ));
  c.push(table([1100, 4100, 4438], [
    ['Regra', 'O que diz', 'Por que importa'],
    ['RN01', 'A segmentação segue uma ordem de precedência fixa, e Em Risco vence Top', 'É o que faz o painel responder "quem está prestes a sair do topo?"'],
    ['RN02', 'A mobilidade do Top N lê o ranking, nunca o segmento gravado', 'Lida do segmento, anunciaria a saída de quem continua no topo em queda'],
    ['RN03', 'O período é obrigatório na importação, sem valor padrão', 'Sem as datas, a segmentação por tendência classifica errado sem emitir erro'],
    ['RN04', 'O ticket médio é derivado na consulta, nunca armazenado', 'Guardado, divergiria das parcelas na primeira correção de dado'],
    ['RN05', 'Categoria inferida vale como sugestão até alguém confirmar', 'Parceiro importado entra sem categoria, em vez de com um palpite'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('1.3 O que está fora, e por quê'));
  c.push(bullet('Os limiares da segmentação (RF21) mudam sem alteração de código, pela API e por comando de terminal, só pelo Administrador. A tela deles é o próximo passo.'));
  c.push(bullet('O histórico de importações (RF13) é gravado e consultável pela API; a interface ainda não o lista.'));
  c.push(bullet('A sugestão de categoria pelo nome (RF15) é da Sprint 3 do backlog e está aberta na issue #35.'));

  c.push(h2('1.4 Números do módulo'));
  c.push(p('Medidos na versão entregue — nenhum é estimado:', { size: 19 }));
  c.push(table([5600, 4038], [
    ['Medida', 'Valor'],
    ['Testes automatizados da API', medida('testesApi')],
    ['Testes automatizados da interface', medida('testesInterface')],
    ['Cobertura do núcleo de regras — a integração contínua reprova abaixo de 70%', medida('coberturaNucleo')],
    ['Verificações de ponta a ponta contra a aplicação no ar', medida('verificacoes')],
    ['Operações da API', medida('operacoes')],
    ['Tabelas no banco', medida('tabelas')],
    ['Painel com 5.000 parceiros — a consulta mais lenta, mediana', medida('painelPiorMediana')],
    ['Painel com 5.000 parceiros — a consulta mais lenta, p95', medida('painelPiorP95')],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER] }));
  c.push(espaco(80));
  c.push(p(
    'O limite do requisito de desempenho é de 2 segundos com 5.000 parceiros. A medição usa um banco '
    + 'separado, repetições calibradas e reporta mediana e p95 — o relatório completo, com o plano de '
    + 'execução de cada consulta, está versionado em docs/medicoes/.',
    { size: 19 },
  ));

  // ============================================ 2. FUNCIONANDO
  c.push(quebra());
  c.push(h1('2. O módulo funcionando'));

  c.push(h2('2.1 Verificação de ponta a ponta'));
  c.push(p(
    'A verificação roda contra a aplicação no ar — HTTP real, cookie real, banco real — e sai com código '
    + 'diferente de zero se qualquer checagem falhar. O trecho abaixo é o do módulo; os seis primeiros '
    + 'blocos, da Sprint 03, continuam passando na mesma execução.',
    { size: 19 },
  ));
  c.push(espaco(60));
  c.push(...mono(trecho('sprint04/verificacao.txt', 'Painel — indicadores', 'Limpeza')));
  c.push(espaco(60));
  c.push(...mono(trecho('sprint04/verificacao.txt', 'Limpeza')));
  c.push(espaco(80));
  c.push(rich([
    { t: 'Resultado: ', b: true, s: 19 },
    { t: `${verificacao} A última checagem é a da limpeza: a verificação apaga o que gravou e confere que o `
       + 'painel voltou ao mesmo período, com os mesmos totais — ela roda no banco em que se demonstra.', s: 19 },
  ]));

  c.push(quebra());
  c.push(h2('2.2 O painel'));
  c.push(p(
    'Resumo antes do detalhe: os indicadores do período no topo, com a variação e a mobilidade do Top N; '
    + 'a série histórica e a distribuição por segmento no meio; o ranking por último. Variação, ticket, '
    + 'posição e segmento vêm prontos da API — a tela formata e desenha.',
  ));
  c.push(evidencia('sprint04/fluxo-1-painel'));
  c.push(legenda('Painel sobre a base de demonstração: indicadores, série, distribuição por segmento e ranking.'));

  c.push(quebra());
  c.push(h2('2.3 A lista recortada'));
  c.push(p(
    'O recorte vive no endereço da página. Esta captura é de /parceiros?segmento=EM_RISCO&ordenar_por=variacao: '
    + 'os parceiros em risco, dos que mais caíram para os que menos caíram. O botão de exportar baixa '
    + 'exatamente este recorte em CSV — é a mesma consulta, em outro formato.',
  ));
  c.push(evidencia('sprint04/fluxo-2-parceiros-em-risco'));
  c.push(legenda('Lista de parceiros filtrada por segmento e ordenada pela variação.'));

  c.push(quebra());
  c.push(h2('2.4 O cadastro do parceiro'));
  c.push(p(
    'O nome na lista abre o cadastro. Além dos dados do parceiro, a tela mostra o desempenho do período — '
    + 'o mesmo da lista — e a série individual, que fecha a metade do RF19 que ainda não tinha tela. A '
    + 'desativação e a exclusão ficam separadas, e as duas pedem confirmação na própria página.',
  ));
  c.push(evidencia('sprint04/fluxo-3-cadastro-do-parceiro'));
  c.push(legenda('Cadastro de um parceiro em risco: dados, desempenho do período, série histórica e situação.'));

  c.push(quebra());
  c.push(h2('2.5 A importação'));
  c.push(p(
    'O relatório não traz datas, e por isso o período é informado à parte e é obrigatório. Antes de '
    + 'gravar, a prévia mostra o que vai entrar — e a linha com faturamento "abacaxi" é recusada com o '
    + 'motivo, sem impedir as outras.',
  ));
  c.push(evidencia('sprint04/fluxo-4-importacao-previa'));
  c.push(legenda('Importação com a prévia aberta: duas linhas reconhecidas e uma rejeitada com o motivo.'));
  c.push(espaco(120));
  c.push(p(
    'Gravado, o aviso diz quantos registros entraram e leva ao painel: a importação termina segmentando a '
    + 'base, na mesma transação, e é lá que o resultado aparece.',
  ));
  c.push(evidencia('sprint04/fluxo-5-importacao-concluida'));
  c.push(legenda('A importação concluída, com o caminho para o painel.'));

  // =========================================== 3. PERSISTÊNCIA
  c.push(quebra());
  c.push(h1('3. Persistência'));

  c.push(p(
    'A entrega pede que os dados continuem lá depois de fechar e reabrir o sistema. O teste abaixo faz '
    + 'isso de verdade, e não por simulação: um analista cadastra e altera um parceiro; o comando '
    + '"docker compose down" remove os três contêineres — não os pausa — e a API para de responder; o '
    + '"docker compose up -d" cria contêineres novos; e tudo é lido de novo e comparado campo a campo.',
  ));
  c.push(p(
    'A releitura usa o mesmo cookie de antes, sem novo login. A sessão tem estado no servidor, gravada '
    + 'no banco, e por isso também é dado persistido: se ela existisse só na memória do processo, teria '
    + 'morrido com ele.',
    { size: 19 },
  ));

  c.push(h2('3.1 Antes de desligar'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/persistencia.txt', 'O estado anotado', '[2/4]')));

  c.push(h2('3.2 Desligar e religar'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/persistencia.txt', '$ docker compose down', '[4/4]')));

  c.push(quebra());
  c.push(h2('3.3 Depois de religar'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/persistencia.txt', 'O estado lido agora', 'Resultado:')));
  c.push(espaco(80));
  c.push(rich([
    { t: 'Resultado: ', b: true, s: 19 },
    { t: persistencia.replace(/^Resultado:\s*/, ''), s: 19 },
  ]));
  c.push(espaco(80));
  c.push(p(
    'O volume do banco nunca é apagado: o script monta o comando do Docker em um lugar só, e esse lugar '
    + 'recusa a opção que remove volumes. A transcrição completa, com as requisições do cadastro, está em '
    + 'docs/entrega/evidencias/sprint04/persistencia.txt.',
    { size: 19 },
  ));

  // ============================================== 4. VALIDAÇÕES
  c.push(quebra());
  c.push(h1('4. Validações'));

  c.push(p(
    'Toda validação é do servidor. A interface ajuda — o campo de data exige a data, o campo de nome não '
    + 'deixa digitar além do limite — mas é o servidor que recusa, e a tela mostra a recusa que recebeu. '
    + 'Validar só na tela seria esconder o botão e deixar a porta aberta.',
  ));

  c.push(h2('4.1 As regras, onde valem e o que dizem'));
  c.push(table([2500, 1500, 5638], [
    ['Regra', 'Onde', 'O que o usuário lê'],
    ['Período ausente (RN03)', 'Importação', 'Por que o período é obrigatório, e que não existe valor padrão'],
    ['Fim antes do início', 'Importação', 'Que o fim não pode ser anterior ao início'],
    ['Data fora do formato', 'Importação', 'Informe uma data válida, no formato AAAA-MM-DD'],
    ['Linha com dado inválido', 'Importação', 'Na prévia, cada linha rejeitada com o conteúdo e o motivo'],
    ['Nenhuma linha válida', 'Importação', 'Nenhuma linha válida no relatório — nada foi gravado'],
    ['Planilha no lugar do CSV', 'Importação', 'Que o arquivo não é texto, e como exportar em CSV'],
    ['Período já importado (RF12)', 'Importação', 'Quantos registros existem e quem os trouxe, antes de oferecer a substituição'],
    ['Nome vazio ou curto', 'Cadastro', 'Obrigatório: informe ao menos 2 caracteres'],
    ['Contato longo', 'Cadastro', 'Longo demais: use no máximo 120 caracteres'],
    ['Situação fora da lista', 'Cadastro', 'Escolha uma destas opções, com as opções'],
    ['Categoria inexistente', 'Cadastro', 'Que a categoria não existe, no próprio campo'],
    ['Nome em uso', 'Cadastro', 'Qual parceiro já usa o nome, com o link para ele'],
    ['Exclusão com histórico', 'Cadastro', 'Por que não pode, e que desativar mantém o histórico'],
    ['Filtro ou ordenação inválidos', 'Lista', 'As opções válidas, ou o limite da página'],
    ['Top N zero (RF21)', 'Limiares', 'Use um valor a partir de 1 — e nada é gravado'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(quebra());
  c.push(h2('4.2 Na importação'));
  c.push(p('Transcrição real, com o esperado de cada troca ao pé dela:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/validacoes.txt', 'RN03 — sem o período', 'Data fora do formato')));
  c.push(espaco(60));
  c.push(...mono(trecho('sprint04/validacoes.txt', 'Planilha do Excel', '[2/6]')));

  c.push(quebra());
  c.push(h2('4.3 No cadastro de parceiro'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/validacoes.txt', 'Nome curto', 'Situação comercial fora')));
  c.push(espaco(60));
  c.push(...mono(trecho('sprint04/validacoes.txt', 'Categoria que não existe', 'UC04-E1')));

  c.push(quebra());
  c.push(h2('4.4 Na tela'));
  c.push(p(
    'O mesmo cadastro, pela interface: nome apagado e contato com 121 caracteres. O limite de 120 no '
    + 'campo só impede digitar além dele — aqui ele foi contornado de propósito, para mostrar que o '
    + 'servidor recusa mesmo assim. Cada mensagem aparece embaixo do seu campo, o resumo no topo leva a '
    + 'cada um, e o foco vai para o primeiro campo com erro. Nada foi gravado.',
  ));
  c.push(evidencia('sprint04/erro-1-campos-do-cadastro'));
  c.push(legenda('Cadastro recusado pelo servidor: as duas mensagens, cada uma no seu campo.'));

  // ======================================== 5. MENSAGENS DE ERRO
  c.push(quebra());
  c.push(h1('5. Mensagens de erro'));

  c.push(p(
    'Toda mensagem é em português e diz o que fazer, não só o que deu errado. A API responde sempre no '
    + 'mesmo formato, e é esse contrato que permite à tela mostrar cada erro no lugar certo sem conhecer '
    + 'as regras:',
  ));
  c.push(table([2400, 3000, 4238], [
    ['Situação', 'Formato', 'Na tela'],
    ['Campo inválido (422)', 'erro + a lista de campos, cada um com a mensagem', 'Embaixo de cada campo, e um resumo no topo'],
    ['Recusa de negócio (409)', 'erro + ajuda, e o que estiver em jogo', 'O aviso com a ajuda e, quando há, a saída ao lado'],
    ['Sem sessão ou sem permissão (401, 403)', 'Mensagem genérica', 'Sessão encerrada leva ao login, que devolve ao lugar de antes; sem permissão, a mensagem'],
    ['Falha inesperada (500)', 'Mensagem genérica + identificador de correlação', 'A mensagem, sem nada do servidor'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('5.1 A recusa aponta a saída'));
  c.push(p(
    'Excluir um parceiro com faturamento importado apagaria números de períodos já fechados. A recusa '
    + 'diz isso, e a própria tela oferece o que resolve: desativar, que tira o parceiro das próximas '
    + 'campanhas e mantém o histórico.',
  ));
  c.push(evidencia('sprint04/erro-2-exclusao-recusada'));
  c.push(legenda('Exclusão recusada, com "Desativar em vez de excluir" dentro do próprio aviso.'));

  c.push(quebra());
  c.push(p(
    'Nome em uso: a recusa diz qual parceiro já usa o nome e leva ao cadastro dele — o mais provável é '
    + 'que a pessoa quisesse editá-lo, e não criar outro.',
  ));
  c.push(evidencia('sprint04/erro-3-nome-em-uso'));
  c.push(legenda('Cadastro recusado por nome em uso, com o link para o parceiro existente.'));

  c.push(espaco(120));
  c.push(p(
    'Período já importado: o padrão é cancelar. A substituição só é oferecida depois de dizer quantos '
    + 'registros seriam apagados e quem os trouxe — destruir dado não pode ser um clique distraído.',
  ));
  c.push(evidencia('sprint04/erro-4-periodo-ja-importado'));
  c.push(legenda('Importação recusada por período repetido, com o que a substituição apagaria.'));

  c.push(quebra());
  c.push(h2('5.2 Acesso'));
  c.push(p(
    'Senha errada e login inexistente respondem exatamente igual. Duas mensagens diferentes entregariam '
    + 'a lista de logins válidos a quem tentasse adivinhar.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/validacoes.txt', 'Senha errada, e depois', 'Sem sessão:')));

  c.push(quebra());
  c.push(h2('5.3 A falha inesperada'));
  c.push(p(
    'Para mostrar o que o usuário vê quando algo quebra de verdade, o banco foi parado por alguns '
    + 'segundos. A resposta traz só uma mensagem genérica e um identificador; o detalhe técnico fica no '
    + 'log do servidor, com o mesmo identificador — é o que liga a reclamação de um usuário ao evento, '
    + 'sem mostrar a ele nada do servidor.',
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/validacoes.txt', 'Uma tela pedindo', '$ docker compose start')));
  c.push(espaco(80));
  c.push(p(
    'Com o banco de volta, a mesma tela funciona sem reiniciar a API: a conexão é testada antes de cada '
    + 'uso, e a que morreu com o banco é descartada.',
    { size: 19 },
  ));
  c.push(espaco(60));
  c.push(rich([
    { t: 'Resultado da transcrição de validações e erros: ', b: true, s: 19 },
    { t: validacoes.replace(/^Resultado:\s*/, ''), s: 19 },
  ]));

  // =============================================== 6. NAVEGAÇÃO
  c.push(quebra());
  c.push(h1('6. Navegação entre telas'));

  c.push(p(
    'Seis telas, cada uma com endereço próprio. O botão voltar desfaz o último passo, um recorte filtrado '
    + 'pode ser mandado por link, e um cadastro abre direto — tudo isso depende de a tela estar no '
    + 'endereço, e não num estado escondido da página.',
  ));
  // O mapa como foi entregue em 26/09, e não o de `docs/09`: aquele é vivo e
  // ganhou as telas de administração depois. Evidência é retrato da entrega.
  c.push(evidencia('sprint04/navegacao-telas'));
  c.push(legenda('Mapa das telas. As setas cheias são os caminhos que a própria tela oferece; o menu lateral está em todas.'));

  c.push(h2('6.1 O percurso da demonstração'));
  c.push(table([700, 3200, 5738], [
    ['#', 'De onde, para onde', 'Como'],
    ['1', 'Login → Painel', 'Entrar; o login devolve à tela pedida antes, se houver'],
    ['2', 'Painel → Importação', 'Pelo menu, ou pela saída do painel vazio'],
    ['3', 'Importação → Painel', '"Ver no painel", no aviso de importação concluída'],
    ['4', 'Painel → Parceiros', 'Pelo menu; o recorte vai para o endereço'],
    ['5', 'Parceiros → Cadastro', 'O nome do parceiro na lista'],
    ['6', 'Cadastro → Parceiros', '"Parceiros" na trilha, ou "Voltar para a lista" — com o mesmo recorte'],
    ['7', 'Parceiros → Novo parceiro → Cadastro', '"Novo parceiro"; cadastrado, a tela passa ao cadastro criado'],
    ['8', 'Cadastro → Cadastro existente', 'O link da recusa por nome em uso'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1, size: 17 }));
  c.push(espaco(80));
  c.push(p(
    'As capturas da seção 2 seguem esse percurso, na ordem. Três comportamentos valem para todas as '
    + 'telas: sessão encerrada leva ao login, que devolve ao lugar de antes; o recorte da lista vive no '
    + 'endereço, e por isso voltar do cadastro devolve o mesmo recorte; e toda tela vazia oferece a saída '
    + '— nunca uma tela em branco sem explicação.',
  ));

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
    'O registro abaixo é gerado do próprio histórico do git, lido da branch principal do repositório '
    + 'remoto — nenhum número foi escrito à mão.',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/commits.txt', 'Totais', 'Por semana')));

  c.push(h2('7.1 Como os commits são organizados'));
  c.push(bullet('Um assunto por commit, no padrão Conventional Commits — o tipo diz se é funcionalidade, correção, teste, documentação ou integração contínua.'));
  c.push(bullet('Nas correções desta entrega, o teste vai em commit próprio e é conferido reprovando no código antigo — senão não se sabe se ele testa o defeito.'));
  c.push(bullet('Cada Pull Request trata de um assunto só, e passa pela integração contínua antes de entrar.'));
  c.push(bullet('Os commits feitos direto na branch principal, antes de ela ser protegida, aparecem no registro como tais — e não foram reescritos.'));

  c.push(quebra());
  c.push(h2('7.2 Autoria e coautoria'));
  c.push(p(
    'O registro mostra a autoria como ela é. Todos os commits têm o mesmo integrante como autor, e os '
    + 'demais aparecem como coautores, pela área de responsabilidade de cada um — interface, banco e '
    + 'testes, documentação, integração contínua. Os Pull Requests também foram abertos e incorporados '
    + 'pelo mesmo integrante: a revisão cruzada entre os integrantes ainda não acontece no GitHub, e está '
    + 'nos próximos passos como ponto a corrigir.',
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/commits.txt', 'Autoria e coautoria', 'Pull Requests incorporados, por')));

  c.push(h2('7.3 Os Pull Requests desta entrega'));
  c.push(espaco(40));
  c.push(...mono(trecho('sprint04/commits.txt', 'Sprint 04 — 20/09 a 26/09')));

  // ====================================== 8. EXECUÇÃO E ROTEIRO
  c.push(quebra());
  c.push(h1('8. Execução e roteiro de demonstração'));

  c.push(p(
    'O ambiente sobe com um comando, como na Sprint 03, e agora volta sozinho quando o Docker é '
    + 'reiniciado. A base de demonstração é gerada e já sai segmentada:',
  ));
  c.push(espaco(40));
  c.push(...mono([
    'docker compose up -d',
    'python scripts/resetar_banco.py --parceiros 500     # base sintética, já segmentada',
    'docker compose exec api python -m app.cli criar-usuario --login seu.login --nome "Seu Nome"',
  ]));
  c.push(espaco(120));

  c.push(h2('8.1 Roteiro para a orientação'));
  c.push(table([700, 8938], [
    ['#', 'Passo'],
    ['1', 'Entrar e mostrar o painel: indicadores, mobilidade do Top N, série, distribuição por segmento e ranking'],
    ['2', 'Ir a Parceiros, filtrar por "Em risco" e ordenar pela variação; exportar o recorte em CSV'],
    ['3', 'Abrir um parceiro pelo nome: desempenho, série individual; tentar excluir e mostrar a recusa'],
    ['4', 'Voltar pela trilha e mostrar que o recorte continua'],
    ['5', 'Novo parceiro com o nome de um existente: a recusa e o link para ele'],
    ['6', 'Importação: prévia com uma linha ruim, gravar, e "Ver no painel"'],
    ['7', 'Importar o mesmo período de novo: a recusa com o que seria apagado'],
    ['8', 'Fechar a aplicação com "docker compose down", subir de novo e mostrar que tudo continua'],
  ], { zebra: true, align: [AlignmentType.CENTER], size: 17 }));
  c.push(espaco(80));
  c.push(p(
    'Antes da orientação, o roteiro é ensaiado na máquina que vai ser usada. O Docker Desktop precisa '
    + 'estar aberto antes, e a verificação de ponta a ponta é a forma mais rápida de conferir que tudo subiu.',
    { size: 19 },
  ));

  // ============================================ 9. DIFICULDADES
  c.push(quebra());
  c.push(h1('9. Dificuldades encontradas'));

  c.push(p(
    'Todas reais, com a causa e a correção — e várias achadas pelas próprias ferramentas de verificação, '
    + 'que é para isso que elas existem.',
  ));

  const dificuldade = (titulo, causa, correcao) => {
    c.push(h2(titulo));
    c.push(p(causa));
    c.push(rich([{ t: 'Correção: ', b: true, s: 19 }, { t: correcao, s: 19 }]));
  };

  dificuldade(
    '9.1 A massa de demonstração subia inteira na mesma semana',
    'Com o gerador de dados sintéticos, 43% da rede saía "em ascensão" e só 4% "em risco" — longe dos '
    + 'perfis de trajetória que o gerador deveria produzir. A causa era a sazonalidade, que empurrava '
    + 'todos os parceiros na mesma direção nas mesmas semanas. A correção sugerida na issue, trocar a '
    + 'forma da onda, acertava com 12 períodos e voltava a enviesar com 13.',
    'cada parceiro passou a ter a própria fase na onda sazonal, sorteada a partir da semente. Medido antes '
    + 'e depois, com 12 e com 13 períodos: as contagens de duas altas e de duas quedas seguidas ficaram '
    + 'equilibradas nos dois casos.',
  );
  dificuldade(
    '9.2 A exportação pendurava sem erro',
    'O CSV da lista é gerado aos poucos, enquanto é baixado. A primeira versão lia do banco pela conexão '
    + 'da requisição — que o servidor já tinha devolvido quando o download começava. Os testes travavam '
    + 'sem mensagem nenhuma.',
    'a exportação abre a própria conexão, que vive enquanto o arquivo é gerado, e fecha no fim.',
  );
  dificuldade(
    '9.3 A medição de desempenho mentia',
    'A primeira medição do painel com 5.000 parceiros acusou varredura completa de tabela onde havia '
    + 'índice. O banco tinha acabado de ser populado, e as estatísticas do planejador ainda eram as de '
    + 'antes da carga; e a varredura, onde aparecia, era a escolha certa para aquele tamanho de tabela.',
    'a medição atualiza as estatísticas antes de medir, e só reprova a varredura quando, forçado a usar '
    + 'índice, o banco não tem nenhum para usar. Medição surpreendente geralmente é medição quebrada.',
  );
  dificuldade(
    '9.4 Um script de verificação quebrado, com a integração contínua verde',
    'A lista de parceiros passou a responder em páginas, e o script de transcrição, que não roda na '
    + 'integração contínua, continuou lendo a resposta como lista. A integração contínua seguiu verde, '
    + 'e o defeito só apareceu quando a transcrição foi executada de novo.',
    'o script passou a ler a página. A lição ficou registrada: verde na integração contínua cobre o que '
    + 'ela executa, e os scripts de evidência rodam antes de cada entrega.',
  );
  dificuldade(
    '9.5 Categoria inexistente respondia "nome duplicado"',
    'Os testes escritos para a tela de cadastro acharam um defeito real: cadastrar um parceiro com uma '
    + 'categoria que não existe violava a chave estrangeira, e a API tratava toda violação de integridade '
    + 'como nome repetido.',
    'a categoria é conferida antes de gravar, e o erro vai para o próprio campo; o nome repetido é '
    + 'reconhecido pela restrição exata que o banco reporta, e não por qualquer violação.',
  );
  dificuldade(
    '9.6 Todo aviso de sucesso saía com a barra vermelha de erro',
    'A cor verde do aviso de sucesso estava na folha de estilo da importação, carregada antes da folha '
    + 'base. Com a mesma especificidade, a regra do aviso de erro, que vinha depois, apagava a cor. '
    + 'Medido no navegador: a barra saía em vermelho em todas as telas.',
    'a variante mudou-se para a folha base, colada à regra que ela modifica.',
  );
  dificuldade(
    '9.7 Mensagens de validação em inglês',
    'A transcrição de validações desta entrega achou três tipos de erro que o tradutor não conhecia — '
    + 'situação fora da lista, filtro de situação inválido e número com casas decimais — e que chegavam '
    + 'ao usuário como "Input should be…".',
    'os três ganharam mensagem própria, e qualquer tipo que ainda não estiver na tabela cai numa frase '
    + 'genérica em português, e não na original. Um teste varre várias entradas ruins de uma vez atrás '
    + 'das palavras da frase original.',
  );
  dificuldade(
    '9.8 Um Pull Request incorporado num ramo morto',
    'A tela de parceiro foi aberta sobre o ramo de outro Pull Request, ainda não incorporado. O primeiro '
    + 'entrou antes, e o segundo foi incorporado ao ramo dele — que já não ia para lugar nenhum. O '
    + 'trabalho não chegou à branch principal, e a integração contínua não rodou, porque só roda para '
    + 'Pull Requests contra ela.',
    'o trabalho foi reaberto contra a branch principal. Desde então, um Pull Request que depende de outro '
    + 'só é aberto depois que o primeiro entra.',
  );

  // ====================================== 10. AJUSTES
  c.push(quebra());
  c.push(h1('10. Ajustes no planejamento, na arquitetura e na modelagem'));

  c.push(p(
    'A modelagem e a especificação são documentos vivos: a Parte II deste documento já mostra o modelo '
    + 'atual, e esta seção registra o que mudou e por quê. As evidências de execução, ao contrário, são '
    + 'retrato — a Parte III está exatamente como foi entregue em 19/09.',
  ));
  c.push(table([2500, 3000, 4138], [
    ['O que mudou', 'De / para', 'Por quê'],
    [
      'Tabela configuracao_segmentacao',
      '16 para 17 tabelas',
      'O RF21 pede limiares configuráveis sem alterar código. Uma linha só — o banco cobra isso —, com o autor e a data da última alteração',
    ],
    [
      'Segmentação na importação',
      'Recálculo à parte para a mesma transação',
      'Era um próximo passo da Sprint 03. Ou o período entra com métrica e classificação, ou não entra: período sem segmento deixaria o painel incompleto sem aviso',
    ],
    [
      'Resposta da lista de parceiros',
      'Lista para página',
      'Com 5.000 parceiros, devolver tudo a cada filtro não se sustenta. A página traz o total e o período de referência, e a interface passou a navegar por ela',
    ],
    [
      'Regras de cálculo',
      'Dentro das rotas para módulos próprios',
      'Ranking, variação e ticket passaram a um lugar só, usado pelo painel, pela lista e pela exportação — com cobertura mínima cobrada a cada Pull Request',
    ],
    [
      'Tela de cadastro de parceiro',
      'Só na API para tela própria',
      'A entrega pede validações nos formulários, e a interface tinha dois. O cadastro já existia na API; ganhou tela, desempenho e série individual',
    ],
    [
      'Mensagens de recusa',
      'Linguagem de API para linguagem de usuário',
      'Duas recusas orientavam com termos técnicos da API, e apareciam assim na tela. Hoje dizem a ação, e a tela oferece o botão',
    ],
    [
      'Gerador de dados sintéticos',
      'Sazonalidade comum para fase por parceiro',
      'A massa de demonstração saía enviesada — seção 9.1',
    ],
    [
      'Ambiente',
      'Contêineres parados para reinício automático',
      'O Docker Desktop desta equipe cai quando a máquina fica ociosa; os contêineres agora voltam sozinhos com ele',
    ],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('10.1 Planejamento'));
  c.push(p(
    'A equipe segue à frente do calendário interno. A Sprint 7 interna — segmentação e mobilidade do Top '
    + 'N — estava prevista para 19/10 a 23/10 e foi concluída em 21/09. A folga não muda o plano: vira '
    + 'margem para o núcleo em GPU, onde o risco técnico do projeto se concentra. A tabela de equivalência '
    + 'entre as sprints da disciplina e as da equipe foi atualizada no cronograma: a Sprint 03 corresponde '
    + 'à interna 6, e esta à interna 7.',
  ));

  c.push(h2('10.2 Um ponto em aberto'));
  c.push(p(
    'A regra de segmentação precisa de um limiar para "recém-chegado", e ele não estava na especificação. '
    + 'O valor em uso, três períodos, foi derivado da própria regra e está configurável — mas espera o '
    + 'aval do Product Owner, registrado na issue #59. Declarado aqui em vez de apresentado como decidido.',
  ));

  // ========================================= 11. PRÓXIMOS PASSOS
  c.push(quebra());
  c.push(h1('11. Próximos passos'));

  c.push(table([1400, 3600, 4638], [
    ['Sprint', 'Tema', 'O que entra'],
    ['8', 'Modelo preditivo', 'Treino a partir do histórico, previsão de faturamento e probabilidade de queda'],
    ['9 a 11', 'Núcleo computacional', 'Otimizador serial, paralelo em CPU e paralelo em GPU, com o comparativo de desempenho'],
    ['12', 'Central de comunicação', 'Geração de mensagens por segmento, com aprovação humana obrigatória'],
    ['13', 'Assistente e fechamento', 'Perguntas em linguagem natural sobre dados já apurados, e a entrega final'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('11.1 O que fecha o módulo'));
  c.push(bullet('A tela dos limiares da segmentação, para o Administrador — hoje só pela API e pelo terminal.'));
  c.push(bullet('O histórico de importações na interface, com autor, data e período de cada uma.'));
  c.push(bullet('A sugestão de categoria pelo nome do parceiro, na issue #35.'));
  c.push(bullet('O aval do Product Owner sobre o limiar de recém-chegado, na issue #59.'));

  c.push(h2('11.2 O que a equipe corrige no processo'));
  c.push(bullet('A tela de administração de usuários, lacuna declarada desde a Sprint 03.'));
  c.push(bullet('Revisão cruzada nos Pull Requests: cada um revisado pelo dono da área antes de entrar, e não só pelo autor.'));
  c.push(bullet('Os scripts de evidência rodados antes de cada entrega, e não só a integração contínua.'));

  c.push(espaco(200));
  c.push(p(
    'Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa '
    + 'visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.',
    { italics: true, color: '5A6B7E', size: 18 },
  ));

  return c;
}

module.exports = { montar };
