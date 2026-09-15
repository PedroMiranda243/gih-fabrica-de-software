# 03 — Casos de Uso

**Projeto:** Growth Intelligence Hub (GIH)
**Sprint:** 1 — Planejamento e Descoberta
**Versão:** 1.0 — 03/09/2026

---

## 1. Atores

| Ator | Tipo | Descrição |
|---|---|---|
| **Administrador** | Primário | Responsável técnico da operação. Gerencia usuários, perfis e parâmetros do sistema; audita as ações registradas. Não participa da operação comercial. |
| **Gestor** | Primário | Responsável pela unidade. É quem decide: configura as restrições, executa o otimizador e acompanha a mobilidade do ranking. Tem acesso a tudo que é operacional. |
| **Analista** | Primário | Executa o relacionamento no dia a dia. Importa relatórios e analisa parceiros — mas **não executa o otimizador**, porque executá-lo é comprometer orçamento. |
| **Parceiro** | Primário | Comércio da rede. Acesso restrito ao próprio desempenho histórico. |
| **Modelo de Linguagem Local** | Secundário (sistema) | Serviço interno que responde ao assistente, se o módulo condicional for implementado. Nunca calcula números. |

> A separação entre **Gestor** e **Analista** é o que materializa a exigência de *diferentes perfis de
> usuários*: os dois enxergam o mesmo painel e analisam os mesmos dados, mas apenas o Gestor pode
> **comprometer recursos** — configurar o orçamento de uma campanha e disparar a otimização. O Analista
> prepara e propõe; o Gestor decide.

---

## 2. Diagrama de casos de uso

![Diagrama de casos de uso do GIH](diagramas/casos-de-uso.svg)

---

## 3. Visão geral dos casos de uso

| ID | Caso de uso | Ator principal | Requisitos cobertos |
|---|---|---|---|
| **UC01** | Autenticar no sistema | Todos | RF01, RF02, RF07 |
| **UC02** | Gerenciar usuários e perfis | Administrador | RF03, RF04, RF05 |
| **UC03** | Importar relatório de desempenho | Analista, Gestor | RF09, RF10, RF11, RF12, RF13 |
| **UC04** | Gerenciar parceiros e categorias | Analista, Gestor | RF14, RF15, RF16 |
| **UC05** | Consultar painel e ranking | Gestor, Analista | RF17, RF18, RF19, RF20, RF23, RF24, RF25 |
| **UC06** | Analisar mobilidade do Top N | Gestor, Analista | RF22 |
| **UC07** | Treinar modelo de previsão | Administrador, Gestor | RF27, RF28 |
| **UC08** | Configurar e executar otimização de campanha | Gestor | RF29, RF30, RF31, RF35 |
| **UC09** | Comparar desempenho serial, paralelo e GPU | Gestor, Administrador | RF32, RF33, RF34 |
| ~~**UC10**~~ | ~~Gerar mensagens por segmento~~ | — | **Fora do escopo** |
| ~~**UC11**~~ | ~~Aprovar ou rejeitar mensagem~~ | — | **Fora do escopo** |
| **UC12** | Consultar assistente analítico | Gestor, Analista | RF41, RF42, RF43 — **condicional** |
| **UC13** | Consultar meu desempenho | Parceiro | RF19, RF26 |
| **UC14** | Auditar ações do sistema | Administrador | RF06, RF08 |

### Matriz de permissões

| Caso de uso | ADM | GES | ANL | PAR |
|---|:--:|:--:|:--:|:--:|
| UC01 Autenticar | ● | ● | ● | ● |
| UC02 Gerenciar usuários | ● | — | — | — |
| UC03 Importar relatório | — | ● | ● | — |
| UC04 Gerenciar parceiros | — | ● | ● | — |
| UC05 Painel e ranking | ○ | ● | ● | — |
| UC06 Mobilidade do Top N | ○ | ● | ● | — |
| UC07 Treinar modelo | ● | ● | — | — |
| UC08 Executar otimização | — | ● | ○ | — |
| UC09 Benchmark | ● | ● | — | — |
| UC12 Assistente *(condicional)* | — | ● | ● | — |
| UC13 Meu desempenho | — | — | — | ● |
| UC14 Auditoria | ● | — | — | — |

● executa · ○ somente leitura · — sem acesso

---

## 4. Especificação detalhada

Detalhamento dos cinco casos de uso centrais do escopo comprometido. Os demais seguem o mesmo formato e
serão detalhados na Sprint 2, conforme o backlog.

---

### UC01 — Autenticar no sistema

| | |
|---|---|
| **Ator principal** | Todos os perfis |
| **Objetivo** | Obter acesso ao sistema conforme o perfil atribuído |
| **Pré-condições** | O usuário possui credenciais válidas e está ativo |
| **Pós-condições** | Sessão criada, identificador de sessão renovado e evento registrado na auditoria |
| **Requisitos** | RF01, RF02, RF05, RF06, RNF09, RNF10, RNF11 |

**Fluxo principal**

1. O usuário acessa o sistema e recebe a tela de autenticação.
2. Informa login e senha.
3. O sistema valida as credenciais contra o hash armazenado.
4. O sistema **renova o identificador de sessão** e cria a sessão com o perfil do usuário.
5. O sistema registra o evento na trilha de auditoria.
6. O sistema apresenta a área inicial correspondente ao perfil.

**Fluxos alternativos**

- **A1 — Credenciais inválidas.** No passo 3, o sistema retorna mensagem genérica de falha, **idêntica** para
  usuário inexistente e para senha incorreta, e incrementa o contador de tentativas da origem. Retorna ao
  passo 2.
- **A2 — Origem bloqueada.** Se a origem acumulou 5 falhas, o sistema recusa novas tentativas por 15 minutos,
  informando apenas que o acesso está temporariamente indisponível.
- **A3 — Usuário desativado.** O sistema responde com a mesma mensagem genérica de A1, sem revelar o estado
  da conta.

**Exceções**

- **E1 — Serviço de dados indisponível.** O sistema exibe mensagem genérica de indisponibilidade e registra o
  erro com identificador de correlação no log do servidor.

---

### UC03 — Importar relatório de desempenho

| | |
|---|---|
| **Ator principal** | Analista (também Gestor) |
| **Objetivo** | Incorporar ao sistema os dados de desempenho de um período |
| **Pré-condições** | Usuário autenticado com perfil Gestor ou Analista; relatório disponível em texto ou CSV |
| **Pós-condições** | Métricas do período gravadas, segmentação recalculada e importação registrada no histórico |
| **Requisitos** | RF09, RF10, RF11, RF12, RF13, RF20; regras RN03, RN04 |

**Fluxo principal**

1. O usuário abre a tela de importação.
2. Informa **a data inicial e a data final do período** — campos obrigatórios.
3. Cola o texto do relatório ou seleciona um arquivo CSV.
4. O sistema analisa o conteúdo e identifica, por parceiro, o faturamento e o número de pedidos.
5. O sistema apresenta uma **prévia** com: registros reconhecidos, registros rejeitados e o motivo de cada
   rejeição, além dos parceiros ainda não cadastrados.
6. O usuário confere a prévia e confirma.
7. O sistema grava as métricas, cadastra os parceiros novos e recalcula a segmentação de toda a base.
8. O sistema registra a importação no histórico com autor, data e período, e registra o evento na auditoria.
9. O sistema exibe o resumo: total gravado, total rejeitado e link para o painel do período.

**Fluxos alternativos**

- **A1 — Período não informado.** No passo 2, o sistema **recusa** o avanço e explica que sem o período as
  métricas não podem ser posicionadas na linha do tempo (RN03). Não há valor padrão.
- **A2 — Período já importado.** No passo 5, o sistema alerta que o período já existe e oferece duas opções
  explícitas: substituir os dados existentes ou cancelar. O padrão é cancelar.
- **A3 — Parceiros novos detectados.** No passo 5, o sistema lista os nomes ainda não cadastrados e **sugere**
  uma categoria para cada um, marcada como sugestão não confirmada (RN05). O usuário pode confirmar,
  corrigir ou deixar em branco.
- **A4 — Formato não reconhecido.** Se nenhuma linha for interpretável, o sistema informa que o formato não
  foi reconhecido e exibe as três primeiras linhas recebidas para ajudar o usuário a identificar o problema.
- **A5 — Rejeição parcial.** Se parte dos registros falhar na validação, o usuário pode prosseguir com os
  válidos; os rejeitados ficam listados no resumo para correção posterior.

**Exceções**

- **E1 — Entrada excede o limite.** O sistema recusa o conteúdo acima do tamanho máximo configurado e informa
  o limite (RNF15).
- **E2 — Falha durante a gravação.** A operação é revertida integralmente: ou o período inteiro entra, ou
  nada entra. O usuário recebe mensagem genérica e o erro vai para o log.

---

### UC05 — Consultar painel e ranking

| | |
|---|---|
| **Ator principal** | Gestor (também Analista) |
| **Objetivo** | Entender o desempenho da rede no período e identificar quem merece atenção |
| **Pré-condições** | Usuário autenticado; existe ao menos um período importado |
| **Pós-condições** | Nenhuma alteração de estado — caso de uso de consulta |
| **Requisitos** | RF17, RF18, RF19, RF20, RF23, RF24, RF25; regras RN01, RN04 |

**Fluxo principal**

1. O usuário acessa o painel.
2. O sistema apresenta os indicadores consolidados do período mais recente: faturamento total, número de
   pedidos, ticket médio, parceiros ativos e a variação de cada um em relação ao período anterior.
3. O sistema apresenta o gráfico da série histórica da unidade.
4. O sistema apresenta a lista de parceiros com posição no ranking, posição anterior, faturamento, pedidos,
   ticket médio, variação e **segmento**.
5. O usuário aplica filtros por categoria e segmento, ordena por qualquer coluna ou busca por nome.
6. O sistema atualiza a lista conforme os critérios.
7. O usuário seleciona um parceiro e o sistema exibe a série histórica individual.

**Fluxos alternativos**

- **A1 — Base vazia.** No passo 2, se não houver período importado, o sistema exibe um estado inicial
  orientando o usuário a importar o primeiro relatório, com atalho para UC03.
- **A2 — Período único.** Com apenas um período, não há comparação possível: o sistema exibe os valores
  absolutos e informa que variação e segmentação por tendência exigem histórico.
- **A3 — Exportação.** No passo 6, o usuário solicita a exportação e o sistema gera um CSV contendo
  exatamente a visão filtrada em tela (RF25).

**Exceções**

- **E1 — Consulta acima do limite de tempo.** Se a consulta exceder o tempo previsto em RNF03, o sistema
  apresenta o resultado paginado e registra a ocorrência para análise de desempenho.

---

### UC08 — Configurar e executar otimização de campanha

| | |
|---|---|
| **Ator principal** | Gestor |
| **Objetivo** | Obter o plano de ações comerciais que maximiza o retorno esperado dentro das restrições reais |
| **Pré-condições** | Usuário autenticado com perfil Gestor; modelo de previsão treinado (UC07); ao menos um período importado |
| **Pós-condições** | Plano de campanha gerado e persistido; execução registrada no histórico e na auditoria |
| **Requisitos** | RF29, RF30, RF31, RF32, RF34, RF35; regra RN07 |

**Fluxo principal**

1. O usuário abre a tela de campanha.
2. Informa os parâmetros: orçamento total, número máximo de ações, período de aplicação e o catálogo de ações
   disponíveis com o custo unitário de cada uma.
3. Opcionalmente define cotas por categoria — por exemplo, ao menos 30% das ações destinadas à cauda longa.
4. Opcionalmente escolhe o modo de execução; se não escolher, o sistema seleciona o modo disponível mais
   rápido (RF32).
5. O usuário dispara a otimização.
6. O sistema recupera, para cada parceiro elegível, o faturamento previsto e o risco de queda (UC07).
7. O sistema executa o otimizador, exibindo indicador de progresso.
8. O sistema apresenta o **plano de campanha**: a lista de pares parceiro-ação selecionados, o uplift total
   esperado, o custo total, a folga em relação a cada restrição e o tempo de execução.
9. O usuário pode exportar o plano de campanha para executá-lo fora do sistema.
10. O sistema registra a execução com autor, parâmetros, modo, tempo e resultado.

**Fluxos alternativos**

- **A1 — Restrições inviáveis.** No passo 7, se as restrições forem mutuamente incompatíveis — por exemplo,
  cota mínima por categoria que excede o orçamento —, o sistema **não retorna plano parcial** (RN07):
  informa a inviabilidade e aponta qual restrição foi violada.
- **A2 — Orçamento superior ao necessário.** Se o orçamento comportar ações para toda a base elegível, o
  sistema retorna o plano completo e informa a sobra, sugerindo ampliar o catálogo de ações.
- **A3 — Comparação de cenários.** O usuário executa uma segunda otimização com parâmetros diferentes e
  solicita a comparação lado a lado dos dois planos (RF35).
- **A4 — GPU indisponível.** Se o modo GPU for solicitado sem placa compatível, o sistema executa em CPU
  paralelo e informa a substituição, sem interromper a operação (RNF06).

**Exceções**

- **E1 — Modelo não treinado.** No passo 6, se não houver modelo treinado, o sistema interrompe e direciona
  o usuário para UC07.
- **E2 — Execução excede o tempo limite.** O sistema encerra a execução, preserva a melhor solução encontrada
  até o momento, sinaliza que o resultado é parcial e registra a ocorrência.

---

### UC09 — Comparar desempenho serial, paralelo e GPU

| | |
|---|---|
| **Ator principal** | Gestor (também Administrador) |
| **Objetivo** | Evidenciar, com medição, o ganho obtido pela paralelização e pela aceleração em GPU |
| **Pré-condições** | Usuário autenticado com perfil Gestor ou Administrador; cenário de dados carregado |
| **Pós-condições** | Resultados do benchmark persistidos e disponíveis para consulta |
| **Requisitos** | RF32, RF33, RF34; RNF01, RNF02, RNF06 |

**Fluxo principal**

1. O usuário abre a tela de benchmark.
2. Escolhe o cenário: número de parceiros, número de tipos de ação e número de repetições.
3. O sistema detecta os modos de execução disponíveis na máquina e apresenta a lista.
4. O usuário dispara o benchmark.
5. O sistema executa o **mesmo problema** em cada modo disponível, com a mesma semente aleatória.
6. O sistema apresenta a tabela comparativa: modo, tempo médio, desvio, *speedup* sobre o baseline serial e
   uplift da solução encontrada.
7. O sistema apresenta o gráfico de escalabilidade — tempo por modo em função do número de parceiros.
8. O sistema registra a execução no histórico.

**Fluxos alternativos**

- **A1 — Sem GPU.** No passo 3, o sistema informa que não há placa compatível e executa apenas os modos
  serial e CPU paralelo, mantendo o comparativo válido para os modos disponíveis.
- **A2 — Cenário pequeno demais.** Se o cenário for pequeno a ponto de o custo de transferência para a GPU
  dominar o tempo total, o sistema apresenta o resultado e **explica** que o ganho da GPU só aparece a partir
  de determinada escala — o resultado negativo é informação legítima, não erro.
- **A3 — Divergência de qualidade.** Se o uplift obtido por um modo divergir do baseline além da tolerância
  de 2% (RNF02), o sistema destaca a divergência como possível defeito de implementação.

**Exceções**

- **E1 — Falha no dispositivo de GPU.** O sistema captura o erro, marca o modo como indisponível para aquela
  execução, prossegue com os demais e registra o detalhe no log.

---

## 5. Casos de uso a detalhar na Sprint 2

UC02, UC04, UC06, UC07, UC12, UC13 e UC14 estão especificados no nível de objetivo, ator e requisitos
cobertos (seção 3). O detalhamento de fluxos entra no backlog da Sprint 2, junto com a modelagem de dados —
ver [04 — Product Backlog](04-product-backlog.md), épico E1.
