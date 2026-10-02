# Acessibilidade e responsividade — H76

> Gerado por `scripts/medir_telas.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

Três verificações, em três lugares:

- **o contraste dos tokens**, par a par, nos dois temas — também conferido a cada PR por `web/src/estilos/contraste.test.js`;
- **rótulos, papéis e nomes acessíveis** — conferidos pelo axe-core no fim de cada teste da interface (`web/src/testes/preparar.js`), e aqui de novo, no navegador, com o contraste real do que está desenhado;
- **a largura**: cada tela a 768 e a 1440 px, sem rolagem horizontal da página e sem conteúdo cortado (RNF21). A tabela larga rola na própria caixa, e a página fica no lugar.

## Ambiente

| Item | Valor |
|---|---|
| Data | 02/10/2026 01:40 |
| Navegador | Microsoft Edge 154.0.4258.48, sem cabeça, pelo Playwright |
| axe-core | 4.13.0 |
| Dados | a base de trabalho, com a massa do gerador; dois planos calculados para a medição e apagados depois |
| Máquina | Windows 10, Python 3.11.9 |

## Como reproduzir

```bash
api/.venv/Scripts/python -m pip install -r scripts/requisitos-medicao.txt
api/.venv/Scripts/python scripts/medir_telas.py
```

## O contraste dos tokens (RNF22)

**19 de 19 pares passam nos dois temas.** O texto pede 4,5:1; a borda de um campo e o anel de foco, 3:1 (WCAG 1.4.11).

| Frente | Fundo | Mínimo | Claro | Escuro |
|---|---|--:|--:|--:|
| `--ink` | `--ground` | 4,50:1 | 16,74:1 | 16,72:1 |
| `--ink` | `--surface` | 4,50:1 | 17,79:1 | 16,03:1 |
| `--ink` | `--surface-2` | 4,50:1 | 15,87:1 | 15,10:1 |
| `--ink` | `--acao-fraca` | 4,50:1 | 16,18:1 | 14,25:1 |
| `--ink-2` | `--ground` | 4,50:1 | 5,63:1 | 8,75:1 |
| `--ink-2` | `--surface` | 4,50:1 | 5,98:1 | 8,39:1 |
| `--ink-2` | `--surface-2` | 4,50:1 | 5,34:1 | 7,90:1 |
| `--ink-2` | `--acao-fraca` | 4,50:1 | 5,44:1 | 7,46:1 |
| `--acao-ink` | `--ground` | 4,50:1 | 5,13:1 | 8,80:1 |
| `--acao-ink` | `--surface` | 4,50:1 | 5,45:1 | 8,44:1 |
| `--acao-ink` | `--surface-2` | 4,50:1 | 4,87:1 | 7,95:1 |
| `--acao-ink` | `--acao-fraca` | 4,50:1 | 4,96:1 | 7,50:1 |
| `--acao-sobre` | `--acao` | 4,50:1 | 5,58:1 | 8,27:1 |
| `--borda-controle` | `--ground` | 3,00:1 | 3,36:1 | 3,67:1 |
| `--borda-controle` | `--surface` | 3,00:1 | 3,57:1 | 3,52:1 |
| `--borda-controle` | `--surface-2` | 3,00:1 | 3,19:1 | 3,31:1 |
| `--acao-ink` | `--ground` | 3,00:1 | 5,13:1 | 8,80:1 |
| `--acao-ink` | `--surface` | 3,00:1 | 5,45:1 | 8,44:1 |
| `--acao-ink` | `--surface-2` | 3,00:1 | 4,87:1 | 7,95:1 |

## As telas

**27 telas. Com a página rolando na horizontal ou conteúdo cortado: 0 das 54 medidas. Com violação do axe no navegador: 0 das 54 auditorias** (cada tela, nos dois temas).

| Tela | Rota | Perfil | 768 px | 1440 px | axe, claro | axe, escuro |
|---|---|---|---|---|--:|--:|
| Entrar | `/entrar` | sem sessão | ok | ok | 0 | 0 |
| Painel | `/` | gestor | ok | ok | 0 | 0 |
| Importação | `/importacao` | gestor | ok | ok | 0 | 0 |
| Parceiros | `/parceiros` | gestor | ok | ok | 0 | 0 |
| Novo parceiro | `/parceiros/novo` | gestor | ok | ok | 0 | 0 |
| Cadastro do parceiro | `/parceiros/246` | gestor | ok | ok | 0 | 0 |
| Assistente | `/assistente` | gestor | ok | ok | 0 | 0 |
| Campanha | `/campanha` | gestor | ok | ok | 0 | 0 |
| Execuções | `/execucoes` | gestor | ok | ok | 0 | 0 |
| Execução | `/execucoes/170` | gestor | ok | ok | 0 | 0 |
| Comparação | `/execucoes/comparar?a=170&b=171` | gestor | ok | ok | 0 | 0 |
| Mensagens | `/mensagens` | gestor | ok | ok | 0 | 0 |
| Aprovação | `/aprovacao` | gestor | ok | ok | 0 | 0 |
| Benchmark | `/benchmark` | gestor | ok | ok | 0 | 0 |
| Modelo | `/modelo` | gestor | ok | ok | 0 | 0 |
| Relatórios | `/relatorios` | gestor | ok | ok | 0 | 0 |
| Relatório de desempenho | `/relatorios/desempenho` | gestor | ok | ok | 0 | 0 |
| Relatório de risco | `/relatorios/risco` | gestor | ok | ok | 0 | 0 |
| Relatório da campanha | `/relatorios/campanha` | gestor | ok | ok | 0 | 0 |
| Usuários | `/usuarios` | administrador | ok | ok | 0 | 0 |
| Novo usuário | `/usuarios/novo` | administrador | ok | ok | 0 | 0 |
| Conta do usuário | `/usuarios/266` | administrador | ok | ok | 0 | 0 |
| Auditoria | `/auditoria` | administrador | ok | ok | 0 | 0 |
| Relatório de operações | `/relatorios/operacoes` | administrador | ok | ok | 0 | 0 |
| Limiares | `/configuracao` | administrador | ok | ok | 0 | 0 |
| Meu desempenho | `/meu-desempenho` | parceiro | ok | ok | 0 | 0 |
| Minha conta | `/conta` | parceiro | ok | ok | 0 | 0 |

**O que rola na própria caixa** — e a página fica no lugar: a tabela larga e, a 768 px, o menu, que vira uma faixa no topo.

| Tela | Largura | Caixas |
|---|--:|---|
| Painel | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Importação | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Parceiros | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Novo parceiro | 768 px | `nav.trilho` |
| Cadastro do parceiro | 768 px | `nav.trilho` |
| Assistente | 768 px | `nav.trilho` |
| Campanha | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Execuções | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Execução | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Comparação | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Mensagens | 768 px | `nav.trilho` |
| Aprovação | 768 px | `nav.trilho` |
| Benchmark | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Modelo | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Relatórios | 768 px | `nav.trilho` |
| Relatório de desempenho | 768 px | `nav.trilho` |
| Relatório de risco | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Relatório da campanha | 768 px | `nav.trilho` |
| Usuários | 768 px | `nav.trilho` |
| Novo usuário | 768 px | `nav.trilho` |
| Conta do usuário | 768 px | `nav.trilho` |
| Auditoria | 768 px | `nav.trilho`, `div.tabela-rolagem` |
| Relatório de operações | 768 px | `nav.trilho` |
| Limiares | 768 px | `nav.trilho` |

## As capturas

Tema claro. À esquerda, 768 px; à direita, 1440 px.

### Entrar

<img src="telas/entrar-768.jpg" width="280" alt="Entrar a 768 px"> <img src="telas/entrar-1440.jpg" width="480" alt="Entrar a 1440 px">

### Painel

<img src="telas/painel-768.jpg" width="280" alt="Painel a 768 px"> <img src="telas/painel-1440.jpg" width="480" alt="Painel a 1440 px">

### Importação

<img src="telas/importacao-768.jpg" width="280" alt="Importação a 768 px"> <img src="telas/importacao-1440.jpg" width="480" alt="Importação a 1440 px">

### Parceiros

<img src="telas/parceiros-768.jpg" width="280" alt="Parceiros a 768 px"> <img src="telas/parceiros-1440.jpg" width="480" alt="Parceiros a 1440 px">

### Novo parceiro

<img src="telas/parceiro-novo-768.jpg" width="280" alt="Novo parceiro a 768 px"> <img src="telas/parceiro-novo-1440.jpg" width="480" alt="Novo parceiro a 1440 px">

### Cadastro do parceiro

<img src="telas/parceiro-768.jpg" width="280" alt="Cadastro do parceiro a 768 px"> <img src="telas/parceiro-1440.jpg" width="480" alt="Cadastro do parceiro a 1440 px">

### Assistente

<img src="telas/assistente-768.jpg" width="280" alt="Assistente a 768 px"> <img src="telas/assistente-1440.jpg" width="480" alt="Assistente a 1440 px">

### Campanha

<img src="telas/campanha-768.jpg" width="280" alt="Campanha a 768 px"> <img src="telas/campanha-1440.jpg" width="480" alt="Campanha a 1440 px">

### Execuções

<img src="telas/execucoes-768.jpg" width="280" alt="Execuções a 768 px"> <img src="telas/execucoes-1440.jpg" width="480" alt="Execuções a 1440 px">

### Execução

<img src="telas/execucao-768.jpg" width="280" alt="Execução a 768 px"> <img src="telas/execucao-1440.jpg" width="480" alt="Execução a 1440 px">

### Comparação

<img src="telas/comparacao-768.jpg" width="280" alt="Comparação a 768 px"> <img src="telas/comparacao-1440.jpg" width="480" alt="Comparação a 1440 px">

### Mensagens

<img src="telas/mensagens-768.jpg" width="280" alt="Mensagens a 768 px"> <img src="telas/mensagens-1440.jpg" width="480" alt="Mensagens a 1440 px">

### Aprovação

<img src="telas/aprovacao-768.jpg" width="280" alt="Aprovação a 768 px"> <img src="telas/aprovacao-1440.jpg" width="480" alt="Aprovação a 1440 px">

### Benchmark

<img src="telas/benchmark-768.jpg" width="280" alt="Benchmark a 768 px"> <img src="telas/benchmark-1440.jpg" width="480" alt="Benchmark a 1440 px">

### Modelo

<img src="telas/modelo-768.jpg" width="280" alt="Modelo a 768 px"> <img src="telas/modelo-1440.jpg" width="480" alt="Modelo a 1440 px">

### Relatórios

<img src="telas/relatorios-768.jpg" width="280" alt="Relatórios a 768 px"> <img src="telas/relatorios-1440.jpg" width="480" alt="Relatórios a 1440 px">

### Relatório de desempenho

<img src="telas/relatorio-desempenho-768.jpg" width="280" alt="Relatório de desempenho a 768 px"> <img src="telas/relatorio-desempenho-1440.jpg" width="480" alt="Relatório de desempenho a 1440 px">

### Relatório de risco

<img src="telas/relatorio-risco-768.jpg" width="280" alt="Relatório de risco a 768 px"> <img src="telas/relatorio-risco-1440.jpg" width="480" alt="Relatório de risco a 1440 px">

### Relatório da campanha

<img src="telas/relatorio-campanha-768.jpg" width="280" alt="Relatório da campanha a 768 px"> <img src="telas/relatorio-campanha-1440.jpg" width="480" alt="Relatório da campanha a 1440 px">

### Usuários

<img src="telas/usuarios-768.jpg" width="280" alt="Usuários a 768 px"> <img src="telas/usuarios-1440.jpg" width="480" alt="Usuários a 1440 px">

### Novo usuário

<img src="telas/usuario-novo-768.jpg" width="280" alt="Novo usuário a 768 px"> <img src="telas/usuario-novo-1440.jpg" width="480" alt="Novo usuário a 1440 px">

### Conta do usuário

<img src="telas/usuario-768.jpg" width="280" alt="Conta do usuário a 768 px"> <img src="telas/usuario-1440.jpg" width="480" alt="Conta do usuário a 1440 px">

### Auditoria

<img src="telas/auditoria-768.jpg" width="280" alt="Auditoria a 768 px"> <img src="telas/auditoria-1440.jpg" width="480" alt="Auditoria a 1440 px">

### Relatório de operações

<img src="telas/relatorio-operacoes-768.jpg" width="280" alt="Relatório de operações a 768 px"> <img src="telas/relatorio-operacoes-1440.jpg" width="480" alt="Relatório de operações a 1440 px">

### Limiares

<img src="telas/configuracao-768.jpg" width="280" alt="Limiares a 768 px"> <img src="telas/configuracao-1440.jpg" width="480" alt="Limiares a 1440 px">

### Meu desempenho

<img src="telas/meu-desempenho-768.jpg" width="280" alt="Meu desempenho a 768 px"> <img src="telas/meu-desempenho-1440.jpg" width="480" alt="Meu desempenho a 1440 px">

### Minha conta

<img src="telas/minha-conta-768.jpg" width="280" alt="Minha conta a 768 px"> <img src="telas/minha-conta-1440.jpg" width="480" alt="Minha conta a 1440 px">
