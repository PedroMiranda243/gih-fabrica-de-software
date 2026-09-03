# 06 — Equipe e Processo

**Projeto:** Growth Intelligence Hub (GIH)
**Sprint:** 1 — Planejamento e Descoberta
**Versão:** 1.0 — 03/09/2026

---

## 1. Composição da equipe

Equipe de **5 integrantes**, dentro do limite de 3 a 5 estabelecido pela disciplina.

| Integrante | Matrícula | GitHub | Papel |
|---|---|---|---|
| Ingryd Vitoria de Araújo Barbosa | 01642893 | [@ingrydaraujob](https://github.com/ingrydaraujob) | *a definir* |
| João Pedro Nunes de França | 01626444 | [@joaopfranca04](https://github.com/joaopfranca04) | *a definir* |
| Marcio Maycom | 01607574 | [@mihaeldatoman](https://github.com/mihaeldatoman) | *a definir* |
| Pedro Miranda | 01607408 | [@PedroMiranda243](https://github.com/PedroMiranda243) | *a definir* |
| Thiago José Falcão de Freitas | 01597267 | [@ThiagojFalcao](https://github.com/ThiagojFalcao) | *a definir* |

Os cinco papéis previstos — Scrum Master, Product Owner, Desenvolvedor Backend / Núcleo Computacional,
Desenvolvedor Frontend, e Banco de Dados / Documentação / Testes — estão descritos na seção 2. A atribuição
de cada papel a cada integrante é definida na primeira reunião da equipe.

> **Os papéis organizam; não isolam.** Todos os integrantes contribuem com código e todos aparecem no
> histórico de commits. A disciplina avalia participação individual, e a ausência de participação de um
> integrante impacta a nota dele.

---

## 2. Responsabilidades

### Scrum Master
Conduz as cerimônias, mantém o board atualizado e acompanha o avanço contra o cronograma. Remove
impedimentos e é quem levanta a mão quando a velocidade real não sustenta a carga planejada. Garante que
cada orientação tenha algo executável para mostrar.

### Product Owner
Dono do backlog: escreve e refina histórias, define critérios de aceite e prioriza. É quem decide o que sai
quando o prazo aperta, seguindo a ordem de corte acordada. Valida a entrega contra os critérios antes de
considerar uma história concluída.

### Desenvolvedor Backend / Núcleo Computacional
Implementa a API, as regras de negócio e — principalmente — o **núcleo em C++/CUDA e o modelo preditivo**.
É a trilha técnica mais especializada do projeto, e por isso a que exige mais disciplina de
compartilhamento: programação em par obrigatória nas histórias H53 e H54, e decisões registradas em
documento.

### Desenvolvedor Frontend
Constrói as telas, o painel, os gráficos e os formulários. Responsável pela responsividade e pela
acessibilidade. Trabalha contra a API acordada, e não contra a implementação dela.

### Banco de Dados, Documentação e Testes
Modela o banco, escreve e mantém as migrações, cuida da suíte de testes automatizados e da documentação
técnica. É quem verifica, ao fim do semestre, se um terceiro consegue subir o sistema seguindo apenas o
README.

### Substituição
Cada papel tem um substituto natural definido no início de cada sprint. Nenhuma história crítica fica com
um único responsável — mitigação dos riscos R4 e R6 do [cronograma](05-cronograma.md).

---

## 3. Definition of Done

Uma história só é considerada concluída quando **todos** os itens abaixo forem verdadeiros:

- [ ] Os critérios de aceite da história foram atendidos
- [ ] O código está em um Pull Request revisado e aprovado por outro integrante
- [ ] A integração contínua passou: análise estática e testes verdes
- [ ] Há teste automatizado cobrindo o comportamento novo, quando se trata de regra de negócio
- [ ] A autorização por perfil foi verificada no servidor, quando a história expõe um endpoint
- [ ] A documentação afetada foi atualizada no mesmo Pull Request
- [ ] A funcionalidade foi demonstrada rodando, e não apenas descrita
- [ ] A *issue* correspondente foi movida para Concluído no board

---

## 4. Fluxo de trabalho no Git

### Ramos

| Ramo | Uso |
|---|---|
| `main` | Sempre estável e executável. **Protegido**: recebe alterações apenas por Pull Request aprovado. |
| `feat/<numero-issue>-<descricao-curta>` | Nova funcionalidade |
| `fix/<numero-issue>-<descricao-curta>` | Correção |
| `docs/<descricao-curta>` | Somente documentação |
| `spike/<descricao-curta>` | Investigação técnica sem compromisso de mesclagem |

Exemplo: `feat/54-otimizador-cuda`

### Commits

Formato: `<tipo>: <o que mudou e por quê>`

Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

```
feat: recusar importação sem período informado

Sem o período, as métricas ficam órfãs na linha do tempo e a segmentação
por tendência classifica errado sem emitir erro. Melhor falhar na entrada.
```

Mensagens em português, explicando **o porquê** e não apenas o quê. O "o quê" já está no diff.

### Pull Requests

- Título referenciando a issue: `H54 · Otimizador em CUDA (#54)`
- Descrição preenchendo o modelo do repositório: o que muda, como testar, o que ficou de fora
- **Ao menos um revisor** que não seja o autor
- CI verde antes da mesclagem
- Mesclagem por *squash*, mantendo o histórico de `main` legível

---

## 5. Cerimônias

| Cerimônia | Quando | Duração | Participantes |
|---|---|---|---|
| Planejamento da sprint | Quinta, início da sprint | 60 min | Toda a equipe |
| Acompanhamento | Segunda e quinta | 15 min | Toda a equipe |
| Orientação | Semanal | conforme a disciplina | Equipe + professora |
| Revisão da sprint | Quarta, fim da sprint | 45 min | Toda a equipe |
| Retrospectiva | Quarta, após a revisão | 30 min | Toda a equipe |

### O que levar para cada orientação

A disciplina é explícita: não são aceitas orientações baseadas apenas em slides ou em ideias sem
implementação. Toda reunião apresenta **evolução prática**. O roteiro fixo:

1. Repositório atualizado, aberto na tela
2. Funcionalidades desenvolvidas na quinzena, **rodando**
3. Dificuldades encontradas e o que foi tentado
4. Planejamento da próxima sprint

---

## 6. Organização no GitHub

| Recurso | Uso |
|---|---|
| **Issues** | Uma por história do backlog, com critérios de aceite no corpo |
| **Labels** | Épico (`E1`…`E9`), prioridade (`must`, `should`, `could`), tipo (`feat`, `fix`, `docs`, `test`, `spike`) |
| **Milestones** | Uma por sprint, com a data de encerramento |
| **Project (board)** | Colunas: Backlog · Sprint atual · Em andamento · Revisão · Concluído |
| **Pull Requests** | Toda alteração em `main`; revisão obrigatória |
| **Actions** | Análise estática e testes a cada Pull Request |

O board é a fonte da verdade sobre o andamento. O documento
[04 — Product Backlog](04-product-backlog.md) é o retrato aprovado na Sprint 1.

---

## 7. Comunicação

| Canal | Uso |
|---|---|
| Grupo de mensagens da equipe | Coordenação do dia a dia e acompanhamentos |
| Issues e Pull Requests | **Toda decisão técnica** — para ficar registrada e rastreável |
| Documentos em `docs/` | Decisões estruturais, requisitos e arquitetura |

Regra: decisão técnica discutida por mensagem só vale depois de registrada na issue ou no Pull Request
correspondente. O que não está escrito no repositório não aconteceu.

---

## 8. Qualidade

| Prática | Compromisso |
|---|---|
| Testes automatizados | Cobertura de no mínimo 70% no núcleo de regras (RNF24) |
| Testes de segurança | Autorização, injeção e sessão cobertos por teste (RNF12, RNF13, RNF14) |
| Análise estática | Executada na CI a cada Pull Request |
| Revisão por par | Obrigatória, sem exceção |
| Programação em par | Obrigatória nas histórias do núcleo em C++/CUDA |
| Reprodutibilidade | Validada por integrante que não escreveu a parte (RNF27) |

---

## 9. Regras de confidencialidade e dados

O repositório é **público**. Valem, sem exceção:

1. **Nenhum dado real** de nenhuma operação entra no repositório. Toda massa de demonstração é gerada por
   `scripts/gerar_dados_sinteticos.py`.
2. **Nenhum segredo** versionado: senhas, tokens e cadeias de conexão ficam em `.env`, bloqueado pelo
   `.gitignore`. O repositório contém apenas o `.env.example`, com valores fictícios.
3. **Nenhum nome de organização, pessoa ou parceiro real** aparece em código, documentação ou dados de
   exemplo.
4. Antes de cada entrega, é executada uma verificação de conteúdo sensível no repositório.

O projeto é acadêmico e os direitos são reservados aos autores. Repositório público significa visível para
avaliação e portfólio — não licenciado para uso, cópia ou redistribuição.
