# Growth Intelligence Hub (GIH)

> Plataforma de inteligência de crescimento para redes de parceiros em marketplaces regionais de delivery.
> Transforma relatórios brutos de faturamento em um **plano de ação comercial priorizado** — previsto por
> modelo próprio e otimizado sob restrições reais de orçamento e capacidade, com aceleração em GPU.

**Projeto Integrador — Fábrica de Software + Tópicos Avançados · UNINASSAU · 2026.2**

---

## O problema

Operações regionais de delivery concentram a atenção comercial no **Top 15** de faturamento. A **cauda longa**
— frequentemente mais de 100 parceiros — não recebe processo de relacionamento, e o próprio Top 15 estagna:
os mesmos nomes ocupam o topo mês após mês.

Os dados existem no painel do marketplace, mas chegam em **texto corrido**: sem série histórica, sem
comparação entre períodos, sem alerta. O gestor enxerga o número de hoje e não a trajetória.

O ponto que mais dói não é a falta de dado — é a **decisão**: com verba de cupom limitada e uma equipe
comercial de uma a três pessoas, *em quais parceiros investir esta semana?* Hoje isso é resolvido por
intuição. É, na verdade, um problema de **otimização combinatória com restrições**.

## A solução

| Etapa | O que o sistema faz |
|---|---|
| **1. Ingestão** | Importa o relatório do período (texto colado ou CSV), valida e normaliza |
| **2. Análise** | Calcula séries históricas, variações e ticket médio; **segmenta cada parceiro por regra determinística** |
| **3. Previsão** | Modelo treinado pela equipe estima o faturamento do próximo período e o risco de queda |
| **4. Otimização** | Motor próprio aloca as ações comerciais sob restrições (orçamento, nº de ações, cotas por categoria) maximizando o uplift esperado |
| **5. Aceleração** | O otimizador roda em três modos — serial, CPU multi-thread e **GPU** — com benchmark comparativo na própria interface |
| **6. Comunicação** | Gera mensagens por segmento; **nada é enviado sem aprovação humana** |

**KPI de produto:** mobilidade do ranking Top N — parceiros da cauda longa subindo ao topo é a prova de que
o relacionamento ativo funcionou.

**KPIs técnicos:** *speedup* do otimizador em GPU sobre o baseline serial (meta ≥ 5×) e MAPE do modelo preditivo.

---

## Princípio de projeto: número não se alucina

Ranking, segmentação e otimização são **determinísticos**, implementados em código. O modelo de linguagem do
assistente **nunca calcula uma métrica** — ele apenas redige texto e responde sobre dados já recuperados,
sempre citando o período de origem ou se abstendo quando não há dado suficiente.

Essa separação é o que permite confiar no painel: dois usuários que rodarem a mesma análise sobre os mesmos
dados obtêm exatamente o mesmo resultado.

---

## Stack

| Camada | Tecnologia | Por quê |
|---|---|---|
| Núcleo computacional | **C++ / CUDA** | Otimizador paralelo e kernels de alto desempenho |
| Backend / API | **Python 3.11 + FastAPI** | Linguagem prioritária da disciplina; integra nativamente com o núcleo e com PyTorch |
| Modelo preditivo | **PyTorch + NumPy** | Modelo treinado pela equipe, não uma API de terceiros |
| Banco de dados | **PostgreSQL 16** | Relacional, com histórico por período |
| Interface | **React + Vite** | Dashboard, gráficos e formulários |
| Assistente | LLM local via **Ollama** | Complementar; roda na máquina, sem enviar dados para fora |
| Versionamento | **Git + GitHub** | Issues, Projects, Pull Requests e CI |
| Execução | **Docker Compose** | `docker compose up` sobe o ambiente inteiro |

> O sistema **funciona sem GPU**: quando não há placa compatível, o otimizador cai automaticamente para o
> modo CPU multi-thread. A GPU acelera; não é pré-requisito.

## Arquitetura

```
Navegador ──▶ Frontend (React + Vite)
                   │  REST /api
                   ▼
              API (Python 3.11 + FastAPI) ──────▶ PostgreSQL 16
                   │
        ┌──────────┴───────────┬────────────────┐
        ▼                      ▼                ▼
  Núcleo Preditivo      Núcleo de Otimização   Assistente
  (PyTorch)             (C++ / OpenMP / CUDA)  (LLM local)
```

Detalhamento em [`docs/07-arquitetura-preliminar.md`](docs/07-arquitetura-preliminar.md).

---

## Documentação

| Documento | Conteúdo |
|---|---|
| [**CLAUDE.md**](CLAUDE.md) | **Contexto e convenções para assistentes de IA — leia antes de codificar** |
| [01 — Visão do produto](docs/01-visao-do-produto.md) | Tema, problema, objetivos, público-alvo, KPIs |
| [02 — Requisitos](docs/02-requisitos.md) | 36 requisitos funcionais e 20 não funcionais, com rastreabilidade |
| [03 — Casos de uso](docs/03-casos-de-uso.md) | 14 casos de uso, diagrama e especificação detalhada |
| [04 — Product Backlog](docs/04-product-backlog.md) | 9 épicos e 50 histórias priorizadas |
| [05 — Cronograma](docs/05-cronograma.md) | 7 sprints até 05/12/2026, marcos e riscos |
| [06 — Equipe e processo](docs/06-equipe-e-processo.md) | Papéis, cerimônias, Definition of Done, fluxo Git |
| [07 — Arquitetura preliminar](docs/07-arquitetura-preliminar.md) | Visão de contêineres, decisões (ADRs), ambiente |
| [Como contribuir](CONTRIBUTING.md) | Branches, commits, Pull Requests |

---

## Como executar

> O ambiente executável entra na **Sprint 3** (01/10 – 14/10). Esta seção descreve o alvo e será
> atualizada com os comandos definitivos quando o esqueleto subir.

**Pré-requisitos:** Docker Desktop · Python 3.11 · Node.js 20 · (opcional) NVIDIA CUDA Toolkit 12.x

```bash
git clone https://github.com/PedroMiranda243/growth-intelligence-hub.git
cd growth-intelligence-hub
cp .env.example .env
docker compose up
```

Interface em `http://localhost:5173` · API em `http://localhost:8000/docs`

### Dados de demonstração

O repositório **não contém dados reais**. Toda a massa de demonstração é gerada por
`scripts/gerar_dados_sinteticos.py`, que produz redes de 100 a 10.000 parceiros com sazonalidade,
tendências e ruído controlados — o mesmo gerador alimenta o benchmark do otimizador, que precisa de
escala para evidenciar o ganho de paralelismo.

---

## Equipe

Projeto desenvolvido por 5 integrantes. Os papéis organizam o trabalho, mas **todos contribuem com código** —
ver [`docs/06-equipe-e-processo.md`](docs/06-equipe-e-processo.md).

| Papel | Integrante |
|---|---|
| Scrum Master | *a definir* |
| Product Owner | *a definir* |
| Desenvolvedor Backend / Núcleo Computacional | *a definir* |
| Desenvolvedor Frontend | *a definir* |
| Banco de Dados, Documentação e Testes | *a definir* |

**Orientação:** Prof.ª Pryscilla Gonçalves (Fábrica de Software) · Prof. Antenor Parnaíba (Tópicos Avançados)

---

## Aviso

Projeto acadêmico. © 2026 os autores — todos os direitos reservados.
O repositório é público para fins de avaliação e portfólio; isso não concede licença de uso, cópia,
modificação ou redistribuição do código.

Os dados utilizados são **inteiramente sintéticos**. O sistema não coleta nem armazena dados pessoais de
consumidores finais.
