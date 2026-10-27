# 12 — Plano de testes

**Projeto:** Growth Intelligence Hub (GIH)
**Versão:** 1.0 — 26/10/2026 · H104 e H105, Sprint 09
**Responsáveis:** João Pedro (testes), Marcio (requisitos), com a equipe inteira na execução manual

---

## 1. Para que serve

Este documento diz **o que se testa no GIH, como, e o que se espera de cada caso**. Os casos das seções
5 a 7 não são uma lista para conferir à mão: o `scripts/testar_na_tela.py` lê as tabelas deste arquivo,
executa cada caso num navegador de verdade, contra o sistema no ar, e registra o resultado **obtido** ao
lado do esperado, com uma captura da tela. Se um caso estiver aqui e não no script, ou no script e não
aqui, o script se recusa a rodar.

## 2. Os quatro níveis

| Nível | O que prova | Onde está | Como roda | Na CI |
|---|---|---|---|---|
| Unidade e integração | Cada regra e cada rota da API, com o banco de teste; cada tela, com a API simulada e o axe no fim | `api/tests/`, `web/src/**/*.test.*`, `nucleo/tests/`, `modelo/tests/` | `pytest`, `npm test` | Sim, a cada PR |
| API de ponta a ponta | O sistema no ar responde como os requisitos dizem: fluxos, permissões e recusas | `api/e2e/verificacao.py`, `validacoes.py`, `transcricao_permissoes.py` | contra o `docker compose up` | Não: precisa do sistema no ar |
| Pela tela | O que a pessoa vê: os casos deste documento, clicando como ela clica | `scripts/testar_na_tela.py` | contra o `docker compose up`, no Edge ou no Chrome | Não: precisa do sistema no ar |
| Medição | As 30 telas a 768 e 1.440 px nos dois temas, o axe na página inteira, o contraste; as regras RN01 a RN11 numa base própria | `scripts/medir_telas.py`, `scripts/revisar_regras.py` | contra o sistema no ar | Não |

Os dois primeiros níveis já existiam. A Sprint 09 acrescenta o terceiro: até aqui, a tela só era testada
com a API simulada, e "teste da tela com a API simulada não prova o contrato" (`CLAUDE.md`, seção 7).

## 3. Ambiente

- **O sistema:** `docker compose up -d`, e o perfil `assistente` para o modelo de linguagem. Sem ele, o
  assistente e as mensagens usam o que o sistema monta sozinho, e os casos dizem qual dos dois respondeu.
- **A base:** a de demonstração, com os dados do gerador sintético (`scripts/gerar_dados_sinteticos.py`).
  Nenhum dado real.
- **As contas:** o executor cria uma conta por perfil, com a marca da execução no login
  (`t12345.gestor`) e uma senha sorteada que só existe na memória dele. Precisa só da senha do
  administrador, em `GIH_ADMIN_SENHA`.
- **Os dados de teste:** parceiros e ações levam a marca no nome; a importação vai para uma semana no
  futuro. No fim, tudo o que a execução gravou sai pela limpeza da verificação de ponta a ponta
  (`api/e2e/limpeza.py`), e as contas são desativadas — não apagadas, porque a trilha de auditoria aponta
  para o autor. O limiar alterado volta ao valor de antes, mesmo se o caso falhar no meio.
- **Os navegadores:** o Microsoft Edge e o Google Chrome instalados na máquina, pelo Playwright
  (Apache 2.0, já usado pela medição das telas). O Firefox não está instalado.

## 4. Critérios de aprovação

- **Um caso passa** quando a tela faz o que a coluna "Esperado" diz **e** nada mais dá errado no
  caminho: nenhuma resposta da API com erro que o caso não provocou de propósito, nenhum erro no console
  do navegador, nenhuma exceção na página.
- **A execução passa** com todos os casos como esperado: "Resultado: N de N casos como esperado".
- **Defeito vira issue** pelo modelo **Defeito**, com o rótulo `fix`, e entra no registro de bugs da
  entrega (`scripts/registrar_bugs.py`). A correção vem num PR com o teste que reprova sem ela.

## 5. Casos funcionais (CT-F)

Cadastro, consulta, atualização e exclusão de cada módulo, e a autenticação.

### Autenticação

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F01 | RF01 | Gestor | Abrir `/entrar`, digitar login e senha válidos e clicar em Entrar | Abre o Painel; o cabeçalho mostra o nome e o perfil de quem entrou |
| CT-F02 | RF02 | Gestor | Com a sessão aberta, clicar em "Encerrar sessão"; depois, abrir `/parceiros` | Volta para `/entrar`; abrir uma tela de dentro pede a entrada de novo |
| CT-F03 | RF07 | Gestor | Em Minha conta, informar a senha atual e a nova duas vezes, e clicar em "Trocar a senha" | A tela confirma a troca; a conta entra com a senha nova |

### Usuários

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F04 | RF03 | Administrador | Em Usuários › Novo, preencher login, nome, senha inicial e perfil Analista, e clicar em "Criar usuário" | A conta é criada e aparece na lista de usuários |
| CT-F05 | RF52 | Administrador | Na lista de usuários, buscar pelo login da conta criada | A lista mostra só ela; o endereço guarda a busca |
| CT-F06 | RF04 | Administrador | Abrir a conta, trocar o perfil de Analista para Gestor e salvar | A alteração é salva e a lista mostra o perfil novo |
| CT-F07 | RF03 | Administrador | Na conta, clicar em Desativar e confirmar; depois, tentar entrar com ela | A conta aparece como Desativada e não entra mais; o histórico continua |
| CT-F08 | RF56 | Administrador | Criar uma conta de perfil Parceiro, buscar o parceiro pelo nome e escolhê-lo | A tela diz de qual parceiro a conta vê o desempenho, e a conta é criada vinculada a ele |
| CT-F09 | RF54 | Administrador | Abrir a conta de outra pessoa, digitar uma senha nova em "Redefinir a senha" e confirmar | A senha é redefinida e a conta entra com ela |

### Parceiros

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F10 | RF14, RF15 | Gestor | Em Parceiros › Novo, digitar o nome, aceitar a categoria sugerida, informar o contato e clicar em "Cadastrar parceiro" | O parceiro é cadastrado e o cadastro dele abre com "Parceiro cadastrado." |
| CT-F11 | RF23 | Gestor | Na lista de parceiros, filtrar pelo segmento Em risco | Só aparecem parceiros Em risco; o endereço guarda o filtro |
| CT-F12 | RF14 | Gestor | No cadastro, mudar o contato e o status comercial e clicar em "Salvar alterações" | A tela diz "Alterações salvas." e a API devolve os valores novos |
| CT-F13 | RF14 | Gestor | No cadastro de um parceiro sem histórico, clicar em "Excluir parceiro" e confirmar | O parceiro é excluído e o cadastro dele deixa de existir |
| CT-F14 | RF25 | Gestor | Na lista filtrada pelo segmento Top, clicar em "Exportar CSV" | Um CSV com o cabeçalho e as linhas do mesmo filtro |
| CT-F15 | RF14 | Gestor | No cadastro, desativar o parceiro e confirmar; depois, reativá-lo | As duas mudanças são gravadas pela tela |

### Importação

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F16 | RF09, RF11 | Gestor | Informar o período, colar um relatório com duas linhas boas e uma sem sentido, e clicar em "Ver a prévia" | A prévia mostra as linhas que serão gravadas e as rejeitadas, cada uma com o motivo |
| CT-F17 | RF09, RF13 | Gestor | Depois da prévia, clicar em Gravar | A importação é gravada e o período aparece em "Importações anteriores" |
| CT-F18 | RF12 | Gestor | Importar de novo o mesmo período e escolher "Substituir mesmo assim" | O período repetido é recusado e explicado; a substituição só acontece com a confirmação |

### Painel

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F19 | RF17, RF18 | Gestor | Abrir o Painel | Os indicadores do período e o ranking de parceiros, com dados |
| CT-F20 | RF17 | Gestor | No Painel, escolher uma categoria no recorte | Indicadores e ranking são pedidos com o recorte, e o endereço o guarda |

### Modelo

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F21 | RF27 | Gestor | Em Modelo, clicar em Treinar e confirmar | O treino é disparado, acompanhado na tela até o fim, e termina |

### Campanha

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F22 | RF29, RF30 | Gestor | Em Campanha, informar orçamento e máximo de ações, clicar em "Calcular plano" e confirmar | O plano é calculado e acompanhado na tela até ficar pronto |
| CT-F23 | RF35 | Gestor | Abrir a comparação de dois planos calculados | A comparação lado a lado abre |
| CT-F24 | RF53 | Gestor | Na execução de um plano, clicar no link do CSV | Um CSV com as ações do plano |
| CT-F25 | RF29 | Gestor | No catálogo de ações, criar uma ação nova; depois, editar o custo e desmarcar "Ativa" | A ação é criada, editada e fica inativa no catálogo |

### Benchmark

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F26 | RF33 | Gestor | Em Benchmark, pedir 500 parceiros e 1 repetição, e clicar em "Rodar benchmark" | O benchmark roda, é acompanhado na tela e termina com os modos medidos |

### Mensagens e aprovação

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F27 | RF36 | Gestor | Abrir Mensagens a partir de um plano e clicar em "Gerar N mensagens" | O público do plano aparece sozinho; as mensagens são geradas, com o link para a fila de aprovação |
| CT-F28 | RF37, RF38, RN06 | Gestor | Na fila de aprovação daquela geração, aprovar uma mensagem | A mensagem é aprovada e sai da fila de pendentes |
| CT-F29 | RF38 | Gestor | Na fila, editar o texto de uma mensagem e salvar | O texto salvo é o editado |
| CT-F30 | RF38, RF40 | Gestor | Na fila, rejeitar uma mensagem com o motivo | A mensagem é rejeitada e o motivo fica gravado |

### Assistente

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F31 | RF41, RF42 | Gestor | Perguntar o faturamento total da rede na última semana | A resposta vem com a fonte (o período de origem) |
| CT-F32 | RF42, RF43, RN08 | Gestor | Perguntar a cotação do dólar amanhã | O assistente se abstém: diz que não tem base para responder, sem inventar número |

### Relatórios

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F33 | RF44, RF45, RF46 | Gestor | Abrir os relatórios de desempenho, de risco e da campanha | Cada um abre a folha do relatório |
| CT-F34 | RF48 | Gestor | Num relatório, imprimir (a mídia de impressão) | Só a folha do relatório aparece; o menu e o cabeçalho saem |
| CT-F35 | RF47 | Administrador | Abrir o relatório de operações | O relatório abre para o Administrador |

### Auditoria

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F36 | RF08, RF49 | Administrador | Na trilha de auditoria, buscar pela marca da execução | Aparecem os registros das ações da execução |

### Configuração

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F37 | RF21, RN01 | Administrador | Em Configuração, aumentar em 1 os períodos de tendência e salvar | O limiar novo é gravado; ao fim, o valor de antes é restaurado |

### Portal do parceiro

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-F38 | RF26 | Parceiro | Entrar como Parceiro | Abre "Meu desempenho", com os indicadores só do próprio parceiro |

## 6. Casos de validação (CT-V)

Dado inválido, campo obrigatório, formato errado e regra de negócio. Em cada um, a mensagem que a pessoa
lê é a que o caso registra como obtida.

### Entrada e senha

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-V01 | RF01 | — | Entrar com o login certo e a senha errada | "Login ou senha inválidos.", a mesma mensagem para login e para senha; só a senha é apagada |
| CT-V02 | RF01 | — | Abrir `/entrar` e olhar o botão com os campos vazios, só com o login, e com os dois | O botão Entrar só liga com os dois campos preenchidos |
| CT-V18 | RF07 | Analista | Em Minha conta, trocar a senha informando a senha atual errada | A recusa aparece embaixo do campo Senha atual |
| CT-V19 | RF07 | Analista | Em Minha conta, digitar a senha nova diferente nas duas vezes | "As duas digitações da senha nova não são iguais.", sem enviar nada à API |

### Usuários

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-V03 | RF03 | Administrador | Em Novo usuário, clicar em "Criar usuário" sem preencher nada | Uma mensagem embaixo de cada campo obrigatório: login, nome, senha e perfil |
| CT-V04 | RF03 | Administrador | Criar um usuário com o login "Fulano Silva" | A mensagem diz o formato do login: minúsculas, números, ponto, hífen e sublinhado |
| CT-V05 | RF03 | Administrador | Criar um usuário com a senha "curta1"; depois, com uma senha que contém o login | Cada recusa diz a regra: o tamanho mínimo; não conter o login |
| CT-V06 | RF03 | Administrador | Criar um usuário com um login que já existe | A recusa diz que o login já é usado e leva à conta que o usa |
| CT-V17 | RF54 | Administrador | Abrir a própria conta na lista de usuários | A redefinição de senha não aparece: a tela aponta para Minha conta, que pede a senha atual |

### Parceiros

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-V07 | RF14 | Gestor | Cadastrar um parceiro sem nome | A mensagem embaixo do campo Nome |
| CT-V08 | RF14 | Gestor | Cadastrar um parceiro com o nome de um que já existe | A recusa diz que o nome já existe e leva ao cadastro dele |
| CT-V09 | RF14 | Gestor | Excluir um parceiro que tem histórico | A exclusão é recusada, com o motivo: o histórico dele sustenta os períodos fechados |
| CT-V21 | RF28, RN09 | Gestor | Abrir o cadastro de um parceiro recém-criado, sem histórico | O bloco de previsão, marcado como estimativa, diz por que não há previsão para ele |

### Importação

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-V10 | RF10, RN03 | Gestor | Pedir a prévia de um relatório sem informar o período | A importação é recusada, com a mensagem no campo do período |
| CT-V11 | RF10 | Gestor | Pedir a prévia com o fim do período antes do início | A recusa diz que o período está invertido |
| CT-V12 | RF12 | Gestor | Gravar um relatório num período que já foi importado, e cancelar | A gravação é recusada, a tela explica e oferece substituir; cancelado, nada muda |
| CT-V13 | RF11 | Gestor | Pedir a prévia de um relatório sem nenhuma linha aproveitável | A prévia diz "Nenhuma linha aproveitável", com o motivo de cada linha, e não oferece gravar |
| CT-V22 | RF09, RNF15 | Gestor | Enviar um arquivo CSV maior que o limite | A recusa diz que o arquivo é grande demais |

### Campanha

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-V14 | RF29 | Gestor | Calcular um plano com orçamento zero | A mensagem embaixo do Orçamento diz o mínimo |
| CT-V15 | RF31, RN07 | Gestor | Calcular um plano com orçamento de R$ 100,00, 8 ações e cota mínima de 100% para a cauda longa | Nenhum plano parcial: a tela diz que as cotas exigem mais que o orçamento, e quanto falta |
| CT-V23 | RF29 | Gestor | Criar uma ação no catálogo com custo zero | A recusa diz que o custo precisa ser maior que zero |

### Configuração e assistente

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-V16 | RF21, RN01 | Administrador | Salvar o tamanho do Top igual a zero | A mensagem embaixo do campo diz o mínimo |
| CT-V20 | RF41 | Gestor | Olhar o botão Perguntar com a pergunta vazia e com só espaços | O botão Perguntar fica desligado |

## 7. Casos de navegação (CT-N)

Menus, links, redirecionamentos, permissões e a continuidade dos fluxos.

### Menus e permissões

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-N01 | RF05 | Administrador | Clicar, um por um, em todos os itens do menu | Cada item abre a sua tela, com título, sem "Sem acesso" nem "Página não encontrada" |
| CT-N02 | RF05 | Gestor | Clicar, um por um, em todos os itens do menu | Cada item abre a sua tela, com título, sem "Sem acesso" nem "Página não encontrada" |
| CT-N03 | RF05 | Analista | Clicar, um por um, em todos os itens do menu | Cada item abre a sua tela, com título, sem "Sem acesso" nem "Página não encontrada" |
| CT-N04 | RF26 | Parceiro | Entrar e abrir `/` | Vai para "Meu desempenho"; o menu tem só esse item |
| CT-N05 | RF05, RNF14 | Analista | Abrir `/modelo` pelo endereço | "O seu perfil não abre esta tela", com o perfil e o endereço, sem chamar a API do modelo |

### Redirecionamentos

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-N06 | RF01 | Gestor | Sem sessão, abrir `/parceiros?segmento=TOP`; depois, entrar | Vai para a entrada e, depois de entrar, volta ao endereço pedido, com o filtro |
| CT-N07 | — | Gestor | Abrir um endereço que não existe e clicar em "Ir para o início" | "Página não encontrada", com o endereço pedido; o link leva ao Painel |
| CT-N13 | RF02 | Gestor | Com a sessão encerrada no servidor, clicar num item do menu; depois, entrar de novo | A tela diz que a sessão terminou; ao entrar, volta para onde a pessoa ia |

### Links entre telas

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-N08 | RF17, RF23 | Gestor | No Painel, clicar num segmento da distribuição | Abre a lista de parceiros filtrada por aquele segmento |
| CT-N09 | RF23 | Gestor | Na lista filtrada, abrir um parceiro e clicar em "Voltar para a lista" | Abre o cadastro dele; a volta mantém o filtro |
| CT-N10 | RF36 | Gestor | Na execução de um plano, clicar em "Gerar mensagens para este plano" | Abre Mensagens com o plano e a prévia do público já carregada |
| CT-N16 | RNF20 | Gestor | No cadastro de um parceiro, ler "Onde você está" e clicar no link de volta | O cabeçalho diz a área (Análise); o link volta à tela de antes |

### Continuidade dos fluxos

| ID | Requisito | Perfil | Passos | Esperado |
|---|---|---|---|---|
| CT-N11 | RNF20 | Gestor | Ir do Painel a Parceiros e a Relatórios pelo menu; voltar duas vezes e avançar uma pelo navegador | Voltar e avançar passam pelas mesmas telas, na ordem |
| CT-N12 | RNF20 | Gestor | Alterar um campo do cadastro e clicar num item do menu; escolher "Continuar editando", e depois "Sair sem salvar" | O aviso de alterações não salvas aparece; continuar mantém o texto; sair navega |
| CT-N14 | RNF20 | Gestor | Apertar Tab ao abrir uma tela, e Enter; trocar de tela pelo menu | O primeiro Tab é "Pular para o conteúdo"; ao trocar de tela, o foco vai ao título |
| CT-N15 | RNF21 | Gestor | A 768 px de largura, abrir o menu pelo botão e escolher Parceiros | O menu começa fechado, abre pelo botão, navega e fecha; a página não rola na horizontal |

## 8. O que não roda pela tela, e onde roda

| O quê | Por que não pela tela | Onde está testado |
|---|---|---|
| O bloqueio depois de cinco tentativas de entrada (RNF11) | O bloqueio é por origem: provocá-lo travaria a entrada de todos na máquina, por 15 minutos | `api/tests/test_autenticacao.py`; o executor faz no máximo duas tentativas recusadas por execução |
| Desativar o último administrador ativo | Exigiria desativar os outros administradores da base da equipe | `api/tests/test_usuarios.py` |
| A matriz inteira de perfil × rota (os quatro perfis contra toda rota) | Uma tela não chama toda rota; o servidor é quem decide | `api/tests/test_autorizacao.py` e `api/e2e/transcricao_permissoes.py` |
| As 64 respostas da API a dado inválido, campo por campo | Muitas não têm tela que as provoque (pedido malformado) | `api/e2e/validacoes.py` |
| As regras RN01 a RN11, com o esperado e o que voltou | Precisam de uma base montada para cada regra | `scripts/revisar_regras.py` |

## 9. Roteiros manuais

Além do executor, cada integrante executa à mão um roteiro da sua área, de 30 a 40 minutos, no sistema
no ar — olhando o que o executor não vê: se o texto se entende, se a ordem dos passos faz sentido, se algo
parece errado. O registro é na issue da campanha manual (#256), com a própria conta.

| Integrante | Área | Perfil | Casos para seguir à mão | E também |
|---|---|---|---|---|
| Ingryd | Telas e navegação | os quatro | CT-N01 a CT-N16 | Os dois temas, claro e escuro; 768 px e uma tela larga; o teclado sem mouse |
| João Pedro | Importação, parceiros e categorias | Gestor e Analista | CT-F10 a CT-F18, CT-V07 a CT-V13, CT-V21, CT-V22 | Um relatório com acento e vírgula nos números; o CSV aberto na planilha |
| Marcio | Painel, campanha e relatórios | Gestor | CT-F19, CT-F20, CT-F22 a CT-F25, CT-F33, CT-F34, CT-V14, CT-V15 | Conferir o que a tela mostra contra a RN01, a RN02, a RN07 e a RN10 (`docs/02`) |
| Thiago | Usuários, permissões, sessão e auditoria | Administrador e Parceiro | CT-F01 a CT-F09, CT-F36, CT-F38, CT-V01 a CT-V06, CT-V17, CT-N04 a CT-N06 | Um perfil tentando abrir pelo endereço uma tela que não é dele |
| Pedro | Modelo, benchmark, mensagens e assistente | Gestor e Analista | CT-F21, CT-F26 a CT-F32, CT-V20 | O Analista na fila de aprovação: vê, mas não decide (RN06) |

## 10. Como rodar e demonstrar

Com o sistema no ar (`docker compose up -d`) e a senha do administrador:

```bash
api/.venv/Scripts/python -m pip install -r scripts/requisitos-medicao.txt
GIH_ADMIN_SENHA=... api/.venv/Scripts/python scripts/testar_na_tela.py --saida <pasta>
```

- `--so CT-N` roda só os casos de navegação; `--so CT-V05,CT-F13`, só estes.
- `--ver` abre a janela e vai devagar: é o modo de **demonstrar na orientação**, caso a caso.
- `--navegador chrome` roda no Chrome, no lugar do Edge.
- A saída tem `casos.txt` (o relatório, que termina em "Resultado: N de N casos como esperado"),
  `casos.json` e uma captura `CT-xxx.png` por caso.

**Roteiro de demonstração, em cerca de cinco minutos:** entrar e sair (CT-F01, CT-F02); uma recusa com a
mensagem na tela (CT-V08); a importação sem período (CT-V10); o Analista barrado no Modelo (CT-N05); a
sessão que termina e volta ao mesmo lugar (CT-N13). Com `--ver --so CT-F01,CT-F02,CT-V08,CT-V10,CT-N05,CT-N13`.
