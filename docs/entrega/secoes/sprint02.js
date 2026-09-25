/**
 * Parte II do documento — Sprint 02 acadêmica: arquitetura e modelagem.
 *
 * As seções seguem a **ordem exata** dos sete itens obrigatórios da entrega, e
 * cada figura vem com explicação: a orientação é explícita em não aceitar
 * imagem ou diagrama sem identificação.
 */
const { AlignmentType } = require('docx');
const { p, rich, h1, h2, h3, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { diagrama, captura, legenda } = require('../comum/figuras');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';

/*
 * **As figuras desta parte são as entregues**, e não as dos documentos vivos.
 * O `docs/08` e o `docs/10` ganharam a tabela do treino do modelo na Sprint 05;
 * renderizados de novo, os diagramas mudariam uma parte que já foi entregue — o
 * defeito que a Parte III e o mapa da Parte IV já tiveram. A pasta guarda o SVG
 * e o PNG de cada figura como saíram no PDF da Sprint 04; a modelagem nova
 * aparece na Parte V, como ajuste justificado.
 */
const PARTE_II = 'parte-ii';

function montar() {
  const c = [];

  // ===================================================== ABERTURA DA PARTE II
  c.push(quebra());
  c.push(h1('Parte II — Sprint 02: Arquitetura e Modelagem'));

  c.push(p(
    'Esta parte apresenta a estrutura técnica que sustenta o desenvolvimento do sistema: como a solução '
    + 'está organizada, como as classes se relacionam, como os dados são modelados, como as telas se '
    + 'comportam e qual é o estado atual do banco e do repositório.',
  ));
  c.push(p(
    'Tudo aqui decorre do que foi definido na Parte I. O problema, os objetivos e os requisitos não '
    + 'mudaram — o que muda é que agora existe uma arquitetura que responde a eles, e código rodando que '
    + 'a comprova.',
  ));

  // ------------------------------------------------- equivalência de sprints
  c.push(h2('Duas numerações de sprint'));
  c.push(p(
    'A equipe trabalha em sprints semanais, e a disciplina avalia por sprints de entrega. Como os dois '
    + 'sistemas de numeração convivem na documentação do repositório, vale deixar a correspondência '
    + 'explícita antes de qualquer outra coisa.',
  ));
  c.push(table([2600, 1500, 1700, 3838], [
    ['Entrega da disciplina', 'Prazo', 'Sprints da equipe', 'O que cobre'],
    ['Sprint 01 — planejamento e descoberta', '05/09/2026', '1', 'Tema, problema, objetivos, requisitos, casos de uso, backlog, cronograma'],
    ['Sprint 02 — arquitetura e modelagem', '19/09/2026', '2 a 5', 'Arquitetura, classes, MER, modelo relacional, protótipo, banco criado'],
  ], { zebra: true, align: [null, AlignmentType.CENTER, AlignmentType.CENTER, null] }));
  c.push(espaco(80));
  c.push(rich([
    { t: 'A segunda entrega cobre quatro das nossas sprints, e não uma. ', b: true, s: 19 },
    { t: 'Na data desta entrega o banco já está criado e migrado, a API já autentica com perfis e já '
       + 'ingere relatórios, e o risco técnico do núcleo em GPU já foi retirado por medição.', s: 19 },
  ]));

  // ======================================================= 1. ARQUITETURA
  c.push(quebra());
  c.push(h1('1. Arquitetura do sistema'));

  c.push(p(
    'O sistema se organiza em cinco componentes com responsabilidades separadas. A separação não é '
    + 'estética: ela é o que permite medir o núcleo computacional isoladamente, trocar o modelo preditivo '
    + 'sem tocar na interface, e garantir que o assistente de linguagem nunca produza um número.',
  ));

  c.push(diagrama('arquitetura-geral', 560, PARTE_II));
  c.push(legenda('Arquitetura geral: interface, API, banco, núcleo computacional, modelo preditivo e assistente.'));

  c.push(h2('1.1 Componentes e responsabilidades'));
  c.push(table([1700, 3500, 4438], [
    ['Camada', 'Responsabilidade', 'O que não faz'],
    ['web/', 'Exibe, formata e coleta entrada', 'Nenhuma regra de negócio'],
    ['api/', 'Regras de negócio, autorização, persistência, orquestração', 'Cálculo pesado dentro da requisição'],
    ['nucleo/', 'Otimizador combinatório: serial, OpenMP e CUDA', 'Não conhece autenticação nem banco'],
    ['modelo/', 'Previsão de faturamento e probabilidade de queda', 'Não decide ação comercial'],
    ['assistente', 'Redige texto sobre fatos já apurados', 'Não calcula número'],
  ], { zebra: true, boldCol: 0 }));

  c.push(h2('1.2 Tecnologias previstas'));
  c.push(table([2400, 3200, 4038], [
    ['Camada', 'Tecnologia', 'Por quê'],
    ['Interface', 'React + Vite', 'Componentização e recarga rápida no desenvolvimento'],
    ['API', 'Python 3.11 + FastAPI', 'Tipagem em tempo de execução e especificação da API gerada automaticamente'],
    ['Banco', 'PostgreSQL 16 + Alembic', 'Restrições de integridade no banco e evolução do esquema versionada'],
    ['Núcleo', 'C++17 + OpenMP + CUDA', 'Paralelismo real em CPU e GPU — é o componente avaliado por Tópicos Avançados'],
    ['Modelo', 'PyTorch + NumPy', 'Treino local, sem serviço externo'],
    ['Assistente', 'Modelo de linguagem local via Ollama', 'Roda na própria máquina: sem custo por uso e sem enviar dados para fora'],
    ['Empacotamento', 'Docker Compose', 'O ambiente inteiro sobe com um comando'],
  ], { zebra: true, boldCol: 0 }));
  c.push(espaco(60));
  c.push(p(
    'A disciplina orienta que JavaScript não seja a tecnologia do núcleo computacional. A arquitetura '
    + 'respeita isso integralmente: JavaScript existe apenas na interface. Inteligência artificial, '
    + 'processamento intensivo, paralelismo, otimização e GPU estão em Python, C++ e CUDA.',
  ));

  c.push(h2('1.3 Como os componentes se comunicam'));
  c.push(bullet('A interface conversa com a API por REST, em JSON, sobre HTTP. Nenhum outro componente é acessível a partir do navegador.'));
  c.push(bullet('A API é o único componente que fala com o banco. Toda leitura e escrita passa por consulta parametrizada.'));
  c.push(bullet('A API entrega ao núcleo um cenário já montado — uplift, custo e categoria por parceiro — e recebe de volta um plano e o tempo de execução.'));
  c.push(bullet('A API entrega ao modelo preditivo a série histórica e recebe previsão por parceiro.'));
  c.push(bullet('A API entrega ao assistente um bloco de fatos já calculados; o assistente devolve texto, nunca número.'));

  c.push(h2('1.4 A integração com o componente computacional avançado'));
  c.push(p(
    'O otimizador resolve um problema combinatório: dados N parceiros e A ações possíveis, escolher no '
    + 'máximo uma ação por parceiro de forma a maximizar o uplift esperado sem violar o orçamento, o '
    + 'número máximo de parceiros e a cota por categoria. O espaço de busca tem (A+1) elevado a N '
    + 'combinações — inviável por força bruta na escala de referência de 2.000 parceiros.',
  ));
  c.push(p(
    'A solução é uma metaheurística populacional escrita pela equipe, com três implementações da mesma '
    + 'interface: serial, paralela em CPU com OpenMP e paralela em GPU com CUDA. As três produzem o mesmo '
    + 'tipo de resultado, o que é o que torna o benchmark comparável.',
  ));
  c.push(espaco(60));
  c.push(rich([
    { t: 'O risco técnico desse componente já foi retirado, por medição. ', b: true, s: 19 },
    { t: 'Uma investigação técnica dedicada validou a cadeia de compilação e mediu o ganho real oito '
       + 'semanas antes de ser necessário. O kernel CUDA chega a 100x sobre o baseline serial, e o '
       + 'resultado confere com o cálculo em CPU com erro relativo zero.', s: 19 },
  ]));
  c.push(espaco(60));
  c.push(p(
    'A medição também produziu um achado que mudou o projeto: comparada com a CPU paralela, e não com a '
    + 'serial, a GPU só compensa se a população permanecer na memória dela entre as gerações. Com '
    + 'transferência a cada geração o ganho cai para 1,1x; sem ela, chega a 11x. Isso deixou de ser '
    + 'otimização e virou requisito de projeto do componente.',
  ));

  c.push(h2('1.5 Decisões de arquitetura registradas'));
  c.push(p(
    'Cada decisão não óbvia está registrada com a situação que a motivou, as alternativas consideradas e '
    + 'as consequências assumidas. São nove até aqui:',
  ));
  c.push(table([1100, 4200, 4338], [
    ['ADR', 'Decisão', 'Consequência assumida'],
    ['001', 'Python + C++/CUDA como stack do núcleo', 'Duas linguagens no projeto, em troca de paralelismo real'],
    ['002', 'Metaheurística paralela, não solver pronto', 'Mais trabalho; é o componente que a disciplina avalia'],
    ['003', 'Segmentação e ranking determinísticos, fora do modelo de linguagem', 'Reprocessar a mesma base dá o mesmo resultado'],
    ['004', 'Degradação para CPU quando não houver GPU', 'O sistema nunca deixa de funcionar por falta de hardware'],
    ['005', 'CUDA via NVRTC, sem instalar o toolkit', 'Superada pela 006 no mesmo dia; mantida como registro'],
    ['006', 'Toolchain nativo: compilar com nvcc e MSVC', 'Quem mexe no núcleo precisa do compilador instalado'],
    ['007', 'Sessão com estado no servidor, não token autocontido', 'Uma consulta a mais por requisição; encerrar sessão tem efeito imediato'],
    ['008', 'A auditoria grava em transação própria', 'Registro a mais é ruído; registro a menos é ponto cego'],
    ['009', 'Formato do relatório importado tolerante, guiado por cabeçalho', 'Tolerância esconde erro; mitigada pela mensagem de recusa'],
  ], { zebra: true, boldCol: 0, align: [AlignmentType.CENTER] }));

  // ================================================= 2. DIAGRAMA DE CLASSES
  c.push(quebra());
  c.push(h1('2. Diagrama de classes'));

  c.push(p(
    'O sistema tem três camadas com naturezas diferentes: entidades de domínio, serviços com a regra de '
    + 'negócio, e o núcleo computacional em C++ e CUDA. Apresentá-las num único desenho produziria uma '
    + 'figura de oitenta caixas, ilegível impressa. São oito diagramas, cada um legível sozinho, e o '
    + 'primeiro mostra como eles se ligam.',
  ));

  c.push(h2('2.1 Visão de integração'));
  c.push(p('Onde cada camada vive e o que atravessa a fronteira entre elas.'));
  c.push(diagrama('classes-integracao', 520, PARTE_II));
  c.push(legenda('Visão de integração entre as camadas, com as tecnologias de cada uma.'));
  c.push(p(
    'Três fronteiras não se atravessam: a interface não conhece regra de negócio, o núcleo não conhece '
    + 'autenticação nem banco, e o assistente não calcula número.',
  ));

  c.push(quebra());
  c.push(h2('2.2 Domínio — acesso, sessões e auditoria'));
  c.push(p('Quem entra no sistema, por quanto tempo, e o rastro que fica.'));
  c.push(diagrama('classes-dominio-acesso', undefined, PARTE_II));
  c.push(legenda('Entidades de controle de acesso: usuário, sessão, tentativas de login e trilha de auditoria.'));
  c.push(p(
    'A sessão guarda o hash do identificador, nunca ele próprio: quem conseguir ler a tabela não consegue '
    + 'se passar por ninguém. E TentativaLogin não se liga a Usuario de propósito — o login é texto livre, '
    + 'porque tentativa contra usuário inexistente também precisa ser contada. É justamente o login '
    + 'desconhecido que o ataque por dicionário usa.',
  ));

  c.push(quebra());
  c.push(h2('2.3 Domínio — parceiros e dados de desempenho'));
  c.push(p('O núcleo informacional do produto: quem são os parceiros, o que faturaram, e como foram classificados.'));
  c.push(diagrama('classes-dominio-desempenho', undefined, PARTE_II));
  c.push(legenda('Entidades de negócio: categoria, parceiro, período, importação, métrica e histórico de segmento.'));
  c.push(p(
    'Métrica não tem atributo de ticket médio: ele é faturamento dividido por pedidos, calculado na '
    + 'consulta. Como coluna, divergiria das parcelas que o originam na primeira correção de dado.',
  ));

  c.push(quebra());
  c.push(h2('2.4 Domínio — núcleo computacional e comunicação'));
  c.push(p('As entidades que registram previsões, execuções do otimizador, planos de campanha e mensagens.'));
  c.push(diagrama('classes-dominio-nucleo', undefined, PARTE_II));
  c.push(legenda('Entidades do núcleo e da comunicação: previsão, ação, execução, plano, item e mensagem.'));
  c.push(p(
    'A execução do otimizador produz zero ou um plano: ou o plano respeita todas as restrições, ou não '
    + 'existe plano. A execução inviável fica registrada com o motivo, porque explicar por que não deu é '
    + 'mais útil que sumir com a tentativa.',
  ));

  c.push(quebra());
  c.push(h2('2.5 Serviços — acesso e segurança'));
  c.push(p(
    'As entidades acima são anêmicas de propósito: carregam dados e restrições, e a regra de negócio vive '
    + 'nos serviços. A razão é testabilidade — a regra fica exercitável sem instanciar entidade.',
  ));
  c.push(diagrama('servicos-acesso', undefined, PARTE_II));
  c.push(legenda('Serviços de autenticação, sessão, bloqueio por força bruta e auditoria. Todos implementados.'));
  c.push(p(
    'A autorização é dependência declarada na rota, e não uma verificação dentro de cada função: esquecer '
    + 'uma verificação é silencioso, e esquecer a dependência reprova o teste que percorre cada endpoint '
    + 'contra cada perfil.',
  ));

  c.push(quebra());
  c.push(h2('2.6 Serviços — ingestão e análise'));
  c.push(diagrama('servicos-negocio', undefined, PARTE_II));
  c.push(legenda('Serviços de ingestão, segmentação, ranking, otimização e assistente. Os dois primeiros implementados.'));
  c.push(p(
    'O interpretador do relatório não toca no banco: é função pura de texto para resultado. É isso que '
    + 'permite a prévia da importação usar exatamente o mesmo código da gravação, sem risco de a prévia '
    + 'mostrar uma coisa e a gravação fazer outra.',
  ));

  c.push(quebra());
  c.push(h2('2.7 Núcleo computacional — as estruturas'));
  c.push(p('O que entra no otimizador, o que sai, e quem avalia um candidato.'));
  c.push(diagrama('nucleo-estruturas', undefined, PARTE_II));
  c.push(legenda('Estruturas do núcleo em C++: cenário, restrições, plano e avaliador de população.'));

  c.push(h2('2.8 Núcleo computacional — as três implementações'));
  c.push(p('Três implementações da mesma interface, para que o benchmark compare o que é comparável.'));
  c.push(diagrama('nucleo-otimizadores', undefined, PARTE_II));
  c.push(legenda('Hierarquia do otimizador: serial, paralelo em CPU com OpenMP e paralelo em GPU com CUDA.'));
  c.push(p(
    'O método privado de manter a população na GPU não é detalhe de implementação: é o que justifica a '
    + 'classe existir. Sem ele, a GPU ganha apenas 1,1x da CPU paralela; com ele, 11x.',
  ));

  c.push(h2('2.9 O que já está implementado'));
  c.push(p(
    'Um diagrama que promete código inexistente é pior que diagrama nenhum, porque ninguém reconfere. '
    + 'A separação abaixo pode ser verificada no repositório.',
  ));
  c.push(table([1800, 4400, 3438], [
    ['Camada', 'Implementado', 'Previsto'],
    ['Domínio', 'As 16 entidades, com restrições no banco', '—'],
    ['Serviços', 'Segurança, sessões, bloqueio, auditoria, dependências, leitor de relatório, importação', 'Segmentador, ranking, otimização, assistente'],
    ['Rotas', 'Sessão, usuários, importações, auditoria, saúde', 'Painel, otimização, mensagens, assistente'],
    ['Núcleo', 'Kernel de avaliação validado em CUDA e OpenMP', 'Otimizador e as três implementações'],
    ['Modelo', '—', 'Previsor em PyTorch'],
  ], { zebra: true, boldCol: 0 }));
  c.push(espaco(60));
  c.push(rich([
    { t: 'Cobertura de teste da parte implementada: ', s: 19 },
    { t: '179 testes automatizados, 96% das linhas.', b: true, s: 19 },
  ]));

  // ============================================================== 3. MER
  c.push(quebra());
  c.push(h1('3. Modelo Entidade-Relacionamento'));

  c.push(p(
    'O modelo conceitual responde "o que o sistema precisa saber", na linguagem do negócio e sem decisão '
    + 'de implementação. São dezesseis entidades.',
  ));
  c.push(diagrama('mer-conceitual', undefined, PARTE_II));
  c.push(legenda('Modelo conceitual: entidades e relacionamentos, com cardinalidade em notação pé-de-galinha.'));
  c.push(p(
    'A entidade de tentativas de login não aparece no diagrama porque não se relaciona com nenhuma outra, '
    + 'e isso é deliberado: ela registra tentativas inclusive contra logins inexistentes, e ligá-la ao '
    + 'usuário quebraria justamente o caso que ela existe para cobrir.',
  ));

  c.push(h2('3.1 Entidades e atributos'));
  c.push(p(
    'Os atributos estão aqui, e não dentro das caixas do desenho: com dezesseis entidades e mais de cem '
    + 'atributos, a figura ficaria ilegível impressa.',
  ));
  c.push(table([2100, 3100, 4438], [
    ['Entidade', 'O que representa', 'Atributos'],
    ['Usuario', 'Quem acessa o sistema', 'login, nome, senha (só hash), perfil, situação, data de cadastro'],
    ['SessaoAcesso', 'Sessão autenticada em curso', 'identificador, início, expiração, revogação e motivo, origem, navegador'],
    ['TentativaLogin', 'Tentativa de autenticação', 'login tentado, origem, resultado, momento'],
    ['Auditoria', 'Ação sensível praticada', 'autor, ação, parâmetros, origem, momento'],
    ['Categoria', 'Ramo de atuação', 'nome, situação'],
    ['Parceiro', 'Comércio da rede', 'nome, categoria, origem da categoria, status comercial, contato, situação'],
    ['Periodo', 'Janela de tempo do relatório', 'data inicial, data final'],
    ['Importacao', 'Uma carga de relatório', 'período, autor, origem, total gravado, total rejeitado, momento'],
    ['Metrica', 'Desempenho num período', 'faturamento, número de pedidos, projeção'],
    ['HistoricoSegmento', 'Classificação num período', 'segmento, momento do cálculo'],
    ['Previsao', 'Estimativa do modelo', 'faturamento previsto, probabilidade de queda, versão do modelo'],
    ['AcaoComercial', 'Tipo de ação da campanha', 'nome, custo unitário, uplift esperado, situação'],
    ['ExecucaoOtimizador', 'Uma rodada do otimizador', 'modo, parâmetros, viabilidade, restrição violada, uplift, custo, tempo'],
    ['PlanoCampanha', 'Plano de uma execução viável', 'janela de aplicação'],
    ['ItemPlano', 'Par parceiro–ação escolhido', 'uplift esperado, custo'],
    ['Mensagem', 'Comunicação para um parceiro', 'texto gerado, texto final, estado, autor da decisão, motivo'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('3.2 Relacionamentos que carregam regra de negócio'));
  c.push(bullet('Métrica é única por parceiro e período — é o que impede uma reimportação de duplicar a série e corromper a segmentação por tendência.'));
  c.push(bullet('Execução do otimizador produz zero ou um plano: ou o plano respeita todas as restrições, ou não existe plano.'));
  c.push(bullet('Plano de campanha compõe um ou mais itens, no máximo um por parceiro. Item sem plano não tem significado.'));
  c.push(bullet('Usuário representa zero ou um parceiro. Só o perfil Parceiro usa esse vínculo, e é ele que restringe o acesso ao próprio desempenho.'));

  // ================================================== 4. MODELO RELACIONAL
  c.push(quebra());
  c.push(h1('4. Modelo relacional'));

  c.push(p(
    'A conversão do modelo conceitual em tabelas. Toda tabela tem chave primária inteira e sequencial: a '
    + 'escolha por chave substituta mantém as chaves estrangeiras com uma coluna só, e permite corrigir o '
    + 'nome de um parceiro sem reescrever as métricas dele.',
  ));
  c.push(espaco(60));
  c.push(rich([{ t: 'Notação: o sublinhado marca chave primária e o asterisco marca chave estrangeira.', i: true, s: 19, c: '5A6B7E' }]));
  c.push(espaco(80));

  const relacional = [
    'usuario(id, login, nome, senha_hash, perfil, ativo, parceiro_id*, criado_em)',
    'sessao_acesso(id, token_hash, usuario_id*, criada_em, expira_em, revogada_em,',
    '              motivo_revogacao, origem, agente)',
    'tentativa_login(id, login, origem, sucesso, ocorrido_em)',
    'auditoria(id, usuario_id*, acao, detalhes, origem, ocorrido_em)',
    '',
    'categoria(id, nome, ativa)',
    'parceiro(id, nome, categoria_id*, origem_categoria, status, contato, ativo, criado_em)',
    '',
    'periodo(id, data_inicio, data_fim)',
    'importacao(id, periodo_id*, usuario_id*, origem, total_gravado, total_rejeitado, enviado_em)',
    'metrica(id, parceiro_id*, periodo_id*, importacao_id*, faturamento, pedidos, projecao)',
    'historico_segmento(id, parceiro_id*, periodo_id*, segmento, calculado_em)',
    '',
    'previsao(id, parceiro_id*, periodo_base_id*, faturamento_previsto, probabilidade_queda,',
    '         modelo_versao, gerada_em)',
    'acao_comercial(id, nome, custo_unitario, uplift_esperado_pct, ativa)',
    'execucao_otimizador(id, usuario_id*, modo, parametros, viavel, restricao_violada,',
    '                    uplift_total, custo_total, tempo_ms, executada_em)',
    'plano_campanha(id, execucao_id*, aplicacao_inicio, aplicacao_fim)',
    'item_plano(id, plano_id*, parceiro_id*, acao_id*, uplift_esperado, custo)',
    '',
    'mensagem(id, parceiro_id*, item_plano_id*, texto_gerado, texto_final, estado,',
    '         decidida_por_id*, motivo_rejeicao, gerada_em, decidida_em)',
  ];
  c.push(...mono(relacional));
  c.push(espaco(160));

  c.push(h2('4.1 Detalhamento das tabelas centrais'));
  c.push(p('As demais tabelas seguem o mesmo padrão e estão detalhadas coluna a coluna na documentação do repositório.'));

  c.push(h3('usuario'));
  c.push(table([2200, 2100, 1900, 3438], [
    ['Coluna', 'Tipo', 'Chave', 'Restrição'],
    ['id', 'serial', 'PK', ''],
    ['login', 'varchar(60)', '', 'único'],
    ['nome', 'varchar(120)', '', ''],
    ['senha_hash', 'varchar(255)', '', 'somente hash Argon2id'],
    ['perfil', 'enum', '', 'ADMINISTRADOR, GESTOR, ANALISTA, PARCEIRO'],
    ['ativo', 'boolean', '', 'padrão verdadeiro'],
    ['parceiro_id', 'integer', 'FK → parceiro', 'nulo, exceto no perfil PARCEIRO'],
    ['criado_em', 'timestamptz', '', 'padrão now()'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(espaco(60));
  c.push(p('Uma restrição do banco garante que ter vínculo com parceiro e ser do perfil Parceiro são a mesma condição, nos dois sentidos.', { size: 19 }));

  c.push(h3('metrica — a tabela central do sistema'));
  c.push(table([2200, 2100, 2400, 2938], [
    ['Coluna', 'Tipo', 'Chave', 'Restrição'],
    ['id', 'serial', 'PK', ''],
    ['parceiro_id', 'integer', 'FK → parceiro', 'único em conjunto com periodo_id'],
    ['periodo_id', 'integer', 'FK → periodo', ''],
    ['importacao_id', 'integer', 'FK → importacao', 'de qual carga o registro veio'],
    ['faturamento', 'numeric(12,2)', '', 'maior ou igual a zero'],
    ['pedidos', 'integer', '', 'maior ou igual a zero'],
    ['projecao', 'numeric(12,2)', '', 'nulo permitido'],
  ], { zebra: true, boldCol: 0, size: 17 }));
  c.push(espaco(60));
  c.push(rich([
    { t: 'Não existe coluna de ticket médio. ', b: true, s: 19 },
    { t: 'Ele é faturamento dividido por pedidos, calculado na consulta. Como coluna, divergiria das '
       + 'parcelas que o originam na primeira correção de dado.', s: 19 },
  ]));

  c.push(quebra());
  c.push(h2('4.2 O que o banco garante sozinho'));
  c.push(p(
    'Nove restrições impedem estado inválido independentemente do código da aplicação. É a diferença entre '
    + 'uma regra que vale e uma regra que valeria se ninguém esquecesse de chamá-la.',
  ));
  c.push(table([4400, 5238], [
    ['Restrição', 'Garante'],
    ['usuario · vínculo com parceiro', 'Vínculo se e somente se o perfil for PARCEIRO'],
    ['parceiro · categoria com origem', 'Categoria sempre acompanhada da procedência'],
    ['periodo · ordem', 'Data final nunca anterior à inicial'],
    ['metrica · faturamento e pedidos', 'Nenhum dos dois negativo'],
    ['previsao · probabilidade', 'Probabilidade entre zero e um'],
    ['acao_comercial · custo', 'Custo de ação não negativo'],
    ['execucao_otimizador · motivo', 'Execução inviável tem o motivo registrado'],
    ['mensagem · autor da decisão', 'Mensagem decidida tem autor e data — nenhuma sai do estado pendente sem um humano'],
  ], { zebra: true, boldCol: 0 }));

  c.push(h2('4.3 Índices'));
  c.push(p('Cada índice existe por causa de uma consulta concreta, e não por precaução.'));
  c.push(table([3400, 2800, 3438], [
    ['Índice', 'Colunas', 'Serve a'],
    ['parceiro por nome', 'nome', 'Busca no painel e casamento na importação'],
    ['métrica por período', 'periodo_id, faturamento', 'Ranking do período sem varrer a tabela'],
    ['segmento por período', 'periodo_id, segmento', 'Filtro por segmento no painel'],
    ['auditoria por data', 'ocorrido_em', 'Consulta da trilha por intervalo'],
    ['sessão por usuário', 'usuario_id', 'Derrubar as sessões de um usuário de uma vez'],
    ['tentativa por origem', 'origem, ocorrido_em', 'Contagem de falhas na janela do bloqueio'],
    ['mensagem por estado', 'estado', 'Fila de aprovação'],
  ], { zebra: true, boldCol: 0 }));

  // ============================================================ 5. PROTÓTIPO
  c.push(quebra());
  c.push(h1('5. Protótipo das telas principais'));

  c.push(p(
    'Quatro telas navegáveis, construídas em HTML e CSS autorais. O protótipo não é uma imagem estática: '
    + 'é uma página que se abre no navegador e permite percorrer as telas, e está versionada no '
    + 'repositório junto com o restante do projeto.',
  ));
  c.push(espaco(40));
  c.push(rich([
    { t: 'Protótipo navegável: ', s: 19 },
    { t: `${REPO}/blob/main/docs/prototipo/index.html`, b: true, s: 19, c: '2C5B8F' },
  ]));
  c.push(espaco(60));
  c.push(rich([
    { t: 'Todos os dados exibidos são sintéticos, ', b: true, s: 19 },
    { t: 'gerados por script. Nenhum nome de empresa, pessoa ou operação real aparece no protótipo ou em '
       + 'qualquer parte do repositório, que é público.', s: 19 },
  ]));

  c.push(h2('5.1 Decisões visuais que valem explicar'));
  c.push(bullet('Cada cor tem um trabalho só. O âmbar significa "responde ao seu clique" — botão, link, foco — e nada mais. Quando uma cor é marca, ação e dado ao mesmo tempo, ela deixa de significar qualquer coisa.'));
  c.push(bullet('Cada segmento tem uma cor e só uma, idêntica em tabela, gráfico e indicador.'));
  c.push(bullet('A paleta foi validada com ferramenta, não escolhida no olho: o primeiro conjunto reprovou porque vermelho e verde ficavam indistinguíveis para daltônicos, e o verde foi trocado por turquesa.'));
  c.push(bullet('Nenhuma informação depende só da cor: o rótulo do segmento aparece sempre em texto ao lado do ponto colorido.'));

  c.push(quebra());
  c.push(h2('5.2 Painel'));
  c.push(p('Responde à pergunta dominante do produto: quem precisa de atenção agora. Indicadores no topo, série histórica e distribuição por segmento, e o ranking de parceiros abaixo.'));
  c.push(captura('painel'));
  c.push(legenda('Tela de painel: indicadores consolidados, faturamento da rede, distribuição por segmento e ranking.'));

  c.push(quebra());
  c.push(h2('5.3 Importação'));
  c.push(p('O período é campo obrigatório e não tem valor padrão. A prévia mostra o que será gravado — reconhecidos, rejeitados com o motivo de cada um, e parceiros ainda não cadastrados — antes de qualquer gravação.'));
  c.push(captura('importar'));
  c.push(legenda('Tela de importação: período obrigatório e prévia com reconhecidos, rejeitados e parceiros novos.'));

  c.push(quebra());
  c.push(h2('5.4 Campanha'));
  c.push(p('Onde o núcleo computacional aparece para o usuário: restrições de orçamento e cota, escolha do modo de execução, comparativo de desempenho entre serial, CPU paralela e GPU, e o plano recomendado.'));
  c.push(captura('campanha'));
  c.push(legenda('Tela de campanha: restrições, comparativo de desempenho entre os três modos e plano recomendado.'));

  c.push(quebra());
  c.push(h2('5.5 Aprovação'));
  c.push(p('Nenhuma mensagem chega ao parceiro sem decisão humana. A fila mostra cada mensagem com o destinatário, o segmento e o texto, e o gestor aprova, edita ou rejeita.'));
  c.push(captura('aprovacao'));
  c.push(legenda('Tela de aprovação: fila de mensagens pendentes, com a decisão humana como passo obrigatório.'));

  // ========================================================= 6. BANCO CRIADO
  c.push(quebra());
  c.push(h1('6. Banco de dados criado'));

  c.push(p(
    'O esquema não está apenas desenhado: está aplicado e em uso. O ambiente completo sobe com um comando, '
    + 'e o processo de inicialização aplica as migrações antes de servir a API.',
  ));

  c.push(h2('6.1 Estrutura aplicada'));
  c.push(table([5200, 4438], [
    ['Objeto', 'Quantidade'],
    ['Tabelas de domínio', '16'],
    ['Chaves primárias', '16'],
    ['Chaves estrangeiras', '21'],
    ['Restrições de unicidade', '11'],
    ['Restrições de validação', '9'],
    ['Índices', '34'],
    ['Tipos enumerados', '7'],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER] }));
  c.push(espaco(80));
  c.push(p('Consultado no catálogo do próprio PostgreSQL, e não estimado a partir do código:', { size: 19 }));
  c.push(espaco(40));

  const terminal = [
    '$ docker compose exec api alembic current',
    '77b3651bd03d (head)',
    '',
    '$ docker compose exec postgres psql -U gih -d gih -c "\\dt"',
    '  acao_comercial   execucao_otimizador   item_plano   metrica     periodo',
    '  alembic_version  historico_segmento    mensagem     parceiro    plano_campanha',
    '  auditoria        importacao            previsao     categoria   sessao_acesso',
    '  tentativa_login  usuario',
    '  (17 rows)',
  ];
  c.push(...mono(terminal));
  c.push(espaco(140));
  c.push(p(
    'São as 16 tabelas de domínio mais a tabela de controle da ferramenta de migração, que registra qual '
    + 'versão do esquema está aplicada.',
  ));

  c.push(h2('6.2 Esquema versionado, não script solto'));
  c.push(p(
    'O banco é criado por migrações versionadas no repositório. Isso permite que qualquer integrante '
    + 'chegue ao mesmo estado a partir de um clone limpo, e torna a evolução do banco auditável no '
    + 'histórico. O ciclo de reverter e reaplicar foi testado duas vezes, e não uma: a falha conhecida de '
    + 'tipos enumerados só aparece na segunda execução.',
  ));
  c.push(espaco(40));
  c.push(p(
    'A suíte de testes também aplica as mesmas migrações num banco separado, em vez de montar o esquema '
    + 'por outro caminho. Custa alguns segundos por execução e cobre a divergência entre o modelo em '
    + 'código e a migração — defeito que ninguém percebe até a hora de implantar.',
  ));

  // ========================================================= 7. REPOSITÓRIO
  c.push(quebra());
  c.push(h1('7. Projeto estruturado no GitHub'));

  c.push(espaco(40));
  c.push(rich([
    { t: 'Repositório: ', s: 21 },
    { t: REPO, b: true, s: 21, c: '2C5B8F' },
  ]));
  c.push(espaco(100));

  c.push(h2('7.1 Organização'));
  c.push(table([2600, 7038], [
    ['Diretório', 'Conteúdo'],
    ['api/', 'API em Python e FastAPI, migrações do banco e suíte de testes'],
    ['nucleo/', 'Núcleo computacional em C++ e CUDA, com a investigação técnica já concluída'],
    ['docs/', 'Toda a documentação técnica, diagramas, protótipo e o gerador deste documento'],
    ['scripts/', 'Gerador de dados sintéticos e comando de reinicialização do banco'],
    ['.github/', 'Integração contínua e mapa de responsáveis por revisão'],
    ['web/', 'Interface: login, painel, importação e parceiros (construída na Sprint 03)'],
  ], { zebra: true, boldCol: 0 }));

  c.push(h2('7.2 Evidências de evolução'));
  c.push(p('A disciplina pede que o repositório demonstre a evolução do projeto. O que está lá para ser verificado:'));
  c.push(bullet('Histórias de usuário registradas como issues, agrupadas por sprint em milestones, com critérios de aceite.'));
  c.push(bullet('Toda alteração entra por Pull Request revisado. A branch principal é protegida e não aceita push direto.'));
  c.push(bullet('Integração contínua obrigatória: análise estática, suíte de testes contra um PostgreSQL real, e verificação de que nenhum dado ou segredo foi versionado.'));
  c.push(bullet('Mapa de responsáveis por diretório, que convida automaticamente o dono de cada área para revisar.'));
  c.push(bullet('Documentação versionada junto com o código, atualizada no mesmo Pull Request que introduz a mudança.'));

  c.push(h2('7.3 Estado atual do desenvolvimento'));
  c.push(table([3400, 1500, 4738], [
    ['Entrega', 'Situação', 'Evidência'],
    ['Banco modelado e migrado', 'Concluído', '16 tabelas, 21 chaves estrangeiras, 9 restrições'],
    ['Ambiente sobe com um comando', 'Concluído', 'Docker Compose com migração automática'],
    ['Autenticação, perfis e auditoria', 'Concluído', 'Testes cobrindo cada endpoint contra cada perfil'],
    ['Importação de relatório com prévia', 'Concluído', 'Interpretador tolerante, com testes próprios'],
    ['Núcleo em GPU', 'Risco retirado', 'Ganho medido de até 100x sobre o baseline serial'],
    ['Protótipo das telas', 'Aprovado', 'Aprovado pela equipe em 17/09/2026 — quatro telas, paleta validada'],
    ['Interface em React', 'Concluído', 'Construída na Sprint 03 sobre o protótipo aprovado — ver a Parte III'],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER] }));

  c.push(espaco(200));
  c.push(p(
    'Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa '
    + 'visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.',
    { italics: true, color: '5A6B7E', size: 18 },
  ));

  return c;
}

module.exports = { montar };
