# 02 — Requisitos Funcionais e Não Funcionais

**Projeto:** Growth Intelligence Hub (GIH)
**Sprint:** 1 — Planejamento e Descoberta
**Versão:** 1.0 — 03/09/2026

---

## Como ler este documento

- **RF** — Requisito Funcional: o que o sistema faz.
- **RNF** — Requisito Não Funcional: como o sistema se comporta (desempenho, segurança, usabilidade).
- **Prioridade** segue MoSCoW: **M** *Must* (indispensável), **S** *Should* (importante), **C** *Could* (desejável).
- A coluna **Perfis** indica quais perfis acessam o requisito:
  **ADM** Administrador, **GES** Gestor, **ANL** Analista, **PAR** Parceiro.

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
| **RF17** | O sistema deve exibir um painel com os indicadores consolidados do período selecionado: faturamento total, número de pedidos, ticket médio, parceiros ativos e variação em relação ao período anterior. | M | GES, ANL |
| **RF18** | O sistema deve exibir o ranking de parceiros por faturamento, com a posição atual, a posição no período anterior e a variação percentual. | M | GES, ANL |
| **RF19** | O sistema deve exibir a série histórica em gráfico, tanto para a unidade quanto para um parceiro individual. | M | GES, ANL, PAR |
| **RF20** | O sistema deve classificar cada parceiro em exatamente um segmento (Top, Em Ascensão, Em Risco, Recém-chegado, Prospecção ou Estável) aplicando regra determinística com ordem de precedência explícita. | M | GES, ANL |
| **RF21** | O sistema deve permitir configurar os limiares da segmentação (tamanho do Top N, número de períodos de queda para caracterizar risco, número de períodos para caracterizar novo parceiro) sem alteração de código. | S | ADM |
| **RF22** | O sistema deve exibir a mobilidade do ranking entre dois períodos, listando quem entrou e quem saiu do Top N. | M | GES, ANL |
| **RF23** | O sistema deve permitir filtrar e ordenar a lista de parceiros por categoria, segmento, faturamento, número de pedidos, ticket médio e variação. | M | GES, ANL |
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
| **RF34** | O sistema deve registrar o histórico das execuções do otimizador com autor, data, parâmetros, modo de execução, tempo e resultado. | S | GES, ADM |
| **RF35** | O sistema deve permitir comparar lado a lado dois planos de campanha gerados com parâmetros diferentes. | C | GES |

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

> **Total: 43 requisitos funcionais** — 31 *Must*, 9 *Should*, 3 *Could*.

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
que o exercita. Casos de uso detalhados em [03 — Casos de uso](03-casos-de-uso.md).

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

### Cobertura inversa: de objetivo para requisito

| Objetivo | Requisitos que o realizam |
|---|---|
| O1 — Ingerir e normalizar | RF09, RF10, RF11, RF12, RF13, RF14, RF16 |
| O2 — Métricas e séries | RF17, RF18, RF19, RF23, RF24, RF25, RF41, RF42 |
| O3 — Segmentar | RF20, RF21, RF22 |
| O4 — Prever | RF27, RF28 |
| O5 — Otimizar | RF29, RF30, RF31, RF35 |
| O6 — Acelerar | RF32, RF33, RF34 |
| O7 — Comunicar com aprovação | RF36, RF37, RF38, RF39, RF40 |
| O8 — Controlar acesso | RF01, RF02, RF03, RF04, RF05, RF06, RF07, RF08 |

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
| 2 | **Recém-chegado** | Possui menos períodos de histórico que o limiar configurado |
| 3 | **Em Risco** | Queda de faturamento em 2 ou mais períodos consecutivos |
| 4 | **Top** | Está entre os N maiores por faturamento no período mais recente |
| 5 | **Em Ascensão** | Crescimento em 2 ou mais períodos consecutivos, fora do Top N |
| 6 | **Estável** | Nenhum critério anterior se aplica |

**Em Risco vence Top deliberadamente.** É o que permite ao painel responder à pergunta *quem está prestes a
sair do Top N?* Um parceiro entre os maiores, mas em queda consecutiva, precisa aparecer como risco, não
diluído entre os campeões.

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

### RN06 — Nenhuma mensagem sai sem aprovação humana

A transição de uma mensagem para o estado aprovado exige ação explícita de um usuário com perfil Gestor
(RF39). Não há aprovação automática, nem por decurso de prazo, nem por regra de confiança do modelo.

### RN07 — O plano de campanha respeita todas as restrições ou não existe

O otimizador não entrega solução parcialmente inviável. Se as restrições configuradas forem incompatíveis
entre si, o sistema informa a inviabilidade e indica qual restrição foi violada (RF31).

### RN08 — O modelo de linguagem não produz número

Todo valor numérico exibido pelo assistente precisa ter sido calculado pelo núcleo determinístico e apenas
citado na redação (RF43, RNF16). O modelo redige; ele não conta, não soma e não compara.
