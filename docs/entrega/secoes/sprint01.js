/**
 * Parte I do documento — Sprint 01 acadêmica: planejamento e descoberta.
 *
 * Conteúdo entregue em 05/09/2026, preservado como foi avaliado. A professora
 * pede o PDF acumulado, com todas as sprints anteriores e a atual.
 */
const path = require('path');
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, PageBreak, Footer, PageNumber, convertMillimetersToTwip,
} = require('docx');
const {
  CW, AZUL, CINZA, VERDE,
  p, rich, h1, h2, h3, bullet, cell, table, espaco, quebra,
} = require('../comum/estilos');

const DIAGRAMAS = path.join(__dirname, '..', 'diagramas');

const TURMA = 'CC8MB';

// Ordem alfabética por nome.
const EQUIPE = [
  ['Ingryd Vitoria de Araújo Barbosa', '01642893', 'ingrydaraujob', 'Desenvolvedora Frontend'],
  ['João Pedro Nunes de França', '01626444', 'joaopfranca04', 'Banco de Dados, Documentação e Testes'],
  ['Marcio Maycom', '01607574', 'mihaeldatoman', 'Product Owner'],
  ['Pedro Miranda', '01607408', 'PedroMiranda243', 'Dev. Backend / Núcleo Computacional'],
  ['Thiago José Falcão de Freitas', '01597267', 'ThiagojFalcao', 'Scrum Master'],
];

const RF = {
  'Módulo 1 — Autenticação, perfis e auditoria': [
    ['RF01', 'Autenticar o usuário por login e senha, criando uma sessão identificada.', 'M', 'todos'],
    ['RF02', 'Permitir o encerramento da sessão, invalidando-a no servidor.', 'M', 'todos'],
    ['RF03', 'Permitir cadastrar, editar, desativar e listar usuários.', 'M', 'ADM'],
    ['RF04', 'Atribuir a cada usuário exatamente um perfil entre Administrador, Gestor, Analista e Parceiro.', 'M', 'ADM'],
    ['RF05', 'Restringir o acesso a cada funcionalidade conforme o perfil, validando a permissão no servidor a cada requisição.', 'M', 'todos'],
    ['RF06', 'Registrar em trilha de auditoria as ações sensíveis, com autor, data, hora e parâmetros.', 'M', 'todos'],
    ['RF07', 'Permitir que o usuário altere a própria senha, exigindo a senha atual.', 'S', 'todos'],
    ['RF08', 'Permitir consultar a trilha de auditoria, com filtro por autor, tipo de ação e datas.', 'S', 'ADM'],
  ],
  'Módulo 2 — Ingestão e gestão de dados': [
    ['RF09', 'Importar um relatório de desempenho por período, aceitando texto colado e arquivo CSV.', 'M', 'GES, ANL'],
    ['RF10', 'Exigir a data inicial e final do período na importação e recusar a importação sem esse dado.', 'M', 'GES, ANL'],
    ['RF11', 'Validar o conteúdo e exibir prévia com registros reconhecidos, rejeitados e o motivo, antes de gravar.', 'M', 'GES, ANL'],
    ['RF12', 'Impedir a importação de um período já registrado, oferecendo opção explícita de substituição.', 'S', 'GES, ANL'],
    ['RF13', 'Manter o histórico das importações com autor, data, período coberto e total de registros.', 'M', 'GES, ANL, ADM'],
    ['RF14', 'Cadastrar, editar e desativar parceiros, com nome, categoria, status comercial e contato.', 'M', 'GES, ANL'],
    ['RF15', 'Sugerir a categoria do parceiro pelo nome, sinalizando que é sugestão e exigindo confirmação.', 'S', 'GES, ANL'],
    ['RF16', 'Oferecer gerador de dados sintéticos de 100 a 10.000 parceiros, para demonstração e benchmark.', 'M', 'ADM'],
  ],
  'Módulo 3 — Inteligência de negócio e segmentação': [
    ['RF17', 'Exibir painel com indicadores consolidados do período e a variação frente ao período anterior.', 'M', 'GES, ANL'],
    ['RF18', 'Exibir ranking por faturamento, com posição atual, posição anterior e variação percentual.', 'M', 'GES, ANL'],
    ['RF19', 'Exibir a série histórica em gráfico, para a unidade e para o parceiro individual.', 'M', 'GES, ANL, PAR'],
    ['RF20', 'Classificar cada parceiro em exatamente um segmento, por regra determinística com precedência explícita.', 'M', 'GES, ANL'],
    ['RF21', 'Permitir configurar os limiares da segmentação sem alteração de código.', 'S', 'ADM'],
    ['RF22', 'Exibir a mobilidade do ranking entre dois períodos, listando quem entrou e quem saiu do Top N.', 'M', 'GES, ANL'],
    ['RF23', 'Permitir filtrar e ordenar a lista de parceiros por categoria, segmento e métricas.', 'M', 'GES, ANL'],
    ['RF24', 'Permitir buscar parceiro por nome, com correspondência parcial.', 'M', 'GES, ANL'],
    ['RF25', 'Permitir exportar em CSV a visão atualmente filtrada.', 'S', 'GES, ANL'],
    ['RF26', 'Permitir que o perfil Parceiro consulte apenas o próprio desempenho, sem acesso a terceiros.', 'C', 'PAR'],
  ],
  'Módulo 4 — Núcleo computacional: previsão e otimização': [
    ['RF27', 'Treinar modelo de previsão a partir do histórico, registrando data, volume de dados e métricas.', 'M', 'ADM, GES'],
    ['RF28', 'Exibir, por parceiro, o faturamento previsto e a probabilidade estimada de queda.', 'M', 'GES, ANL'],
    ['RF29', 'Permitir configurar orçamento, número máximo de ações, catálogo com custos e cotas por categoria.', 'M', 'GES'],
    ['RF30', 'Executar o otimizador e retornar o plano de campanha, com uplift esperado e custo total.', 'M', 'GES'],
    ['RF31', 'Garantir que todo plano respeite as restrições e sinalizar quando não existir solução viável.', 'M', 'GES'],
    ['RF32', 'Permitir escolher o modo de execução entre serial, CPU paralelo e GPU, com seleção automática.', 'M', 'GES, ADM'],
    ['RF33', 'Exibir benchmark comparativo entre os modos: tempo, speedup e qualidade da solução.', 'M', 'GES, ADM'],
    ['RF34', 'Registrar o histórico das execuções do otimizador com parâmetros, modo, tempo e resultado.', 'S', 'GES, ADM'],
    ['RF35', 'Permitir comparar lado a lado dois planos de campanha gerados com parâmetros diferentes.', 'C', 'GES'],
  ],
  'Módulo 5 — Central de comunicação': [
    ['RF36', 'Gerar mensagens personalizadas por segmento e categoria, a partir do plano ou de seleção manual.', 'M', 'GES, ANL'],
    ['RF37', 'Manter as mensagens geradas em fila de aprovação, no estado pendente.', 'M', 'GES, ANL'],
    ['RF38', 'Permitir aprovar, editar ou rejeitar cada mensagem antes de considerá-la pronta para envio.', 'M', 'GES'],
    ['RF39', 'Impedir que qualquer mensagem seja aprovada sem ação explícita de um usuário com perfil Gestor.', 'M', 'GES'],
    ['RF40', 'Manter o histórico das mensagens decididas, com autor, data e conteúdo final.', 'S', 'GES, ANL'],
  ],
  'Módulo 6 — Assistente analítico': [
    ['RF41', 'Responder a perguntas em linguagem natural sobre os dados armazenados.', 'S', 'GES, ANL'],
    ['RF42', 'Citar o período e a origem dos dados em toda resposta, ou declarar insuficiência de dados.', 'M', 'GES, ANL'],
    ['RF43', 'Impedir que o assistente produza valores numéricos não calculados pelo núcleo determinístico.', 'M', 'GES, ANL'],
  ],
};

const RNF = {
  'Desempenho e escalabilidade': [
    ['RNF01', 'O otimizador em GPU resolve o cenário de referência (2.000 parceiros, 5 ações) em uso interativo.', 'Até 5 s de ponta a ponta'],
    ['RNF02', 'O otimizador em GPU apresenta ganho sobre o baseline serial, com qualidade equivalente.', 'Speedup mínimo de 5x, uplift dentro de 2% do baseline'],
    ['RNF03', 'O painel responde dentro do limiar de fluidez para bases realistas.', 'Até 2 s com 5.000 parceiros'],
    ['RNF04', 'O sistema suporta a carga máxima prevista sem degradação funcional.', '10.000 parceiros e 52 períodos'],
    ['RNF05', 'As consultas ao histórico usam índices, evitando varredura completa.', 'Plano sem varredura sequencial'],
  ],
  'Portabilidade e disponibilidade': [
    ['RNF06', 'O sistema funciona sem GPU compatível, recorrendo ao modo CPU paralelo.', 'Fluxo completo executado sem GPU, com aviso'],
    ['RNF07', 'O ambiente sobe com um único comando, sem etapa manual.', 'docker compose up a partir de clone limpo'],
    ['RNF08', 'O sistema funciona nos navegadores de maior uso.', 'Chrome, Edge e Firefox, duas versões recentes'],
  ],
  'Segurança': [
    ['RNF09', 'Senhas armazenadas apenas como hash com derivação lenta e sal por usuário.', 'bcrypt ou Argon2; nenhuma senha em claro'],
    ['RNF10', 'Sessão em cookie HttpOnly e SameSite, com renovação do identificador no login.', 'Verificado por teste automatizado'],
    ['RNF11', 'Bloqueio temporário após falhas sucessivas; resposta idêntica para usuário inexistente e senha errada.', 'Bloqueio após 5 falhas'],
    ['RNF12', 'Toda saída originada do usuário ou do modelo é escapada antes de chegar ao navegador.', 'Teste com carga de injeção de script'],
    ['RNF13', 'Todo acesso ao banco usa consultas parametrizadas.', 'Revisão de código e teste de injeção SQL'],
    ['RNF14', 'A autorização por perfil é verificada no servidor em todos os endpoints.', 'Teste de cada endpoint com cada perfil'],
    ['RNF15', 'O sistema limita o tamanho das entradas aceitas.', 'Limite para relatório e para pergunta'],
  ],
  'Confiabilidade e rastreabilidade': [
    ['RNF16', 'Ranking, segmentação e métricas são determinísticos; o modelo de linguagem não calcula número.', 'Reprocessar produz resultado idêntico'],
    ['RNF17', 'Toda resposta do assistente cita a origem ou declara insuficiência de dados.', 'Conjunto de perguntas de teste'],
    ['RNF18', 'Erros retornam mensagem genérica; o detalhe fica no log do servidor.', 'Nenhum rastreamento de pilha na resposta'],
    ['RNF19', 'Log estruturado com identificador de correlação entre resposta e evento.', 'Identificador presente em ambos'],
  ],
  'Usabilidade e acessibilidade': [
    ['RNF20', 'Interface integralmente em português e operável sem treinamento formal.', 'Usuário novo completa o fluxo sem documentação'],
    ['RNF21', 'Interface responsiva para desktop e tablet.', 'Layout funcional a partir de 768 px'],
    ['RNF22', 'Texto atende ao contraste mínimo do nível AA.', 'Razão mínima de 4,5:1'],
    ['RNF23', 'Operações longas informam progresso.', 'Indicador em importação e otimização'],
  ],
  'Manutenibilidade e processo': [
    ['RNF24', 'O núcleo de regras tem cobertura de testes automatizados adequada.', 'Cobertura mínima de 70%'],
    ['RNF25', 'Toda alteração chega ao ramo principal por Pull Request revisado.', 'Proteção ativa; nenhum push direto'],
    ['RNF26', 'A integração contínua executa análise estática e testes a cada Pull Request.', 'CI obrigatória e verde antes da mesclagem'],
    ['RNF27', 'A documentação permite a um terceiro executar o sistema do zero.', 'Validado por integrante que não escreveu o código'],
  ],
  'Privacidade': [
    ['RNF28', 'O sistema não coleta dados pessoais de consumidores finais.', 'Modelo sem entidade de consumidor final'],
    ['RNF29', 'O repositório não contém dados reais; toda massa é sintética.', 'Verificação antes de cada entrega'],
  ],
};

const BACKLOG = [
  ['E1', 'Fundação, planejamento e ambiente', '47', '1–3'],
  ['E2', 'Autenticação, perfis e auditoria', '39', '4–5'],
  ['E3', 'Ingestão e modelo de dados', '46', '2–6'],
  ['E4', 'Inteligência de negócio e segmentação', '47', '6–9'],
  ['E5', 'Núcleo preditivo', '34', '8–9'],
  ['E6', 'Otimização, paralelismo e GPU', '82', '3–11'],
  ['E7', 'Central de comunicação', '26', '12'],
  ['E8', 'Assistente analítico', '21', '12–13'],
  ['E9', 'Qualidade, documentação e entrega', '47', '2–13'],
  ['', 'Total', '389', ''],
];

const HIST = [
  ['H01', 'Definir tema, problema e objetivos', 'E1', 'M', '5', '1'],
  ['H02', 'Levantar requisitos funcionais e não funcionais', 'E1', 'M', '8', '1'],
  ['H03', 'Modelar os casos de uso', 'E1', 'M', '5', '1'],
  ['H04', 'Priorizar o product backlog', 'E1', 'M', '3', '1'],
  ['H05', 'Construir o cronograma até 05/12', 'E1', 'M', '3', '1'],
  ['H06', 'Configurar o repositório GitHub', 'E1', 'M', '3', '1'],
  ['H07', 'Modelar o banco (entidade-relacionamento)', 'E1', 'M', '8', '2'],
  ['H08', 'Prototipar as telas principais', 'E1', 'M', '5', '3'],
  ['H09', 'Subir o ambiente com um comando', 'E1', 'M', '5', '2'],
  ['H10', 'Configurar integração contínua', 'E1', 'M', '2', '2'],
  ['H11', 'Autenticar com login e senha', 'E2', 'M', '5', '4'],
  ['H12', 'Encerrar a sessão', 'E2', 'M', '2', '4'],
  ['H13', 'Renovar o identificador de sessão no login', 'E2', 'M', '3', '4'],
  ['H14', 'Bloquear tentativas repetidas de login', 'E2', 'M', '3', '4'],
  ['H15', 'Cadastrar e editar usuários', 'E2', 'M', '5', '4'],
  ['H16', 'Atribuir perfis de acesso', 'E2', 'M', '5', '4'],
  ['H17', 'Validar permissão no servidor a cada requisição', 'E2', 'M', '8', '5'],
  ['H18', 'Consultar a trilha de auditoria', 'E2', 'S', '5', '4'],
  ['H19', 'Alterar a própria senha', 'E2', 'S', '3', '4'],
  ['H20', 'Versionar o esquema do banco por migrações', 'E3', 'M', '5', '2'],
  ['H21', 'Importar relatório colando o texto', 'E3', 'M', '8', '5'],
  ['H22', 'Importar relatório por arquivo CSV', 'E3', 'M', '3', '6'],
  ['H23', 'Recusar importação sem período informado', 'E3', 'M', '3', '5'],
  ['H24', 'Ver prévia antes de gravar', 'E3', 'M', '5', '5'],
  ['H25', 'Alertar ao reimportar período existente', 'E3', 'S', '3', '6'],
  ['H26', 'Cadastrar e editar parceiros', 'E3', 'M', '5', '3'],
  ['H27', 'Sugerir categoria pelo nome', 'E3', 'S', '5', '3'],
  ['H28', 'Construir o gerador de dados sintéticos', 'E3', 'M', '5', '3'],
  ['H29', 'Consultar o histórico de importações', 'E3', 'M', '2', '6'],
  ['H77', 'Comando para limpar e repovoar o banco', 'E3', 'M', '2', '3'],
  ['H30', 'Ver indicadores consolidados do período', 'E4', 'M', '5', '6'],
  ['H31', 'Ver ranking com variação de posição', 'E4', 'M', '5', '6'],
  ['H32', 'Ver a série histórica em gráfico', 'E4', 'M', '5', '6'],
  ['H33', 'Segmentar por regra determinística', 'E4', 'M', '8', '7'],
  ['H34', 'Configurar os limiares da segmentação', 'E4', 'S', '3', '7'],
  ['H35', 'Ver quem entrou e saiu do Top N', 'E4', 'M', '5', '7'],
  ['H36', 'Filtrar e ordenar a lista de parceiros', 'E4', 'M', '5', '7'],
  ['H37', 'Buscar parceiro por nome', 'E4', 'M', '2', '6'],
  ['H38', 'Exportar a visão filtrada em CSV', 'E4', 'S', '3', '7'],
  ['H39', 'Consultar o próprio desempenho (parceiro)', 'E4', 'C', '3', '9'],
  ['H40', 'Painel rápido mesmo com base grande', 'E4', 'M', '3', '6'],
  ['H41', 'Definir e extrair as variáveis preditivas', 'E5', 'M', '8', '8'],
  ['H42', 'Treinar o modelo de previsão', 'E5', 'M', '8', '8'],
  ['H43', 'Estimar a probabilidade de queda', 'E5', 'M', '5', '8'],
  ['H44', 'Ver previsão e risco na tela do parceiro', 'E5', 'M', '5', '8'],
  ['H45', 'Disparar o retreino do modelo', 'E5', 'S', '5', '9'],
  ['H46', 'Comparar o modelo com baselines estatísticos', 'E5', 'M', '3', '8'],
  ['H47', 'Validar a cadeia de compilação da GPU (spike)', 'E6', 'M', '5', '3'],
  ['H48', 'Formalizar o problema de otimização', 'E6', 'M', '5', '9'],
  ['H49', 'Implementar o otimizador serial (baseline)', 'E6', 'M', '8', '9'],
  ['H50', 'Configurar as restrições da campanha', 'E6', 'M', '5', '9'],
  ['H51', 'Executar o otimizador e receber o plano', 'E6', 'M', '8', '10'],
  ['H52', 'Recusar planos inviáveis', 'E6', 'M', '3', '9'],
  ['H53a', 'Portar o otimizador para C++', 'E6', 'M', '8', '10'],
  ['H53b', 'Paralelizar as partidas com OpenMP', 'E6', 'M', '5', '10'],
  ['H54a', 'Estruturas na GPU e transferência host-device', 'E6', 'M', '5', '11'],
  ['H54b', 'Kernel CUDA de avaliação da população', 'E6', 'M', '5', '11'],
  ['H54c', 'Laço completo do otimizador na GPU', 'E6', 'M', '3', '11'],
  ['H55', 'Escolher o modo de execução', 'E6', 'M', '3', '10'],
  ['H56', 'Cair para CPU quando não houver GPU', 'E6', 'M', '3', '10'],
  ['H57', 'Ver o benchmark comparativo na interface', 'E6', 'M', '8', '11'],
  ['H58', 'Consultar o histórico de execuções', 'E6', 'S', '3', '10'],
  ['H59', 'Comparar dois planos lado a lado', 'E6', 'C', '5', '11'],
  ['H60', 'Gerar mensagens por segmento e categoria', 'E7', 'M', '8', '12'],
  ['H61', 'Manter fila de mensagens pendentes', 'E7', 'M', '5', '12'],
  ['H62', 'Aprovar, editar ou rejeitar mensagem', 'E7', 'M', '5', '12'],
  ['H63', 'Impedir aprovação sem ação humana', 'E7', 'M', '5', '12'],
  ['H64', 'Consultar histórico de mensagens decididas', 'E7', 'S', '3', '12'],
  ['H65', 'Perguntar sobre os dados em linguagem natural', 'E8', 'S', '8', '13'],
  ['H66', 'Resposta citando o período usado', 'E8', 'M', '5', '13'],
  ['H67', 'Impedir que o modelo produza números próprios', 'E8', 'M', '5', '13'],
  ['H68', 'Assistente admite quando não sabe', 'E8', 'M', '3', '12'],
  ['H69', 'Testes automatizados no núcleo de regras', 'E9', 'M', '8', '7'],
  ['H70', 'Testes de segurança automatizados', 'E9', 'M', '5', '11'],
  ['H71', 'Exigir Pull Request revisado em main', 'E9', 'M', '2', '2'],
  ['H78', 'Teste de ponta a ponta contra a API no ar', 'E9', 'M', '5', '5'],
  ['H72', 'Subir o sistema seguindo apenas o README', 'E9', 'M', '5', '13'],
  ['H73', 'Documentação técnica final consolidada', 'E9', 'M', '5', '13'],
  ['H74', 'Produzir o vídeo horizontal (até 10 min, 16:9)', 'E9', 'M', '8', '13'],
  ['H75', 'Produzir o vídeo vertical (9:16)', 'E9', 'M', '5', '13'],
  ['H76', 'Validar acessibilidade e responsividade', 'E9', 'S', '4', '13'],
];


function montar() {
  const children = [];


  // A capa e o sumario originais desta sprint ficaram de fora: o documento
  // acumulado tem uma capa so, montada em gerar.js. Mantidos aqui, apareciam
  // duplicados no meio do PDF.

// ===== 1. EQUIPE =====
children.push(h1('1. Identificação da equipe'));
children.push(table([2800, 6838], [
  ['Nome do projeto', 'Growth Intelligence Hub (GIH)'],
  ['Turma', TURMA],
  ['Disciplinas', 'Fábrica de Software · Tópicos Avançados'],
  ['Repositório', 'github.com/PedroMiranda243/gih-fabrica-de-software'],
], { boldCol: 0 }));
children.push(espaco(200));
children.push(p('Integrantes', { bold: true, size: 21 }));
children.push(p('Equipe de 5 integrantes, dentro do limite de 3 a 5 estabelecido pela disciplina. Os papéis organizam o trabalho, mas todos os integrantes contribuem com código e aparecem no histórico de commits do repositório.'));
children.push(table([3200, 1500, 2100, 2838], [
  ['Integrante', 'Matrícula', 'GitHub', 'Papel'],
  ...EQUIPE.map(([nome, mat, gh, papel]) => [nome, mat, '@' + gh, papel]),
], { boldCol: 0, zebra: true, align: [undefined, AlignmentType.CENTER, undefined, undefined] }));
children.push(espaco(200));
children.push(p('Papéis previstos e responsabilidades', { bold: true, size: 21 }));
children.push(table([3400, 6238], [
  ['Papel', 'Responsabilidade principal'],
  ['Scrum Master', 'Cerimônias, board e acompanhamento das entregas'],
  ['Product Owner', 'Backlog, requisitos, priorização e critérios de aceite'],
  ['Dev. Backend / Núcleo Computacional', 'API, regras de negócio, otimizador C++/CUDA e modelo preditivo'],
  ['Desenvolvedor Frontend', 'Telas, painel, gráficos, responsividade e acessibilidade'],
  ['Banco de Dados, Documentação e Testes', 'Modelagem, migrações, suíte de testes e documentação'],
], { boldCol: 0, zebra: true }));
children.push(espaco(160));
children.push(p('Os papéis organizam o trabalho; todos os integrantes contribuem com código e aparecem no histórico de commits. As histórias do núcleo em OpenMP e CUDA exigem programação em par, para que ninguém seja a única pessoa a entender o motor do projeto.', { italics: true, color: '5A6B7E' }));
children.push(quebra());

// ===== 2. TEMA =====
children.push(h1('2. Tema'));
children.push(p('Growth Intelligence Hub (GIH) — plataforma de inteligência de crescimento para redes de parceiros em marketplaces regionais de delivery.', { bold: true, size: 22 }));
children.push(p('O sistema recebe os relatórios periódicos de desempenho de uma rede de comércios parceiros e devolve decisões priorizadas: quem está crescendo, quem está prestes a cair, e — dado um orçamento e uma equipe limitados — exatamente em quais parceiros investir a próxima rodada de ações comerciais.'));
children.push(h2('Domínio de aplicação'));
children.push(p('Marketplaces regionais de delivery operam por franquia ou licença local. Uma unidade típica intermedeia pedidos entre consumidores de uma cidade ou microrregião e uma rede de 50 a 500 comércios parceiros. A unidade recebe da plataforma nacional um relatório periódico com o desempenho de cada parceiro, e é responsável por desenvolver comercialmente essa base.'));
children.push(h2('Por que este tema atende aos critérios da disciplina'));
children.push(table([3000, 6638], [
  ['Critério', 'Como o tema atende'],
  ['Resolver um problema real', 'Redes regionais gerenciam a base comercial sem qualquer ferramenta analítica'],
  ['Complexidade compatível com um TCC', 'Ingestão, modelagem temporal, regras de segmentação, aprendizado de máquina, otimização combinatória, paralelismo, GPU, controle de acesso e auditoria'],
  ['Permitir evolução no semestre', 'Sete sprints com entregas independentes, cumulativas e executáveis'],
  ['Ser viável no prazo', 'Escopo fatiado por módulo; o núcleo pesado tem investigação técnica antecipada para a Sprint 3'],
  ['Funcionalidades suficientes', '43 requisitos funcionais em 6 módulos integrados'],
  ['Componente de IA/otimização não decorativo', 'O motor de decisão é o produto — sem ele o sistema vira um painel passivo'],
], { boldCol: 0, zebra: true }));
children.push(quebra());

// ===== 3. PROBLEMA =====
children.push(h1('3. Definição do problema'));
children.push(h2('3.1 A situação'));
children.push(p('Numa operação regional de delivery, a atenção comercial se concentra nos parceiros de maior faturamento — o Top 15. É uma escolha racional a curto prazo: são eles que sustentam a receita. Mas produz três efeitos que se realimentam:'));
children.push(bullet('Os parceiros fora do topo — a cauda longa, tipicamente 85% da base — passam meses sem contato.'));
children.push(bullet('Sem estímulo, a cauda longa não cresce, e o ranking permanece imóvel: os mesmos nomes no topo, período após período.'));
children.push(bullet('Como o topo é sempre o mesmo, ele também não é desafiado — e estagna.'));
children.push(p('Ao mesmo tempo, os dados chegam em formato que não sustenta análise. O painel da plataforma mostra o número do período atual em texto corrido. Não há série histórica, não há comparação automática com o período anterior, não há alerta. O gestor vê o retrato, nunca o filme.'));
children.push(h2('3.2 Os sub-problemas'));
children.push(table([900, 3900, 4838], [
  ['ID', 'Sub-problema', 'Consequência operacional'],
  ['P1', 'Dados sem visualização analítica', 'Tendências passam despercebidas; a leitura depende de esforço manual repetido a cada período'],
  ['P2', 'Queda de parceiro detectada tarde', 'Quando a perda fica evidente no faturamento, o parceiro já pode ter migrado ou reduzido a operação'],
  ['P3', 'Cauda longa sem processo de relacionamento', 'Ranking imóvel; potencial de crescimento não explorado em cerca de 85% da base'],
  ['P4', 'Alocação do esforço comercial decidida por intuição', 'Verba de cupom e agenda da equipe são distribuídas sem critério explícito nem verificação de retorno'],
  ['P5', 'Comunicação manual e sem segmentação', 'Ações por categoria exigem esforço proporcional ao número de parceiros, e por isso não acontecem'],
], { boldCol: 0, zebra: true }));
children.push(h2('3.3 O problema central'));
children.push(rich([{ t: 'P4 é o núcleo técnico do projeto.', b: true, s: 22 }]));
children.push(p('Escolher em quais parceiros aplicar quais ações, respeitando orçamento, capacidade da equipe e cotas por categoria, para maximizar o retorno esperado, é um problema de otimização combinatória com restrições.'));
children.push(p('O espaço de busca cresce exponencialmente: com N parceiros e A tipos de ação, existem (A+1)^N planos possíveis. Para 200 parceiros e 4 tipos de ação, isso já ultrapassa 10^139 combinações — inviável por força bruta e igualmente inviável de resolver "no olho".'));
children.push(p('É exatamente o tipo de problema que justifica metaheurística paralelizada e aceleração em GPU — e é a ponte entre as duas disciplinas: a Fábrica de Software entrega o produto completo em torno dele, Tópicos Avançados entrega o motor.'));
children.push(h2('3.4 Por que este problema é relevante'));
children.push(rich([{ t: 'Para a operação. ', b: true }, { t: 'A cauda longa concentra a maior parte do potencial de crescimento não explorado: são 85% dos parceiros recebendo uma fração da atenção comercial. Um parceiro que sai da base não é apenas receita perdida — é um comércio que passa a operar só no concorrente, e reconquistá-lo custa muito mais do que teria custado mantê-lo. O alerta que chega um período antes é a diferença entre uma conversa de retenção e uma perda consumada.' }]));
children.push(rich([{ t: 'Para os parceiros. ', b: true }, { t: 'São comércios pequenos, quase sempre sem estrutura de marketing. Entrar numa campanha bem escolhida é acesso a demanda que não conseguiriam gerar sozinhos. Quando a alocação é feita por intuição, quem já é grande recebe mais, e a assimetria se aprofunda sozinha.' }]));
children.push(rich([{ t: 'Para a decisão. ', b: true }, { t: 'Verba de incentivo e agenda da equipe são recursos escassos e disputados. Hoje a escolha é feita sem critério explícito e, principalmente, sem verificação posterior: não se sabe se a campanha da semana passada funcionou, porque nada foi medido contra uma previsão. Sem linha de base não existe aprendizado, apenas repetição.' }]));
children.push(rich([{ t: 'Para o campo técnico. ', b: true }, { t: 'O problema não é uma desculpa para usar tecnologia; ele exige a tecnologia. Priorizar ações sob restrições de orçamento, capacidade e cotas é otimização combinatória, e estimar o retorno de cada ação é um problema de previsão. São duas classes de problema com solução conhecida e mensurável, o que permite avaliar objetivamente se a solução funcionou, comparando speedup e erro de previsão contra baselines, em vez de opinar sobre a interface.' }]));
children.push(h2('3.5 O que já se sabe que não resolve'));
children.push(table([2600, 7038], [
  ['Alternativa', 'Por que não basta'],
  ['Planilha', 'Não sustenta série histórica multi-período de centenas de parceiros, nem otimização com restrições'],
  ['Assistente de IA genérico', 'Responde sobre os dados colados, mas sem rastreabilidade, sem persistência, sem painel e sem garantia de consistência numérica entre duas perguntas iguais'],
  ['BI genérico', 'Mostra o passado. Não prevê, não otimiza e não fecha o ciclo até a ação'],
  ['Ampliar a equipe comercial', 'Custo recorrente; não resolve o critério de priorização, apenas aumenta o volume de contatos feitos sem critério'],
], { boldCol: 0, zebra: true }));
children.push(quebra());

// ===== 4. OBJETIVOS =====
children.push(h1('4. Objetivos do sistema'));
children.push(h2('4.1 Objetivo geral'));
children.push(p('Transformar os dados brutos de desempenho de uma rede de parceiros em um plano de ação comercial priorizado, previsto por modelo treinado a partir do histórico e otimizado sob as restrições reais de orçamento e capacidade da operação.', { bold: true }));
children.push(h2('4.2 Objetivos específicos'));
children.push(table([800, 4200, 4638], [
  ['ID', 'Objetivo', 'Verificação'],
  ['O1', 'Ingerir e normalizar relatórios periódicos por parceiro', 'Importação de 500 parceiros gera 500 registros consistentes, com período obrigatório'],
  ['O2', 'Calcular métricas derivadas e séries históricas', 'Ticket médio, variação e tendência disponíveis para qualquer parceiro com 2 ou mais períodos'],
  ['O3', 'Segmentar automaticamente por regra determinística', 'A mesma base reprocessada produz exatamente a mesma segmentação'],
  ['O4', 'Prever faturamento e risco de queda com modelo próprio', 'MAPE inferior ao de um baseline ingênuo em conjunto de teste separado'],
  ['O5', 'Otimizar a alocação de ações sob restrições', 'O plano respeita 100% das restrições e supera a heurística "investir nos maiores"'],
  ['O6', 'Acelerar o otimizador por paralelismo em CPU e GPU', 'Speedup mínimo de 5x em GPU, com qualidade de solução equivalente'],
  ['O7', 'Gerar mensagens com aprovação humana obrigatória', 'Nenhuma mensagem é aprovada sem ação explícita de usuário autorizado'],
  ['O8', 'Controlar acesso por perfil, com trilha de auditoria', 'Toda ação sensível registra autor, data e parâmetros'],
], { boldCol: 0, zebra: true }));
children.push(h2('4.3 Indicadores de sucesso'));
children.push(h3('Do produto'));
children.push(table([2600, 4400, 2638], [
  ['Indicador', 'Definição', 'Meta'],
  ['Mobilidade do Top N', 'Parceiros que entram ou saem do Top 15 entre dois períodos', 'Tornar visível e crescente'],
  ['Cobertura de relacionamento', 'Percentual da base que recebeu ao menos uma ação no período', 'Cobertura planejada'],
  ['Antecedência do alerta de risco', 'Períodos de antecedência do sinal antes da queda se confirmar', 'Mínimo de 1 período'],
], { boldCol: 0, zebra: true }));
children.push(espaco(140));
children.push(h3('Técnicos'));
children.push(table([6000, 3638], [
  ['Indicador', 'Meta'],
  ['Speedup do otimizador (GPU sobre serial)', 'Mínimo de 5x no cenário de referência'],
  ['Tempo de resposta do otimizador em GPU', 'Até 5 s no cenário de referência'],
  ['MAPE do modelo preditivo', 'Inferior ao baseline ingênuo'],
  ['Cobertura de testes no núcleo de regras', 'Mínimo de 70%'],
], { boldCol: 0, zebra: true }));
children.push(quebra());

// ===== 5. PÚBLICO-ALVO =====
children.push(h1('5. Público-alvo'));
children.push(h2('5.1 Perfil da organização usuária'));
children.push(p('Unidade regional de marketplace de delivery — franquia ou licenciada local — com:'));
children.push(bullet('50 a 500 comércios parceiros ativos'));
children.push(bullet('1 a 3 pessoas na equipe comercial'));
children.push(bullet('Relacionamento predominantemente remoto, por aplicativo de mensagens'));
children.push(bullet('Sem ferramenta de BI, sem analista de dados e sem equipe de tecnologia própria'));
children.push(bullet('Verba de incentivo limitada e disputada entre parceiros'));
children.push(h2('5.2 Usuários do sistema'));
children.push(table([1900, 2500, 2700, 2538], [
  ['Perfil', 'Quem é', 'O que faz no sistema', 'Necessidade central'],
  ['Gestor (primário)', 'Responsável pela unidade; decide onde investir', 'Consulta o painel, executa o otimizador, aprova mensagens', 'Decidir rápido, com critério defensável, sem depender de analista'],
  ['Analista comercial', 'Executa o relacionamento no dia a dia', 'Importa relatórios, analisa parceiros, redige mensagens', 'Saber quem procurar hoje e com qual argumento'],
  ['Administrador', 'Responsável técnico da operação', 'Gerencia usuários e perfis, ajusta parâmetros, audita', 'Manter o sistema seguro e configurado sem mexer em código'],
  ['Parceiro (opcional)', 'Comércio cadastrado na rede', 'Consulta apenas o próprio desempenho', 'Enxergar o próprio resultado e a própria evolução'],
], { boldCol: 0, zebra: true }));
children.push(h2('5.3 Restrições impostas pelo público'));
children.push(p('O público-alvo condiciona decisões técnicas que aparecem nos requisitos não funcionais:'));
children.push(bullet('Interface em português e autoexplicativa — não há treinamento formal nem suporte de TI interno (RNF20)'));
children.push(bullet('Instalação em um comando — não há equipe para configurar ambiente (RNF07)'));
children.push(bullet('Funcionar sem GPU — a máquina do usuário pode ser um notebook comum (RNF06)'));
children.push(bullet('Rastreabilidade das análises — o gestor precisa justificar a decisão para a franqueadora e para os parceiros (RNF17)'));
children.push(bullet('Aprovação humana antes de qualquer envio — a relação com o parceiro é ativo estratégico (RF39)'));
children.push(quebra());

// ===== 6. RF =====
children.push(h1('6. Requisitos Funcionais'));
children.push(p('43 requisitos funcionais distribuídos em 6 módulos. Prioridade em MoSCoW: M (indispensável), S (importante), C (desejável). Perfis: ADM Administrador, GES Gestor, ANL Analista, PAR Parceiro.'));
for (const [mod, reqs] of Object.entries(RF)) {
  children.push(h2(mod));
  children.push(table([900, 6100, 700, 1938], [
    ['ID', 'Requisito', 'Pri', 'Perfis'],
    ...reqs,
  ], { boldCol: 0, zebra: true, align: [undefined, undefined, AlignmentType.CENTER, undefined] }));
}
children.push(espaco(200));
children.push(p('Total: 43 requisitos funcionais — 31 Must, 9 Should, 3 Could.', { bold: true }));
children.push(quebra());

// ===== 7. RNF =====
children.push(h1('7. Requisitos Não Funcionais'));
children.push(p('29 requisitos não funcionais, cada um com métrica de aceitação verificável — nenhum enunciado subjetivo.'));
for (const [cat, reqs] of Object.entries(RNF)) {
  children.push(h2(cat));
  children.push(table([1000, 5300, 3338], [
    ['ID', 'Requisito', 'Métrica de aceitação'],
    ...reqs,
  ], { boldCol: 0, zebra: true }));
}
children.push(quebra());

// ===== 8. CASOS DE USO =====
children.push(h1('8. Casos de Uso'));
children.push(h2('8.1 Atores'));
children.push(table([2300, 1500, 5838], [
  ['Ator', 'Tipo', 'Descrição'],
  ['Administrador', 'Primário', 'Responsável técnico da operação. Gerencia usuários, perfis e parâmetros; audita as ações registradas'],
  ['Gestor', 'Primário', 'Responsável pela unidade. Executa o otimizador, aprova mensagens e acompanha a mobilidade do ranking'],
  ['Analista', 'Primário', 'Executa o relacionamento. Importa relatórios, analisa e redige mensagens, mas não aprova envio'],
  ['Parceiro', 'Primário', 'Comércio da rede. Acesso restrito ao próprio desempenho histórico'],
  ['Modelo de Linguagem Local', 'Secundário', 'Serviço interno que redige textos e responde ao assistente. Nunca calcula números'],
], { boldCol: 0, zebra: true }));
children.push(espaco(140));
children.push(p('A separação entre Gestor e Analista é o que materializa a exigência de diferentes perfis de usuários: os dois enxergam o mesmo painel, mas apenas o Gestor pode comprometer recursos (executar campanha) e comprometer a relação com o parceiro (aprovar mensagem).', { italics: true, color: '5A6B7E' }));
children.push(h2('8.2 Diagrama de casos de uso'));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 200 },
  children: [new ImageRun({
    type: 'png',
    data: fs.readFileSync(path.join(DIAGRAMAS, 'casos-de-uso.png')),
    transformation: { width: 640, height: 423 },
  })],
}));
children.push(h2('8.3 Visão geral'));
children.push(table([900, 3900, 2100, 2738], [
  ['ID', 'Caso de uso', 'Ator principal', 'Requisitos cobertos'],
  ['UC01', 'Autenticar no sistema', 'Todos', 'RF01, RF02, RF07'],
  ['UC02', 'Gerenciar usuários e perfis', 'Administrador', 'RF03, RF04, RF05'],
  ['UC03', 'Importar relatório de desempenho', 'Analista, Gestor', 'RF09 a RF13'],
  ['UC04', 'Gerenciar parceiros e categorias', 'Analista, Gestor', 'RF14, RF15, RF16'],
  ['UC05', 'Consultar painel e ranking', 'Gestor, Analista', 'RF17 a RF20, RF23 a RF25'],
  ['UC06', 'Analisar mobilidade do Top N', 'Gestor, Analista', 'RF22'],
  ['UC07', 'Treinar modelo de previsão', 'Administrador, Gestor', 'RF27, RF28'],
  ['UC08', 'Configurar e executar otimização de campanha', 'Gestor', 'RF29 a RF31, RF35'],
  ['UC09', 'Comparar desempenho serial, paralelo e GPU', 'Gestor, Administrador', 'RF32, RF33, RF34'],
  ['UC10', 'Gerar mensagens por segmento', 'Analista, Gestor', 'RF36, RF37'],
  ['UC11', 'Aprovar ou rejeitar mensagem', 'Gestor', 'RF38, RF39, RF40'],
  ['UC12', 'Consultar assistente analítico', 'Gestor, Analista', 'RF41, RF42, RF43'],
  ['UC13', 'Consultar meu desempenho', 'Parceiro', 'RF19, RF26'],
  ['UC14', 'Auditar ações do sistema', 'Administrador', 'RF06, RF08'],
], { boldCol: 0, zebra: true }));
children.push(h2('8.4 Matriz de permissões'));
children.push(p('Legenda: X executa · L somente leitura · — sem acesso', { size: 18, color: '5A6B7E' }));
const perm = [
  ['UC01 Autenticar', 'X', 'X', 'X', 'X'], ['UC02 Gerenciar usuários', 'X', '—', '—', '—'],
  ['UC03 Importar relatório', '—', 'X', 'X', '—'], ['UC04 Gerenciar parceiros', '—', 'X', 'X', '—'],
  ['UC05 Painel e ranking', 'L', 'X', 'X', '—'], ['UC06 Mobilidade do Top N', 'L', 'X', 'X', '—'],
  ['UC07 Treinar modelo', 'X', 'X', '—', '—'], ['UC08 Executar otimização', '—', 'X', 'L', '—'],
  ['UC09 Benchmark', 'X', 'X', '—', '—'], ['UC10 Gerar mensagens', '—', 'X', 'X', '—'],
  ['UC11 Aprovar mensagem', '—', 'X', '—', '—'], ['UC12 Assistente', '—', 'X', 'X', '—'],
  ['UC13 Meu desempenho', '—', '—', '—', 'X'], ['UC14 Auditoria', 'X', '—', '—', '—'],
];
children.push(table([4838, 1200, 1200, 1200, 1200], [
  ['Caso de uso', 'ADM', 'GES', 'ANL', 'PAR'], ...perm,
], { boldCol: 0, zebra: true, align: [undefined, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }));
children.push(quebra());

// UC08 detalhado
children.push(h2('8.5 Especificação detalhada — UC08: Executar otimização de campanha'));
children.push(table([2400, 7238], [
  ['Ator principal', 'Gestor'],
  ['Objetivo', 'Obter o plano de ações que maximiza o retorno esperado dentro das restrições reais'],
  ['Pré-condições', 'Usuário autenticado com perfil Gestor; modelo de previsão treinado; ao menos um período importado'],
  ['Pós-condições', 'Plano de campanha gerado e persistido; execução registrada no histórico e na auditoria'],
  ['Requisitos', 'RF29, RF30, RF31, RF32, RF34, RF35'],
], { boldCol: 0 }));
children.push(espaco(160));
children.push(h3('Fluxo principal'));
[
  'O usuário abre a tela de campanha.',
  'Informa orçamento total, número máximo de ações, período de aplicação e o catálogo de ações com custo unitário.',
  'Opcionalmente define cotas por categoria — por exemplo, ao menos 30% das ações destinadas à cauda longa.',
  'Opcionalmente escolhe o modo de execução; se não escolher, o sistema seleciona o modo disponível mais rápido.',
  'O usuário dispara a otimização.',
  'O sistema recupera, para cada parceiro elegível, o faturamento previsto e o risco de queda.',
  'O sistema executa o otimizador, exibindo indicador de progresso.',
  'O sistema apresenta o plano de campanha: pares parceiro-ação, uplift esperado, custo total, folga por restrição e tempo de execução.',
  'O usuário pode exportar o plano ou encaminhá-lo para a geração de mensagens.',
  'O sistema registra a execução com autor, parâmetros, modo, tempo e resultado.',
].forEach((t, i) => children.push(p(`${i + 1}. ${t}`, { after: 70, indent: { left: 280 } })));
children.push(h3('Fluxos alternativos'));
children.push(bullet('A1 — Restrições inviáveis. O sistema não retorna plano parcial: informa a inviabilidade e aponta qual restrição foi violada.'));
children.push(bullet('A2 — Orçamento superior ao necessário. Retorna o plano completo, informa a sobra e sugere ampliar o catálogo de ações.'));
children.push(bullet('A3 — Comparação de cenários. O usuário executa uma segunda otimização e solicita a comparação lado a lado.'));
children.push(bullet('A4 — GPU indisponível. Executa em CPU paralelo e informa a substituição, sem interromper a operação.'));
children.push(h3('Exceções'));
children.push(bullet('E1 — Modelo não treinado. O sistema interrompe e direciona o usuário para o caso de uso UC07.'));
children.push(bullet('E2 — Execução excede o tempo limite. Preserva a melhor solução encontrada, sinaliza que é parcial e registra a ocorrência.'));
children.push(espaco(200));
children.push(p('Os demais casos de uso centrais — UC01, UC03, UC05, UC09 e UC11 — estão especificados no mesmo nível de detalhe no repositório, em docs/03-casos-de-uso.md.', { italics: true, color: '5A6B7E' }));
children.push(quebra());

// ===== 9. BACKLOG =====
children.push(h1('9. Product Backlog'));
children.push(p('Histórias no formato "Como <perfil>, quero <ação>, para <valor>", com prioridade MoSCoW, estimativa em story points (Fibonacci), sprint alocada e critérios de aceite. Os critérios de aceite completos estão nas issues do repositório.'));
children.push(h2('9.1 Épicos'));
children.push(table([1000, 5400, 1600, 1638], [
  ['Épico', 'Título', 'Pontos', 'Sprints'],
  ...BACKLOG,
], { boldCol: 0, zebra: true, align: [AlignmentType.CENTER, undefined, AlignmentType.CENTER, AlignmentType.CENTER] }));
children.push(h2('9.2 Histórias'));
children.push(table([900, 5400, 900, 800, 800, 838], [
  ['ID', 'História', 'Épico', 'Pri', 'Pts', 'Spr'],
  ...HIST,
], { boldCol: 0, zebra: true, size: 16, align: [undefined, undefined, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }));
children.push(h2('9.3 Primeiro corte, se o prazo apertar'));
children.push(p('Ordem de remoção acordada previamente, para que a decisão não seja tomada sob pressão:'));
children.push(bullet('H59 — comparar planos lado a lado (Could)'));
children.push(bullet('H39 — portal do parceiro (Could)'));
children.push(bullet('H27 — sugestão de categoria (Should)'));
children.push(bullet('H38 — exportação em CSV (Should)'));
children.push(bullet('H65 — perguntas livres ao assistente (Should), mantendo H66, H67 e H68, que protegem a confiabilidade'));
children.push(espaco(140));
children.push(p('Nada dos épicos E6 e E9 entra nessa lista: são, respectivamente, o diferencial técnico avaliado e a condição de entrega.', { bold: true }));
children.push(quebra());

// ===== 10. CRONOGRAMA =====
children.push(h1('10. Cronograma'));
children.push(p('Treze sprints: a primeira já entregue e doze ciclos semanais, de segunda a sexta, até 04/12. A mudança de sprints quinzenais para semanais atende ao pedido da avaliação da Sprint 1 e traz três consequências práticas: as histórias de 13 pontos foram quebradas em etapas verificáveis, cada semana passa a ter um entregável demonstrável próprio, e um eventual atraso aparece em sete dias em vez de quatorze.'));
children.push(p('Regra permanente: toda sprint termina com algo executável.', { bold: true }));
children.push(table([700, 1700, 3300, 3938], [
  ['Spr', 'Período', 'Tema', 'Entregável demonstrável'],
  ['1', 'até 05/09', 'Planejamento e descoberta', 'Documentação completa e repositório configurado'],
  ['2', '14/09 – 18/09', 'Modelagem e fundação', 'Banco criado por migração; ambiente sobe com um comando'],
  ['3', '21/09 – 25/09', 'Dados, protótipo e spike de GPU', 'Base populada por um comando; protótipo aprovado; kernel de GPU rodando'],
  ['4', '28/09 – 02/10', 'Autenticação e usuários', 'Login com sessão; cadastro de usuários e perfis'],
  ['5', '05/10 – 09/10', 'Autorização e ingestão por texto', 'Perfis barrados no servidor; relatório importado com prévia'],
  ['6', '12/10 – 16/10', 'Ingestão completa e painel', 'CSV, histórico e painel com indicadores e ranking'],
  ['7', '19/10 – 23/10', 'Segmentação e mobilidade do Top N', 'Cada parceiro segmentado; quem entrou e saiu do Top N'],
  ['8', '26/10 – 30/10', 'Modelo preditivo', 'Modelo treinado, MAPE melhor que o baseline, previsão na tela'],
  ['9', '02/11 – 06/11', 'Otimizador: formalização e baseline', 'Otimizador serial devolvendo plano válido'],
  ['10', '09/11 – 13/11', 'Otimizador integrado e CPU paralela', 'Plano na interface; versão C++ com OpenMP e ganho medido'],
  ['11', '16/11 – 20/11', 'GPU e benchmark', 'Speedup medido e exibido na tela'],
  ['12', '23/11 – 27/11', 'Central de comunicação', 'Mensagens geradas e fila de aprovação funcionando'],
  ['13', '30/11 – 04/12', 'Assistente e fechamento', 'Sistema completo, documentado e os dois vídeos'],
], { boldCol: 0, zebra: true, align: [AlignmentType.CENTER] }));
children.push(espaco(160));
children.push(rich([
  { t: 'Carga: ', b: true },
  { t: '389 pontos no total, 27 já entregues na Sprint 1 e 362 distribuídos em doze semanas — média de 30,2 pontos por sprint, contra uma capacidade nominal de cerca de 40. A Sprint 13 está deliberadamente acima da média, e isso está tratado em 10.3.' },
]));
children.push(h2('10.1 Marcos'));
children.push(table([1400, 4200, 4038], [
  ['Data', 'Marco', 'Critério de verificação'],
  ['05/09', 'Planejamento entregue', 'Documento no Teams e formulário de identificação preenchido'],
  ['25/09', 'Risco de GPU retirado', 'Kernel CUDA compilado e conferido contra a CPU'],
  ['02/10', 'Acesso controlado', 'Login com 4 perfis, negação validada no servidor'],
  ['16/10', 'Dados entrando e painel no ar', 'Importação completa e ranking com variação'],
  ['23/10', 'Inteligência de negócio pronta', 'Segmentação determinística e mobilidade do Top N'],
  ['30/10', 'Modelo batendo o baseline', 'MAPE registrado e inferior ao baseline ingênuo'],
  ['13/11', 'Otimizador paralelo em CPU', 'Plano válido e ganho medido sobre o serial'],
  ['20/11', 'Componente avançado demonstrável', 'Speedup medido e exibido na interface'],
  ['27/11', 'Produto completo', 'Fluxo inteiro, do dado bruto à mensagem aprovada'],
  ['30/11', 'Congelamento de escopo', 'Nenhuma funcionalidade nova a partir desta data'],
  ['05/12', 'Entrega final', 'Sistema, código, documentação, banco e os dois vídeos'],
], { boldCol: 0, zebra: true }));
children.push(h2('10.2 Riscos e mitigações'));
children.push(table([700, 2900, 900, 5138], [
  ['#', 'Risco', 'Prob.', 'Mitigação'],
  ['R1', 'A cadeia de compilação de GPU não funcionar no ambiente disponível', 'Média', 'Spike antecipado para a Sprint 3, oito semanas antes de ser necessário. Alternativas em ordem: CuPy, Numba com destino CUDA, OpenCL'],
  ['R2', 'Escopo completo sem folga no calendário', 'Alta', 'A média de 30 pontos por semana não deixa margem. Válvula de escape definida em 10.3: o assistente analítico sai primeiro. A velocidade real das Sprints 2 e 3 recalibra o plano antes da Sprint 8'],
  ['R3', 'O speedup em GPU ficar abaixo da meta de 5x', 'Média', 'Ampliar a escala do cenário com o gerador sintético. Se ainda assim não atingir, reportar o resultado medido com a análise do porquê'],
  ['R4', 'Trilha do núcleo concentrada em uma pessoa', 'Alta', 'E5 e E6 somam 116 pontos sob o mesmo responsável, sem par. Mitigação por transferência de conhecimento: decisões em ADR e apresentação do código do núcleo nas revisões das Sprints 10 e 11'],
  ['R5', 'Modelo preditivo não superar o baseline ingênuo', 'Média', 'Baselines implementados antes do modelo, para saber cedo qual é o alvo; o otimizador segue com a melhor estimativa disponível'],
  ['R6', 'Ausência ou queda de participação de um integrante', 'Média', 'O ciclo semanal expõe o problema em sete dias; acompanhamento por commits e board em cada orientação'],
  ['R7', 'Vídeos deixados para os últimos dias', 'Alta', 'A Sprint 13 já nasce sobrecarregada. Roteiros escritos na Sprint 12; congelamento em 30/11; gravação distribuída entre 01/12 e 04/12'],
  ['R8', 'Escopo crescer durante o semestre', 'Média', 'Toda ideia nova entra no backlog como história e disputa prioridade; não é incorporada direto à sprint em andamento'],
], { boldCol: 0, zebra: true, align: [AlignmentType.CENTER, undefined, AlignmentType.CENTER] }));
children.push(h2('10.3 A semana que não fecha'));
children.push(p('A Sprint 13 está com 45 pontos contra uma média de 30, e é justamente a semana dos dois vídeos. Não é erro de distribuição: é o que sobra quando o escopo completo é dividido por doze semanas, com as outras onze já entre 22 e 32 pontos.'));
children.push(p('Registrar isso agora tem um propósito: quando a pressão chegar, a decisão já estará tomada em vez de improvisada. O assistente analítico é a válvula de escape — se qualquer semana entre a 8 e a 12 atrasar, ele é o que não se constrói. A justificativa é que ele não é o componente de inteligência avaliado: esse papel cabe ao modelo preditivo e ao otimizador paralelo.'));
children.push(p('O que não pode sair em nenhuma hipótese: os dois vídeos, a documentação final e a reprodutibilidade a partir do README. Sem eles não há entrega.', { bold: true }));
children.push(espaco(160));
children.push(p('As doze sprints semanais foram distribuídas a partir das duas datas oficiais divulgadas: entrega da Sprint 1 em 05/09 e entrega final em 05/12. O calendário de orientações da disciplina tem precedência: o cronograma será ajustado preservando a sequência de temas e os marcos técnicos.', { italics: true, color: '5A6B7E' }));
children.push(quebra());

// ===== 11. REPOSITÓRIO =====
children.push(h1('11. Repositório GitHub'));
children.push(rich([
  { t: 'Endereço: ', s: 21 },
  { t: 'github.com/PedroMiranda243/gih-fabrica-de-software', b: true, s: 21, c: '2C5B8F' },
], { after: 200 }));
children.push(h2('11.1 O que já está configurado'));
children.push(table([3400, 6238], [
  ['Recurso', 'Situação'],
  ['Visibilidade', 'Público'],
  ['Documentação', 'Sete documentos em docs/, cobrindo todos os entregáveis desta sprint'],
  ['Diagrama de casos de uso', 'Publicado em SVG, renderizando diretamente no GitHub'],
  ['Labels', 'Por épico (E1 a E9), prioridade (MoSCoW) e tipo (feat, fix, docs, test, spike)'],
  ['Milestones', 'Sete, uma por sprint, com data de encerramento'],
  ['Issues', 'Histórias das Sprints 1 a 3 abertas, com critérios de aceite'],
  ['Modelos', 'Issue (história e defeito) e Pull Request, com Definition of Done'],
  ['Proteção do ramo main', 'Exige 1 aprovação em Pull Request; bloqueia push forçado e exclusão'],
  ['Contribuição', 'CONTRIBUTING.md com padrão de ramos, commits e Definition of Done'],
], { boldCol: 0, zebra: true }));
children.push(h2('11.2 Estrutura do repositório'));
[
  'README.md — problema, solução, stack, execução e equipe',
  'CONTRIBUTING.md — fluxo de branches, commits e Pull Requests',
  'docs/01-visao-do-produto.md — tema, problema, objetivos e público-alvo',
  'docs/02-requisitos.md — requisitos funcionais e não funcionais, com rastreabilidade',
  'docs/03-casos-de-uso.md — diagrama e especificação dos casos de uso',
  'docs/04-product-backlog.md — épicos e histórias priorizadas',
  'docs/05-cronograma.md — sprints, marcos e riscos',
  'docs/06-equipe-e-processo.md — papéis, cerimônias e Definition of Done',
  'docs/07-arquitetura-preliminar.md — visão de contêineres, stack e decisões de arquitetura',
].forEach(t => children.push(bullet(t)));
children.push(h2('11.3 Regras de dados e confidencialidade'));
children.push(p('O repositório é público, e por isso valem sem exceção:'));
children.push(bullet('Nenhum dado real de nenhuma operação. Toda massa de demonstração é gerada por script.'));
children.push(bullet('Nenhum segredo versionado: senhas e tokens ficam em .env, bloqueado pelo .gitignore.'));
children.push(bullet('Nenhum nome de organização, pessoa ou parceiro real em código, documentação ou dados de exemplo.'));
children.push(bullet('Verificação de conteúdo sensível executada antes de cada entrega.'));
children.push(espaco(200));
children.push(p('Projeto acadêmico. © 2026 os autores — todos os direitos reservados. Repositório público significa visível para avaliação e portfólio; não constitui licença de uso, cópia ou redistribuição.', { italics: true, color: '5A6B7E' }));

  return children;
}

module.exports = { montar, EQUIPE, TURMA };
