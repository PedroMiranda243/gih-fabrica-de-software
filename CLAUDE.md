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

Estas oito regras não são preferências. Violar qualquer uma delas reprova o Pull Request.

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

RN01 a RN08 em [`docs/02-requisitos.md`](docs/02-requisitos.md), parte IV. Se o seu código precisa de uma
regra que não está lá, **abra uma issue e pergunte**. Não escolha um comportamento razoável e siga em
frente: quatro outras pessoas vão escolher outro.

As duas mais fáceis de errar:

- **RN01** — a segmentação tem ordem de precedência, e *Em Risco vence Top de propósito*.
- **RN02** — a mobilidade do Top N lê o **ranking**, nunca o segmento armazenado. Ler do segmento faz o
  sistema anunciar que um parceiro saiu do Top N enquanto ele continua lá.

### 2.7 Toda alteração passa por Pull Request revisado

`main` é protegida. Nada de push direto, nada de auto-aprovação. Ver [`CONTRIBUTING.md`](CONTRIBUTING.md).

### 2.8 Não altere o que não é seu sem combinar

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

| Diretório | Dono (papel) | Quem mais mexe |
|---|---|---|
| `api/` | Dev Backend / Núcleo | Banco/Testes (migrações e testes) |
| `nucleo/` | Dev Backend / Núcleo | ninguém sozinho — ver abaixo |
| `modelo/` | Dev Backend / Núcleo | — |
| `web/` | Dev Frontend | — |
| `api/migrations/` | Banco de Dados | Backend, com aviso |
| `scripts/` | Banco de Dados | todos |
| `docs/` | Product Owner | todos |
| `.github/` | Scrum Master | — |

**`nucleo/` exige programação em par.** As histórias H53 (OpenMP) e H54 (CUDA) não podem ter uma única
pessoa que entenda o código — é o risco R4 do cronograma. Duas pessoas, sempre.

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

### Antes de abrir o Pull Request

- [ ] Li o diff inteiro e entendo cada linha
- [ ] Nenhum dado real, segredo ou nome real entrou
- [ ] Nenhuma menção a assistente de IA no commit ou no PR
- [ ] Testes passam localmente
- [ ] Não mexi em diretório que não é meu sem combinar
- [ ] A regra de negócio que implementei está em `docs/`, e eu cito o identificador dela

---

## 7. Armadilhas conhecidas

Estas já custaram tempo. Se bater de frente com uma delas, a resposta está aqui.

- **Importação sem período corrompe a segmentação em silêncio.** Sem as datas, as métricas ficam órfãs na
  linha do tempo e a segmentação por tendência classifica errado *sem emitir erro*. Por isso a importação
  sem período é recusada na entrada (RN03), não tolerada com um valor padrão.

- **Mobilidade do Top N lida do segmento dá resposta errada.** Ver RN02. O teste que cobre isso precisa
  incluir um parceiro que está no Top N *e* em queda.

- **Ticket médio é derivado, nunca armazenado.** Guardar como coluna faz o valor divergir das parcelas que
  o originam (RN04).

- **GPU não é garantida.** O sistema precisa funcionar em máquina sem placa compatível, caindo para CPU
  paralela (RNF06). Nunca assuma CUDA disponível.

- **Escala pequena não mostra ganho de GPU.** Com ~100 parceiros, o custo de transferência domina o tempo
  total. O benchmark usa o cenário de referência de 2.000 parceiros por isso — e essa limitação faz parte
  do resultado a ser reportado, não é defeito.

- **Uma migração por Pull Request.** Duas em paralelo conflitam no número sequencial e quebram o histórico
  do banco para todo mundo.

---

## 8. Onde encontrar o resto

| Preciso de… | Está em |
|---|---|
| Problema, objetivos, público-alvo | [`docs/01-visao-do-produto.md`](docs/01-visao-do-produto.md) |
| Requisitos e **regras de negócio RN01–RN08** | [`docs/02-requisitos.md`](docs/02-requisitos.md) |
| Casos de uso e fluxos | [`docs/03-casos-de-uso.md`](docs/03-casos-de-uso.md) |
| O que construir e em que ordem | [`docs/04-product-backlog.md`](docs/04-product-backlog.md) |
| Prazos, marcos e riscos | [`docs/05-cronograma.md`](docs/05-cronograma.md) |
| Papéis, cerimônias, Definition of Done | [`docs/06-equipe-e-processo.md`](docs/06-equipe-e-processo.md) |
| Arquitetura e decisões registradas | [`docs/07-arquitetura-preliminar.md`](docs/07-arquitetura-preliminar.md) |
| Ramos, commits, Pull Requests | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

**Este arquivo é vivo.** Decisão de arquitetura ou convenção nova entra aqui, no mesmo Pull Request que a
introduz. Se o código diverge deste documento, um dos dois está errado — e vale a pena descobrir qual
antes de seguir.
