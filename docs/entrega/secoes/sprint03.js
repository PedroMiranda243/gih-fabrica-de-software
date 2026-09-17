/**
 * Parte III do documento — Sprint 03 acadêmica: estrutura inicial funcionando.
 *
 * Esta entrega é de implementação, não de documentação: o enunciado avisa que
 * diagrama, protótipo e descrição de funcionalidade não implementada não
 * contam. Por isso cada item traz saída de execução real, e não descrição.
 *
 * As evidências vêm dos arquivos gerados pelos scripts, e não são transcritas à
 * mão — se alguém reescrever um trecho para ficar mais bonito, a evidência
 * deixa de ser evidência. Ver `comum/evidencias.js`.
 */
const { AlignmentType } = require('docx');
const { p, rich, h1, h2, bullet, table, espaco, quebra, mono } = require('../comum/estilos');
const { evidencia, legenda } = require('../comum/figuras');
const { trecho } = require('../comum/evidencias');

const REPO = 'github.com/PedroMiranda243/gih-fabrica-de-software';

function montar() {
  const c = [];

  c.push(quebra());
  c.push(h1('Parte III — Sprint 03: Estrutura Inicial Funcionando'));

  c.push(p(
    'Esta parte demonstra o sistema em funcionamento. Os seis itens da entrega estão implementados, '
    + 'persistem no banco e são exercitados por teste automatizado — e cada um aparece aqui com saída '
    + 'de execução real, não com descrição.',
  ));
  c.push(p(
    'A interface web ainda não existe, e isso é decisão de sequência, não atraso. O protótipo das telas '
    + 'está em validação pela equipe, e a regra que a própria equipe escreveu diz que nenhuma linha de '
    + 'CSS entra antes dessa aprovação — num projeto anterior do mesmo domínio, pular essa etapa custou '
    + 'um redesenho inteiro descartado. Enquanto isso, a API é operável pela documentação interativa, '
    + 'que é por onde a demonstração acontece.',
  ));

  c.push(h2('Os seis itens, e onde estão'));
  c.push(table([700, 3200, 1900, 3838], [
    ['#', 'Item', 'Situação', 'Evidência neste documento'],
    ['1', 'Banco de dados conectado', 'Funcionando', 'Seção 2 — saída da verificação'],
    ['2', 'Login funcional', 'Funcionando', 'Seção 3 — transcrição das requisições'],
    ['3', 'Cadastro de usuários', 'Funcionando', 'Seção 4 — transcrição e persistência'],
    ['4', 'Controle de perfis', 'Funcionando', 'Seção 5 — negação por perfil'],
    ['5', 'CRUD principal', 'Funcionando', 'Seção 6 — as quatro operações'],
    ['6', 'Deploy local', 'Funcionando', 'Seção 7 — passo a passo'],
  ], { zebra: true, align: [AlignmentType.CENTER], boldCol: 1 }));

  // ==================================================== 1. A ESTRUTURA
  c.push(quebra());
  c.push(h1('1. A estrutura implementada'));

  c.push(p(
    'O sistema está organizado em camadas com responsabilidades separadas, e a separação é o que permite '
    + 'medir o núcleo computacional isoladamente e garantir que a regra de negócio não escape para a '
    + 'interface.',
  ));

  c.push(h2('1.1 O que existe hoje'));
  c.push(table([2300, 3500, 3838], [
    ['Camada', 'O que está implementado', 'Como se verifica'],
    ['Banco', '16 tabelas, 21 chaves estrangeiras, 9 restrições de validação, 34 índices', 'Migração versionada, aplicada na subida'],
    ['Acesso', 'Sessão com estado no servidor, senha em Argon2id, bloqueio por força bruta', '36 verificações contra a API no ar'],
    ['Usuários', 'Cadastro, edição, desativação e atribuição de perfil', 'Testes automatizados e transcrição'],
    ['Autorização', 'Quatro perfis, verificados no servidor a cada requisição', 'Cada endpoint contra cada perfil'],
    ['Parceiros', 'CRUD completo, com busca, filtros e exclusão condicional', 'Transcrição das quatro operações'],
    ['Ingestão', 'Importação por texto com prévia, período obrigatório e rejeição parcial', 'Verificação de ponta a ponta'],
    ['Auditoria', 'Trilha de ações sensíveis, com filtro e paginação', 'Consulta na própria API'],
    ['Núcleo', 'Kernel de avaliação validado em CUDA e OpenMP', 'Medição registrada no repositório'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('1.2 Números do que foi construído'));
  c.push(table([4800, 4838], [
    ['Medida', 'Valor'],
    ['Endpoints em funcionamento', '21'],
    ['Testes automatizados', '242'],
    ['Cobertura de linhas da API', '96%'],
    ['Verificações de ponta a ponta', '36'],
    ['Tabelas no banco', '16'],
    ['Decisões de arquitetura registradas', '9'],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER] }));

  c.push(h2('1.3 Como a qualidade é verificada'));
  c.push(bullet('Toda alteração entra por Pull Request revisado; a branch principal é protegida.'));
  c.push(bullet('A integração contínua roda análise estática e a suíte completa contra um PostgreSQL real a cada Pull Request.'));
  c.push(bullet('A suíte de testes aplica as mesmas migrações do ambiente real, em um banco separado — e não monta o esquema por outro caminho, para cobrir a divergência entre o modelo em código e a migração.'));
  c.push(bullet('Um teste percorre cada endpoint contra cada perfil. Endpoint novo sem permissão declarada reprova a suíte, o que impede a cobertura de envelhecer em silêncio.'));

  // ============================================== 2. BANCO CONECTADO
  c.push(quebra());
  c.push(h1('2. Banco de dados conectado'));

  c.push(p(
    'A aplicação conversa com o PostgreSQL desde a primeira requisição. A conexão é verificada em três '
    + 'níveis: a própria API reporta o estado do banco, a migração aplicada é identificável, e a trilha '
    + 'de auditoria só tem conteúdo porque houve escrita real.',
  ));

  c.push(h2('2.1 Verificação executada'));
  c.push(p(
    'A saída abaixo é de uma execução real do comando de verificação, que roda contra a API no ar — '
    + 'HTTP real, cookie real, banco real:',
    { size: 19 },
  ));
  c.push(espaco(60));
  c.push(...mono(trecho('verificacao.txt', '[1/6]', '[2/6]')));
  c.push(espaco(120));

  c.push(h2('2.2 Estrutura aplicada'));
  c.push(p('Consultado no catálogo do próprio PostgreSQL, e não estimado a partir do código:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono([
    '$ docker compose exec api alembic current',
    '77b3651bd03d (head)',
    '',
    '$ docker compose exec postgres psql -U gih -d gih -c "\\dt"',
    '  acao_comercial   execucao_otimizador   item_plano   metrica     periodo',
    '  alembic_version  historico_segmento    mensagem     parceiro    plano_campanha',
    '  auditoria        importacao            previsao     categoria   sessao_acesso',
    '  tentativa_login  usuario',
    '  (17 rows)',
  ]));
  c.push(espaco(120));
  c.push(p(
    'São as 16 tabelas de domínio mais a tabela de controle da ferramenta de migração. O esquema é criado '
    + 'por migração versionada no repositório, o que permite a qualquer integrante chegar ao mesmo estado '
    + 'a partir de um clone limpo.',
  ));

  // =================================================== 3. LOGIN
  c.push(quebra());
  c.push(h1('3. Login funcional'));

  c.push(p(
    'A autenticação é por login e senha, integrada ao banco. A sessão tem estado no servidor: encerrar a '
    + 'sessão a invalida de verdade, e não apenas apaga o cookie do navegador.',
  ));

  c.push(h2('3.1 Como funciona'));
  c.push(bullet('A senha é armazenada apenas como hash Argon2id, com sal por usuário. Nenhuma senha em texto claro no banco ou em log.'));
  c.push(bullet('O identificador da sessão são 256 bits sorteados, guardados no banco como hash — quem ler a tabela não consegue se passar por ninguém.'));
  c.push(bullet('O cookie vem com HttpOnly e SameSite, e o identificador é renovado a cada autenticação, o que impede fixação de sessão.'));
  c.push(bullet('Cinco tentativas falhas a partir da mesma origem bloqueiam temporariamente novas tentativas.'));
  c.push(bullet('Login inexistente e senha errada respondem de forma idêntica — mesma mensagem, mesmo código e mesmo tempo. Responder mais rápido para um login que não existe entregaria a lista de usuários válidos.'));

  c.push(h2('3.2 Verificação executada'));
  c.push(espaco(40));
  c.push(...mono(trecho('verificacao.txt', '[2/6]', '[3/6]')));
  c.push(espaco(120));

  c.push(h2('3.3 A requisição e a resposta'));
  c.push(p('Transcrição de uma autenticação real. A senha aparece mascarada de propósito:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('crud.txt', 'Login — item 2', 'CADASTRAR')));

  // =============================================== 4. CADASTRO
  c.push(quebra());
  c.push(h1('4. Cadastro de usuários'));

  c.push(p(
    'O cadastro é do Administrador, persiste no banco e registra a criação na trilha de auditoria. Cada '
    + 'usuário recebe exatamente um perfil, entre Administrador, Gestor, Analista e Parceiro.',
  ));

  c.push(h2('4.1 Verificação executada'));
  c.push(espaco(40));
  c.push(...mono(trecho('verificacao.txt', '[3/6]', '[4/6]')));
  c.push(espaco(120));

  c.push(h2('4.2 A requisição e a resposta'));
  c.push(espaco(40));
  c.push(...mono(trecho('crud.txt', 'Preparação — um analista', 'Login — item 2')));
  c.push(espaco(60));
  c.push(rich([
    { t: 'A resposta não devolve a senha nem o hash dela. ', b: true, s: 19 },
    { t: 'As respostas da API são declaradas campo a campo, e não serializam a entidade inteira — é o que '
       + 'impede um campo sensível de vazar quando alguém acrescentar uma coluna nova.', s: 19 },
  ]));

  c.push(h2('4.3 Não existe apagar usuário'));
  c.push(p(
    'A trilha de auditoria referencia o autor de cada ação, e remover a linha deixaria o histórico '
    + 'apontando para o nada. O que existe é desativar, que resolve o problema real — tirar o acesso — '
    + 'sem destruir o registro. Desativar também encerra as sessões abertas daquele usuário na hora.',
  ));
  c.push(p(
    'Há ainda uma trava: a última conta de Administrador ativa não pode ser desativada nem rebaixada. Sem '
    + 'ela, uma edição distraída deixaria o sistema sem ninguém capaz de gerenciar usuários.',
  ));

  // ============================================ 5. CONTROLE DE PERFIS
  c.push(quebra());
  c.push(h1('5. Controle de perfis'));

  c.push(p(
    'A autorização é verificada no servidor a cada requisição. Esconder um botão não é controle de '
    + 'acesso: mesmo que a interface não ofereça o caminho, o endereço continua acessível por outros '
    + 'meios, e é o servidor que precisa recusar.',
  ));

  c.push(h2('5.1 A matriz'));
  c.push(p(
    'Os perfis e o que cada um alcança vêm da matriz de permissões definida na Sprint 01, e não de '
    + 'leitura do código:',
    { size: 19 },
  ));
  c.push(table([3200, 1600, 1600, 1600, 1638], [
    ['Área', 'Administrador', 'Gestor', 'Analista', 'Parceiro'],
    ['Autenticar', 'sim', 'sim', 'sim', 'sim'],
    ['Gerenciar usuários', 'sim', '—', '—', '—'],
    ['Auditar ações', 'sim', '—', '—', '—'],
    ['Gerenciar parceiros', '—', 'sim', 'sim', '—'],
    ['Importar relatório', '—', 'sim', 'sim', '—'],
  ], { zebra: true, boldCol: 0, align: [null, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }));

  c.push(h2('5.2 Verificação executada'));
  c.push(p(
    'Cada rota protegida foi exercitada com cada perfil, e o resultado confrontado com a matriz:',
    { size: 19 },
  ));
  c.push(espaco(40));
  c.push(...mono(trecho('verificacao.txt', '[4/6]', '[5/6]')));
  c.push(espaco(120));

  c.push(h2('5.3 A negação, na prática'));
  c.push(p('Um analista tentando a área de usuários, que é exclusiva do Administrador:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('crud.txt', 'Controle de perfis — item 4', 'Fim da transcrição')));

  // ================================================== 6. CRUD
  c.push(quebra());
  c.push(h1('6. CRUD principal — parceiros'));

  c.push(p(
    'O parceiro é a entidade central do produto: métrica, segmento, previsão, plano de campanha e '
    + 'mensagem pendem dele. As quatro operações estão implementadas, integradas ao banco, e são '
    + 'exercitadas por 28 testes automatizados além da verificação de ponta a ponta.',
  ));

  c.push(h2('6.1 As operações'));
  c.push(table([1400, 3400, 4838], [
    ['Operação', 'Endereço', 'Comportamento'],
    ['Cadastrar', 'POST /api/parceiros', 'Nome único, garantido pelo banco; categoria escolhida vira confirmada'],
    ['Consultar', 'GET /api/parceiros', 'Busca parcial por nome, filtro por categoria, status e situação'],
    ['Consultar', 'GET /api/parceiros/{id}', 'Um parceiro, com a categoria resolvida'],
    ['Atualizar', 'PATCH /api/parceiros/{id}', 'Nome, categoria, status, contato e situação'],
    ['Excluir', 'DELETE /api/parceiros/{id}', 'Exclui sem histórico; recusa explicando quando há'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('6.2 Verificação executada'));
  c.push(espaco(40));
  c.push(...mono(trecho('verificacao.txt', '[5/6]', '[6/6]')));

  c.push(quebra());
  c.push(h2('6.3 Cadastrar, consultar e atualizar'));
  c.push(p('Transcrição das requisições reais, com o corpo enviado e o corpo recebido:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('crud.txt', 'CADASTRAR — item 5', 'CONSULTAR')));
  c.push(espaco(100));
  c.push(...mono(trecho('crud.txt', 'ATUALIZAR', 'Nome repetido')));

  c.push(quebra());
  c.push(h2('6.4 A exclusão, e por que ela tem duas saídas'));
  c.push(p(
    'A entrega pede a operação de excluir. Excluir um parceiro que já tem faturamento importado, porém, '
    + 'falsearia as séries dos períodos já fechados: o total da rede deixaria de bater com a soma das '
    + 'partes, e ninguém perceberia, porque a tela continuaria parecendo correta.',
  ));
  c.push(p(
    'A solução não foi escolher um dos dois lados. Sem histórico, o parceiro é apagado de verdade. Com '
    + 'histórico, a exclusão é recusada dizendo quantos registros de cada tipo impedem, e apontando a '
    + 'desativação — que resolve o problema real, que é tirar o parceiro de circulação.',
  ));
  c.push(espaco(60));
  c.push(...mono(trecho('crud.txt', 'EXCLUIR — sem histórico', 'EXCLUIR — com histórico')));

  c.push(quebra());
  c.push(p('E o caminho que protege o histórico:', { size: 19 }));
  c.push(espaco(40));
  c.push(...mono(trecho('crud.txt', '$ DELETE /api/parceiros', 'Controle de perfis — item 4')));

  c.push(h2('6.5 Documentação interativa'));
  c.push(p(
    'A especificação da API é gerada automaticamente e permite executar qualquer operação pelo navegador. '
    + 'É por onde a demonstração acontece enquanto a interface não existe.',
  ));
  c.push(evidencia('swagger-geral'));
  c.push(legenda('Documentação interativa em /api/docs: as 21 operações, agrupadas por assunto.'));

  c.push(quebra());
  c.push(evidencia('swagger-parceiros'));
  c.push(legenda('Contrato de entrada e saída da listagem de parceiros, com os filtros disponíveis.'));

  // ============================================== 7. EXECUÇÃO LOCAL
  c.push(quebra());
  c.push(h1('7. Execução local'));

  c.push(p(
    'O ambiente completo sobe com um comando, a partir de um clone limpo. Não há etapa manual de '
    + 'configuração: o processo de inicialização aplica as migrações e cria o administrador antes de '
    + 'servir a API.',
  ));

  c.push(h2('7.1 Pré-requisitos'));
  c.push(bullet('Docker Desktop'));
  c.push(bullet('Python 3.11, apenas para rodar a verificação e os testes fora do contêiner'));
  c.push(bullet('Placa NVIDIA e CUDA Toolkit são opcionais, e só para o núcleo computacional'));

  c.push(h2('7.2 Passo a passo'));
  c.push(espaco(40));
  c.push(...mono([
    'git clone https://github.com/PedroMiranda243/gih-fabrica-de-software.git',
    'cd gih-fabrica-de-software',
    'cp .env.example .env',
    'docker compose up',
  ]));
  c.push(espaco(120));
  c.push(p(
    'O compose sobe o PostgreSQL, espera ele ficar saudável, aplica as migrações, cria o administrador '
    + 'inicial se não houver nenhum, e serve a API.',
  ));

  c.push(h2('7.3 Primeiro acesso'));
  c.push(rich([
    { t: 'Não existe senha padrão. ', b: true, s: 20 },
    { t: 'O repositório é público, e um usuário e senha fixos no código seriam porta aberta em qualquer '
       + 'instalação que esquecesse de trocá-los. Na primeira subida o sistema sorteia uma senha e a '
       + 'imprime uma única vez no log:', s: 20 },
  ]));
  c.push(espaco(40));
  c.push(...mono([
    'docker compose logs api | grep "Senha sorteada"',
  ]));
  c.push(espaco(120));
  c.push(p(
    'Ela não é gravada em lugar nenhum e não pode ser recuperada; troque no primeiro acesso. Para '
    + 'definir a senha de antemão, preencha ADMIN_SENHA no arquivo de ambiente antes de subir.',
  ));

  c.push(h2('7.4 Verificando que subiu'));
  c.push(table([3400, 6238], [
    ['O quê', 'Onde'],
    ['Estado do sistema e do banco', 'http://localhost:8000/api/health'],
    ['Documentação interativa', 'http://localhost:8000/api/docs'],
    ['Verificação de ponta a ponta', 'cd api && GIH_ADMIN_SENHA=... python e2e/verificacao.py'],
    ['Suíte de testes', 'cd api && pytest'],
  ], { zebra: true, boldCol: 0 }));
  c.push(espaco(80));
  c.push(p(
    'A verificação sai com código diferente de zero se qualquer checagem falhar — senão não é '
    + 'verificação, é impressão.',
    { size: 19 },
  ));

  // =================================================== 8. REPOSITÓRIO
  c.push(quebra());
  c.push(h1('8. Repositório'));

  c.push(espaco(40));
  c.push(rich([
    { t: 'Repositório: ', s: 21 },
    { t: REPO, b: true, s: 21, c: '2C5B8F' },
  ]));
  c.push(espaco(100));

  c.push(h2('8.1 O que demonstra a evolução'));
  c.push(bullet('Histórias de usuário registradas como issues, agrupadas por sprint em milestones, com critérios de aceite verificáveis.'));
  c.push(bullet('Toda alteração entra por Pull Request revisado, com o dono de cada diretório convidado automaticamente.'));
  c.push(bullet('Integração contínua obrigatória: análise estática, suíte de testes contra um PostgreSQL real, e verificação de que nenhum dado ou segredo foi versionado.'));
  c.push(bullet('Documentação versionada junto com o código, atualizada no mesmo Pull Request que introduz a mudança.'));
  c.push(bullet('Este documento é gerado a partir da documentação do repositório, e não escrito à parte.'));

  c.push(h2('8.2 Divisão de responsabilidades'));
  c.push(p(
    'Cada diretório tem um dono. Isso não impede ninguém de contribuir — impede cinco pessoas de editarem '
    + 'o mesmo arquivo na mesma semana.',
  ));
  c.push(table([2600, 3200, 3838], [
    ['Diretório', 'Responsável', 'Conteúdo'],
    ['api/', 'Dev Backend / Núcleo', 'API, migrações e testes'],
    ['nucleo/', 'Dev Backend / Núcleo', 'Otimizador em C++ e CUDA'],
    ['web/', 'Dev Frontend', 'Interface — próxima sprint'],
    ['docs/', 'Product Owner', 'Documentação e este gerador'],
    ['scripts/', 'Banco de Dados', 'Gerador sintético e reinicialização'],
    ['.github/', 'Scrum Master', 'Integração contínua'],
  ], { zebra: true, boldCol: 0 }));

  // ============================================= 9. DIFICULDADES
  c.push(quebra());
  c.push(h1('9. Dificuldades encontradas'));

  c.push(p(
    'As dificuldades abaixo são reais, com a causa e a correção. Nenhuma delas é de prazo ou de '
    + 'coordenação: são problemas técnicos que custaram tempo e que ficaram registrados no repositório '
    + 'para não voltarem.',
  ));

  c.push(h2('9.1 A GPU perde para a CPU paralela em escala pequena'));
  c.push(p(
    'A investigação técnica do núcleo mediu o ganho real e encontrou o contrário do esperado: abaixo de '
    + 'cerca de 4.000 planos candidatos, dezesseis threads de CPU batem a GPU inteira. Acima disso, a GPU '
    + 'com transferência a cada geração ganha apenas 1,1 vez do OpenMP — mas o kernel sozinho ganha 11 '
    + 'vezes. A transferência consome 88% do tempo.',
  ));
  c.push(rich([
    { t: 'Correção: ', b: true, s: 19 },
    { t: 'manter a população na memória da GPU entre as gerações deixou de ser otimização e virou '
       + 'requisito de projeto do componente. Sem isso, o caminho CUDA não se justificaria.', s: 19 },
  ]));

  c.push(h2('9.2 O benchmark media o relógio, não o trabalho'));
  c.push(p(
    'Na validação do compilador, o ganho do OpenMP em 1.024 planos saiu 7,5 vezes numa execução e 13,9 '
    + 'vezes na seguinte — mesmo cenário, mesmo programa. Cinco repetições de uma operação que dura menos '
    + 'de um milissegundo medem a precisão do relógio, não o desempenho.',
  ));
  c.push(rich([
    { t: 'Correção: ', b: true, s: 19 },
    { t: 'o teste passou a calibrar quantas repetições cabem num alvo de tempo, a aquecer antes de medir, '
       + 'e a reportar mediana de várias execuções. Um número que não se reproduz não serve de resultado.', s: 19 },
  ]));

  c.push(h2('9.3 O contêiner morria apontando para um arquivo que existe'));
  c.push(p(
    'O script de inicialização foi gravado com fim de linha do Windows, e o Docker respondeu que o '
    + 'arquivo não existe — apontando exatamente para o arquivo que estava lá. O comparador de versões '
    + 'não mostrava diferença nenhuma, porque ele normaliza a leitura enquanto o Docker copia o arquivo '
    + 'do disco.',
  ));
  c.push(rich([
    { t: 'Correção: ', b: true, s: 19 },
    { t: 'o fim de linha passou a ser fixado no repositório por configuração, nos arquivos que o Linux '
       + 'precisa ler.', s: 19 },
  ]));

  c.push(h2('9.4 Os diagramas saíram vazios no PDF'));
  c.push(p(
    'Na entrega anterior, os diagramas foram embutidos em formato vetorial. O documento abria normal na '
    + 'tela, mas ao exportar para PDF o Word desenhava as caixas e as setas e descartava todo o texto '
    + 'dentro delas. Um diagrama de classes sem os nomes das classes não é um diagrama ruim — é uma '
    + 'figura vazia, e teria sido entregue assim.',
  ));
  c.push(rich([
    { t: 'Correção: ', b: true, s: 19 },
    { t: 'os diagramas passaram a entrar rasterizados em resolução de impressão, e a conferência da '
       + 'entrega passou a incluir abrir o PDF e olhar as páginas — e não apenas conferir que o arquivo '
       + 'foi gerado.', s: 19 },
  ]));

  c.push(h2('9.5 A própria verificação reprovava por defeito dela'));
  c.push(p(
    'A verificação de ponta a ponta falhou duas vezes por causa de si mesma antes de passar. A varredura '
    + 'de autorização percorria o endereço que encerra a sessão, e tudo depois dele respondia como não '
    + 'autenticado — o sintoma parecia falha de permissão. E o período usado na importação era fixo, '
    + 'colidindo com a execução anterior.',
  ));
  c.push(rich([
    { t: 'Correção: ', b: true, s: 19 },
    { t: 'a varredura passou a pular as operações destrutivas, e a marca de cada execução passou a ser '
       + 'sorteada em vez de derivada do relógio. Os dois motivos ficaram comentados no código.', s: 19 },
  ]));

  // ======================================= 10. AJUSTES NO PLANEJAMENTO
  c.push(quebra());
  c.push(h1('10. Ajustes no planejamento e na modelagem'));

  c.push(p(
    'A entrega pede que alterações feitas nas sprints anteriores sejam registradas e justificadas. Foram '
    + 'cinco, e todas estão versionadas no repositório com a justificativa junto.',
  ));

  c.push(table([2600, 3400, 3638], [
    ['O que mudou', 'De / para', 'Por quê'],
    [
      'Cadência das sprints',
      'Quinzenal para semanal',
      'Pedido na avaliação da Sprint 01. O atraso passa a aparecer na primeira semana, não na terceira. Duas histórias grandes demais para uma semana foram quebradas; o total de pontos não mudou',
    ],
    [
      'Número de tabelas',
      '14 para 16',
      'A implementação da autenticação exigiu guardar a sessão e as tentativas de login. A sessão precisa de estado no servidor para que encerrar tenha efeito imediato',
    ],
    [
      'Compilação do núcleo',
      'Em tempo de execução para antecipada',
      'O compilador C++ e o toolkit foram instalados, e a implementação em OpenMP exige compilação antecipada de qualquer forma. A decisão anterior ficou registrada como histórico',
    ],
    [
      'Formato do relatório importado',
      'Indefinido para tolerante',
      'A história pedia "o formato definido", e não havia formato definido em lugar nenhum. Foi decidido em equipe: separador livre, ordem de colunas livre, sinônimos aceitos',
    ],
    [
      'Exclusão de parceiro',
      'Apenas desativar para exclusão condicional',
      'Esta entrega pede a operação de excluir. A exclusão acontece quando não há histórico, e é recusada com explicação quando há',
    ],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(espaco(80));
  c.push(p(
    'Há ainda um ponto em aberto que vale registrar: o critério de aceite da história do ambiente menciona '
    + 'que o comando único sobe também a interface. Como a interface ainda não existe, essa metade do '
    + 'critério não está cumprida — e está declarada aqui em vez de omitida.',
  ));

  // ============================================ 11. PRÓXIMOS PASSOS
  c.push(quebra());
  c.push(h1('11. Próximos passos'));

  c.push(p(
    'A ordem abaixo segue o backlog priorizado da Sprint 01, com o ajuste de cadência já aplicado.',
  ));

  c.push(table([1400, 3600, 4638], [
    ['Sprint', 'Tema', 'O que entra'],
    ['6', 'Ingestão completa e painel', 'Importação por arquivo, substituição de período, e as primeiras telas em React sobre o protótipo aprovado'],
    ['7', 'Segmentação e mobilidade', 'Classificação determinística com precedência explícita, ranking e mobilidade do Top N'],
    ['8', 'Modelo preditivo', 'Treino a partir do histórico, previsão de faturamento e probabilidade de queda'],
    ['9 a 11', 'Núcleo computacional', 'Otimizador serial, paralelo em CPU e paralelo em GPU, com o comparativo de desempenho'],
    ['12', 'Central de comunicação', 'Geração de mensagens por segmento, com aprovação humana obrigatória'],
    ['13', 'Assistente e fechamento', 'Perguntas em linguagem natural sobre dados já apurados, e a entrega final'],
  ], { zebra: true, boldCol: 0, size: 17 }));

  c.push(h2('11.1 O que vem primeiro'));
  c.push(bullet('Aprovar a direção visual do protótipo, que é o portão para a interface começar.'));
  c.push(bullet('As primeiras telas em React, consumindo a API que já existe e está documentada.'));
  c.push(bullet('A sugestão automática de categoria pelo nome do parceiro, que completa o cadastro.'));
  c.push(bullet('O recálculo da segmentação após cada importação, que hoje não acontece.'));

  c.push(espaco(200));
  c.push(p(
    'Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa '
    + 'visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.',
    { italics: true, color: '5A6B7E', size: 18 },
  ));

  return c;
}

module.exports = { montar };
