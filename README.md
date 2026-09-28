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
  (PyTorch)             (C++ / OpenMP / CUDA)  (Ollama, opcional)
```

Detalhamento em [`docs/07-arquitetura-preliminar.md`](docs/07-arquitetura-preliminar.md), e tudo num volume só
na [documentação técnica final](#documentação-técnica-final).

---

## Entregas da disciplina

| Entrega | Prazo | Documento |
|---|---|---|
| Sprint 01 — planejamento e descoberta | 05/09/2026 | incluída nos documentos abaixo |
| Sprint 02 — arquitetura e modelagem | 19/09/2026 | [`GRUPO-18-GIH-SPRINT-02.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-02.pdf) |
| Sprint 03 — estrutura inicial funcionando | 19/09/2026 | [`GRUPO-18-GIH-SPRINT-03.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-03.pdf) |
| Sprint 04 — primeiro módulo completo | 26/09/2026 | [`GRUPO-18-GIH-SPRINT-04.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-04.pdf) |
| **Sprint 05 — segundo módulo funcionando** | 03/10/2026 | [`GRUPO-18-GIH-SPRINT-05.pdf`](docs/entregas/GRUPO-18-GIH-SPRINT-05.pdf) |

O documento é acumulado: cada entrega traz as sprints anteriores e a atual. Ele é **gerado a partir da
documentação deste repositório**, e não escrito à parte — ver [`docs/entrega/`](docs/entrega/).

```bash
node docs/entrega/renderizar_diagramas.js   # diagramas, a partir dos blocos mermaid do markdown
node docs/entrega/gerar.js                  # monta o .docx
powershell -ExecutionPolicy Bypass -File docs/entrega/converter_pdf.ps1 -Nome GRUPO-18-GIH-SPRINT-05
```

A conversão pelo Word trava nesta máquina com frequência, sem erro e sem janela. Quando acontecer, o
caminho é abrir o `.docx` no Word e usar **Arquivo › Exportar › Criar PDF** — o resultado é o mesmo.

### Documentação técnica final

A arquitetura e as ADRs, o modelo de dados, as classes e os serviços, e os resultados medidos — do núcleo
em CPU e GPU, do otimizador, do modelo preditivo, do assistente e da acessibilidade —, num documento só
(H73): [`GRUPO-18-GIH-DOCUMENTACAO-TECNICA.pdf`](docs/entregas/GRUPO-18-GIH-DOCUMENTACAO-TECNICA.pdf).

Ele não é escrito à parte: cada parte é o arquivo do repositório, convertido como está (`docs/07`,
`docs/08`, `docs/10` e `docs/medicoes/`). Ao contrário das entregas, que são o retrato de uma data, ele
**se regera a cada mudança** da documentação:

```bash
node docs/entrega/renderizar_diagramas.js arquitetura-geral   # só os diagramas que mudaram, pelo nome
node docs/entrega/gerar_documentacao.js
```

Sem nomes, o `renderizar_diagramas.js` refaz todos — e o Mermaid não sai idêntico de uma execução para a
outra, então o diff ganha arquivos que não mudaram de conteúdo. O PDF sai do `.docx` pelo Word, como o das
entregas.

As evidências de execução vêm de execuções reais, e não são transcritas à mão. Cada entrega grava na
sua própria pasta, e **a pasta de uma sprint já entregue não se regera** — é o retrato daquela data:

```bash
cd api
GIH_ADMIN_SENHA=... python e2e/verificacao.py        > ../docs/entrega/evidencias/sprint05/verificacao.txt
GIH_ADMIN_SENHA=... python e2e/transcricao_modelo.py > ../docs/entrega/evidencias/sprint05/modelo.txt
GIH_ADMIN_SENHA=... python e2e/validacoes.py         > ../docs/entrega/evidencias/sprint05/validacoes.txt
GIH_ADMIN_SENHA=... python e2e/persistencia.py       > ../docs/entrega/evidencias/sprint05/persistencia.txt
cd ..
GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprint05.js       # as telas: fluxo e erros
api/.venv/Scripts/python scripts/registrar_testes.py --saida docs/entrega/evidencias/sprint05
python scripts/registrar_bugs.py --desde 2026-09-22 --saida docs/entrega/evidencias/sprint05
node docs/entrega/registrar_commits.js > docs/entrega/evidencias/sprint05/commits.txt
```

A persistência desliga e religa os contêineres, e as validações param o banco por alguns segundos:
rode com a aplicação livre. Nenhum dos scripts deixa resíduo no banco.

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
| [05 — Cronograma](docs/05-cronograma.md) | O plano e o realizado das 13 sprints semanais, o que resta até 05/12/2026, marcos e riscos |
| [06 — Equipe e processo](docs/06-equipe-e-processo.md) | Papéis, cerimônias, Definition of Done, fluxo Git |
| [07 — Arquitetura](docs/07-arquitetura-preliminar.md) | As camadas e onde cada uma roda, o núcleo, as decisões (ADR-001 a ADR-013), o ambiente |
| [08 — Modelo de dados](docs/08-modelo-de-dados.md) | Diagrama ER, entidades, restrições e índices |
| [09 — Sistema visual](docs/09-sistema-visual.md) | Paleta validada, tipografia, espaçamento e estados vazios |
| [10 — Diagrama de classes](docs/10-diagrama-de-classes.md) | O domínio, os serviços e o núcleo computacional, em oito diagramas |
| [Medições](docs/medicoes/) | O núcleo em CPU e GPU, o otimizador, o modelo preditivo, o assistente e a acessibilidade — gerados por script |
| [Documentação técnica final](#documentação-técnica-final) | 07, 08, 10 e as medições, num documento só |
| [Como contribuir](CONTRIBUTING.md) | Branches, commits, Pull Requests |

---

## Como executar

**Para subir e avaliar, basta o Docker Desktop.** Python 3.11 e Node.js 22 só entram para desenvolver, rodar
os testes e a verificação de ponta a ponta, mais abaixo. Com placa NVIDIA, o otimizador também roda na GPU —
opcional.

> **No Windows, clone numa pasta de caminho curto**, como `C:\gih`. Alguns arquivos das migrações têm nome
> longo, e numa pasta funda — dentro de `Documentos` ou do OneDrive — o caminho passa do limite de 260
> caracteres do Windows: o `git clone` falha com `Filename too long`. A alternativa é rodar
> `git config --global core.longpaths true` antes de clonar.

```bash
git clone https://github.com/PedroMiranda243/gih-fabrica-de-software.git
cd gih-fabrica-de-software
cp .env.example .env
docker compose up -d
```

É só isso. O compose sobe o PostgreSQL, espera ele ficar saudável, **aplica as migrações**, cria o
administrador inicial se não houver nenhum, serve a API e sobe a interface. Sem o `-d`, ele fica preso ao
terminal, mostrando o log; com ele, o log está em `docker compose logs -f`.

**A aplicação fica em `http://localhost:5173`.** A interface e a API dividem a mesma origem — o `/api`
é repassado pelo servidor da interface — e é isso que deixa o cookie de sessão funcionar sem abrir CORS
na API.

Verificação: `http://localhost:8000/api/health` deve responder `banco: "ok"`.
Documentação da API em `http://localhost:8000/api/docs`.

**Com placa NVIDIA**, o otimizador pode usar a GPU. O núcleo é compilado com CUDA, e a placa é reservada
para a API, por um arquivo à parte. Com ele, o modo GPU aparece na tela de campanha, e é o que roda quando o
gestor não escolhe; e a tela de benchmark mede os quatro modos lado a lado, com o mesmo plano:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Sem ele, o sistema sobe em qualquer máquina, em CPU paralela, e a tela de campanha diz por que não há GPU
(RNF06). A primeira vez baixa a imagem de compilação da NVIDIA, de alguns GB. No Windows, o Docker Desktop
com WSL2 já entrega a placa ao contêiner. Para voltar à CPU, suba de novo sem o arquivo, com `--build`.

**O modelo de linguagem é opcional**, e sobe num perfil à parte: o `qwen2.5:7b` (Apache 2.0), local, pelo
Ollama. É ele que vai redigir as mensagens da central de comunicação (H60) e responder no assistente (H65).
Os números não saem dele: saem do núcleo, e uma guarda recusa o texto com número que não veio de lá
(ADR-013).

```bash
docker compose --profile assistente up -d
```

Com placa NVIDIA, junte o arquivo da GPU, que reserva a placa também para o modelo:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile assistente up -d --build
```

A primeira vez baixa a imagem do Ollama (~8 GB) e o modelo (~4,7 GB): o serviço `ollama-modelo` baixa e
sai. Sem o perfil, o sistema funciona igual — as mensagens saem de textos fixos por segmento, com os mesmos
números, e o assistente se diz indisponível. Um Ollama já instalado na máquina também serve, com
`OLLAMA_BASE_URL=http://host.docker.internal:11434` no `.env`.

### Avaliar: a base de demonstração e o seu usuário

**A base nasce vazia**, e um sistema sem dados não mostra o que faz. Com o ambiente no ar, dois comandos:

```bash
docker compose exec api python -m app.cli popular-demonstracao
docker compose exec api python -m app.cli criar-usuario --login avaliador --nome "Avaliador"
```

O primeiro roda **dentro do contêiner**, sem nada instalado na máquina. Ele gera 500 parceiros com 12 semanas
de histórico — dados inteiramente sintéticos —, calcula a segmentação e treina o modelo preditivo, em cerca de
10 s. O segundo pede a senha duas vezes; o perfil é Gestor, que abre tudo o que a avaliação precisa. Aí é
entrar em `http://localhost:5173`.

Numa base que já tem dados, o `popular-demonstracao` se recusa e diz o que há nela. Com `--substituir`, ele
troca tudo pela massa — e **os usuários vão junto**; o administrador é recriado, com a senha nova na saída.

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

### Administração pelo terminal

As telas **Usuários** e **Configuração** cobrem a administração pelo navegador. Os comandos abaixo fazem o
mesmo pelo terminal, para quem administra sem abrir a aplicação.

Os limiares da segmentação (RF21) — tamanho do Top N, períodos de queda para caracterizar risco e
períodos de histórico para o parceiro ainda ser recém-chegado:

```
docker compose exec api python -m app.cli configurar-segmentacao
docker compose exec api python -m app.cli configurar-segmentacao --top-n 20 --reprocessar
```

Sem argumento, mostra o que está em vigor. Alterar reclassifica **só o período mais recente**; os
anteriores mantêm a classificação antiga até `--reprocessar` ou:

```
docker compose exec api python -m app.cli reprocessar-segmentos
```

Esse último é também o que classifica uma base carregada antes da segmentação existir — sem ele, o painel
mostra a distribuição vazia sem dizer por quê.

O modelo preditivo (UC07) treina pela tela **Modelo** ou pelo terminal:

```
docker compose exec api python -m app.cli treinar-modelo
```

Pelo terminal ele roda até o fim e imprime as métricas contra as referências e a versão que ficou em uso.
As regras são as da tela: com menos de 8 períodos na base o treino é recusado (RN09), e a versão treinada
só entra em uso se superar as referências (UC07-A1). O `scripts/resetar_banco.py` já treina depois de
segmentar, e a base de demonstração nasce com previsão.

A campanha (UC08) se calcula pela tela **Campanha**, só pelo Gestor; o Analista consulta. O plano parte das
previsões da versão em uso: sem modelo treinado, a tela diz isso e não calcula. A busca roda em segundo
plano, uma por vez, e a campanha inviável é registrada sem plano, dizendo a restrição e quanto falta (RN07).

#### O administrador inicial

**Não existe senha padrão.** Este repositório é público, e um `admin/admin` no código seria porta aberta
em qualquer implantação que esquecesse de trocá-la. Na primeira subida, o sistema sorteia uma senha e a
imprime **uma única vez** no log:

```
docker compose logs api | grep "Senha sorteada"
```

No PowerShell, que não tem `grep`: `docker compose logs api | Select-String "Senha sorteada"`.

Anote: ela não é gravada em lugar nenhum e não pode ser recuperada. Troque no primeiro acesso, em
`POST /api/sessao/senha`. Para definir a senha de antemão, preencha `ADMIN_SENHA` no `.env` antes de subir.
Depois de um `resetar_banco.py`, a senha sorteada sai na saída do reset, e não no log.

Perdeu a senha do administrador? `redefinir-senha --login admin`, como acima.

### Desenvolvendo a API fora do container

Para ter recarga automática ao salvar:

```bash
docker compose up -d postgres
cd api
python -m venv .venv && .venv/Scripts/activate      # Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt -r ../modelo/requirements.txt
pip install --no-deps -e ../modelo                   # o modelo preditivo, que a API chama
pip install --no-deps -e ../nucleo                   # o otimizador serial, idem
alembic upgrade head
uvicorn app.main:app --reload
```

Testes e análise estática, de dentro de `api/`: `pytest` e `ruff check .`

Os testes que falam com o modelo de linguagem de verdade rodam quando o `OLLAMA_BASE_URL` do `api/.env`
aponta para um Ollama com o modelo (fora do Docker, `http://localhost:11434`); sem ele, pulam. Com
`GIH_ASSISTENTE_OBRIGATORIO=1`, reprovam em vez de pular.

### Verificação de ponta a ponta

A suíte do `pytest` sobe a aplicação em processo. A verificação abaixo roda contra **a API no ar** — HTTP
real, cookie real, banco real — e reporta cada checagem agrupada pelos itens de entrega da disciplina.
É também o roteiro da demonstração.

```bash
docker compose up -d
cd api
GIH_ADMIN_SENHA=... python e2e/verificacao.py
```

**Ela roda do Python da máquina, com as dependências da API**: o `.venv` da seção acima, *Desenvolvendo a
API fora do container*. Sem ele, para no primeiro `import`. No PowerShell, a senha vai numa variável antes:
`$env:GIH_ADMIN_SENHA = "..."`, e depois `python e2e/verificacao.py`.

A senha do administrador sai no log da primeira subida:
`docker compose logs api | grep "Senha sorteada"`. O comando **sai com código diferente de zero** se
qualquer verificação falhar — senão não é verificação, é impressão.

**A verificação não deixa resíduo no banco da equipe.** Ela importa relatórios em semanas no futuro, e
antes elas se acumulavam até o painel abrir numa semana de 2055. Agora, no fim de cada execução — mesmo
interrompida —, os períodos, importações, métricas, parceiros e categorias que ela gravou saem do banco,
e a última checagem confere que o painel voltou a abrir onde abria. Os usuários de teste ficam
**desativados**, não apagados, porque a trilha de auditoria aponta para eles. A transcrição do CRUD faz
o mesmo.

A limpeza vai **direto no banco**, pelo `DATABASE_URL` do `.env`, porque a API recusa de propósito apagar
histórico — o porquê completo está em [`api/e2e/limpeza.py`](api/e2e/limpeza.py). Se o `DATABASE_URL`
apontar para outro banco que não o da API, a limpeza recusa e a verificação reprova, em vez de dar por
limpo o banco errado.

> Os testes precisam do PostgreSQL no ar: eles criam um banco `gih_teste` separado, aplicam as migrações
> nele e limpam as tabelas entre cada teste. SQLite em memória seria mais rápido e não exercitaria `JSONB`,
> os tipos `ENUM` nem as restrições `CHECK` do esquema.

> A porta do Postgres no host é **5433** por padrão (`POSTGRES_PORT` no `.env`), porque a 5432 costuma já
> estar ocupada por outro Postgres na máquina.

A interface (`web/`) sobe junto: `docker compose up` entrega banco, API e aplicação em
`http://localhost:5173`.

### Dados de demonstração

O repositório **não contém dados reais**. Toda a massa de demonstração é gerada por script.

Para avaliar, o caminho é o `popular-demonstracao`, de dentro do contêiner, como acima. Os scripts abaixo são
os da equipe, e rodam do Python da máquina, com o `.venv` da API:

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

**Os usuários vão junto.** No fim, o reset recria o administrador — com a senha de `ADMIN_SENHA`, ou
sorteada e impressa na saída do próprio reset — e reinicia a API, cujas conexões abertas guardavam
consultas preparadas das tabelas antigas e respondiam erro interno (#115). Logins pessoais se recriam
com `criar-usuario`, como acima.

### Medição de desempenho

```bash
api/.venv/Scripts/python scripts/medir_painel.py        # o painel com 5.000 parceiros (H40)
api/.venv/Scripts/python scripts/medir_modelo.py        # o modelo contra as referências (H46)
api/.venv/Scripts/python scripts/medir_otimizador.py    # o otimizador contra o guloso e o teto (H49)
```

O núcleo em C++ é medido no contêiner, que é onde ele roda (ADR-012) — o OpenMP e a GPU contra o C++
serial, o RNF01 e o RNF02 no cenário de referência, a transferência para a GPU e o kernel de avaliação:

```bash
docker build -t gih-nucleo nucleo
docker run --rm --gpus all -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py
```

O primeiro mede o tempo de resposta do painel (RNF03) e confere por `EXPLAIN` que as consultas têm índice
que as atenda; o último fixa o tempo do baseline serial, que é o denominador do *speedup* (RNF02). Os três
criam o banco `gih_medicao` na mesma instância e geram a massa lá — **o banco de trabalho não é tocado**,
então dá para medir com a aplicação aberta em outra janela.

O resultado é gravado em [`docs/medicoes/`](docs/medicoes/), com o comando e a semente que o produzem.

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
