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

## Entregas da disciplina

| Entrega | Prazo | Documento |
|---|---|---|
| Sprint 01 — planejamento e descoberta | 05/09/2026 | incluída nos documentos abaixo |
| Sprint 02 — arquitetura e modelagem | 19/09/2026 | [`GRUPO-18-GIH-SPRINT-02.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-02.pdf) |
| **Sprint 03 — estrutura inicial funcionando** | 19/09/2026 | [`GRUPO-18-GIH-SPRINT-03.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-03.pdf) |

O documento é acumulado: cada entrega traz as sprints anteriores e a atual. Ele é **gerado a partir da
documentação deste repositório**, e não escrito à parte — ver [`docs/entrega/`](docs/entrega/).

```bash
node docs/entrega/renderizar_diagramas.js   # diagramas, a partir dos blocos mermaid do markdown
node docs/entrega/capturar_prototipo.js     # as quatro telas do protótipo
node docs/entrega/capturar_evidencias.js    # a documentação interativa da API   (exige a API no ar)
node docs/entrega/gerar.js                  # monta o .docx
powershell -ExecutionPolicy Bypass -File docs/entrega/converter_pdf.ps1
```

As evidências de execução vêm de execuções reais, e não são transcritas à mão:

```bash
cd api
GIH_ADMIN_SENHA=... python e2e/verificacao.py > ../docs/entrega/evidencias/verificacao.txt
GIH_ADMIN_SENHA=... python e2e/transcricao.py > ../docs/entrega/evidencias/crud.txt
```

> As sprints da disciplina não são as mesmas da equipe: trabalhamos em 13 sprints semanais, e a entrega de
> arquitetura e modelagem cobre da nossa sprint 2 à 5. A tabela de equivalência está em
> [`docs/05-cronograma.md`](docs/05-cronograma.md), seção 1.

## Documentação

| Documento | Conteúdo |
|---|---|
| [**CLAUDE.md**](CLAUDE.md) | **Contexto e convenções para assistentes de IA — leia antes de codificar** |
| [01 — Visão do produto](docs/01-visao-do-produto.md) | Tema, problema, objetivos, público-alvo, KPIs |
| [02 — Requisitos](docs/02-requisitos.md) | 43 requisitos funcionais e 29 não funcionais, com rastreabilidade |
| [03 — Casos de uso](docs/03-casos-de-uso.md) | 14 casos de uso, diagrama e especificação detalhada |
| [04 — Product Backlog](docs/04-product-backlog.md) | 9 épicos e 81 histórias priorizadas |
| [05 — Cronograma](docs/05-cronograma.md) | 13 sprints semanais até 05/12/2026, marcos e riscos |
| [06 — Equipe e processo](docs/06-equipe-e-processo.md) | Papéis, cerimônias, Definition of Done, fluxo Git |
| [07 — Arquitetura preliminar](docs/07-arquitetura-preliminar.md) | Visão de contêineres, decisões (ADRs), ambiente |
| [08 — Modelo de dados](docs/08-modelo-de-dados.md) | Diagrama ER, entidades, restrições e índices |
| [09 — Sistema visual](docs/09-sistema-visual.md) | Paleta validada, tipografia, espaçamento e estados vazios |
| [Como contribuir](CONTRIBUTING.md) | Branches, commits, Pull Requests |

---

## Como executar

**Pré-requisitos:** Docker Desktop · Python 3.11 · Node.js 20 · (opcional) NVIDIA CUDA Toolkit 12.x

```bash
git clone https://github.com/PedroMiranda243/gih-fabrica-de-software.git
cd gih-fabrica-de-software
cp .env.example .env
docker compose up
```

É só isso. O compose sobe o PostgreSQL, espera ele ficar saudável, **aplica as migrações**, cria o
administrador inicial se não houver nenhum, serve a API e sobe a interface.

**A aplicação fica em `http://localhost:5173`.** A interface e a API dividem a mesma origem — o `/api`
é repassado pelo servidor da interface — e é isso que deixa o cookie de sessão funcionar sem abrir CORS
na API.

Verificação: `http://localhost:8000/api/health` deve responder `banco: "ok"`.
Documentação da API em `http://localhost:8000/api/docs`.

### Primeiro acesso

**O jeito mais direto de entrar é criar o seu próprio usuário pelo terminal**, com o ambiente no ar:

```
docker compose exec api python -m app.cli criar-usuario --login seu.login --nome "Seu Nome"
```

A senha é **digitada no terminal**, duas vezes — nunca passada como argumento, que ficaria no histórico
do shell. O perfil padrão é **Gestor**, que é o que usa painel, importação e parceiros; passe
`--perfil ANALISTA` ou `--perfil ADMINISTRADOR` se precisar de outro. Esqueceu a senha:

```
docker compose exec api python -m app.cli redefinir-senha --login seu.login
```

A redefinição encerra as sessões abertas daquele usuário, como a troca pela tela faz.

#### O administrador inicial

**Não existe senha padrão.** Este repositório é público, e um `admin/admin` no código seria porta aberta
em qualquer implantação que esquecesse de trocá-la. Na primeira subida, o sistema sorteia uma senha e a
imprime **uma única vez** no log:

```
docker compose logs api | grep "Senha sorteada"
```

Anote: ela não é gravada em lugar nenhum e não pode ser recuperada. Troque no primeiro acesso, em
`POST /api/sessao/senha`. Para definir a senha de antemão, preencha `ADMIN_SENHA` no `.env` antes de subir.

Perdeu a senha do administrador? `redefinir-senha --login admin`, como acima.

### Desenvolvendo a API fora do container

Para ter recarga automática ao salvar:

```bash
docker compose up -d postgres
cd api
python -m venv .venv && .venv/Scripts/activate      # Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Testes e análise estática, de dentro de `api/`: `pytest` e `ruff check .`

### Verificação de ponta a ponta

A suíte do `pytest` sobe a aplicação em processo. A verificação abaixo roda contra **a API no ar** — HTTP
real, cookie real, banco real — e reporta cada checagem agrupada pelos itens de entrega da disciplina.
É também o roteiro da demonstração.

```bash
docker compose up -d
cd api
GIH_ADMIN_SENHA=... python e2e/verificacao.py
```

A senha do administrador sai no log da primeira subida:
`docker compose logs api | grep "Senha sorteada"`. O comando **sai com código diferente de zero** se
qualquer verificação falhar — senão não é verificação, é impressão.

> Os testes precisam do PostgreSQL no ar: eles criam um banco `gih_teste` separado, aplicam as migrações
> nele e limpam as tabelas entre cada teste. SQLite em memória seria mais rápido e não exercitaria `JSONB`,
> os tipos `ENUM` nem as restrições `CHECK` do esquema.

> A porta do Postgres no host é **5433** por padrão (`POSTGRES_PORT` no `.env`), porque a 5432 costuma já
> estar ocupada por outro Postgres na máquina.

A interface (`web/`) entra na Sprint 3.

### Dados de demonstração

O repositório **não contém dados reais**. Toda a massa de demonstração é gerada por script.

```bash
python scripts/gerar_dados_sinteticos.py --parceiros 2000 --periodos 12
```

```bash
python scripts/resetar_banco.py --parceiros 500
```

O gerador produz redes de 100 a 10.000 parceiros, com **cauda longa** (o Top 15 concentra cerca de um terço
do faturamento numa rede de algumas centenas), perfis de trajetória distintos — em ascensão, em queda,
estável, volátil e recém-chegado — sazonalidade e ruído. A semente é parametrizável, então a mesma execução
sempre produz a mesma rede.

Isso não é enfeite: sem cauda longa não existiria o problema que o produto resolve, e sem perfis de
trajetória não haveria o que segmentar nem o que o modelo preditivo aprender. O mesmo gerador alimenta o
benchmark do otimizador, que precisa de escala para evidenciar o ganho de paralelismo.

O `resetar_banco.py` reverte as migrações, reaplica e repovoa — é o ciclo que se usa dezenas de vezes por
dia durante o desenvolvimento.

---

## Equipe

**Turma:** CC8MB

Projeto desenvolvido por 5 integrantes. Os papéis organizam o trabalho, mas **todos contribuem com código** —
ver [`docs/06-equipe-e-processo.md`](docs/06-equipe-e-processo.md).

| Integrante | Matrícula | GitHub | Papel |
|---|---|---|---|
| Ingryd Vitoria de Araújo Barbosa | 01642893 | [@ingrydaraujob](https://github.com/ingrydaraujob) | Desenvolvedora Frontend |
| João Pedro Nunes de França | 01626444 | [@joaopfranca04](https://github.com/joaopfranca04) | Banco de Dados, Documentação e Testes |
| Marcio Maycom | 01607574 | [@mihaeldatoman](https://github.com/mihaeldatoman) | Product Owner |
| Pedro Miranda | 01607408 | [@PedroMiranda243](https://github.com/PedroMiranda243) | Desenvolvedor Backend / Núcleo Computacional |
| Thiago José Falcão de Freitas | 01597267 | [@ThiagojFalcao](https://github.com/ThiagojFalcao) | Scrum Master |

**Orientação:** Prof.ª Pryscilla Gonçalves (Fábrica de Software) · Prof. Antenor Parnaíba (Tópicos Avançados)

---

## Aviso

Projeto acadêmico. © 2026 os autores — todos os direitos reservados.
O repositório é público para fins de avaliação e portfólio; isso não concede licença de uso, cópia,
modificação ou redistribuição do código.

Os dados utilizados são **inteiramente sintéticos**. O sistema não coleta nem armazena dados pessoais de
consumidores finais.
