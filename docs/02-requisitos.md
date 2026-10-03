# 02 — Requisitos Funcionais e Não Funcionais

**Projeto:** Growth Intelligence Hub (GIH)
**Sprint:** 1 — Planejamento e Descoberta
**Versão:** 1.4 — 02/10/2026 · a revisão das regras de negócio, na H99 (1.3 — 02/10/2026, a coluna Perfis conferida contra as rotas; 1.2 — 02/10/2026, o módulo 8; 1.1 — 01/10/2026, o módulo 7; 1.0 — 03/09/2026)

---

## Como ler este documento

- **RF** — Requisito Funcional: o que o sistema faz.
- **RNF** — Requisito Não Funcional: como o sistema se comporta (desempenho, segurança, usabilidade).
- **Prioridade** segue MoSCoW: **M** *Must* (indispensável), **S** *Should* (importante), **C** *Could* (desejável).
- A coluna **Perfis** indica quais perfis acessam o requisito, **para executar ou só para ler**:
  **ADM** Administrador, **GES** Gestor, **ANL** Analista, **PAR** Parceiro. Quem executa e quem só lê, em
  cada caso de uso, está na matriz de permissões de [03 — Casos de uso](03-casos-de-uso.md).
- A coluna é **conferida por teste** contra as rotas da API, pela matriz de
  [11 — Rastreabilidade](11-rastreabilidade.md). A primeira conferência, em 02/10/2026, achou sete requisitos
  em que a coluna dizia menos do que a matriz de permissões e a API: o Administrador lê o painel desde a
  Sprint 1 (RF17, RF18, RF19, RF20 e RF22), e o Analista consulta o histórico das execuções e compara planos
  (RF34 e RF35). A coluna foi corrigida; nenhuma permissão mudou.

---

## Parte I — Requisitos Funcionais

### Módulo 1 — Autenticação, perfis e auditoria

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF01** | O sistema deve autenticar o usuário por login e senha, criando uma sessão identificada. | M | todos |
| **RF02** | O sistema deve permitir o encerramento da sessão, invalidando-a no servidor. | M | todos |
| **RF03** | O sistema deve permitir cadastrar, editar, desativar e listar usuários. | M | ADM |
| **RF04** | O sistema deve permitir atribuir a cada usuário exatamente um perfil de acesso entre Administrador, Gestor, Analista e Parceiro. | M | ADM |
| **RF05** | O sistema deve restringir o acesso a cada funcionalidade conforme o perfil do usuário, validando a permissão no servidor a cada requisição. | M | todos |
| **RF06** | O sistema deve registrar em trilha de auditoria as ações sensíveis (autenticação, importação de dados, execução do otimizador, aprovação ou rejeição de mensagem e alteração de usuários) com autor, data, hora e parâmetros. | M | todos |
| **RF07** | O sistema deve permitir que o usuário altere a própria senha, exigindo a senha atual. | S | todos |
| **RF08** | O sistema deve permitir consultar a trilha de auditoria, com filtro por autor, tipo de ação e intervalo de datas. | S | ADM |

### Módulo 2 — Ingestão e gestão de dados

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF09** | O sistema deve permitir importar um relatório de desempenho por período, aceitando texto colado e arquivo CSV. | M | GES, ANL |
| **RF10** | O sistema deve exigir a data inicial e a data final do período na importação e **recusar** a importação sem esse dado. | M | GES, ANL |
| **RF11** | O sistema deve validar o conteúdo importado e exibir uma prévia com os registros reconhecidos, os rejeitados e o motivo da rejeição, antes de gravar. | M | GES, ANL |
| **RF12** | O sistema deve impedir a importação de um período já registrado, oferecendo a opção explícita de substituição. | S | GES, ANL |
| **RF13** | O sistema deve manter o histórico das importações com autor, data de envio, período coberto e total de registros. | M | GES, ANL, ADM |
| **RF14** | O sistema deve permitir cadastrar, editar e desativar parceiros, com nome, categoria, status comercial e dados de contato. | M | GES, ANL |
| **RF15** | O sistema deve sugerir a categoria do parceiro a partir do nome, sinalizando que se trata de sugestão e exigindo confirmação do usuário para efetivá-la. | S | GES, ANL |
| **RF16** | O sistema deve oferecer um gerador de dados sintéticos capaz de produzir redes de 100 a 10.000 parceiros com múltiplos períodos, para demonstração e para o benchmark do otimizador. | M | ADM |

### Módulo 3 — Inteligência de negócio e segmentação

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF17** | O sistema deve exibir um painel com os indicadores consolidados do período selecionado, da rede inteira ou de uma categoria: faturamento total, número de pedidos, ticket médio, parceiros ativos e variação em relação ao período anterior. | M | GES, ANL, ADM |
| **RF18** | O sistema deve exibir o ranking de parceiros por faturamento, com a posição atual, a posição no período anterior e a variação percentual. | M | GES, ANL, ADM |
| **RF19** | O sistema deve exibir a série histórica em gráfico, tanto para a unidade quanto para um parceiro individual. | M | GES, ANL, ADM, PAR |
| **RF20** | O sistema deve classificar cada parceiro em exatamente um segmento (Top, Em Ascensão, Em Risco, Recém-chegado, Prospecção ou Estável) aplicando regra determinística com ordem de precedência explícita. | M | GES, ANL, ADM |
| **RF21** | O sistema deve permitir configurar os limiares da segmentação (tamanho do Top N, número de períodos de queda para caracterizar risco, número de períodos para caracterizar novo parceiro) sem alteração de código. | S | ADM |
| **RF22** | O sistema deve exibir a mobilidade do ranking entre dois períodos, listando quem entrou e quem saiu do Top N. | M | GES, ANL, ADM |
| **RF23** | O sistema deve permitir filtrar e ordenar a lista de parceiros por categoria, segmento, faturamento, número de pedidos, ticket médio, variação e risco estimado de queda (H80). | M | GES, ANL |
| **RF24** | O sistema deve permitir buscar parceiro por nome, com correspondência parcial. | M | GES, ANL |
| **RF25** | O sistema deve permitir exportar em CSV a visão atualmente filtrada da lista de parceiros. | S | GES, ANL |
| **RF26** | O sistema deve permitir que o perfil Parceiro consulte exclusivamente o próprio desempenho histórico, sem acesso a dados de outros parceiros nem a rankings comparativos. | C | PAR |

### Módulo 4 — Núcleo computacional: previsão e otimização

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF27** | O sistema deve treinar um modelo de previsão a partir do histórico armazenado, registrando a data do treino, o volume de dados utilizado e as métricas de avaliação obtidas. | M | ADM, GES |
| **RF28** | O sistema deve exibir, para cada parceiro, o faturamento previsto para o próximo período e a probabilidade estimada de queda. | M | GES, ANL |
| **RF29** | O sistema deve permitir configurar os parâmetros de uma campanha: orçamento total, número máximo de ações, catálogo de ações disponíveis com custo unitário, cotas por categoria e período de aplicação. | M | GES |
| **RF30** | O sistema deve executar o otimizador sobre os parâmetros configurados e retornar o plano de campanha (o conjunto de pares parceiro-ação selecionado) acompanhado do uplift esperado e do custo total. | M | GES |
| **RF31** | O sistema deve garantir que todo plano retornado respeite integralmente as restrições configuradas, e sinalizar explicitamente quando não existir solução viável. | M | GES |
| **RF32** | O sistema deve permitir escolher o modo de execução do otimizador entre serial, CPU paralelo e GPU, e deve selecionar automaticamente o modo disponível mais rápido quando o usuário não especificar. | M | GES, ADM |
| **RF33** | O sistema deve exibir o benchmark comparativo entre os modos de execução, apresentando tempo decorrido, *speedup* em relação ao baseline serial e qualidade da solução obtida. | M | GES, ADM |
| **RF34** | O sistema deve registrar o histórico das execuções do otimizador com autor, data, parâmetros, modo de execução, tempo e resultado. | S | GES, ANL, ADM |
| **RF35** | O sistema deve permitir comparar lado a lado dois planos de campanha gerados com parâmetros diferentes. | C | GES, ANL |

### Módulo 5 — Central de comunicação

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF36** | O sistema deve gerar mensagens de relacionamento personalizadas por segmento e categoria, a partir do plano de campanha ou de uma seleção manual de parceiros. | M | GES, ANL |
| **RF37** | O sistema deve manter as mensagens geradas em uma fila de aprovação, no estado pendente. | M | GES, ANL |
| **RF38** | O sistema deve permitir aprovar, editar ou rejeitar cada mensagem individualmente antes de considerá-la pronta para envio. | M | GES |
| **RF39** | O sistema deve impedir que qualquer mensagem transite para o estado aprovado sem ação explícita de um usuário com perfil Gestor. | M | GES |
| **RF40** | O sistema deve manter o histórico das mensagens aprovadas e rejeitadas, com autor da decisão, data e conteúdo final. | S | GES, ANL |

### Módulo 6 — Assistente analítico

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF41** | O sistema deve responder a perguntas em linguagem natural sobre os dados armazenados. | S | GES, ANL |
| **RF42** | O sistema deve citar, em toda resposta do assistente, o período e a origem dos dados utilizados; e deve declarar explicitamente a insuficiência de dados quando não houver base para responder, em vez de produzir uma resposta especulativa. | M | GES, ANL |
| **RF43** | O sistema deve impedir que o assistente produza valores numéricos que não tenham sido calculados pelo núcleo determinístico. | M | GES, ANL |

### Módulo 7 — Relatórios, consulta e acompanhamento

Acrescentado em 01/10/2026, para a Sprint 07 da disciplina: os relatórios, e o que faltava de pesquisa, filtro,
exportação e histórico de operações nos módulos anteriores. Nenhum deles traz regra de negócio nova — todos
leem o que os módulos 1 a 4 já gravam.

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF44** | O sistema deve gerar o relatório de desempenho de um período, consolidado por categoria e por segmento, com faturamento, pedidos, ticket médio, número de parceiros e variação em relação ao período anterior. Por categoria, e no total, a variação é a do painel: o faturamento do grupo contra o do mesmo grupo no período anterior. Por segmento — e em tudo, quando o relatório é filtrado por um segmento —, a variação é a **dos mesmos parceiros**: o que os parceiros do grupo que venderam nos dois períodos faturaram agora, contra o que faturaram antes. O segmento muda de um período para o outro, e comparar o segmento de agora com o de antes mediria quem entrou e quem saiu dele, e não como os parceiros dele foram. | M | GES, ANL |
| **RF45** | O sistema deve gerar o relatório de parceiros em risco, com o segmento, a variação, o faturamento medido e o previsto, o risco estimado de queda e a ação no último plano de campanha. Entram os parceiros com movimento no período de onde a previsão parte; quem não tem previsão aparece com o motivo, e não com zero (RN09). O risco mínimo é um filtro de quem consulta, e não um limiar do sistema. | M | GES, ANL |
| **RF46** | O sistema deve gerar o relatório de um plano de campanha, resumido por ação, por categoria e por segmento, com parceiros, custo e ganho esperado. | M | GES, ANL |
| **RF47** | O sistema deve gerar o relatório das operações registradas na trilha de auditoria, por tipo de ação, por usuário e por dia, num intervalo de datas. Sem datas, vale o dos últimos trinta dias; o dia é o do relógio do servidor, como nos filtros da trilha. | S | ADM |
| **RF48** | O sistema deve permitir exportar cada relatório em CSV, com o recorte aplicado, e imprimi-lo ou salvá-lo em PDF. | M | GES, ANL, ADM |
| **RF49** | O sistema deve permitir buscar por texto na trilha de auditoria e exportá-la em CSV, com o recorte aplicado. | S | ADM |
| **RF50** | O sistema deve exibir, no cadastro do parceiro, o histórico das alterações do próprio cadastro, com autor e data. O histórico diz o que mudou: o nome e o status com o valor de antes e o de depois, e a categoria pelo nome que tinha na hora. O contato entra como alterado, sem o valor — é dado de uma pessoa, e a trilha não se apaga. | S | GES, ANL |
| **RF51** | O sistema deve permitir filtrar o histórico de execuções do otimizador por modo, resultado, autor e data. | S | GES, ANL, ADM |
| **RF52** | O sistema deve permitir buscar usuário por nome ou login. | S | ADM |
| **RF53** | O sistema deve permitir exportar em CSV os itens de um plano de campanha. | S | GES, ANL |

### Módulo 8 — Conta, ajuda e vínculo do parceiro

Acrescentado em 02/10/2026, para a Sprint 08 da disciplina, que pede todas as funcionalidades implementadas. O
levantamento achou três coisas que faltavam para o sistema ser usado sem a API na mão: quem esquecia a senha não
tinha como voltar, a conta de perfil Parceiro só se criava pela API, e não havia ajuda. O RF07 — trocar a
própria senha — já existia e ganha a tela nesta sprint, sem mudar de texto.

| ID | Requisito | Prioridade | Perfis |
|---|---|---|---|
| **RF54** | O sistema deve permitir ao Administrador redefinir a senha de outro usuário. A senha nova passa pela mesma validação de força da criação; todas as sessões abertas da conta são encerradas na hora; e o evento entra na trilha de auditoria, sem a senha. A própria senha, o Administrador troca pelo RF07, que exige a atual. | M | ADM |
| **RF55** | O sistema deve oferecer uma tela de ajuda com o significado dos termos que usa — os segmentos, na ordem de precedência da RN01, a estimativa e o ganho esperado — e com o que o perfil de quem lê pode fazer. Os valores das regras exibidos vêm da configuração em vigor. O perfil Parceiro recebe só a ajuda do próprio portal, sem a classificação da rede (RF26). | S | todos |
| **RF56** | O sistema deve permitir ao Administrador localizar um parceiro pelo nome para vinculá-lo a uma conta de perfil Parceiro (RF04). A busca devolve apenas o nome e a situação do parceiro — nada de desempenho, segmento, categoria ou contato —, e não lhe dá o cadastro nem a lista de parceiros, que continuam do Gestor e do Analista. | M | ADM |

> **Total: 56 requisitos funcionais** — 37 *Must*, 16 *Should*, 3 *Could*.

---

## Parte II — Requisitos Não Funcionais

### Desempenho e escalabilidade

| ID | Requisito | Métrica de aceitação |
|---|---|---|
| **RNF01** | O otimizador em GPU deve resolver o **cenário de referência** (2.000 parceiros e 5 tipos de ação) em tempo compatível com uso interativo. | Até 5 s de ponta a ponta |
| **RNF02** | O otimizador em GPU deve apresentar ganho mensurável sobre o baseline serial em Python, com qualidade de solução equivalente. | Speedup de no mínimo 5x, com uplift esperado dentro de 2% do obtido pelo baseline |
| **RNF03** | O painel principal deve responder dentro do limiar de percepção de fluidez para bases de porte realista. | Até 2 s para até 5.000 parceiros |
| **RNF04** | O sistema deve suportar a carga máxima prevista sem degradação funcional. | 10.000 parceiros e 52 períodos importados e consultáveis |
| **RNF05** | As consultas ao histórico devem usar índices adequados, evitando varredura completa das tabelas de métricas. | Plano de execução sem varredura sequencial nas consultas do painel |

### Portabilidade e disponibilidade

| ID | Requisito | Métrica de aceitação |
|---|---|---|
| **RNF06** | O sistema deve funcionar em máquinas **sem GPU compatível**, recorrendo automaticamente ao modo CPU paralelo. | Execução completa do fluxo em máquina sem GPU, com aviso informativo na interface |
| **RNF07** | O ambiente completo deve subir com um único comando, sem etapas manuais de configuração. | `docker compose up` a partir de um clone limpo |
| **RNF08** | O sistema deve funcionar nas versões atuais dos navegadores de maior uso. | Chrome, Edge e Firefox nas duas versões mais recentes |

### Segurança

| ID | Requisito | Métrica de aceitação |
|---|---|---|
| **RNF09** | As senhas devem ser armazenadas exclusivamente como hash com algoritmo de derivação lenta e sal por usuário. | bcrypt ou Argon2; nenhuma senha em texto claro no banco ou em log |
| **RNF10** | A sessão deve trafegar em cookie com as marcações `HttpOnly` e `SameSite`, e o identificador de sessão deve ser renovado no momento da autenticação. | Verificado por teste automatizado de segurança |
| **RNF11** | O sistema deve bloquear temporariamente novas tentativas de autenticação após sucessivas falhas a partir de uma mesma origem, e deve responder de forma idêntica para usuário inexistente e senha incorreta. | Bloqueio após 5 falhas; resposta indistinguível entre os dois casos |
| **RNF12** | Toda saída de dado originado do usuário ou do modelo de linguagem deve ser escapada antes de chegar ao navegador. | Teste automatizado com carga de injeção de script |
| **RNF13** | Todo acesso ao banco deve usar consultas parametrizadas, sem concatenação de entrada do usuário. | Revisão de código e teste automatizado com carga de injeção SQL |
| **RNF14** | A autorização por perfil deve ser verificada no servidor em todos os endpoints, nunca apenas na interface. | Teste automatizado tentando acessar cada endpoint com cada perfil |
| **RNF15** | O sistema deve limitar o tamanho das entradas aceitas para evitar consumo excessivo de recursos. | Limite explícito para relatório importado e para pergunta ao assistente |

### Confiabilidade e rastreabilidade

| ID | Requisito | Métrica de aceitação |
|---|---|---|
| **RNF16** | Ranking, segmentação e cálculo de métricas devem ser **determinísticos**: o modelo de linguagem não participa de nenhum cálculo numérico. | Reprocessar a mesma base produz resultado idêntico, verificado por teste |
| **RNF17** | Toda resposta do assistente deve citar o período e a origem dos dados, ou declarar a insuficiência de dados. | Verificação por conjunto de perguntas de teste, incluindo perguntas sem resposta possível nos dados |
| **RNF18** | Erros devem retornar mensagem genérica ao cliente, com o detalhe técnico registrado apenas no log do servidor. | Nenhum rastreamento de pilha exposto na resposta da API |
| **RNF19** | O sistema deve registrar log estruturado dos erros, com identificador de correlação que permita associar a resposta ao evento no log. | Identificador presente na resposta de erro e no log |

### Usabilidade e acessibilidade

| ID | Requisito | Métrica de aceitação |
|---|---|---|
| **RNF20** | A interface deve estar integralmente em português e ser operável sem treinamento formal. | Um usuário novo completa o fluxo importar, analisar e otimizar sem consultar documentação |
| **RNF21** | A interface deve ser responsiva para desktop e tablet. | Layout funcional a partir de 768 px de largura |
| **RNF22** | O texto deve atender ao contraste mínimo do nível AA das diretrizes de acessibilidade. | Razão de contraste de no mínimo 4,5:1 para texto normal, verificada por ferramenta |
| **RNF23** | Operações longas devem informar o progresso e nunca deixar a interface sem retorno visual. | Indicador de progresso em importação e em execução do otimizador |

### Manutenibilidade e processo

| ID | Requisito | Métrica de aceitação |
|---|---|---|
| **RNF24** | O núcleo de regras de negócio deve ter cobertura de testes automatizados adequada. | Cobertura de no mínimo 70% nos módulos de segmentação, ranking, previsão e otimização |
| **RNF25** | Toda alteração deve chegar ao ramo principal por Pull Request revisado por outro integrante. | Regra de proteção configurada no repositório; nenhum push direto em `main` |
| **RNF26** | A integração contínua deve executar análise estática e a suíte de testes a cada Pull Request. | Fluxo de CI obrigatório e verde antes da mesclagem |
| **RNF27** | A documentação deve permitir a um terceiro executar o sistema do zero. | Um integrante que não escreveu o código sobe o ambiente seguindo apenas o README |

### Privacidade

| ID | Requisito | Métrica de aceitação |
|---|---|---|
| **RNF28** | O sistema não deve coletar nem armazenar dados pessoais de consumidores finais; os dados tratados referem-se a pessoas jurídicas parceiras. | Modelo de dados sem entidade de consumidor final |
| **RNF29** | O repositório não deve conter dados reais de nenhuma operação; toda massa de demonstração deve ser sintética. | `.gitignore` bloqueando arquivos de dados e verificação antes de cada entrega |

> **Total: 29 requisitos não funcionais.**

---

## Parte III — Rastreabilidade

Cada requisito funcional está vinculado ao objetivo que atende, ao sub-problema que endereça e ao caso de uso
que o exercita. Casos de uso detalhados em [03 — Casos de uso](03-casos-de-uso.md). A matriz que segue até a
rota, a tela e o teste de cada requisito está em [11 — Rastreabilidade](11-rastreabilidade.md).

| Requisitos | Objetivo | Sub-problema | Casos de uso |
|---|---|---|---|
| RF01 a RF08 | O8 | transversal | UC01, UC02, UC14 |
| RF09 a RF13 | O1 | P1 | UC03 |
| RF14 a RF16 | O1, O2 | P1 | UC04 |
| RF17 a RF19 | O2 | P1 | UC05 |
| RF20 a RF21 | O3 | P2, P3 | UC05 |
| RF22 | O3 | P3 | UC06 |
| RF23 a RF26 | O2 | P1, P3 | UC05, UC13 |
| RF27 a RF28 | O4 | P2 | UC07 |
| RF29 a RF31, RF35 | O5 | **P4** | UC08 |
| RF32 a RF34 | O6 | **P4** | UC09 |
| RF36 a RF40 | O7 | P5 | UC10, UC11 |
| RF41 a RF43 | O2 | P1 | UC12 |
| RF44 a RF48 | O2, O4, O5, O8 | P1, P2, **P4** | UC15 |
| RF49, RF52 | O8 | transversal | UC14, UC02 |
| RF50 | O1 | P1 | UC04 |
| RF51, RF53 | O5, O6 | **P4** | UC08, UC09 |
| RF54, RF56 | O8 | transversal | UC02 |
| RF55 | O8 | transversal | UC16 |

### Cobertura inversa: de objetivo para requisito

| Objetivo | Requisitos que o realizam |
|---|---|
| O1 — Ingerir e normalizar | RF09, RF10, RF11, RF12, RF13, RF14, RF16, RF50 |
| O2 — Métricas e séries | RF17, RF18, RF19, RF23, RF24, RF25, RF41, RF42, RF44, RF48 |
| O3 — Segmentar | RF20, RF21, RF22 |
| O4 — Prever | RF27, RF28, RF45 |
| O5 — Otimizar | RF29, RF30, RF31, RF35, RF46, RF53 |
| O6 — Acelerar | RF32, RF33, RF34, RF51 |
| O7 — Comunicar com aprovação | RF36, RF37, RF38, RF39, RF40 |
| O8 — Controlar acesso | RF01, RF02, RF03, RF04, RF05, RF06, RF07, RF08, RF47, RF49, RF52, RF54, RF55, RF56 |

Nenhum objetivo está sem requisito, e nenhum requisito funcional está órfão de objetivo.

---

## Parte IV — Regras de negócio

Regras que atravessam vários requisitos e precisam valer de forma uniforme.

### RN01 — Segmentação com precedência explícita

Cada parceiro recebe **exatamente um** segmento. Quando mais de um critério se aplica, a ordem de precedência
decide:

| Ordem | Segmento | Critério |
|---|---|---|
| 1 | **Prospecção** | Marcado manualmente; ainda não converteu |
| 2 | **Recém-chegado** | Possui menos períodos de histórico que o limiar de recém-chegado |
| 3 | **Em Risco** | Queda de faturamento em tantos períodos consecutivos quanto o limiar de tendência, ou mais |
| 4 | **Top** | Está entre os N maiores por faturamento no período mais recente |
| 5 | **Em Ascensão** | Crescimento em tantos períodos consecutivos quanto o limiar de tendência, ou mais, fora do Top N |
| 6 | **Estável** | Nenhum critério anterior se aplica |

**Em Risco vence Top deliberadamente.** É o que permite ao painel responder à pergunta *quem está prestes a
sair do Top N?* Um parceiro entre os maiores, mas em queda consecutiva, precisa aparecer como risco, não
diluído entre os campeões.

**Os três limiares, e o valor de fábrica de cada um.** O Administrador os muda sem alteração de código
(RF21), e a mudança reclassifica o período mais recente.

| Limiar | De fábrica | De onde vem o valor |
|---|--:|---|
| Tamanho do Top (N) | **15** | O problema que o produto ataca, em `docs/01`: a atenção concentrada no Top 15 |
| Períodos de tendência | **2** | Duas quedas seguidas já são padrão, e não oscilação; uma só não classifica ninguém |
| Períodos de recém-chegado | **3** | A premissa de `docs/01`, seção 6: com menos de 3 períodos de histórico, tendência não faz sentido |

O limiar de tendência é **um só**, para a queda e para a alta: com dois números, daria para exigir três
quedas para o risco e uma alta para a ascensão, e o mesmo parceiro oscilando mudaria de segmento a cada
semana. O limiar de recém-chegado não estava escrito aqui até 02/10/2026 — a regra dizia só "o limiar
configurado", e o valor estava no código (issue #59).

**O nome do segmento é "Top", sem o número.** O número é o do limiar em vigor, e aparece onde importa: na
mobilidade do painel, na ajuda e na configuração. Até a Sprint 08 o rótulo era "Top 15", fixo, e continuava
dizendo 15 com o limiar em outro valor (issue #229).

### RN02 — Mobilidade do Top N lê o ranking, não o segmento

O cálculo de entradas e saídas do Top N compara a **posição no ranking por faturamento** entre dois períodos.
Não pode ser derivado do segmento armazenado: como Em Risco tem precedência sobre Top (RN01), um parceiro
entre os N maiores mas em queda fica gravado como Em Risco, e lê-lo dali faria o sistema anunciar que ele
saiu do Top N enquanto ele continua lá.

### RN03 — Período é obrigatório na importação

O relatório de origem não carrega datas. Sem o período informado pelo usuário, as métricas ficam órfãs na
linha do tempo e a segmentação por tendência classifica errado **sem emitir erro**. Por isso a importação sem
período é recusada na entrada (RF10), e não tolerada com um valor padrão.

### RN04 — Ticket médio é derivado, nunca importado

Ticket médio = faturamento dividido pelo número de pedidos, calculado no momento da consulta. Não é
armazenado como campo independente, para não divergir das parcelas que o originam.

### RN05 — Categoria sugerida não é categoria confirmada

Uma categoria inferida a partir do nome permanece marcada como sugestão até que um usuário a confirme. Ações
comerciais por categoria só consideram categorias confirmadas, o que evita que um parceiro classificado por
engano entre numa campanha à qual não pertence.

**Como a categoria é inferida** (RF15, H27 — regra aprovada na issue #35):

1. O nome é comparado **sem acento e sem caixa**, por **palavra inteira** — "Pet" casa com "Pet Shop do
   Vale", e não com "Carpete".
2. Se as palavras apontarem para **exatamente uma** categoria, ela é sugerida, com origem `INFERIDA`.
3. Se não apontarem para nenhuma, **ou para mais de uma**, não há sugestão. Branco é resultado aceitável.
4. Só se sugere categoria que **existe e está ativa** na base.
5. A sugestão acontece em dois lugares: na importação, para os parceiros novos; e no cadastro manual, como
   sugestão que a pessoa usa, troca ou ignora. Salvar o cadastro com a categoria a confirma (`MANUAL`).

| Categoria | Palavras no nome |
|---|---|
| Pizzaria | pizza, pizzas, pizzaria |
| Padaria | padaria, panificadora, pão, pães |
| Lanchonete | lanche, lanches, lanchonete, burger, hambúrguer, hamburgueria |
| Restaurante | restaurante, marmita, marmitaria, churrascaria |
| Açaí e sorvetes | açaí, sorvete, sorvetes, sorveteria |
| Mercado | mercado, mercadinho, minimercado, supermercado, mercearia |
| Bebidas | bebidas, adega |
| Farmácia | farmácia, drogaria |
| Petshop | pet, petshop |
| Gás e água | gás, botijão, "água mineral" (as duas palavras juntas) |

Ficam de fora, de propósito, palavras que não dizem a categoria: forno, cantina, empório, casa, esquina,
sabor, cozinha, distribuidora, e "água" sozinha. Um parceiro "pendente de classificação" é o que não tem
categoria **confirmada** — em branco ou só sugerida.

### RN06 — Nenhuma mensagem sai sem aprovação humana

A transição de uma mensagem para o estado aprovado exige ação explícita de um usuário com perfil Gestor
(RF39). Não há aprovação automática, nem por decurso de prazo, nem por regra de confiança do modelo.

### RN07 — O plano de campanha respeita todas as restrições ou não existe

O otimizador não entrega solução parcialmente inviável. Se as restrições configuradas forem incompatíveis
entre si, o sistema informa a inviabilidade e indica qual restrição foi violada (RF31).

### RN08 — O modelo de linguagem não produz número

Todo valor numérico exibido pelo assistente precisa ter sido calculado pelo núcleo determinístico e apenas
citado na redação (RF43, RNF16). O modelo redige; ele não conta, não soma e não compara.

### RN09 — Queda prevista é entrar em risco, e o modelo exige histórico

A "probabilidade de queda" do RF28 e da H43 é a probabilidade de o parceiro estar **Em Risco no período
seguinte**, pelo critério da RN01: a sequência de quedas consecutivas chegar ao limiar de tendência (de
fábrica, 2 períodos). Para quem já está em risco, é a probabilidade de continuar. Regra decidida na issue #85.

1. **O rótulo do treino sai da mesma regra que classifica o segmento.** Modelo e segmentação nunca discordam
   sobre o que é queda, e mudar o limiar na configuração (RF21) muda os dois juntos.
2. **O treino exige 8 períodos na base.** Abaixo disso é recusado, dizendo quantos faltam (UC07, E1). São
   quatro de janela de variáveis, dois para treinar, um para validar e um para testar, separados no tempo.
3. **Parceiro com menos de 4 períodos de histórico não recebe previsão**, porque 4 é a janela de variáveis.
   Parceiro que não aparece no período mais recente também não. Nos dois casos, a tela diz por quê.
4. **Versão que não supera a referência não entra em uso** (UC07, A1). Sem versão anterior, as previsões
   saem da melhor referência, identificadas como tal.
5. **Previsão é estimativa e aparece como tal**, com o período-base e a versão que a produziu (H44).

### RN10 — O ganho esperado de uma ação soma crescimento e perda evitada

O ganho esperado (*uplift*) de aplicar a ação *a* ao parceiro *i* no próximo período é:

```
u(i,a) = F̂ᵢ · cₐ  +  F̂ᵢ · pᵢ · rₐ
```

- **F̂ᵢ** é o faturamento previsto e **pᵢ** a chance de o parceiro estar em risco no próximo período (RN09).
  As duas vêm da previsão da versão em uso.
- **cₐ** é o efeito de crescimento da ação: a fração do faturamento previsto que ela acrescenta.
- **rₐ** é o efeito de retenção: a fração do faturamento que ela preserva quando o parceiro cairia.

As duas saídas do modelo entram no plano. Uma ação de retenção vale mais para quem está prestes a cair, e
uma de crescimento vale mais para quem fatura mais. Os efeitos são atributos do catálogo de ações, editáveis
pelo Gestor (RF29). Os valores da base de demonstração são dado sintético, e não regra.

O ganho é calculado pela API, em **centavos inteiros**. O núcleo recebe o valor pronto e não faz conta de
dinheiro em ponto flutuante: é o que permite às três versões do otimizador chegarem ao mesmo plano (ADR-011).
Regra decidida na issue #117.

### RN11 — Quem recebe ação, e como as cotas contam

1. **Só é elegível o parceiro ativo que tem previsão da versão em uso.** Os demais ficam fora do plano, e o
   resultado diz quantos ficaram fora e por quê: histórico curto, ausência no período mais recente,
   inativo ou em prospecção. Sem previsão não há ganho a calcular, e estimar um no lugar seria seguir com
   dado parcial (`CLAUDE.md`, §7).
2. **Cota é fração do número máximo de ações K e vira contagem:** o mínimo arredonda para cima e o máximo
   para baixo. Com K = 45, uma cauda longa de pelo menos 30% exige ⌈13,5⌉ = 14 ações. Se a cota fosse fração
   das ações que o plano acabou escolhendo, o plano vazio cumpriria qualquer uma (30% de zero é zero), e
   nenhuma cota jamais tornaria a campanha inviável (RN07).
3. **Cotas por categoria:** mínimo e máximo opcionais, por categoria **confirmada** do parceiro.
4. **Cota da cauda longa:** um mínimo opcional. A cauda longa é quem está **fora do Top N no ranking do
   período-base** das previsões. É a mesma leitura da RN02: o ranking, e nunca o segmento armazenado.
5. **Parceiro pendente de classificação recebe ação normalmente.** Conta no total e na cauda longa, mas em
   nenhuma cota de categoria: sugestão não é categoria confirmada (RN05).

Com as cotas em contagem, a viabilidade é **decidida com exatidão antes da busca** (RF31, RN07). Nenhuma
ação custa menos que a mais barata do catálogo, e todo parceiro pode recebê-la; então os mínimos cabem na
campanha se, e somente se, o menor conjunto que os cumpre couber no máximo de ações e no orçamento pagando a
ação mais barata. A recusa nomeia a restrição e diz quanto falta. Regra decidida na issue #117.

### Onde cada regra está, e como é conferida

Revisão de 02/10/2026 (H99). Cada regra tem um lugar no código, testes automatizados que a cobram a cada
Pull Request, e um cenário no roteiro `scripts/revisar_regras.py`, que monta uma rede pequena desenhada para
cair em cada ramo, passa-a pela aplicação e compara o que voltou com o que a regra manda. O resultado, regra
a regra, está em [`medicoes/regras.md`](medicoes/regras.md).

| Regra | Onde está no código | Teste que a cobra |
|---|---|---|
| RN01 | `api/app/servico_segmentacao.py`, `classificar` e `Limiares` | `api/tests/test_segmentacao.py` — os seis ramos e a ordem da precedência |
| RN02 | `api/app/ranking.py` e `api/app/rotas/painel.py`, `mobilidade` | `api/tests/test_painel.py::test_top_em_queda_nao_aparece_como_saida` |
| RN03 | `api/app/esquemas.py`, `PedidoImportacao`, e `api/app/erros.py` | `api/tests/test_importacao.py::test_sem_periodo_a_importacao_e_recusada` |
| RN04 | `api/app/calculos.py`, `ticket_medio` | `api/tests/test_importacao.py::test_ticket_medio_nao_e_gravado` |
| RN05 | `api/app/sugestao_categoria.py` e `api/app/servico_importacao.py` | `api/tests/test_sugestao_categoria.py` |
| RN06 | `api/app/rotas/mensagens.py` e `api/app/servico_aprovacao.py` | `api/tests/test_aprovacao.py` — o Analista não decide, e o banco recusa decisão sem autor |
| RN07 | `nucleo/gih_nucleo/viabilidade.py` e `api/app/servico_otimizacao.py` | `nucleo/tests/test_viabilidade.py` e `api/tests/test_campanha.py::test_campanha_inviavel_diz_quanto_falta` |
| RN08 | `api/app/guarda_numerica.py` | `api/tests/test_guarda_numerica.py` e `api/tests/test_assistente.py::test_numero_inventado_nunca_chega_a_tela` |
| RN09 | `api/app/servico_previsao.py` e `modelo/gih_modelo/variaveis.py` | `api/tests/test_previsao.py` e `modelo/tests/test_variaveis.py::test_os_minimos_sao_os_da_rn09` |
| RN10 | `api/app/servico_otimizacao.py`, `ganho_em_centavos` | `api/tests/test_campanha.py::test_o_ganho_de_cada_item_e_o_da_rn10` |
| RN11 | `api/app/servico_otimizacao.py` | `api/tests/test_campanha.py::test_quem_fica_fora_e_contado_por_motivo` e `::test_a_cauda_longa_vem_do_ranking_e_nao_do_segmento` |

**O que a revisão achou e ajustou:**

- **RN01 não dizia o limiar de recém-chegado** (issue #59). O valor, 3, estava só no código. Passou a estar
  na regra, com a origem dele, junto dos outros dois.
- **RN01 e RN09 escreviam "2 períodos" como número fixo**, e o limiar é configurável desde a H34. As duas
  passaram a dizer "o limiar de tendência", com o 2 como valor de fábrica.
- **O rótulo "Top 15" era fixo** (issue #229), na interface, nos arquivos exportados e nas respostas do
  assistente. Com o limiar em 10, o sistema classificava dez parceiros e chamava o segmento de "Top 15". O
  rótulo passou a ser "Top".
- **O `CLAUDE.md` listava cinco segmentos**, sem a Prospecção, onde a RN01 tem seis.

Nenhuma regra foi achada com o comportamento errado: as 79 conferências do roteiro passaram. E o roteiro
acusa regra quebrada — com a precedência de Em Risco e Top invertida de propósito no código, quatro
conferências da RN01 e da RN02 falharam.
