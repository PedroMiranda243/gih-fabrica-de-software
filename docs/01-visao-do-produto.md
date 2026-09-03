# 01 — Visão do Produto

**Projeto:** Growth Intelligence Hub (GIH)
**Disciplinas:** Fábrica de Software · Tópicos Avançados — UNINASSAU, 2026.2
**Sprint:** 1 — Planejamento e Descoberta
**Versão:** 1.0 — 03/09/2026

---

## 1. Tema

**Growth Intelligence Hub (GIH)** — plataforma de inteligência de crescimento para redes de parceiros em
marketplaces regionais de delivery.

O sistema recebe os relatórios periódicos de desempenho de uma rede de comércios parceiros e devolve
**decisões priorizadas**: quem está crescendo, quem está prestes a cair, e — dado um orçamento e uma equipe
limitados — exatamente em quais parceiros investir a próxima rodada de ações comerciais.

### Domínio de aplicação

Marketplaces regionais de delivery operam por franquia ou licença local. Uma unidade típica intermedeia
pedidos entre consumidores de uma cidade ou microrregião e uma rede de 50 a 500 comércios parceiros
(restaurantes, mercados, farmácias, distribuidoras de água e gás, petshops). A unidade recebe do painel da
plataforma nacional um relatório periódico com o desempenho de cada parceiro, e é responsável por
desenvolver comercialmente essa base.

### Por que este tema

| Critério da disciplina | Como o tema atende |
|---|---|
| Resolver um **problema real** | O problema nasce de um cenário operacional concreto: redes regionais que gerenciam a base comercial sem qualquer ferramenta analítica |
| **Complexidade compatível com um TCC** | Ingestão, modelagem temporal, regras de segmentação, aprendizado de máquina, otimização combinatória, paralelismo e GPU, controle de acesso e auditoria |
| Permitir **evolução** ao longo do semestre | Sete sprints com entregas independentes e cumulativas, cada uma executável |
| Ser **viável** no prazo | Escopo fatiado por módulo; o núcleo pesado tem *spike* técnico antecipado para a Sprint 3 |
| **Funcionalidades suficientes** | 36 requisitos funcionais em 6 módulos integrados |
| Componente **de IA / otimização / GPU** não decorativo | O motor de decisão *é* o produto — sem ele o sistema vira um painel passivo |

---

## 2. Definição do problema

### 2.1 A situação

Numa operação regional de delivery, a atenção comercial se concentra nos parceiros de maior faturamento —
o **Top 15**. É uma escolha racional a curto prazo: são eles que sustentam a receita. Mas produz três efeitos
que se realimentam:

1. Os parceiros fora do topo — a **cauda longa**, tipicamente 85% da base — passam meses sem contato.
2. Sem estímulo, a cauda longa não cresce, e o ranking permanece **imóvel**: os mesmos nomes no topo,
   período após período.
3. Como o topo é sempre o mesmo, ele também não é desafiado — e estagna.

Ao mesmo tempo, os dados chegam em formato que não sustenta análise. O painel da plataforma mostra o número
do período atual em texto corrido. Não há série histórica, não há comparação automática com o período
anterior, não há alerta. O gestor vê o retrato, nunca o filme.

### 2.2 Os sub-problemas

| ID | Sub-problema | Consequência operacional |
|---|---|---|
| **P1** | Dados sem visualização analítica — texto corrido, sem série histórica nem comparação entre períodos | Tendências passam despercebidas; a leitura dos dados depende de esforço manual repetido a cada período |
| **P2** | Queda de parceiro é detectada tarde | Quando a perda vira evidente no faturamento, o parceiro já pode ter migrado para o concorrente ou reduzido a operação |
| **P3** | Cauda longa sem processo de relacionamento contínuo | Ranking imóvel; potencial de crescimento não explorado em ~85% da base |
| **P4** | **A alocação do esforço comercial é decidida por intuição** | Verba de cupom e agenda da equipe — recursos escassos — são distribuídas sem critério explícito nem verificação posterior de retorno |
| **P5** | Comunicação com parceiros é manual, individual e sem segmentação | Ações de categoria (ex.: campanha de uma categoria específica) exigem esforço proporcional ao número de parceiros, e por isso não acontecem |

### 2.3 O problema central

> **P4 é o núcleo técnico do projeto.**

Escolher em quais parceiros aplicar quais ações, respeitando orçamento, capacidade da equipe e cotas por
categoria, para maximizar o retorno esperado, é um **problema de otimização combinatória com restrições**.

O espaço de busca cresce exponencialmente: com *N* parceiros e *A* tipos de ação, existem (A+1)^N planos
possíveis. Para 200 parceiros e 4 tipos de ação, isso já ultrapassa 10^139 combinações — inviável por força
bruta e igualmente inviável de resolver "no olho".

É exatamente o tipo de problema que justifica **metaheurística paralelizada e aceleração em GPU** — e é a
ponte natural entre as duas disciplinas: a Fábrica de Software entrega o produto completo em torno dele,
Tópicos Avançados entrega o motor.

### 2.4 Por que este problema é relevante

**Para a operação.** A cauda longa concentra a maior parte do potencial de crescimento não explorado: são
85% dos parceiros recebendo uma fração da atenção comercial. Um parceiro que sai da base não é apenas uma
receita perdida — é um restaurante que passa a operar só no concorrente, e reconquistá-lo custa muito mais
do que teria custado mantê-lo. O alerta que chega um período antes é a diferença entre uma conversa de
retenção e uma perda consumada.

**Para os parceiros.** São comércios pequenos, quase sempre sem estrutura de marketing. Para eles, entrar
numa campanha bem escolhida é acesso a demanda que não conseguiriam gerar sozinhos. Quando a alocação é
feita por intuição, quem já é grande recebe mais — e a assimetria se aprofunda sozinha.

**Para a decisão.** Verba de incentivo e agenda da equipe são recursos escassos e disputados. Hoje a
escolha é feita sem critério explícito e, principalmente, **sem verificação posterior**: não se sabe se a
campanha da semana passada funcionou, porque nada foi medido contra uma previsão. Sem linha de base, não
existe aprendizado — apenas repetição.

**Para o campo técnico.** O problema não é uma desculpa para usar tecnologia; ele *exige* a tecnologia.
Priorizar ações sob restrições de orçamento, capacidade e cotas é otimização combinatória, e estimar o
retorno de cada ação é um problema de previsão. São duas classes de problema com solução conhecida e
mensurável — e é isso que permite avaliar objetivamente se a solução funcionou, comparando *speedup* e erro
de previsão contra baselines, em vez de opinar sobre a interface.

### 2.5 O que já se sabe que não resolve

| Alternativa | Por que não basta |
|---|---|
| Planilha | Não sustenta série histórica multi-período de centenas de parceiros, nem otimização com restrições |
| Assistente de IA genérico (ChatGPT e similares) | Responde sobre os dados colados, mas sem rastreabilidade, sem persistência, sem painel e sem garantia de consistência numérica entre duas perguntas iguais |
| BI genérico (Power BI, Metabase) | Mostra o passado. Não prevê, não otimiza e não fecha o ciclo até a ação |
| Contratar mais gente para o comercial | Custo recorrente; não resolve o critério de priorização, apenas aumenta o volume de contatos feitos sem critério |

O GIH se posiciona onde nenhum deles chega: **do dado bruto até o plano de ação otimizado**, num único fluxo.

---

## 3. Objetivos do sistema

### 3.1 Objetivo geral

Transformar os dados brutos de desempenho de uma rede de parceiros em um **plano de ação comercial
priorizado**, previsto por modelo treinado a partir do histórico e otimizado sob as restrições reais de
orçamento e capacidade da operação.

### 3.2 Objetivos específicos

| ID | Objetivo | Verificação |
|---|---|---|
| **O1** | Ingerir e normalizar relatórios periódicos de desempenho por parceiro, aceitando texto colado e arquivo CSV | Importação de um relatório de 500 parceiros gera 500 registros consistentes, com período obrigatório |
| **O2** | Calcular métricas derivadas e séries históricas por parceiro e para a unidade | Ticket médio, variação percentual e tendência disponíveis para qualquer parceiro com ≥ 2 períodos |
| **O3** | Segmentar automaticamente cada parceiro por regra determinística | A mesma base reprocessada produz exatamente a mesma segmentação |
| **O4** | Prever o faturamento do próximo período e o risco de queda de cada parceiro, com modelo treinado pela equipe | MAPE do modelo inferior ao de um baseline ingênuo (repetir o último período) em conjunto de teste separado |
| **O5** | Otimizar a alocação de ações comerciais sob restrições, maximizando o uplift esperado | O plano gerado respeita 100% das restrições e supera a heurística "investir nos maiores" em uplift esperado |
| **O6** | Acelerar o otimizador por paralelismo em CPU e GPU, com ganho medido | *Speedup* ≥ 5× em GPU sobre o baseline serial, no cenário de referência, com qualidade de solução equivalente |
| **O7** | Gerar mensagens de relacionamento por segmento, com aprovação humana obrigatória | Nenhuma mensagem transita para o estado "aprovada" sem ação explícita de um usuário autorizado |
| **O8** | Controlar o acesso por perfil, com trilha de auditoria das ações sensíveis | Toda ação sensível registra autor, data e parâmetros; usuário sem permissão recebe negação no servidor |

### 3.3 Indicadores de sucesso

**Do produto**

| Indicador | Definição | Meta |
|---|---|---|
| **Mobilidade do Top N** | Número de parceiros que entram ou saem do Top 15 entre dois períodos | Tornar o indicador visível e crescente — é a evidência de que o relacionamento ativo funcionou |
| Cobertura de relacionamento | Percentual da base que recebeu ao menos uma ação no período | Sair de uma cauda longa sem contato para cobertura planejada |
| Antecedência do alerta de risco | Períodos de antecedência com que o sistema sinaliza um parceiro antes da queda se confirmar | ≥ 1 período |

**Técnicos**

| Indicador | Meta |
|---|---|
| *Speedup* do otimizador (GPU × serial) | ≥ 5× no cenário de referência (2.000 parceiros × 5 tipos de ação) |
| Tempo de resposta do otimizador em GPU | ≤ 5 s no cenário de referência |
| MAPE do modelo preditivo | Inferior ao baseline ingênuo em conjunto de teste |
| Cobertura de testes no núcleo de regras | ≥ 70% |

---

## 4. Público-alvo

### 4.1 Perfil da organização usuária

Unidade regional de marketplace de delivery — franquia ou licenciada local — com:

- **50 a 500 comércios parceiros** ativos
- **1 a 3 pessoas** na equipe comercial
- Relacionamento predominantemente remoto, por aplicativo de mensagens
- **Sem** ferramenta de BI, **sem** analista de dados, **sem** equipe de tecnologia própria
- Verba de incentivo (cupons, campanhas) limitada e disputada entre parceiros

### 4.2 Usuários do sistema

| Perfil | Quem é | O que faz no sistema | Necessidade central |
|---|---|---|---|
| **Gestor(a) da operação** *(primário)* | Responsável pela unidade; decide onde investir | Consulta o painel, executa o otimizador, aprova mensagens, acompanha a mobilidade do ranking | Decidir rápido, com critério defensável, sem depender de analista |
| **Analista comercial** *(secundário)* | Executa o relacionamento no dia a dia | Importa relatórios, analisa parceiros, propõe campanhas, redige mensagens | Saber quem procurar hoje e com qual argumento |
| **Administrador** | Responsável técnico da operação | Gerencia usuários e perfis, ajusta parâmetros de segmentação, audita ações | Manter o sistema seguro e configurado sem mexer em código |
| **Parceiro** *(opcional)* | Comércio cadastrado na rede | Consulta exclusivamente o próprio desempenho | Enxergar o próprio resultado e a própria evolução |

### 4.3 Restrições impostas pelo público

O público-alvo condiciona decisões técnicas que aparecem nos requisitos não funcionais:

- **Interface em português e autoexplicativa** — não há treinamento formal nem suporte de TI interno (RNF12)
- **Instalação em um comando** — não há equipe para configurar ambiente (RNF18)
- **Funcionar sem GPU** — a máquina do usuário pode ser um notebook comum; a GPU acelera, mas o sistema
  precisa operar sem ela (RNF04)
- **Rastreabilidade das análises** — o gestor precisa justificar a decisão para a franqueadora e para os
  próprios parceiros, então toda resposta cita a fonte (RNF11)
- **Aprovação humana antes de qualquer envio** — a relação com o parceiro é ativo estratégico da unidade;
  nenhuma mensagem sai automaticamente (O7, RF33)

---

## 5. Escopo

### 5.1 Dentro do escopo

| Módulo | Entrega |
|---|---|
| M1 — Autenticação e perfis | Login, 4 perfis com permissões distintas, auditoria |
| M2 — Ingestão e dados | Importação por texto e CSV, validação, cadastro de parceiros, gerador de dados sintéticos |
| M3 — BI e segmentação | Dashboard, ranking com variação, séries históricas, segmentação, mobilidade do Top N, filtros, busca, exportação |
| M4 — Núcleo computacional | Modelo preditivo treinado, otimizador de campanhas, execução serial/CPU/GPU, benchmark, histórico e comparação de cenários |
| M5 — Comunicação | Geração de mensagens por segmento e fila de aprovação |
| M6 — Assistente | Consulta em linguagem natural com citação de fonte e abstenção |

### 5.2 Fora do escopo desta entrega

| Item | Motivo |
|---|---|
| Integração direta por API com plataformas de delivery | Depende de acesso concedido por terceiros; a ingestão por texto e CSV cobre o caso de uso |
| Envio efetivo das mensagens por aplicativo de mensageria | Exige dados de contato reais e conta habilitada; o sistema entrega a mensagem aprovada e pronta para envio |
| Aplicativo móvel nativo | A interface responsiva atende o uso em desktop e tablet |
| Operação multi-unidade (várias franquias na mesma instância) | Ampliaria o modelo de dados e o controle de acesso além do prazo do semestre |
| Leitura de dados por reconhecimento óptico de imagem | A importação por texto e CSV já cobre a entrada; agregaria risco sem agregar avaliação |

---

## 6. Premissas e restrições

**Premissas**

- Os relatórios de desempenho estão disponíveis em texto ou CSV, com uma linha por parceiro
- O período (data inicial e final) é informado pelo usuário no momento da importação — o relatório de origem
  não o traz embutido
- Existe histórico de ao menos 3 períodos para que a segmentação por tendência e a previsão façam sentido
- A operação possui um canal de comunicação já estabelecido com os parceiros

**Restrições**

- Prazo fixo: entrega final em **05/12/2026**
- Equipe de 5 integrantes, todos estudantes, com dedicação parcial
- Linguagens do núcleo restritas a Python, C e C++ por orientação da disciplina
- Hardware de desenvolvimento com GPU NVIDIA (RTX 4060, 8 GB) disponível em uma das estações; o sistema
  precisa degradar para CPU nas demais

---

## 7. Glossário

| Termo | Definição |
|---|---|
| **Parceiro** | Comércio cadastrado na rede que recebe pedidos pelo marketplace |
| **Cauda longa** | Conjunto de parceiros fora do Top N por faturamento — a maioria da base |
| **Período** | Janela de tempo de um relatório de desempenho (tipicamente uma semana) |
| **Segmento** | Classificação atribuída ao parceiro por regra determinística: Top, Em Ascensão, Em Risco, Recém-chegado, Prospecção ou Estável |
| **Mobilidade do Top N** | Quantidade de parceiros que entram ou saem do Top N entre dois períodos consecutivos |
| **Uplift** | Ganho incremental de faturamento atribuível a uma ação comercial |
| **Ação comercial** | Intervenção aplicável a um parceiro (cupom, campanha de categoria, visita, contato de reativação), com custo e efeito esperado |
| **Plano de campanha** | Conjunto de pares (parceiro, ação) selecionado pelo otimizador para um período |
| **Speedup** | Razão entre o tempo de execução do baseline serial e o da versão acelerada |
| **MAPE** | *Mean Absolute Percentage Error* — erro percentual médio do modelo preditivo |

---

## 8. Referências internas

- [02 — Requisitos](02-requisitos.md)
- [03 — Casos de uso](03-casos-de-uso.md)
- [04 — Product Backlog](04-product-backlog.md)
- [05 — Cronograma](05-cronograma.md)
- [07 — Arquitetura preliminar](07-arquitetura-preliminar.md)
