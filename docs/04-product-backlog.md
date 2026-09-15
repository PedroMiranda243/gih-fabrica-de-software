# 04 — Product Backlog

**Projeto:** Growth Intelligence Hub (GIH)
**Sprint:** 1 — Planejamento e Descoberta
**Versão:** 2.0 — 15/09/2026 · sprints semanais

---

## Convenções

**Formato das histórias:** *Como &lt;perfil&gt;, quero &lt;ação&gt;, para &lt;valor&gt;.*

**Prioridade (MoSCoW)**

| Símbolo | Significado |
|---|---|
| **M** | *Must have* — sem isso não há produto entregável |
| **S** | *Should have* — importante; sai apenas se o prazo apertar |
| **C** | *Could have* — agrega valor, primeiro a ser cortado |

**Estimativa:** story points na sequência de Fibonacci (1, 2, 3, 5, 8, 13). Um ponto equivale
aproximadamente a meia sessão de trabalho de um integrante. Histórias de 13 pontos são candidatas a
quebra durante o planejamento da sprint.

**Velocidade planejada:** ~40 pontos por sprint **semanal** (5 integrantes × ~8 pontos). Referência de
capacidade; será recalibrada ao fim da Sprint 3, com duas semanas de execução medidas.

**Este backlog é vivo.** A versão de referência para execução são as *issues* do GitHub, organizadas no
board do projeto. Esta tabela é o retrato aprovado na Sprint 1.

---

## Épicos

| Épico | Título | Pontos | Sprints |
|---|---|---:|---|
| **E1** | Fundação, planejamento e ambiente | 47 | 1–3 |
| **E2** | Autenticação, perfis e auditoria | 39 | 4–5 |
| **E3** | Ingestão e modelo de dados | 46 | 2–6 |
| **E4** | Inteligência de negócio e segmentação | 47 | 6–9 |
| **E5** | Núcleo preditivo | 34 | 8–9 |
| **E6** | Otimização, paralelismo e GPU | 82 | 3–11 |
| **E7** | Central de comunicação | 26 | 12 |
| **E8** | Assistente analítico | 21 | 12–13 |
| **E9** | Qualidade, documentação e entrega | 47 | 2–13 |
| | **Total** | **389** | |

---

## E1 — Fundação, planejamento e ambiente

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H01** | Como equipe, quero definir tema, problema e objetivos, para ter um alvo comum e defensável. | M | 5 | 1 | Documento `01-visao-do-produto.md` aprovado na orientação; problema, objetivos e público-alvo escritos e vinculados entre si |
| **H02** | Como equipe, quero levantar requisitos funcionais e não funcionais, para delimitar o escopo. | M | 8 | 1 | 43 RF e 29 RNF documentados; todo RF ligado a um objetivo; RNF com métrica de aceitação verificável |
| **H03** | Como equipe, quero modelar os casos de uso, para descrever o comportamento esperado por ator. | M | 5 | 1 | Diagrama publicado; 6 casos centrais com fluxo principal, alternativos e exceções |
| **H04** | Como equipe, quero um product backlog priorizado, para saber o que construir primeiro. | M | 3 | 1 | Épicos e histórias com prioridade, pontos, sprint e critérios de aceite |
| **H05** | Como equipe, quero um cronograma por sprint até 05/12, para acompanhar o avanço. | M | 3 | 1 | 7 sprints com datas, metas e entregável executável por sprint |
| **H06** | Como equipe, quero o repositório GitHub configurado, para versionar e evidenciar o processo. | M | 3 | 1 | Repositório público, README, `.gitignore`, milestones, labels, board e regra de proteção em `main` |
| **H07** | Como equipe, quero um modelo entidade-relacionamento, para orientar a implementação do banco. | M | 8 | 2 | Diagrama ER com entidades, atributos, chaves e cardinalidades; revisado pela equipe |
| **H08** | Como equipe, quero um protótipo navegável das telas principais, para validar a interface antes de codificar. | **M** | 5 | 3 | Protótipo cobrindo painel, importação, campanha e aprovação; paleta, tipografia e cor por segmento definidas; **aprovado pela equipe antes de existir qualquer CSS** |
| **H09** | Como desenvolvedor, quero o ambiente subindo com um comando, para eliminar divergência entre máquinas. | M | 5 | 2 | `docker compose up` sobe API, banco e interface a partir de um clone limpo |
| **H10** | Como equipe, quero integração contínua no repositório, para não integrar código quebrado. | M | 2 | 2 | Fluxo executa análise estática e testes a cada Pull Request e bloqueia a mesclagem se falhar |

## E2 — Autenticação, perfis e auditoria

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H11** | Como usuário, quero autenticar com login e senha, para acessar o sistema. | M | 5 | 4 | RF01; senha em hash; sessão criada; teste automatizado cobrindo sucesso e falha |
| **H12** | Como usuário, quero encerrar minha sessão, para proteger o acesso em máquina compartilhada. | M | 2 | 4 | RF02; sessão invalidada no servidor, não apenas no navegador |
| **H13** | Como sistema, quero renovar o identificador de sessão no login, para impedir fixação de sessão. | M | 3 | 4 | RNF10; teste comprova que o identificador anterior deixa de valer |
| **H14** | Como sistema, quero bloquear tentativas repetidas de login, para dificultar ataque por força bruta. | M | 3 | 4 | RNF11; bloqueio após 5 falhas; resposta idêntica para usuário inexistente e senha errada |
| **H15** | Como administrador, quero cadastrar e editar usuários, para controlar quem acessa. | M | 5 | 4 | RF03; criar, editar, desativar e listar, com validação de dados |
| **H16** | Como administrador, quero atribuir perfis, para que cada pessoa veja apenas o que lhe cabe. | M | 5 | 4 | RF04; quatro perfis disponíveis; um perfil por usuário |
| **H17** | Como sistema, quero validar a permissão no servidor a cada requisição, para que a interface não seja a barreira de segurança. | M | 8 | 5 | RNF14; teste automatizado tenta cada endpoint com cada perfil e confirma a negação esperada |
| **H18** | Como administrador, quero consultar a trilha de auditoria, para investigar o que foi feito e por quem. | S | 5 | 4 | RF06, RF08; registro de ações sensíveis com autor, data e parâmetros; filtros funcionando |
| **H19** | Como usuário, quero alterar minha senha, para manter minha conta segura. | S | 3 | 4 | RF07; exige a senha atual; nova senha validada quanto à força mínima |

## E3 — Ingestão e modelo de dados

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H20** | Como equipe, quero o esquema do banco versionado por migrações, para evoluir o modelo sem perder dados. | M | 5 | 2 | Migrações aplicam e revertem; esquema recriável do zero |
| **H21** | Como analista, quero importar um relatório colando o texto, para carregar os dados do período. | M | 8 | 5 | RF09; interpreta o formato definido; registros gravados corretamente |
| **H22** | Como analista, quero importar por arquivo CSV, para aproveitar exportações já existentes. | M | 3 | 6 | RF09; aceita CSV com o mesmo conjunto de colunas |
| **H23** | Como sistema, quero recusar importação sem período informado, para não corromper a linha do tempo. | M | 3 | 5 | RF10, RN03; importação sem período é bloqueada com mensagem explicativa; coberto por teste |
| **H24** | Como analista, quero ver uma prévia antes de gravar, para conferir o que será importado. | M | 5 | 5 | RF11; lista reconhecidos, rejeitados com motivo e parceiros novos |
| **H25** | Como analista, quero ser avisado ao reimportar um período já existente, para não duplicar dados. | S | 3 | 6 | RF12; alerta com opção explícita de substituir; padrão é cancelar |
| **H26** | Como analista, quero cadastrar e editar parceiros, para manter a base correta. | M | 5 | 3 | RF14; nome, categoria, status e contato; validações aplicadas |
| **H27** | Como analista, quero que o sistema sugira a categoria pelo nome, para acelerar o cadastro. | S | 5 | 3 | RF15, RN05; sugestão marcada como não confirmada até validação humana |
| **H28** | Como equipe, quero um gerador de dados sintéticos, para demonstrar o sistema e medir o otimizador em escala. | M | 5 | 3 | RF16; gera de 100 a 10.000 parceiros com múltiplos períodos, tendência, sazonalidade e ruído; semente reproduzível |
| **H29** | Como analista, quero consultar o histórico de importações, para auditar a origem dos dados. | M | 2 | 6 | RF13; autor, data, período e total de registros |
| **H77** | Como desenvolvedor, quero um comando que limpe e repovoe o banco, para testar sempre a partir de um estado conhecido. | M | 2 | 3 | Limpa o banco, aplica as migrações e repovoa com o gerador em um comando; pede confirmação antes de apagar |

## E4 — Inteligência de negócio e segmentação

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H30** | Como gestor, quero ver os indicadores consolidados do período, para entender o resultado da rede. | M | 5 | 6 | RF17; faturamento, pedidos, ticket médio, parceiros ativos e variação |
| **H31** | Como gestor, quero ver o ranking com a variação de posição, para saber quem subiu e quem caiu. | M | 5 | 6 | RF18; posição atual, posição anterior e variação percentual |
| **H32** | Como gestor, quero ver a série histórica em gráfico, para enxergar tendência e não apenas o retrato. | M | 5 | 6 | RF19; série da unidade e série individual por parceiro |
| **H33** | Como sistema, quero segmentar cada parceiro por regra determinística, para classificar sem ambiguidade. | M | 8 | 7 | RF20, RN01; precedência respeitada; reprocessar produz resultado idêntico; coberto por testes; **recálculo por consulta agregada, sem uma consulta por parceiro** |
| **H34** | Como administrador, quero configurar os limiares da segmentação, para adaptar a regra à operação. | S | 3 | 7 | RF21; alteração sem recompilar e sem alterar código |
| **H35** | Como gestor, quero ver quem entrou e saiu do Top N, para acompanhar a mobilidade do ranking. | M | 5 | 7 | RF22, RN02; cálculo derivado do ranking, não do segmento; coberto por teste que expõe a diferença |
| **H36** | Como analista, quero filtrar e ordenar a lista de parceiros, para chegar rápido ao recorte que me interessa. | M | 5 | 7 | RF23; filtros por categoria e segmento; ordenação por qualquer coluna |
| **H37** | Como analista, quero buscar parceiro por nome, para localizar um caso específico. | M | 2 | 6 | RF24; correspondência parcial e sem sensibilidade a acentuação |
| **H38** | Como analista, quero exportar a visão filtrada em CSV, para trabalhar fora do sistema quando necessário. | S | 3 | 7 | RF25; o arquivo reflete exatamente os filtros aplicados |
| **H39** | Como parceiro, quero consultar meu próprio desempenho, para acompanhar minha evolução. | C | 3 | 9 | RF26; sem acesso a dados de terceiros nem a ranking comparativo; negação validada no servidor |
| **H40** | Como gestor, quero que o painel responda rápido mesmo com base grande, para usar o sistema no dia a dia. | M | 3 | 6 | RNF03, RNF05; até 2 s com 5.000 parceiros; consultas com índice |

## E5 — Núcleo preditivo

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H41** | Como equipe, quero definir e extrair as variáveis preditivas do histórico, para alimentar o modelo. | M | 8 | 8 | Conjunto de variáveis documentado; extração reproduzível; separação treino/teste sem vazamento temporal |
| **H42** | Como equipe, quero treinar o modelo de previsão de faturamento, para estimar o próximo período. | M | 8 | 8 | RF27; modelo treinado; MAPE registrado e **inferior ao baseline ingênuo** em conjunto de teste |
| **H43** | Como equipe, quero estimar a probabilidade de queda por parceiro, para alimentar a priorização. | M | 5 | 8 | RF27; probabilidade calibrada; métrica de avaliação documentada |
| **H44** | Como gestor, quero ver previsão e risco na tela do parceiro, para decidir com base no que vem, não só no que passou. | M | 5 | 8 | RF28; valores exibidos com indicação clara de que são estimativas |
| **H45** | Como administrador, quero disparar o retreino do modelo, para incorporar os períodos novos. | S | 5 | 9 | RF27; registra data, volume de dados e métricas obtidas; execução registrada na auditoria |
| **H46** | Como equipe, quero comparar o modelo com baselines estatísticos, para provar que o aprendizado agrega. | M | 3 | 8 | Tabela comparativa com pelo menos dois baselines; resultado publicado na documentação |

## E6 — Otimização, paralelismo e GPU

> Núcleo do componente avançado. É aqui que a integração com Tópicos Avançados se materializa.

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H47** | Como equipe, quero validar a cadeia de compilação da GPU, para retirar cedo o maior risco técnico. | M | 5 | 3 | *Spike*: kernel mínimo compilado e invocado a partir do Python, com resultado conferido contra a CPU |
| **H48** | Como equipe, quero formalizar o problema de otimização, para ter um alvo matemático explícito. | M | 5 | 9 | Função objetivo, variáveis de decisão e restrições documentadas; instância de teste com ótimo conhecido |
| **H49** | Como equipe, quero implementar o otimizador serial em Python, para estabelecer o baseline de corretude e tempo. | M | 8 | 9 | Encontra o ótimo na instância pequena; tempo medido e registrado |
| **H50** | Como gestor, quero configurar as restrições da campanha, para refletir o orçamento e a capacidade reais. | M | 5 | 9 | RF29; orçamento, número de ações, catálogo com custos e cotas por categoria |
| **H51** | Como gestor, quero executar o otimizador e receber o plano de campanha, para saber onde investir. | M | 8 | 10 | RF30; plano com pares parceiro-ação, uplift esperado, custo e folga por restrição |
| **H52** | Como sistema, quero recusar planos inviáveis, para nunca entregar recomendação que viola restrição. | M | 3 | 9 | RF31, RN07; informa a inviabilidade e aponta a restrição violada; coberto por teste |
| **H53a** | Como equipe, quero portar o otimizador para C++, para ter a base sobre a qual paralelizar. | M | 8 | 10 | Resultado idêntico ao baseline em Python na instância de referência; invocável a partir do Python |
| **H53b** | Como equipe, quero paralelizar as partidas com OpenMP, para reduzir o tempo em CPU. | M | 5 | 10 | Ganho medido sobre a versão serial em C++; qualidade de solução equivalente |
| **H54a** | Como equipe, quero as estruturas de dados na GPU e a transferência host-device, para ter onde o kernel operar. | M | 5 | 11 | População e parâmetros transferidos e recuperados corretamente; tempo de transferência medido |
| **H54b** | Como equipe, quero o kernel CUDA de avaliação da população, para paralelizar a parte cara do laço. | M | 5 | 11 | Resultado do kernel conferido contra o cálculo equivalente em CPU |
| **H54c** | Como equipe, quero o laço completo do otimizador na GPU, para fechar o modo acelerado. | M | 3 | 11 | RNF01, RNF02; cenário de referência em até 5 s; speedup de no mínimo 5x com uplift dentro de 2% do baseline |
| **H55** | Como gestor, quero escolher o modo de execução, para comparar ou forçar um comportamento. | M | 3 | 10 | RF32; seleção automática do modo mais rápido disponível quando não especificado |
| **H56** | Como sistema, quero cair para CPU quando não houver GPU, para funcionar em qualquer máquina. | M | 3 | 10 | RNF06; execução completa sem GPU, com aviso informativo |
| **H57** | Como gestor, quero ver o benchmark comparativo na interface, para enxergar o ganho de forma objetiva. | M | 8 | 11 | RF33; tabela com tempo, desvio, speedup e uplift; gráfico de escalabilidade |
| **H58** | Como gestor, quero consultar o histórico de execuções do otimizador, para retomar e comparar decisões. | S | 3 | 10 | RF34; autor, data, parâmetros, modo, tempo e resultado |
| **H59** | Como gestor, quero comparar dois planos lado a lado, para escolher entre cenários. | C | 5 | 11 | RF35; diferenças destacadas entre os dois planos |

## E7 — Central de comunicação

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H60** | Como analista, quero gerar mensagens por segmento e categoria, para me comunicar em escala sem perder personalização. | M | 8 | 12 | RF36; geração a partir do plano de campanha ou de seleção manual |
| **H61** | Como gestor, quero uma fila de mensagens pendentes, para revisar antes de qualquer envio. | M | 5 | 12 | RF37; mensagens nascem no estado pendente |
| **H62** | Como gestor, quero aprovar, editar ou rejeitar cada mensagem, para manter o controle sobre a comunicação. | M | 5 | 12 | RF38; edição preserva a versão original para auditoria |
| **H63** | Como sistema, quero impedir aprovação sem ação humana de um gestor, para proteger a relação com o parceiro. | M | 5 | 12 | RF39, RN06; tentativa por outro perfil é negada no servidor e registrada |
| **H64** | Como gestor, quero consultar o histórico de mensagens decididas, para acompanhar o que foi comunicado. | S | 3 | 12 | RF40; autor da decisão, data e conteúdo final |

## E8 — Assistente analítico

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H65** | Como gestor, quero perguntar sobre os dados em linguagem natural, para consultar sem navegar por telas. | S | 8 | 13 | RF41; responde a um conjunto de perguntas de referência |
| **H66** | Como gestor, quero que a resposta cite o período usado, para confiar no que leio. | M | 5 | 13 | RF42; toda resposta traz a fonte ou declara insuficiência de dados |
| **H67** | Como sistema, quero impedir que o modelo produza números próprios, para eliminar erro numérico inventado. | M | 5 | 13 | RF43, RNF16; números vêm do núcleo determinístico; teste com perguntas-armadilha |
| **H68** | Como gestor, quero que o assistente admita quando não sabe, para não ser induzido ao erro. | M | 3 | 12 | RF42; conjunto de perguntas sem resposta possível resulta em abstenção explícita |

## E9 — Qualidade, documentação e entrega

| ID | História | Pri | Pts | Sprint | Critérios de aceite |
|---|---|:--:|--:|:--:|---|
| **H69** | Como equipe, quero testes automatizados no núcleo de regras, para não regredir a cada mudança. | M | 8 | 7 | RNF24; cobertura de no mínimo 70% em segmentação, ranking, previsão e otimização |
| **H70** | Como equipe, quero testes de segurança automatizados, para validar autorização, injeção e sessão. | M | 5 | 11 | RNF12, RNF13, RNF14; testes cobrindo cada vetor previsto |
| **H71** | Como equipe, quero exigir Pull Request revisado para entrar em `main`, para elevar a qualidade e distribuir o conhecimento. | M | 2 | 2 | RNF25; regra de proteção ativa; nenhum push direto |
| **H78** | Como equipe, quero um teste de ponta a ponta contra a API no ar, para pegar o que o teste unitário não pega. | M | 5 | 5 | Verifica autorização de cada endpoint por perfil, ingestão completa e recálculo da segmentação; escrito em Python, não em `curl` |
| **H72** | Como avaliador, quero conseguir subir o sistema seguindo apenas o README, para verificar o resultado sem ajuda. | M | 5 | 13 | RNF27; validado por um integrante que não escreveu a parte em questão |
| **H73** | Como equipe, quero a documentação técnica final consolidada, para entregar junto ao código. | M | 5 | 13 | Arquitetura, modelo de dados, decisões, resultados do benchmark e do modelo |
| **H74** | Como equipe, quero produzir o vídeo horizontal de apresentação, para cumprir a entrega final. | M | 8 | 13 | Até 10 minutos, formato 16:9, publicado; cobre problema, solução, arquitetura, tecnologias, demonstração, IA, GPU, otimizações e resultados |
| **H75** | Como equipe, quero produzir o vídeo vertical de divulgação, para cumprir a entrega final. | M | 5 | 13 | Formato 9:16, publicado, com as marcações exigidas |
| **H76** | Como equipe, quero validar acessibilidade e responsividade, para atender aos requisitos de interface. | S | 4 | 13 | RNF21, RNF22; contraste conferido por ferramenta; layout funcional a partir de 768 px |

---

## Distribuição por sprint

Sprints **semanais**, de segunda a sexta, conforme pedido na avaliação da Sprint 1.
Detalhamento e datas em [05 — Cronograma](05-cronograma.md).

| Sprint | Tema | Histórias | Pontos |
|:--:|---|---|---:|
| **1** | Planejamento e descoberta | H01, H02, H03, H04, H05, H06 | 27 |
| **2** | Modelagem e fundação | H07, H20, H09, H10, H71 | 22 |
| **3** | Dados, protótipo e spike de GPU | H28, H77, H08, H47, H26, H27 | 27 |
| **4** | Autenticação e usuários | H11, H12, H13, H14, H19, H15, H16, H18 | 31 |
| **5** | Autorização e ingestão por texto | H17, H21, H23, H24, H78 | 29 |
| **6** | Ingestão completa e painel | H22, H25, H29, H30, H31, H32, H40, H37 | 28 |
| **7** | Segmentação e mobilidade do Top N | H33, H34, H35, H36, H38, H69 | 32 |
| **8** | Modelo preditivo | H41, H46, H42, H43, H44 | 29 |
| **9** | Otimizador: formalização e baseline | H45, H48, H49, H50, H52, H39 | 29 |
| **10** | Otimizador integrado e CPU paralela | H51, H53a, H53b, H55, H56, H58 | 30 |
| **11** | GPU e benchmark | H54a, H54b, H54c, H57, H70, H59 | 31 |
| **12** | Central de comunicação | H60, H61, H62, H63, H64, H68 | 29 |
| **13** | Assistente e fechamento | H65, H66, H67, H72, H73, H74, H75, H76 | 45 |
| | | **Total** | **389** |

> A média é de **30,2 pontos por semana**, contra uma capacidade nominal de ~40. A folga é pequena, e a
> Sprint 13 está deliberadamente acima da média — ver a seção *A semana que não fecha* no cronograma.

## Primeiro corte, se o prazo apertar

Ordem de remoção acordada previamente, para que a decisão não seja tomada sob pressão:

1. **H59** comparar planos lado a lado (C)
2. **H39** portal do parceiro (C)
3. **H27** sugestão de categoria (S)
4. **H38** exportação em CSV (S)
5. **H65** perguntas livres ao assistente (S) — mantendo H66, H67 e H68, que protegem a confiabilidade

Nada dos épicos **E6** e **E9** entra nessa lista: são, respectivamente, o diferencial técnico avaliado e a
condição de entrega.
