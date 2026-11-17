# Growth Intelligence Hub (GIH)

> Plataforma de inteligência de crescimento para redes de parceiros em marketplaces regionais de delivery.
> Transforma relatórios brutos de faturamento em um **plano de ação comercial priorizado** — previsto por
> modelo próprio e otimizado sob restrições reais de orçamento e capacidade, com aceleração em GPU.

**Projeto Integrador — Fábrica de Software + Tópicos Avançados · UNINASSAU · 2026.2**

Operações regionais de delivery concentram a atenção comercial nos parceiros do topo do ranking de
faturamento. A **cauda longa** — frequentemente mais de 100 parceiros — não recebe processo de
relacionamento, e o próprio topo estagna: os mesmos nomes ocupam as primeiras posições mês após mês. Os
dados existem, mas chegam em texto corrido, sem série histórica nem alerta; e a decisão de *em quais
parceiros investir a verba limitada desta semana* é tomada por intuição. É, na verdade, um problema de
**otimização combinatória com restrições**.

O GIH resolve isso em seis etapas:

| Etapa | O que o sistema faz |
|---|---|
| **1. Ingestão** | Importa o relatório do período (texto colado ou CSV), valida e normaliza |
| **2. Análise** | Calcula séries históricas, variações e ticket médio; **segmenta cada parceiro por regra determinística** |
| **3. Previsão** | Um modelo treinado pela equipe estima o faturamento do próximo período e o risco de queda |
| **4. Otimização** | Um motor próprio aloca as ações comerciais sob restrições (orçamento, número de ações, cotas por categoria), maximizando o *uplift* esperado |
| **5. Aceleração** | O otimizador roda em três modos — serial, CPU multi-thread e **GPU** —, com benchmark comparativo na própria interface |
| **6. Comunicação** | Gera mensagens por segmento; **nada é enviado sem aprovação humana** |

---

## Objetivo

Transformar os dados brutos de desempenho de uma rede de parceiros em um **plano de ação comercial
priorizado**, previsto por modelo treinado a partir do histórico e otimizado sob as restrições reais de
orçamento e capacidade da operação.

Para isso, o sistema precisa:

- importar relatórios periódicos, recusando o que viria sem período (RN03);
- calcular as métricas e segmentar cada parceiro — a mesma base reprocessada dá sempre a mesma segmentação;
- prever o faturamento e o risco de queda com erro menor que o de repetir o último período;
- montar o plano respeitando 100% das restrições, e melhor que "investir nos maiores";
- acelerar o otimizador em CPU e GPU, com o ganho medido (meta: 5× sobre o serial);
- redigir as mensagens, que só saem com a aprovação de uma pessoa;
- controlar o acesso por perfil, com a trilha de auditoria das ações sensíveis.

**O KPI do produto** é a mobilidade do ranking: parceiros da cauda longa subindo ao topo são a prova de que o
relacionamento ativo funcionou. Os objetivos, com a forma de conferir cada um, estão em
[`docs/01-visao-do-produto.md`](docs/01-visao-do-produto.md), seção 3.

**Número não se alucina.** Ranking, segmentação, previsão e otimização são **determinísticos**, feitos em
código. O modelo de linguagem do assistente nunca calcula uma métrica: ele só redige texto e responde
sobre dados já recuperados, citando o período de origem ou se abstendo. Dois usuários que rodarem a mesma
análise sobre os mesmos dados obtêm exatamente o mesmo resultado.

---

## Tecnologias

Tudo é autoral ou de código aberto, e roda na própria máquina: nenhum serviço pago, nenhuma API de IA de
terceiros.

| Camada | Tecnologia | Para quê |
|---|---|---|
| API | **Python 3.11**, **FastAPI 0.115**, Uvicorn, Pydantic | As regras de negócio, a autorização e a orquestração |
| Persistência | **PostgreSQL 16**, **SQLAlchemy 2.0**, **Alembic 1.14** | O banco relacional, com o histórico por período, e as migrações |
| Segurança | Argon2id (`argon2-cffi`), sessão no servidor com cookie `HttpOnly` | O hash das senhas (RNF09) e a sessão |
| Modelo preditivo | **PyTorch 2.14** (CPU), **NumPy 2.4** | A previsão de faturamento e de risco, treinada pela equipe |
| Núcleo de otimização | **C++17**, **OpenMP**, **CUDA 13.4** | O otimizador nos três modos: serial, CPU paralela e GPU |
| Interface | **React 19**, React Router 7, **Vite 8** | O painel, os gráficos (desenhados em SVG, sem biblioteca) e os formulários |
| Assistente (opcional) | **Ollama 0.32**, com o modelo **`qwen2.5:7b`** (Apache 2.0) | Redige as mensagens e responde perguntas, localmente |
| Acesso remoto (opcional) | **nginx 1.30**, **Tailscale 1.102** | A interface empacotada, por uma rede privada |
| Testes | **pytest 8**, **Vitest 5**, Testing Library, **axe-core 4.14**, **Playwright 1.63** | Os testes da API, da interface, da acessibilidade e pela tela |
| Análise estática | ruff (Python), oxlint (JavaScript) | |
| Execução | **Docker Compose v2** | Um comando sobe o ambiente inteiro (RNF07) |
| Versionamento | **Git + GitHub** (Issues, Projects, Pull Requests, Actions) | O processo e a integração contínua |

> O sistema **funciona sem GPU e sem o modelo de linguagem**: sem placa compatível, o otimizador cai para a
> CPU paralela; sem o modelo, as mensagens saem de textos fixos por segmento, com os mesmos números.

---

## Requisitos

**Para subir e avaliar, basta o Docker.**

| O quê | Detalhe |
|---|---|
| **Docker Desktop** (Windows ou macOS) ou Docker Engine (Linux), com o **Compose v2** | No Windows, com o WSL2, que é o padrão |
| **Git** | Para clonar o repositório |
| **Memória** | Os três contêineres usam cerca de 0,8 GB em repouso; 8 GB na máquina dão folga |
| **Disco** | Cerca de 5 GB livres: as imagens somam 2,5 GB, e a construção precisa de espaço |
| **Portas livres** | 5173 (a aplicação), 8000 (a API) e 5433 (o banco) — as duas últimas se mudam no `.env` |
| **No Windows, uma pasta de caminho curto** | Alguns arquivos das migrações têm nome longo: numa pasta funda, como dentro de `Documentos` ou do OneDrive, o `git clone` falha com `Filename too long`. Clone em `C:\gih`, ou rode `git config --global core.longpaths true` antes |

**Opcionais:**

| Para… | É preciso |
|---|---|
| **O otimizador na GPU** | Uma placa NVIDIA com driver que suporte o CUDA 13, e mais cerca de 14 GB de disco para a imagem de compilação da NVIDIA. No Windows, o Docker Desktop com WSL2 já entrega a placa ao contêiner |
| **O assistente** | Mais cerca de 13 GB de disco (a imagem do Ollama, 8 GB, e o modelo, 4,7 GB). Com uma GPU de 8 GB, o modelo roda nela e responde em segundos; sem ela, roda na CPU, mais devagar |

**Para desenvolver** — rodar a API fora do contêiner, os testes e os scripts da equipe: **Python 3.11** e
**Node.js 22**. O passo a passo está no [guia de operação](docs/14-guia-de-operacao.md).

---

## Instalação e configuração

```bash
git clone https://github.com/PedroMiranda243/gih-fabrica-de-software.git
cd gih-fabrica-de-software
cp .env.example .env
docker compose up -d
```

O `docker compose up -d` constrói as imagens na primeira vez (alguns minutos) e sobe três serviços: o banco
(`postgres`), a API (`api`) e a interface (`web`). A API espera o banco ficar saudável, aplica as migrações e
cria o administrador inicial, se não houver nenhum. Para conferir:

- `http://localhost:8000/api/health` responde `"banco": "ok"`;
- `http://localhost:5173` abre a tela de entrada.

**A configuração fica no `.env`**, que não vai para o repositório. Os valores do `.env.example` servem como
estão para a avaliação na própria máquina:

| Variável | Padrão | O que faz |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `gih`, `troque-esta-senha`, `gih` | O usuário, a senha e o banco do PostgreSQL. Valem na criação do volume: trocá-los depois não muda o banco que já existe |
| `POSTGRES_PORT` | `5433` | A porta do banco na máquina. Não é a 5432 porque ela costuma estar ocupada por outro PostgreSQL |
| `DATABASE_URL` | aponta para `localhost:5433` | Só para quem roda a API ou os scripts **fora** do contêiner; a API do Compose monta a dela. Mantenha a senha e a porta iguais às de cima |
| `API_PORT` | `8000` | A porta da API na máquina |
| `TZ` | `America/Recife` | O fuso do servidor: o filtro por data da auditoria usa o dia local |
| `SESSAO_DURACAO_HORAS` | `8` | Quanto tempo a sessão dura sem novo login |
| `COOKIE_SEGURO` | `false` | O `Secure` do cookie. Fica falso no acesso local, em HTTP; no acesso remoto, quem o põe é a borda, em HTTPS |
| `ADMIN_LOGIN`, `ADMIN_NOME` | `admin`, `Administrador` | O administrador criado na primeira subida |
| `ADMIN_SENHA` | vazia | Vazia, o sistema sorteia a senha e a imprime uma vez no log — o recomendado. Ver [Primeiro acesso](#primeiro-acesso) |
| `OLLAMA_BASE_URL` | o serviço `ollama` do Compose | O endereço do modelo de linguagem. Para usar um Ollama já instalado na máquina: `http://host.docker.internal:11434` |
| `LLM_MODEL` | `qwen2.5:7b` | O modelo que o assistente usa |
| `TS_HOSTNAME`, `TS_AUTHKEY` | `gih`, vazia | Só para o acesso remoto por rede privada ([guia de operação](docs/14-guia-de-operacao.md#acesso-de-fora-de-casa-por-rede-privada)) |

**Todas as portas ficam presas à própria máquina** (`127.0.0.1`): o sistema não fica exposto na rede
(RNF30).

---

## Banco de dados

O **PostgreSQL 16** roda no serviço `postgres` do Compose, e os dados ficam no volume `dados_postgres`: eles
sobrevivem a `docker compose down`, a reiniciar os contêineres e a reiniciar a máquina. Só
`docker compose down -v` apaga o volume — e, com ele, tudo.

**A estrutura vem das migrações**, em [`api/migrations/`](api/migrations/) (Alembic), e a API as aplica
sozinha a cada subida (`alembic upgrade head`): não há script SQL para rodar à mão. São 20 tabelas,
descritas em [`docs/08-modelo-de-dados.md`](docs/08-modelo-de-dados.md) — os diagramas entidade-relacionamento,
cada entidade, as restrições, os índices e a política de exclusão. Um teste confere, a cada Pull Request, que
o documento, as migrações e o banco dizem a mesma coisa.

**A base nasce vazia**, e um sistema sem dados não mostra o que faz. Com o ambiente no ar:

```bash
docker compose exec api python -m app.cli popular-demonstracao
```

O comando roda **dentro do contêiner**, sem nada instalado na máquina. Ele gera 500 parceiros com 12 semanas
de histórico — dados inteiramente sintéticos —, calcula a segmentação e treina o modelo preditivo, em cerca de
10 s. Numa base que já tem dados, ele se recusa e diz o que há nela. Com `--substituir`, troca tudo pela
massa nova — e **os usuários vão junto**; o administrador é recriado, com a senha nova na saída.

Para consultar o banco direto, com o usuário e o banco do `.env`:

```bash
docker compose exec postgres psql -U gih -d gih
```

Ou, da máquina, por qualquer cliente PostgreSQL em `localhost:5433`. A estrutura do banco no ar, tabela por
tabela, sai do `scripts/descrever_banco.py`; ele e a recriação da base para desenvolvimento estão no
[guia de operação](docs/14-guia-de-operacao.md#dados-de-demonstração-e-o-banco).

---

## Como executar

### Subir, parar e atualizar

| Para… | Comando |
|---|---|
| Subir | `docker compose up -d` |
| Ver o log da API | `docker compose logs -f api` |
| Parar, sem perder dados | `docker compose stop` |
| Depois de um `git pull` | `docker compose up -d --build` |

Os serviços voltam sozinhos quando o Docker volta; quem os para com `stop` os encontra parados.

| Endereço | O que é |
|---|---|
| `http://localhost:5173` | **A aplicação** |
| `http://localhost:8000/api/health` | A saúde da API e do banco |
| `http://localhost:8000/api/docs` | **A documentação da API** (Swagger): cada rota, quem pode chamá-la, os parâmetros, as respostas e os exemplos |
| `http://localhost:8000/api/redoc` | A mesma documentação, para leitura |

A documentação da API também está no repositório, sem precisar subir nada:
[`docs/13-api.md`](docs/13-api.md), com um exemplo de uso de ponta a ponta, e
[`docs/api/openapi.json`](docs/api/openapi.json).

### Primeiro acesso

**Não existe senha padrão.** Este repositório é público, e um `admin/admin` no código seria porta aberta em
qualquer instalação que esquecesse de trocá-lo. Na primeira subida, o sistema sorteia a senha do
administrador e a imprime **uma única vez** no log:

```bash
docker compose logs api | grep "Senha sorteada"
```

No PowerShell, que não tem `grep`: `docker compose logs api | Select-String "Senha sorteada"`. Anote: ela
não fica gravada em lugar nenhum. Troque-a no primeiro acesso, em **Minha conta**. Para definir a senha de
antemão, preencha `ADMIN_SENHA` no `.env` antes da primeira subida.

**Para avaliar, crie o seu próprio usuário**, com o ambiente no ar:

```bash
docker compose exec api python -m app.cli criar-usuario --login avaliador --nome "Avaliador"
```

A senha é **digitada no terminal**, duas vezes — nunca passada como argumento, que ficaria no histórico. O
perfil padrão é **Gestor**, que abre tudo o que a avaliação precisa; `--perfil ANALISTA` ou
`--perfil ADMINISTRADOR` dão os outros. O administrador também cria usuários pela tela **Usuários**.
Esqueceu a senha:

```bash
docker compose exec api python -m app.cli redefinir-senha --login avaliador
```

A redefinição encerra as sessões abertas daquele usuário. Vale também para o `admin`.

### Com a GPU

Com placa NVIDIA, o núcleo é compilado com CUDA e a placa é reservada para a API, por um arquivo à parte:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Com ele, o modo GPU aparece na tela **Campanha**, e é o que roda quando o gestor não escolhe; a tela
**Benchmark** mede os quatro modos lado a lado, com o mesmo plano. Sem ele, o sistema roda em CPU paralela, e
a Campanha diz por que não há GPU (RNF06). Para voltar à CPU, suba de novo sem o arquivo, com `--build`.

### Com o assistente

O modelo de linguagem sobe num perfil à parte:

```bash
docker compose --profile assistente up -d
```

Com a GPU, junte o arquivo dela, que reserva a placa também para o modelo:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile assistente up -d --build
```

A primeira vez baixa a imagem do Ollama e o modelo; o serviço `ollama-modelo` baixa e sai. A primeira
resposta leva perto de 45 s, enquanto o modelo carrega; depois, poucos segundos. Os números não saem do
modelo: saem do núcleo, e uma guarda recusa o texto com número que não veio de lá (ADR-013).

### De outro aparelho

O sistema não fica na internet, de propósito. Para usá-lo do celular ou de outro computador, há o perfil
`remoto`, por uma rede privada (Tailscale), com HTTPS. O passo a passo está no
[guia de operação](docs/14-guia-de-operacao.md#acesso-de-fora-de-casa-por-rede-privada).

### Testes

Os testes da interface, de dentro de `web/`, com o Node 22:

```bash
npm ci
npm run lint
npm test
```

Os da API (`pytest`), a verificação de ponta a ponta contra o sistema no ar, os casos de teste executados
pela tela e as medições de desempenho estão no [guia de operação](docs/14-guia-de-operacao.md). A integração
contínua roda os testes da API, do modelo e da interface a cada Pull Request.

---

## Estrutura do projeto

```
Navegador ──▶ web/ (React + Vite)
                  │  REST /api, na mesma origem
                  ▼
              api/ (Python + FastAPI) ──────▶ PostgreSQL 16
                  │
        ┌─────────┴──────────┬───────────────────┐
        ▼                    ▼                   ▼
   modelo/ (PyTorch)   nucleo/ (C++/OpenMP/CUDA)  assistente (Ollama, opcional)
```

A interface só exibe e coleta; a API decide (as regras de negócio nunca ficam no navegador). O detalhe e as
decisões registradas (ADR-001 a ADR-015) estão em
[`docs/07-arquitetura-preliminar.md`](docs/07-arquitetura-preliminar.md).

```
gih-fabrica-de-software/
├── api/                      a API (FastAPI)
│   ├── app/                  as rotas (rotas/), os serviços, os modelos do banco e a linha de comando (cli.py)
│   ├── migrations/           as migrações do banco (Alembic)
│   ├── tests/                os testes da API (pytest), contra um banco de teste separado
│   └── e2e/                  a verificação de ponta a ponta, contra o sistema no ar
├── modelo/                   o modelo preditivo (PyTorch): treino, avaliação e previsão
├── nucleo/                   o otimizador em C++: serial, OpenMP e CUDA (cpp/), e o spike de GPU
├── web/                      a interface (React + Vite)
│   └── src/                  as telas (paginas/), os componentes, os gráficos e os estilos
├── remoto/                   a borda do acesso remoto (nginx), que entrega a interface empacotada
├── scripts/                  o gerador de dados sintéticos, as medições e os testes pela tela
├── docs/                     a documentação: requisitos, casos de uso, arquitetura, dados, testes
│   ├── api/                  a especificação OpenAPI exportada
│   ├── diagramas/            os diagramas, gerados dos blocos Mermaid dos documentos
│   ├── medicoes/             os resultados medidos, gerados por script
│   ├── entrega/              o gerador dos documentos de entrega e as evidências de cada sprint
│   └── entregas/             os PDFs entregues
├── .github/                  a integração contínua, os modelos de issue e de PR, e os donos de cada pasta
├── docker-compose.yml        o ambiente: banco, API e interface, e os perfis opcionais
├── docker-compose.gpu.yml    a GPU para a API e para o modelo de linguagem
├── .env.example              a configuração, com valores fictícios
├── CLAUDE.md                 as regras e convenções do projeto, para pessoas e assistentes de IA
└── CONTRIBUTING.md           ramos, commits e Pull Requests
```

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

## Documentação

| Documento | Conteúdo |
|---|---|
| [**CLAUDE.md**](CLAUDE.md) | **Contexto e convenções para assistentes de IA — leia antes de codificar** |
| [01 — Visão do produto](docs/01-visao-do-produto.md) | Tema, problema, objetivos, público-alvo, KPIs |
| [02 — Requisitos](docs/02-requisitos.md) | 56 requisitos funcionais e 30 não funcionais, e as regras de negócio RN01 a RN11 |
| [03 — Casos de uso](docs/03-casos-de-uso.md) | 16 casos de uso, diagrama e especificação detalhada |
| [04 — Product Backlog](docs/04-product-backlog.md) | 9 épicos e 109 histórias priorizadas |
| [05 — Cronograma](docs/05-cronograma.md) | O plano e o realizado das 13 sprints semanais, o que resta até 05/12/2026, marcos e riscos |
| [06 — Equipe e processo](docs/06-equipe-e-processo.md) | Papéis, cerimônias, Definition of Done, fluxo Git |
| [07 — Arquitetura](docs/07-arquitetura-preliminar.md) | As camadas e onde cada uma roda, o núcleo, as decisões (ADR-001 a ADR-015), o ambiente |
| [08 — Modelo de dados](docs/08-modelo-de-dados.md) | Diagramas ER, entidades, restrições, índices e a política de exclusão |
| [09 — Sistema visual](docs/09-sistema-visual.md) | As regras de cor, a paleta medida, tipografia, espaçamento, estados vazios e o mapa das telas |
| [10 — Diagrama de classes](docs/10-diagrama-de-classes.md) | O domínio, os serviços e o núcleo computacional, em nove diagramas |
| [11 — Rastreabilidade](docs/11-rastreabilidade.md) | Cada requisito com o caso de uso, a rota, a tela e o teste, conferidos pela suíte |
| [12 — Plano de testes](docs/12-plano-de-testes.md) | Os níveis de teste, o ambiente e os 78 casos — funcionais, de validação e de navegação — executados pela tela, com o esperado |
| [13 — API](docs/13-api.md) | Cada rota: quem pode chamar, os parâmetros, o corpo com exemplo, as respostas e os erros |
| [14 — Guia de operação](docs/14-guia-de-operacao.md) | O que a equipe usa: desenvolver fora do contêiner, os testes, as medições, a administração pelo terminal, o acesso remoto e as entregas |
| [Medições](docs/medicoes/) | O núcleo em CPU e GPU, o otimizador, o modelo preditivo, o assistente e a acessibilidade — gerados por script |
| [Documentação técnica final](docs/entregas/GRUPO-18-GIH-DOCUMENTACAO-TECNICA.pdf) | A arquitetura e as ADRs, o modelo de dados, as classes e os resultados medidos, num documento só (H73) |
| [Como contribuir](CONTRIBUTING.md) | Ramos, commits, Pull Requests |

## Entregas da disciplina

| Entrega | Prazo | Documento |
|---|---|---|
| Sprint 01 — planejamento e descoberta | 05/09/2026 | incluída nos documentos abaixo |
| Sprint 02 — arquitetura e modelagem | 19/09/2026 | [`GRUPO-18-GIH-SPRINT-02.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-02.pdf) |
| Sprint 03 — estrutura inicial funcionando | 19/09/2026 | [`GRUPO-18-GIH-SPRINT-03.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-03.pdf) |
| Sprint 04 — primeiro módulo completo | 26/09/2026 | [`GRUPO-18-GIH-SPRINT-04.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-04.pdf) |
| Sprint 05 — segundo módulo funcionando | 03/10/2026 | [`GRUPO-18-GIH-SPRINT-05.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-05.pdf) |
| Sprint 06 — aprimoramento do sistema | 17/10/2026 | [`GRUPO-18-GIH-SPRINT-06.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-06.pdf) |
| Sprint 07 — sistema quase completo | 24/10/2026 | [`GRUPO-18-GIH-SPRINT-07.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-07.pdf) |
| Sprint 08 — funcionalidades concluídas | 31/10/2026 | [`GRUPO-18-GIH-SPRINT-08.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-08.pdf) |
| Sprint 09 — testes e correções | 07/11/2026 | entregue junto com a Sprint 10 |
| **Sprint 10 — Release Candidate** | 14/11/2026 | em preparação |

O documento é acumulado: cada entrega traz as sprints anteriores e a atual. Ele é **gerado a partir da
documentação deste repositório**, e não escrito à parte; como gerá-lo está no
[guia de operação](docs/14-guia-de-operacao.md#como-gerar-as-entregas).

> As sprints da disciplina não são as mesmas da equipe: trabalhamos em 13 sprints semanais. A tabela de
> equivalência está em [`docs/05-cronograma.md`](docs/05-cronograma.md), seção 1.

---

## Aviso

Projeto acadêmico. © 2026 os autores — todos os direitos reservados.
O repositório é público para fins de avaliação e portfólio; isso não concede licença de uso, cópia,
modificação ou redistribuição do código.

Os dados utilizados são **inteiramente sintéticos**. O sistema não coleta nem armazena dados pessoais de
consumidores finais.
