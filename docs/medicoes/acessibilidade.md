# Acessibilidade e responsividade — H76

> Gerado por `scripts/medir_telas.py`. **Não edite à mão**: número escrito à mão não é evidência. Para atualizar, rode o comando abaixo de novo.

Três verificações, em três lugares:

- **o contraste dos tokens**, par a par, nos dois temas — também conferido a cada PR por `web/src/estilos/contraste.test.js`;
- **rótulos, papéis e nomes acessíveis** — conferidos pelo axe-core no fim de cada teste da interface (`web/src/testes/preparar.js`), e aqui de novo, no navegador, com o contraste real do que está desenhado;
- **a largura**: cada tela a 768 e a 1440 px, sem rolagem horizontal da página e sem conteúdo cortado (RNF21). A tabela larga rola na própria caixa, e a página fica no lugar.

## Ambiente

| Item | Valor |
|---|---|
| Data | 22/10/2026 14:54 |
| Navegador | Microsoft Edge 155.0.4283.62, sem cabeça, pelo Playwright |
| axe-core | 4.14.0 |
| Dados | a base de trabalho, com a massa do gerador; dois planos calculados para a medição e apagados depois |
| Máquina | Windows 10, Python 3.11.9 |

## Como reproduzir

```bash
api/.venv/Scripts/python -m pip install -r scripts/requisitos-medicao.txt
api/.venv/Scripts/python scripts/medir_telas.py
```

## O contraste dos tokens (RNF22)

**77 de 77 pares passam nos dois temas.** O texto pede 4,5:1; a borda de um campo e o anel de foco, 3:1 (WCAG 1.4.11).

| Frente | Fundo | Mínimo | Claro | Escuro |
|---|---|--:|--:|--:|
| `--carbono` | `--chao` | 4,50:1 | 16,13:1 | 17,47:1 |
| `--carbono` | `--etiqueta` | 4,50:1 | 18,42:1 | 15,72:1 |
| `--carbono` | `--etiqueta-2` | 4,50:1 | 17,18:1 | 14,43:1 |
| `--carbono` | `--acao-fundo` | 4,50:1 | 15,68:1 | 13,34:1 |
| `--carbono` | `--neutro-fundo` | 4,50:1 | 16,26:1 | 14,26:1 |
| `--carbono` | `--erro-fundo` | 4,50:1 | 16,15:1 | 14,50:1 |
| `--carbono` | `--atencao-fundo` | 4,50:1 | 16,81:1 | 13,62:1 |
| `--carbono` | `--sucesso-fundo` | 4,50:1 | 16,52:1 | 13,68:1 |
| `--carbono-2` | `--chao` | 4,50:1 | 6,58:1 | 8,65:1 |
| `--carbono-2` | `--etiqueta` | 4,50:1 | 7,51:1 | 7,79:1 |
| `--carbono-2` | `--etiqueta-2` | 4,50:1 | 7,00:1 | 7,15:1 |
| `--carbono-2` | `--acao-fundo` | 4,50:1 | 6,39:1 | 6,61:1 |
| `--carbono-2` | `--neutro-fundo` | 4,50:1 | 6,63:1 | 7,06:1 |
| `--carbono-2` | `--erro-fundo` | 4,50:1 | 6,59:1 | 7,18:1 |
| `--carbono-2` | `--atencao-fundo` | 4,50:1 | 6,86:1 | 6,75:1 |
| `--carbono-2` | `--sucesso-fundo` | 4,50:1 | 6,74:1 | 6,78:1 |
| `--carbono-3` | `--etiqueta` | 4,50:1 | 4,93:1 | 5,69:1 |
| `--carbono-3` | `--etiqueta-2` | 4,50:1 | 4,60:1 | 5,22:1 |
| `--acao` | `--chao` | 4,50:1 | 6,47:1 | 8,43:1 |
| `--acao` | `--etiqueta` | 4,50:1 | 7,40:1 | 7,59:1 |
| `--acao` | `--etiqueta-2` | 4,50:1 | 6,89:1 | 6,96:1 |
| `--acao` | `--acao-fundo` | 4,50:1 | 6,29:1 | 6,44:1 |
| `--erro` | `--chao` | 4,50:1 | 5,26:1 | 7,80:1 |
| `--erro` | `--etiqueta` | 4,50:1 | 6,01:1 | 7,02:1 |
| `--erro` | `--etiqueta-2` | 4,50:1 | 5,60:1 | 6,44:1 |
| `--erro` | `--erro-fundo` | 4,50:1 | 5,27:1 | 6,48:1 |
| `--atencao` | `--chao` | 4,50:1 | 5,54:1 | 12,02:1 |
| `--atencao` | `--etiqueta` | 4,50:1 | 6,33:1 | 10,82:1 |
| `--atencao` | `--etiqueta-2` | 4,50:1 | 5,90:1 | 9,93:1 |
| `--atencao` | `--atencao-fundo` | 4,50:1 | 5,78:1 | 9,37:1 |
| `--sucesso` | `--chao` | 4,50:1 | 4,70:1 | 10,80:1 |
| `--sucesso` | `--etiqueta` | 4,50:1 | 5,37:1 | 9,72:1 |
| `--sucesso` | `--etiqueta-2` | 4,50:1 | 5,01:1 | 8,92:1 |
| `--sucesso` | `--sucesso-fundo` | 4,50:1 | 4,81:1 | 8,45:1 |
| `--variacao-boa` | `--chao` | 4,50:1 | 4,70:1 | 10,80:1 |
| `--variacao-boa` | `--etiqueta` | 4,50:1 | 5,37:1 | 9,72:1 |
| `--variacao-boa` | `--etiqueta-2` | 4,50:1 | 5,01:1 | 8,92:1 |
| `--variacao-ruim` | `--chao` | 4,50:1 | 5,64:1 | 8,51:1 |
| `--variacao-ruim` | `--etiqueta` | 4,50:1 | 6,44:1 | 7,66:1 |
| `--variacao-ruim` | `--etiqueta-2` | 4,50:1 | 6,01:1 | 7,03:1 |
| `--acao-tinta` | `--acao` | 4,50:1 | 7,40:1 | 8,43:1 |
| `--acao-tinta` | `--acao-forte` | 4,50:1 | 10,18:1 | 11,34:1 |
| `--erro-tinta` | `--erro` | 4,50:1 | 6,01:1 | 7,84:1 |
| `--lacre-tinta` | `--lacre` | 4,50:1 | 12,74:1 | 12,74:1 |
| `--etiqueta` | `--carbono` | 4,50:1 | 18,42:1 | 15,72:1 |
| `--nailon-tinta` | `--nailon` | 4,50:1 | 15,62:1 | 16,60:1 |
| `--nailon-tinta` | `--nailon-2` | 4,50:1 | 13,75:1 | 15,13:1 |
| `--nailon-tinta-2` | `--nailon` | 4,50:1 | 8,10:1 | 8,60:1 |
| `--nailon-tinta-2` | `--nailon-2` | 4,50:1 | 7,13:1 | 7,84:1 |
| `--nailon-tinta-forte` | `--nailon` | 4,50:1 | 19,18:1 | 20,37:1 |
| `--nailon-tinta-forte` | `--nailon-2` | 4,50:1 | 16,88:1 | 18,58:1 |
| `--rota-tinta` | `--rota-analise` | 4,50:1 | 9,13:1 | 9,13:1 |
| `--rota-tinta` | `--rota-previsao` | 4,50:1 | 8,43:1 | 8,43:1 |
| `--rota-tinta` | `--rota-otimizacao` | 4,50:1 | 8,71:1 | 8,71:1 |
| `--rota-tinta` | `--rota-comunicacao` | 4,50:1 | 9,37:1 | 9,37:1 |
| `--rota-tinta` | `--rota-administracao` | 4,50:1 | 9,00:1 | 9,00:1 |
| `--seg-prospeccao-tinta` | `--seg-prospeccao-fundo` | 4,50:1 | 6,93:1 | 9,51:1 |
| `--seg-recem-chegado-tinta` | `--seg-recem-chegado-fundo` | 4,50:1 | 7,80:1 | 9,17:1 |
| `--seg-em-risco-tinta` | `--seg-em-risco-fundo` | 4,50:1 | 7,68:1 | 9,08:1 |
| `--seg-top-tinta` | `--seg-top-fundo` | 4,50:1 | 7,80:1 | 9,29:1 |
| `--seg-em-ascensao-tinta` | `--seg-em-ascensao-fundo` | 4,50:1 | 6,74:1 | 9,60:1 |
| `--seg-estavel-tinta` | `--seg-estavel-fundo` | 4,50:1 | 7,38:1 | 9,63:1 |
| `--rota-analise` | `--nailon` | 4,50:1 | 9,13:1 | 9,70:1 |
| `--rota-analise` | `--nailon-2` | 4,50:1 | 8,03:1 | 8,84:1 |
| `--rota-previsao` | `--nailon` | 4,50:1 | 8,43:1 | 8,96:1 |
| `--rota-previsao` | `--nailon-2` | 4,50:1 | 7,42:1 | 8,17:1 |
| `--rota-otimizacao` | `--nailon` | 4,50:1 | 8,71:1 | 9,25:1 |
| `--rota-otimizacao` | `--nailon-2` | 4,50:1 | 7,67:1 | 8,44:1 |
| `--rota-comunicacao` | `--nailon` | 4,50:1 | 9,37:1 | 9,95:1 |
| `--rota-comunicacao` | `--nailon-2` | 4,50:1 | 8,25:1 | 9,08:1 |
| `--rota-administracao` | `--nailon` | 4,50:1 | 9,00:1 | 9,56:1 |
| `--rota-administracao` | `--nailon-2` | 4,50:1 | 7,92:1 | 8,72:1 |
| `--fio-forte` | `--etiqueta` | 3,00:1 | 3,22:1 | 4,54:1 |
| `--fio-forte` | `--etiqueta-2` | 3,00:1 | 3,00:1 | 4,16:1 |
| `--foco` | `--chao` | 3,00:1 | 6,47:1 | 8,43:1 |
| `--foco` | `--etiqueta` | 3,00:1 | 7,40:1 | 7,59:1 |
| `--foco` | `--etiqueta-2` | 3,00:1 | 6,89:1 | 6,96:1 |

## As telas

**30 telas. Com a página rolando na horizontal ou conteúdo cortado: 0 das 60 medidas. Com violação do axe no navegador: 0 das 60 auditorias** (cada tela, nos dois temas).

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
| Execução | `/execucoes/44` | gestor | ok | ok | 0 | 0 |
| Comparação | `/execucoes/comparar?a=44&b=45` | gestor | ok | ok | 0 | 0 |
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
| Conta do usuário | `/usuarios/38` | administrador | ok | ok | 0 | 0 |
| Auditoria | `/auditoria` | administrador | ok | ok | 0 | 0 |
| Relatório de operações | `/relatorios/operacoes` | administrador | ok | ok | 0 | 0 |
| Limiares | `/configuracao` | administrador | ok | ok | 0 | 0 |
| Meu desempenho | `/meu-desempenho` | parceiro | ok | ok | 0 | 0 |
| Minha conta | `/conta` | parceiro | ok | ok | 0 | 0 |
| Sem acesso | `/parceiros` | parceiro | ok | ok | 0 | 0 |
| Ajuda | `/ajuda` | gestor | ok | ok | 0 | 0 |
| Ajuda do parceiro | `/ajuda` | parceiro | ok | ok | 0 | 0 |

**O que rola na própria caixa** — e a página fica no lugar: a tabela larga. A 768 px, o menu vira gaveta e sai da tela.

| Tela | Largura | Caixas |
|---|--:|---|
| Painel | 768 px | `div.caixa-tabela` |
| Parceiros | 768 px | `div.caixa-tabela` |
| Campanha | 768 px | `div.caixa-tabela` |
| Execução | 768 px | `div.caixa-tabela` |
| Relatório de risco | 768 px | `div.caixa-tabela` |
| Auditoria | 768 px | `div.caixa-tabela` |

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

### Sem acesso

<img src="telas/sem-acesso-768.jpg" width="280" alt="Sem acesso a 768 px"> <img src="telas/sem-acesso-1440.jpg" width="480" alt="Sem acesso a 1440 px">

### Ajuda

<img src="telas/ajuda-768.jpg" width="280" alt="Ajuda a 768 px"> <img src="telas/ajuda-1440.jpg" width="480" alt="Ajuda a 1440 px">

### Ajuda do parceiro

<img src="telas/ajuda-parceiro-768.jpg" width="280" alt="Ajuda do parceiro a 768 px"> <img src="telas/ajuda-parceiro-1440.jpg" width="480" alt="Ajuda do parceiro a 1440 px">
