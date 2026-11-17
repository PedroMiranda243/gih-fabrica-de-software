# 14 — Guia de operação

**Projeto:** Growth Intelligence Hub (GIH)
**Versão:** 1.0 — 16/11/2026 · H109, Sprint 10
**Responsáveis:** João Pedro (scripts e testes), Pedro (API e núcleo), Marcio (documentação)

---

O [README](../README.md) diz o que é preciso para **subir e avaliar** o sistema. Este guia tem o resto: o
que a equipe usa para desenvolver, testar, medir, administrar e montar as entregas. Os comandos são dados a
partir da raiz do repositório, salvo quando dizem outra coisa, e no formato do Git Bash; as diferenças do
PowerShell vêm ao lado.

**A senha do administrador** aparece em vários comandos como `GIH_ADMIN_SENHA=...`. No PowerShell, ela vai
numa variável antes: `$env:GIH_ADMIN_SENHA = "..."`, e depois o comando sem o prefixo. Ela nunca vai para
arquivo versionado.

## Desenvolver a API fora do contêiner

Para ter recarga automática ao salvar, o banco fica no contêiner e a API roda na máquina:

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

A API fora do contêiner lê o `DATABASE_URL` do `api/.env` — o mesmo formato do `.env` da raiz, apontando
para `localhost` e para a porta publicada do banco (**5433** por padrão, `POSTGRES_PORT`). A 5432 costuma
estar ocupada por outro PostgreSQL na máquina, e as migrações rodariam no banco errado.

**Os testes e a análise estática**, de dentro de `api/`:

```bash
pytest
ruff check .
```

Os testes precisam do PostgreSQL no ar: eles criam um banco `gih_teste` separado, aplicam as migrações nele
e limpam as tabelas entre cada teste. SQLite em memória seria mais rápido e não exercitaria `JSONB`, os tipos
`ENUM` nem as restrições `CHECK` do esquema. O projeto não usa `ruff format`: o formato segue o do arquivo
vizinho.

Os testes que falam com o modelo de linguagem de verdade rodam quando o `OLLAMA_BASE_URL` do `api/.env`
aponta para um Ollama com o modelo (fora do Docker, `http://localhost:11434`); sem ele, pulam. Com
`GIH_ASSISTENTE_OBRIGATORIO=1`, reprovam em vez de pular.

**A interface**, de dentro de `web/`, com o Node 22: `npm ci`, `npm run lint` e `npm test`. O
`docker compose up` já a serve em `http://localhost:5173`, com recarga ao salvar.

**Mudou uma rota da API?** Ela precisa entrar na matriz de rastreabilidade (`docs/11`) e na documentação
da API (`api/app/documentacao_api.py`) — os testes reprovam a rota que falta em uma das duas. Depois:

```bash
api/.venv/Scripts/python scripts/exportar_api.py
```

Ele grava de novo o `docs/api/openapi.json` e o `docs/13-api.md`, a partir da mesma especificação do Swagger.
O teste da documentação reprova os dois quando ficam velhos.

## Verificação de ponta a ponta

A suíte do `pytest` sobe a aplicação em processo. A verificação abaixo roda contra **a API no ar** — HTTP
real, cookie real, banco real — e reporta cada checagem agrupada pelos itens de entrega da disciplina. É
também o roteiro da demonstração.

```bash
docker compose up -d
cd api
GIH_ADMIN_SENHA=... python e2e/verificacao.py
```

**Ela roda do Python da máquina, com as dependências da API**: o `.venv` da seção anterior. Sem ele, para no
primeiro `import`. O comando **sai com código diferente de zero** se qualquer verificação falhar — senão não é
verificação, é impressão.

Na mesma pasta estão os outros roteiros contra o sistema no ar: `validacoes.py` (a API recusa dado inválido
com mensagem clara), `transcricao_permissoes.py` (cada perfil, o que pode e o que não pode),
`persistencia.py` (os dados sobrevivem a reiniciar os contêineres) e as transcrições de cada módulo.

**A verificação não deixa resíduo no banco da equipe.** Ela importa relatórios em semanas no futuro, e antes
elas se acumulavam até o painel abrir numa semana de 2055. Agora, no fim de cada execução — mesmo
interrompida —, os períodos, importações, métricas, parceiros e categorias que ela gravou saem do banco, e a
última checagem confere que o painel voltou a abrir onde abria. Os usuários de teste ficam **desativados**,
não apagados, porque a trilha de auditoria aponta para eles. As transcrições fazem o mesmo.

A limpeza vai **direto no banco**, pelo `DATABASE_URL` do `.env`, porque a API recusa de propósito apagar
histórico — o porquê completo está em [`api/e2e/limpeza.py`](../api/e2e/limpeza.py). Se o `DATABASE_URL`
apontar para outro banco que não o da API, a limpeza recusa e a verificação reprova, em vez de dar por limpo
o banco errado.

A persistência desliga e religa os contêineres, e as validações param o banco por alguns segundos: rode com
a aplicação livre.

## Testes pela tela

Os casos de teste do [`docs/12`](12-plano-de-testes.md) — funcionais, de validação e de navegação —
executados num navegador de verdade (o Edge ou o Chrome da máquina), contra o sistema no ar. Cada caso
registra o resultado obtido ao lado do esperado, com uma captura:

```bash
api/.venv/Scripts/python -m pip install -r scripts/requisitos-medicao.txt
GIH_ADMIN_SENHA=... api/.venv/Scripts/python scripts/testar_na_tela.py --saida <pasta>
```

`--so CT-N` roda só os de navegação; `--navegador chrome`, no Chrome; `--ver` abre a janela e vai devagar,
para demonstrar. Como a verificação, ele não deixa resíduo: as contas e os dados de teste levam a marca da
execução e saem no fim. Os dois casos do assistente pedem o perfil `assistente`; sem ele, saem como "não
executados".

## Medição de desempenho

```bash
api/.venv/Scripts/python scripts/medir_painel.py        # o painel com 5.000 parceiros (H40)
api/.venv/Scripts/python scripts/medir_modelo.py        # o modelo contra as referências (H46)
api/.venv/Scripts/python scripts/medir_otimizador.py    # o otimizador contra o guloso e o teto (H49)
api/.venv/Scripts/python scripts/medir_assistente.py    # o assistente contra o modelo de verdade (H65 a H68)
api/.venv/Scripts/python scripts/revisar_regras.py      # as regras RN01 a RN11, com o esperado e o que voltou (H99)
GIH_ADMIN_SENHA=... api/.venv/Scripts/python scripts/medir_telas.py   # as 30 telas: rolagem, axe e contraste (H76)
```

As duas últimas gravam [`docs/medicoes/regras.md`](medicoes/regras.md) e
[`docs/medicoes/acessibilidade.md`](medicoes/acessibilidade.md); a das telas usa o Edge da máquina e as
dependências de `scripts/requisitos-medicao.txt`, e roda contra o sistema no ar.

O núcleo em C++ é medido no contêiner, que é onde ele roda (ADR-012) — o OpenMP e a GPU contra o C++ serial,
o RNF01 e o RNF02 no cenário de referência, a transferência para a GPU e o kernel de avaliação:

```bash
docker build -t gih-nucleo nucleo
docker run --rm --gpus all -v "$PWD:/repo" -w /repo gih-nucleo python scripts/medir_nucleo.py
```

O primeiro mede o tempo de resposta do painel (RNF03) e confere por `EXPLAIN` que as consultas têm índice que
as atenda; o terceiro fixa o tempo do baseline serial, que é o denominador do *speedup* (RNF02); o quarto
pede o modelo de linguagem no ar (o perfil `assistente`). Os quatro primeiros criam o banco `gih_medicao` na
mesma instância e geram a massa lá — **o banco de trabalho não é tocado**, então dá para medir com a
aplicação aberta em outra janela.

O resultado é gravado em [`docs/medicoes/`](medicoes/), com o comando e a semente que o produzem.

## Dados de demonstração e o banco

O repositório **não contém dados reais**. Toda a massa de demonstração é gerada por script.

Para avaliar, o caminho é o `popular-demonstracao`, de dentro do contêiner, como no README. Os scripts abaixo
são os da equipe, e rodam do Python da máquina, com o `.venv` da API:

```bash
python scripts/gerar_dados_sinteticos.py --parceiros 2000 --periodos 12
python scripts/resetar_banco.py --parceiros 500
```

O gerador produz redes de 100 a 10.000 parceiros, com **cauda longa** (numa rede de algumas centenas, os 15
maiores parceiros concentram cerca de um terço do faturamento), perfis de trajetória distintos — em ascensão,
em queda, estável, volátil e recém-chegado —, sazonalidade e ruído. A semente é parametrizável, então a mesma
execução sempre produz a mesma rede.

Isso não é enfeite: sem cauda longa não existiria o problema que o produto resolve, e sem perfis de
trajetória não haveria o que segmentar nem o que o modelo preditivo aprender. O mesmo gerador alimenta o
benchmark do otimizador, que precisa de escala para evidenciar o ganho de paralelismo.

O `resetar_banco.py` reverte as migrações, reaplica, repovoa, segmenta e treina o modelo — é o ciclo que se
usa dezenas de vezes por dia durante o desenvolvimento.

**Os usuários vão junto.** No fim, o reset recria o administrador — com a senha de `ADMIN_SENHA`, ou sorteada
e impressa na saída do próprio reset, e não no log — e reinicia a API, cujas conexões abertas guardavam
consultas preparadas das tabelas antigas e respondiam erro interno (#115). Logins pessoais se recriam com
`criar-usuario`, como no README, ou pela tela **Usuários**.

**A estrutura do banco no ar**, tabela por tabela — colunas, tipos, chaves, restrições, índices e quantas
linhas cada uma tem —, lida do catálogo do PostgreSQL, e não escrita à mão:

```bash
api/.venv/Scripts/python scripts/descrever_banco.py --saida <arquivo>
```

Ele só lê, e usa o mesmo `DATABASE_URL` da verificação. O `docs/08` descreve o mesmo banco à mão, e o
`api/tests/test_modelo_de_dados.py` confere, a cada Pull Request, que o documento, as migrações e o banco
dizem a mesma coisa.

## Administração pelo terminal

As telas **Usuários** e **Configuração** cobrem a administração pelo navegador. Os comandos abaixo fazem o
mesmo pelo terminal, para quem administra sem abrir a aplicação. Criar usuário e redefinir senha estão no
README, em *Primeiro acesso*.

Os limiares da segmentação (RF21) — tamanho do Top N, períodos de queda para caracterizar risco e períodos de
histórico para o parceiro ainda ser recém-chegado:

```bash
docker compose exec api python -m app.cli configurar-segmentacao
docker compose exec api python -m app.cli configurar-segmentacao --top-n 20 --reprocessar
```

Sem argumento, mostra o que está em vigor. Alterar reclassifica **só o período mais recente**; os anteriores
mantêm a classificação antiga até `--reprocessar` ou:

```bash
docker compose exec api python -m app.cli reprocessar-segmentos
```

Esse último é também o que classifica uma base carregada antes da segmentação existir — sem ele, o painel
mostra a distribuição vazia sem dizer por quê.

O modelo preditivo (UC07) treina pela tela **Modelo** ou pelo terminal:

```bash
docker compose exec api python -m app.cli treinar-modelo
```

Pelo terminal ele roda até o fim e imprime as métricas contra as referências e a versão que ficou em uso. As
regras são as da tela: com menos de 8 períodos na base o treino é recusado (RN09), e a versão treinada só
entra em uso se superar as referências (UC07-A1). O `resetar_banco.py` e o `popular-demonstracao` já treinam
depois de segmentar, e a base de demonstração nasce com previsão.

A campanha (UC08) se calcula pela tela **Campanha**, só pelo Gestor; o Analista consulta. O plano parte das
previsões da versão em uso: sem modelo treinado, a tela diz isso e não calcula. A busca roda em segundo plano,
uma por vez, e a campanha inviável é registrada sem plano, dizendo a restrição e quanto falta (RN07).

## Acesso de fora de casa, por rede privada

**O sistema não fica na internet, e isso é de propósito.** Todas as portas ficam presas à própria máquina
(RNF30). Para usá-lo de outro aparelho — o celular, o notebook, fora de casa —, o caminho é uma **rede
privada** (Tailscale): só os aparelhos da sua conta, ou os que você convidar, chegam ao sistema, por conexão
cifrada e HTTPS; e depois ainda vem o login do GIH. Um link público por túnel foi avaliado e recusado — o
porquê está na ADR-014 do [`docs/07`](07-arquitetura-preliminar.md).

É um perfil opcional, como o do modelo de linguagem. Sem ele, nada disto sobe.

**Uma vez só, na sua conta:**

1. Crie uma conta gratuita em `tailscale.com`, com **verificação em duas etapas** no login que você usar.
2. No painel dela, em **DNS**, ligue **MagicDNS** e **HTTPS Certificates**.

**Na máquina que roda o sistema:**

```bash
docker compose --profile remoto up -d --build
docker compose --profile remoto logs tailscale
```

O primeiro comando sobe dois serviços: a `borda`, que entrega a interface empacotada e repassa o `/api`, e o
`tailscale`, o nó da rede privada. O segundo mostra, na primeira subida, a linha `To authenticate, visit:` com
um endereço: abra-o, entre na sua conta e aprove a máquina **`gih`**. A identidade fica guardada num volume, e
as subidas seguintes entram sozinhas. Com a GPU ou o modelo de linguagem, junte o arquivo e o perfil deles ao
comando, como no README.

**No aparelho de onde você vai acessar:** instale o aplicativo do Tailscale, entre com a mesma conta e abra
`https://gih.<nome-da-sua-rede>.ts.net`. O endereço exato aparece no painel, em *Machines*, e na saída da
conferência abaixo. A primeira abertura leva alguns segundos, enquanto o certificado é emitido.

**Confira antes de confiar**, depois de mexer no Compose e antes de cada demonstração feita de fora:

```bash
python scripts/conferir_acesso_remoto.py
```

O roteiro reprova se alguma porta sair do `127.0.0.1`, se a borda entregar o servidor de desenvolvimento ou a
documentação interativa da API, se o cookie de sessão sair sem `Secure`, ou se o acesso estiver aberto para
fora da rede privada (Funnel). Com `GIH_ADMIN_SENHA` no ambiente, ele confere também o cookie; a sessão que
abre para isso é encerrada no fim.

| Para… | Faça |
|---|---|
| **Convidar um colega** | No painel, *Machines* › `gih` › *Share*: ele aceita com a conta **dele** e instala o aplicativo. Vê só esta máquina. O usuário dele no GIH é criado na tela **Usuários**, como qualquer outro |
| **Tirar o acesso de um colega** | No painel, remova o compartilhamento. No GIH, desative o usuário |
| **Desligar o acesso remoto** | `docker compose --profile remoto stop tailscale borda` |
| **Cortar tudo, de vez** | No painel, remova a máquina `gih`. Para voltar, é autorizar de novo |
| **Perdeu um aparelho** | No painel, remova o aparelho; no GIH, troque a senha em **Minha conta**, que derruba as outras sessões |

O que vale saber:

- **A máquina precisa ficar ligada**, sem suspender, e com o Docker aberto. Se o endereço parou de responder,
  é quase sempre isso.
- **A autorização da máquina vence em 180 dias**, por padrão. No painel, em *Machines* › `gih`, dá para
  desligar o vencimento.
- **O nome `gih` e o da sua rede ficam no registro público de certificados.** O endereço não responde fora da
  rede; só não ponha nada sensível no nome (`TS_HOSTNAME`, no `.env`).
- **Cinco senhas erradas seguidas, de qualquer aparelho de fora, travam o login de fora por 15 minutos** — o
  bloqueio é por origem (RNF11), e todos os remotos chegam pela borda. O acesso por esta máquina não é afetado.
- **Não troque isto por um túnel público**, nem tire o `127.0.0.1` de uma porta "só para testar": o roteiro de
  conferência reprova as duas coisas.

## Como gerar as entregas

O documento de cada entrega é acumulado — traz as sprints anteriores e a atual — e é **gerado a partir da
documentação deste repositório**, e não escrito à parte. O gerador fica em [`docs/entrega/`](entrega/), com
uma seção por sprint em `secoes/`:

```bash
node docs/entrega/renderizar_diagramas.js   # diagramas, a partir dos blocos mermaid do markdown
node docs/entrega/gerar.js                  # monta o .docx
powershell -ExecutionPolicy Bypass -File docs/entrega/converter_pdf.ps1 -Nome GRUPO-18-GIH-SPRINT-NN
```

A conversão pelo Word trava nesta máquina com frequência, sem erro e sem janela. Quando acontecer, o caminho
é abrir o `.docx` no Word e usar **Arquivo › Exportar › Criar PDF** — o resultado é o mesmo.

**A documentação técnica final** (H73) — a arquitetura e as ADRs, o modelo de dados, as classes e os
serviços, e os resultados medidos — não é escrita à parte: cada parte é o arquivo do repositório, convertido
como está (`docs/07`, `docs/08`, `docs/10` e `docs/medicoes/`). Ao contrário das entregas, que são o retrato
de uma data, ela **se regera a cada mudança** da documentação:

```bash
node docs/entrega/renderizar_diagramas.js arquitetura-geral   # só os diagramas que mudaram, pelo nome
node docs/entrega/gerar_documentacao.js
```

Sem nomes, o `renderizar_diagramas.js` refaz todos — e o Mermaid não sai idêntico de uma execução para a
outra, então o diff ganha arquivos que não mudaram de conteúdo. O PDF sai do `.docx` pelo Word, como o das
entregas.

**As evidências de execução** vêm de execuções reais, e não são transcritas à mão. Cada entrega grava na sua
própria pasta, `docs/entrega/evidencias/sprintNN/`, e **a pasta de uma sprint já entregue não se regera** —
é o retrato daquela data:

```bash
cd api
GIH_ADMIN_SENHA=... python e2e/verificacao.py        > ../docs/entrega/evidencias/sprintNN/verificacao.txt
GIH_ADMIN_SENHA=... python e2e/transcricao_modelo.py > ../docs/entrega/evidencias/sprintNN/modelo.txt
GIH_ADMIN_SENHA=... python e2e/validacoes.py         > ../docs/entrega/evidencias/sprintNN/validacoes.txt
GIH_ADMIN_SENHA=... python e2e/persistencia.py       > ../docs/entrega/evidencias/sprintNN/persistencia.txt
cd ..
GIH_ADMIN_SENHA=... node docs/entrega/capturar_sprintNN.js       # as telas da sprint
api/.venv/Scripts/python scripts/registrar_testes.py --saida docs/entrega/evidencias/sprintNN
python scripts/registrar_bugs.py --desde AAAA-MM-DD --saida docs/entrega/evidencias/sprintNN
python scripts/registrar_revisoes.py --depois-do-pr NNN --saida docs/entrega/evidencias/sprintNN
node docs/entrega/registrar_commits.js > docs/entrega/evidencias/sprintNN/commits.txt
```

Os registros de bugs e de revisões leem o GitHub, e pedem o `gh` autenticado; a janela das revisões começa
depois do PR do PDF da entrega anterior. Nenhum dos scripts deixa resíduo no banco. A seção de uma parte já entregue lê só a cópia da pasta dela, e
nunca o arquivo vivo: antes de exportar o PDF, compare o texto e as figuras das partes anteriores com o
documento já entregue (CLAUDE.md, seção 7).
