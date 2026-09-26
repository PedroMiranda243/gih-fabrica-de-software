# CLAUDE.md — contexto do projeto para assistentes de IA

> **Leia este arquivo inteiro antes de escrever qualquer linha de código.**
>
> Cinco pessoas desenvolvem este projeto, e todas usam assistentes de IA. Sem um contrato comum, cada
> assistente inventa a sua própria arquitetura, os seus próprios nomes e as suas próprias regras de
> negócio — e o resultado é um repositório com cinco projetos dentro. Este arquivo é esse contrato.
>
> Vale para Claude Code, Copilot, Cursor, Gemini ou qualquer outro. Se você é uma pessoa, leia também:
> as regras são as mesmas.

---

## 1. O que é este projeto

**Growth Intelligence Hub (GIH)** — plataforma que recebe relatórios periódicos de desempenho de uma rede
de comércios parceiros de delivery e devolve um **plano de ação comercial priorizado**: quem está
crescendo, quem vai cair, e em quem investir a verba limitada da próxima campanha.

Projeto integrador das disciplinas **Fábrica de Software** e **Tópicos Avançados** (UNINASSAU, 2026.2).
Entrega final em **05/12/2026**.

O coração técnico é um **otimizador combinatório paralelizado** (serial → OpenMP → CUDA) alimentado por um
**modelo preditivo treinado pela equipe**. Não é um CRUD com um chatbot pendurado.

Documentação completa em [`docs/`](docs/). Comece por
[`docs/01-visao-do-produto.md`](docs/01-visao-do-produto.md).

---

## 2. Regras inegociáveis

Estas nove regras não são preferências. Violar qualquer uma delas reprova o Pull Request.

### 2.1 O repositório é público — nada real entra aqui

- **Nenhum dado real** de nenhuma operação, empresa ou pessoa. Toda massa de demonstração vem de
  `scripts/gerar_dados_sinteticos.py`.
- **Nenhum segredo**: senhas, tokens e cadeias de conexão ficam em `.env`, que está no `.gitignore`.
  O repositório contém apenas `.env.example`, com valores fictícios.
- **Nenhum nome** de organização, cliente, parceiro ou pessoa real — em código, comentário, documentação,
  teste ou dado de exemplo.

### 2.2 Commits são apenas dos integrantes

**Nunca** adicione `Co-Authored-By` de assistente de IA, nem `Generated with`, nem qualquer menção a
ferramenta de IA em mensagem de commit, título de Pull Request ou descrição.

O trabalho é da equipe e o histórico reflete isso. Esta regra já custou uma reescrita de histórico — não
a reintroduza.

### 2.3 O modelo de linguagem nunca calcula número

Ranking, segmentação, métricas, previsão e otimização são **determinísticos**, implementados em código.
O LLM só redige texto e responde sobre dados já recuperados, citando o período de origem ou se abstendo.

Se você está prestes a pedir a um modelo que some, conte, compare ou classifique por valor: pare. Isso é
código.

### 2.4 Regra de negócio nunca no frontend

A interface exibe e coleta. A API decide. Se você precisa de um `if` sobre valor de negócio no React,
ele está no lugar errado.

### 2.5 Autorização é verificada no servidor

Esconder um botão não é controle de acesso. Todo endpoint valida o perfil do usuário no servidor, sempre,
mesmo que a interface já impeça a ação.

### 2.6 As regras de negócio estão escritas — não as invente

RN01 a RN11 em [`docs/02-requisitos.md`](docs/02-requisitos.md), parte IV. Se o seu código precisa de uma
regra que não está lá, **abra uma issue e pergunte**. Não escolha um comportamento razoável e siga em
frente: quatro outras pessoas vão escolher outro.

As duas mais fáceis de errar:

- **RN01** — a segmentação tem ordem de precedência, e *Em Risco vence Top de propósito*.
- **RN02** — a mobilidade do Top N lê o **ranking**, nunca o segmento armazenado. Ler do segmento faz o
  sistema anunciar que um parceiro saiu do Top N enquanto ele continua lá.

### 2.7 Toda alteração passa por Pull Request revisado

`main` é protegida. Nada de push direto, nada de auto-aprovação. Ver [`CONTRIBUTING.md`](CONTRIBUTING.md).

### 2.8 Tudo é autoral ou open source

Nenhuma dependência paga, nenhum serviço que cobre por uso, nenhuma API proprietária de IA. O que o
sistema faz, ele faz com código da equipe ou com biblioteca livre rodando na própria infraestrutura.

- **IA roda local.** Modelo via Ollama, na máquina. Nunca OpenAI, Gemini, Claude ou similar por API — além
  do custo, mandaria dados para fora e tiraria a reprodutibilidade da avaliação.
- **O núcleo de decisão é escrito pela equipe.** Segmentação, previsão e otimização. Pegar um solver pronto
  resolveria o problema e eliminaria justamente o componente que a disciplina avalia (ver ADR-002 em
  `docs/07-arquitetura-preliminar.md`).
- **Bibliotecas com licença permissiva** — MIT, Apache 2.0 ou BSD. Evite copyleft forte: o repositório é
  público mas com direitos reservados aos autores, e uma dependência GPL/AGPL conflita com isso.
- **Exceção conhecida:** o CUDA Toolkit é gratuito, porém proprietário da NVIDIA. Foi explicitamente
  recomendado pela disciplina, então fica. O equivalente aberto é o **OpenCL**, já registrado como
  alternativa no risco R1 do cronograma.

Antes de adicionar qualquer dependência: confira a licença e registre a escolha na issue.

### 2.9 Não altere o que não é seu sem combinar

Ver o mapa de responsabilidades na seção 4. Assistentes de IA adoram "melhorar de passagem" arquivos
vizinhos — é a principal fonte de conflito de merge em equipe. Se algo fora do seu escopo está errado,
**abra uma issue**.

---

## 3. Arquitetura

```
Navegador ──▶ web/ (React + Vite)
                  │  REST /api
                  ▼
              api/ (Python 3.11 + FastAPI) ──────▶ PostgreSQL 16
                  │
        ┌─────────┴──────────┬──────────────────┐
        ▼                    ▼                  ▼
   modelo/ (PyTorch)   nucleo/ (C++/CUDA)   assistente (LLM local)
```

| Camada | Responsabilidade | O que **não** faz |
|---|---|---|
| `web/` | Exibe, formata, coleta entrada | Nenhuma regra de negócio |
| `api/` | Regras de negócio, autorização, persistência, orquestração | Cálculo pesado dentro da requisição |
| `nucleo/` | Otimizador: serial, OpenMP, CUDA | Não conhece autenticação nem banco |
| `modelo/` | Previsão de faturamento e risco | Não decide ação comercial |
| assistente | Redige texto | **Não calcula número** |

Detalhes e decisões registradas em
[`docs/07-arquitetura-preliminar.md`](docs/07-arquitetura-preliminar.md).

### Stack — não troque por conta própria

Python 3.11 + FastAPI · C++17 + OpenMP + CUDA · PyTorch + NumPy · PostgreSQL 16 + Alembic ·
React + Vite · pytest + Vitest · Docker Compose.

A disciplina orienta que **JavaScript não seja usado no núcleo computacional**. JavaScript existe apenas
em `web/`. IA, processamento intensivo, paralelismo, otimização e GPU ficam em Python, C++ e CUDA.

Trocar biblioteca ou padrão arquitetural exige issue com justificativa e aval da equipe. "O assistente
sugeriu" não é justificativa.

---

## 4. Mapa de responsabilidades

Cada diretório tem um dono. Isso não impede ninguém de contribuir — impede cinco pessoas de editarem o
mesmo arquivo na mesma semana.

| Diretório | Dono | Papel | Quem mais mexe |
|---|---|---|---|
| `api/` | @PedroMiranda243 | Dev Backend / Núcleo | Banco/Testes (migrações e testes) |
| `nucleo/` | @PedroMiranda243 | Dev Backend / Núcleo | responsável único — ver abaixo |
| `modelo/` | @PedroMiranda243 | Dev Backend / Núcleo | — |
| `web/` | @ingrydaraujob | Dev Frontend | — |
| `api/migrations/` | @joaopfranca04 | Banco de Dados | Backend, com aviso |
| `scripts/` | @joaopfranca04 | Banco de Dados | todos |
| `docs/` | @mihaeldatoman | Product Owner | todos |
| `.github/` | @ThiagojFalcao | Scrum Master | — |

Esse mapa está automatizado em [`.github/CODEOWNERS`](.github/CODEOWNERS): ao abrir um Pull Request que
toque um destes caminhos, o dono é convidado a revisar.

**`nucleo/` tem um único responsável, e isso é um risco assumido.** É o R4 do cronograma: se só uma pessoa
entende o motor do projeto, a banca pode perguntar a quem não sabe responder. Como não há par, a mitigação
é **transferência de conhecimento**:

- Toda decisão não óbvia vira ADR em `docs/07-arquitetura-preliminar.md`, não só comentário no código
- O código do núcleo é apresentado à equipe nas revisões das Sprints 10 e 11, com alguém além do autor
  conseguindo explicar o que o kernel faz e por quê
- Os comentários no `nucleo/` explicam o *porquê* com mais rigor que no resto do projeto

### Como evitar conflito de merge

1. Uma issue por vez, um ramo por issue.
2. Atualize seu ramo com `main` **todo dia**: `git pull --rebase origin main`.
3. Pull Request pequeno vale mais que Pull Request completo. Prefira dois PRs de 200 linhas a um de 800.
4. Vai mexer em arquivo fora do seu diretório? Comente na issue **antes**.
5. Migrações de banco: uma por PR, nunca duas em paralelo — o número sequencial conflita.

---

## 5. Convenções de código

### Idioma

| Onde | Idioma |
|---|---|
| Domínio de negócio: entidades, campos, segmentos, mensagens ao usuário | **Português** (`Parceiro`, `faturamento`, `EM_RISCO`) |
| Termos técnicos universais | Inglês, como já se escreve (`endpoint`, `commit`, `cache`) |
| Comentários e documentação | **Português** |
| Mensagens de commit e Pull Request | **Português** |

Não traduza pela metade. `partnerFaturamento` não existe.

### Nomenclatura

| Contexto | Padrão | Exemplo |
|---|---|---|
| Python: funções, variáveis | `snake_case` | `calcular_ticket_medio` |
| Python: classes | `PascalCase` | `SegmentadorDeterministico` |
| Python: constantes | `MAIÚSCULO_COM_UNDERSCORE` | `LIMIAR_TOP_N` |
| Banco: tabelas e colunas | `snake_case`, tabela no singular | `parceiro`, `historico_segmento` |
| C++: funções e variáveis | `snake_case` | `avaliar_populacao` |
| C++: tipos | `PascalCase` | `PlanoCampanha` |
| React: componentes | `PascalCase` | `PainelRanking.jsx` |
| React: hooks | `useCamelCase` | `useParceiros` |
| Rotas da API | plural, `kebab-case` | `/api/parceiros`, `/api/planos-campanha` |

### Comentários

Comentário explica **por que**, não o quê. O quê já está no código.

```python
# Em Risco vence Top de propósito: é assim que o painel responde
# "quem está prestes a sair do Top 15?" (RN01).
if quedas_consecutivas >= limiar:
    return Segmento.EM_RISCO
```

Se um trecho parece estranho, o comentário deve dizer por que é assim. Se não parece estranho, provavelmente
não precisa de comentário.

### Contrato da API

A API é o contrato entre `api/` e `web/`. Ele é definido **antes** de qualquer um dos dois codificar.

- FastAPI gera a especificação em `/docs` automaticamente
- Mudou o formato de uma resposta? Avise no canal da equipe **e** atualize a issue
- Frontend não codifica contra a implementação; codifica contra o contrato

### Erros

Cliente recebe mensagem genérica em português. Detalhe técnico vai para o log com identificador de
correlação. Nunca exponha rastreamento de pilha na resposta (RNF18, RNF19).

---

## 6. Trabalhando com assistente de IA

Sugestões práticas para que cinco assistentes produzam código coerente.

### Faça

- **Dê o contexto certo**: aponte o assistente para este arquivo, para a issue e para os requisitos
  envolvidos (RFxx, RNFxx, RNxx).
- **Peça mudanças cirúrgicas**: "edite a função X" produz diffs revisáveis. "reescreva o arquivo" produz
  Pull Requests que ninguém consegue revisar.
- **Cole a regra de negócio** de `docs/02-requisitos.md` em vez de descrevê-la de memória.
- **Exija teste junto**: toda regra de negócio nova vem com teste no mesmo Pull Request.
- **Leia o que foi gerado antes de commitar.** Você assina o commit; a responsabilidade é sua, e a
  disciplina avalia participação individual.

### Não faça

- Não aceite refatoração fora do escopo da issue, por mais tentadora que pareça.
- Não deixe o assistente inventar valor de negócio: limiar, peso, custo de ação, fórmula de uplift.
  Se não está em `docs/`, pergunte na issue.
- Não deixe o assistente criar dado de exemplo com nome de empresa real — use o gerador sintético.
- Não deixe o assistente adicionar dependência nova sem discussão. Cada biblioteca é dívida.
- Não peça ao assistente para "fazer os testes passarem". Peça para corrigir o defeito.

### Interface: carregue as referências de design antes de codificar

Tela feita "no capricho do momento" fica com cara de template. Antes de escrever qualquer coisa em `web/`,
carregue as skills de design e UX disponíveis no seu assistente — e, para **qualquer gráfico**, carregue a
referência de visualização de dados **antes da primeira linha de código do gráfico**, não depois.

Isto vale especialmente aqui: o produto **é** um painel. Ranking, séries históricas, comparativo de
benchmark e distribuição por segmento são o núcleo da experiência, não enfeite. Gráfico ilegível ou paleta
inconsistente compromete a demonstração final, que vale 20% da nota.

O que precisa estar decidido antes de codificar, e registrado em `docs/`:

- Paleta, tipografia e escala de espaçamento — uma vez, para o projeto inteiro
- Regra de cor para os **segmentos** (Top, Em Ascensão, Em Risco, Recém-chegado, Estável): cada segmento
  tem uma cor e só uma, usada de forma idêntica em tabela, gráfico e indicador
- Contraste mínimo AA (RNF22) e layout a partir de 768 px (RNF21) — verificados, não presumidos
- Estados vazios: base sem dados, período único, otimização sem solução viável

**O protótipo (H08) é portão, não sugestão.** A direção visual precisa estar aprovada pela equipe antes de
existir CSS. Num projeto anterior deste mesmo domínio, "tema escuro e elegante" foi tratado como
especificação suficiente; o redesign inteiro foi rejeitado depois de pronto e ~500 linhas de CSS foram
descartadas. Validar antes custa uma conversa; validar depois custa o trabalho inteiro.

### Sistema visual: duas regras que não se negociam

Vieram da correção daquele redesign rejeitado. Valem desde a primeira tela.

**1. Cada cor tem um trabalho só.** A cor de ação significa *"responde ao seu clique"* — botão, link, foco,
seleção — e nada mais. No projeto anterior ela era marca, ação **e** dado ao mesmo tempo, usada 18 vezes
incluindo todas as barras de categoria. Quando uma cor significa tudo, não significa nada.

- As cores semânticas (risco, ascensão, Top, recém-chegado) aparecem só como **ponto ou barra**
- O rótulo do segmento é **neutro** — "Top 15" repetido doze vezes em cor é ruído puro
- Gráficos usam uma **rampa fria própria**, nunca a cor de ação nem as semânticas

Se você for acrescentar a cor de ação em algo que não responde a clique, é sinal de que a cor errada está
sendo usada.

**2. Hierarquia vem do peso e da superfície, não do contraste.** Passar no teste de contraste não faz o
olho achar nada. Na tabela de parceiros, o nome deve ser o **único** elemento em peso alto e tinta cheia.
A escada de superfícies precisa de degraus largos o bastante para serem percebidos.

### Antes de abrir o Pull Request

- [ ] Li o diff inteiro e entendo cada linha
- [ ] Nenhum dado real, segredo ou nome real entrou
- [ ] Nenhuma menção a assistente de IA no commit ou no PR
- [ ] Testes passam localmente
- [ ] Não mexi em diretório que não é meu sem combinar
- [ ] A regra de negócio que implementei está em `docs/`, e eu cito o identificador dela

---

## 7. Armadilhas conhecidas

Boa parte destas veio de um projeto anterior no mesmo domínio, onde cada uma custou horas. Se bater de
frente com alguma, a resposta já está aqui.

### Dados e regras de negócio

- **Importação sem período corrompe a segmentação em silêncio.** Sem as datas, as métricas ficam órfãs na
  linha do tempo e a segmentação por tendência classifica errado *sem emitir erro*. Aconteceu de verdade:
  parceiros perderam classificação e o painel continuou parecendo correto. Por isso a importação sem
  período é recusada na entrada (RN03), não tolerada com um valor padrão.

- **Mobilidade do Top N lida do segmento dá resposta errada.** Ver RN02. O teste que cobre isso precisa
  incluir um parceiro que está no Top N *e* em queda.

- **Ticket médio é derivado, nunca armazenado.** Guardar como coluna faz o valor divergir das parcelas que
  o originam (RN04).

- **Sempre que a escolha for entre seguir com dado parcial e recusar explicando, recuse e explique.**
  Corromper em silêncio custa muito mais caro que falhar alto.

### Desempenho

- **Nada de N+1 na segmentação.** Recalcular o segmento com uma consulta por parceiro funciona com 100 e
  morre com 10.000 — que é a carga do RNF04, com resposta em até 2 s pelo RNF03. A solução é **consulta
  agregada**, não thread. Isso precisa estar certo na primeira versão do serviço, não virar otimização
  depois.

- **Escala pequena não mostra ganho de GPU — e agora há número.** O spike da H47 mediu: abaixo de ~4.000
  planos candidatos, 16 threads de OpenMP batem a GPU inteira; acima disso, a GPU com transferência a cada
  geração ganha só 1,1x–1,3x do OpenMP — mas o kernel sozinho ganha 11x. A transferência é 88% do tempo.
  Por isso a população **permanece na GPU entre gerações** (H54c): não é otimização, é o que justifica usar
  GPU. O benchmark usa o cenário de referência de 2.000 parceiros por isso — e essa limitação faz parte do
  resultado a ser reportado, não é defeito. Ver `nucleo/spike/RESULTADO.md`.

- **GPU não é garantida.** O sistema precisa funcionar em máquina sem placa compatível, caindo para CPU
  paralela (RNF06). Nunca assuma CUDA disponível.

- **O núcleo roda no contêiner, e é lá que se mede.** Dentro do Docker (WSL2), a transferência para a GPU
  custa ~40% a mais que no Windows nativo, e o OpenMP do GCC ganha menos que o do MSVC em trabalho pequeno
  (0,8x contra 10,4x em 256 planos). Número tirado do `construir.bat` não vale para o benchmark. Ver a
  parte 3 de `nucleo/spike/RESULTADO.md` e a ADR-012.

### Como testar de verdade

- **Teste o que o usuário vê, não o que o código diz.** Num projeto anterior, a tela de login "não fazia
  nada": o login funcionava, mas a tela não sumia. O atributo `[hidden]` tem especificidade baixíssima em
  CSS e uma classe com `display` o anulava. **Os testes validavam a propriedade `hidden` e passavam com a
  tela visível na frente do usuário.** Verifique visibilidade por `getComputedStyle().display`, nunca pelo
  atributo — e mantenha um reset `[hidden] { display: none !important }` no CSS.

- **Desconfie do instrumento antes do resultado.** Uma auditoria de contraste lia as cores com regex
  esperando `rgb()`; como as cores eram `oklch()`, o regex lia zeros e acusava falha catastrófica que não
  existia. O mesmo padrão deu falso positivo em testes de XSS feitos com regex sobre HTML. Meça contraste
  pintando a cor num `<canvas>` e lendo o pixel; parseie HTML com parser de HTML. **Medição surpreendente
  geralmente é medição quebrada.**

- **Benchmark com número fixo de repetições mede o relógio, não o trabalho.** Na validação do toolchain
  (H47), o ganho do OpenMP em 1.024 planos saiu **7,5x numa execução e 13,9x na seguinte**, no mesmo cenário
  e no mesmo binário: cinco repetições de uma passada sub-milissegundo são ruído. Calibre quantas repetições
  cabem num alvo de tempo (~300 ms), aqueça antes de medir e reporte **mediana de várias execuções**. Sem
  isso, a Sprint 12 vai colocar num gráfico um número que não se reproduz na frente da banca.

- **A medição paralela oscila mais que a serial — reporte dispersão.** No mesmo teste, o tempo serial repetiu
  em 0,1% entre execuções enquanto o paralelo variou 45%. Um número único de *speedup* esconde isso.

- **Comentário sem medição é hipótese.** Um comentário afirmando "aqui o CORS nem é exercitado" escondeu
  um bug por semanas. Se você não mediu, não escreva como certeza — a próxima pessoa vai confiar no
  comentário em vez de investigar.

- **Escreva o teste de ponta a ponta cedo.** Num projeto anterior ele só apareceu depois da auditoria de
  segurança, e foi identificado como erro de ordem. Aqui ele entra junto com a ingestão.

### Ambiente Windows

- **O console mostra mojibake** (`JoÃ£o`) mesmo com os dados corretos em UTF-8. **Não confunda com bug de
  encoding.** Para verificar de verdade, escreva num arquivo com `encoding='utf-8'` e leia o arquivo, ou
  cheque os bytes.

- **Aspas em JSON no shell quebram com frequência.** Para testar a API, prefira um script Python a
  `curl -d '{...}'` — já houve teste "passando" porque o corpo chegava vazio.

- **O caminho deste projeto tem acento, e o `cmd` quebra com ele.** `cd` funciona, mas encadear com `&&`,
  `|` ou `&` na mesma linha falha sem mensagem útil — e `cl`/`nvcc` só existem depois do `vcvars64.bat`,
  que é exatamente um encadeamento desses. Por isso compilar o `nucleo/` é sempre por `construir.bat`, nunca
  chamando o compilador solto. Se precisar mesmo de uma linha de `cmd`, use o caminho curto 8.3 (obtido com
  `for %I in (".") do @echo %~sI`).

- **Arquivo gravado no Windows vira CRLF e quebra o contêiner.** O `entrypoint.sh` com fim de
  linha CRLF faz o shebang virar `/bin/sh\r`, e o Docker responde
  `exec ./entrypoint.sh: no such file or directory` — apontando para o arquivo, **que existe**. Pior: o
  `git diff` não mostra nada, porque o git normaliza na leitura enquanto o Docker copia o arquivo do
  disco. O `.gitattributes` fixa LF nos arquivos que o Linux lê; e se você gravar um `.sh` por
  script Python, passe `newline="\n"` — o modo texto traduz para CRLF sozinho.

- **Docker para quando a máquina fica ociosa.** Se a API não sobe e o banco está fora, é provavelmente
  isso. Suba o Docker Desktop de novo antes de procurar bug.

### Processo

- **Uma migração por Pull Request.** Duas em paralelo conflitam no número sequencial e quebram o histórico
  do banco para todo mundo.

- **O `autogenerate` do Alembic não remove os tipos ENUM no downgrade.** Ele só derruba as tabelas. Sem
  acrescentar `DROP TYPE` à mão, reverter e reaplicar falha com *type already exists* — e o erro só aparece
  na segunda execução, quando já se perdeu tempo procurando em outro lugar. Toda migração que cria enum
  precisa derrubá-lo no downgrade. Ver `esquema_inicial`.

- **A porta 5432 costuma estar ocupada.** Outro Postgres na máquina impede o container de subir. O
  `docker-compose.yml` usa `POSTGRES_PORT`, com 5433 como padrão — e o `DATABASE_URL` precisa apontar para
  a mesma porta, senão as migrações rodam no banco errado.

---

## 8. Onde encontrar o resto

| Preciso de… | Está em |
|---|---|
| Problema, objetivos, público-alvo | [`docs/01-visao-do-produto.md`](docs/01-visao-do-produto.md) |
| Requisitos e **regras de negócio RN01–RN11** | [`docs/02-requisitos.md`](docs/02-requisitos.md) |
| Casos de uso e fluxos | [`docs/03-casos-de-uso.md`](docs/03-casos-de-uso.md) |
| O que construir e em que ordem | [`docs/04-product-backlog.md`](docs/04-product-backlog.md) |
| Prazos, marcos e riscos | [`docs/05-cronograma.md`](docs/05-cronograma.md) |
| Papéis, cerimônias, Definition of Done | [`docs/06-equipe-e-processo.md`](docs/06-equipe-e-processo.md) |
| Arquitetura e decisões registradas | [`docs/07-arquitetura-preliminar.md`](docs/07-arquitetura-preliminar.md) |
| Ramos, commits, Pull Requests | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

**Este arquivo é vivo.** Decisão de arquitetura ou convenção nova entra aqui, no mesmo Pull Request que a
introduz. Se o código diverge deste documento, um dos dois está errado — e vale a pena descobrir qual
antes de seguir.
