# 13 — Referência da API

**Projeto:** Growth Intelligence Hub (GIH)
**Versão da API:** 1.0.0-rc.1 · **Gerado por** `scripts/exportar_api.py` — não edite à mão

> **Este documento sai da própria API.** O `app.openapi()` — o mesmo documento do Swagger, em
> `/api/docs` com o sistema no ar — é exportado para `docs/api/openapi.json` e convertido aqui,
> rota por rota. Um teste reprova o Pull Request que mude a API sem gerar os dois de novo. Os
> esquemas completos de cada corpo e de cada resposta estão no `openapi.json`.

## Como usar

A API do **Growth Intelligence Hub**: recebe os relatórios de desempenho de uma rede de parceiros
e devolve o painel, a previsão, o plano de campanha otimizado e as mensagens para cada parceiro.
A interface web usa estas mesmas rotas.

### Autenticação

A sessão vive num **cookie** (`gih_sessao`, `HttpOnly`, `SameSite=Lax`), e nunca num token que o
cliente guarda:

1. `POST /api/sessao` com `{"login": "...", "senha": "..."}` abre a sessão e devolve o cookie;
2. as chamadas seguintes mandam o cookie de volta (o navegador faz isso sozinho; com `httpx` ou
   `requests`, use um cliente com sessão);
3. `DELETE /api/sessao` encerra a sessão **no servidor**.

A sessão dura 8 horas por padrão. Cinco tentativas de entrada erradas da mesma origem bloqueiam
novas tentativas por 15 minutos (`429`). Nesta página (Swagger), entre por `POST /api/sessao` com
"Try it out": o navegador guarda o cookie, e as outras rotas passam a responder.

### Perfis

Cada rota diz, na descrição, os **perfis** que podem chamá-la: Administrador, Gestor, Analista e
Parceiro. A permissão é conferida **no servidor**, em toda chamada: o perfil sem permissão recebe
`403`, e a tentativa fica na trilha de auditoria.

### Erros

| Código | Quando | Corpo |
|---|---|---|
| `401` | Sem sessão, ou a sessão terminou | `{"detail": "..."}` |
| `403` | O perfil não pode fazer isto | `{"detail": "..."}` |
| `404` | O registro não existe | `{"detail": "..."}` ou `{"detail": {"erro", "ajuda"}}` |
| `409` | A regra de negócio recusa o pedido | `{"detail": {"erro", "ajuda", ...}}` |
| `413` | O arquivo passa do limite | `{"detail": {"erro", "ajuda"}}` |
| `422` | Um campo não passa na validação | `{"erro", "campos": [{"campo", "mensagem", "ajuda"}]}` |
| `429` | Tentativas de entrada demais | `{"detail": "..."}` |
| `500` | Falha inesperada; o detalhe fica no log, com o identificador | `{"erro", "correlacao"}` |

O `409` é o da regra de negócio: o período já importado, o nome que já existe, um cálculo que já
está em andamento. Toda mensagem está em português, escrita para quem usa o sistema, e diz o que
fazer.

### Convenções

- **Listas paginadas**: `pagina` (a partir de 1) e `tamanho`; a resposta traz `itens` e `total`.
- **Filtros na URL**: o que a tela filtra vai na query, e o CSV da mesma lista aceita os mesmos
  filtros (`.../exportacao.csv`) — o arquivo é exatamente o recorte da tela.
- **Operações longas** (o treino do modelo, o plano de campanha, o benchmark, a geração de
  mensagens) respondem `202` com o registro criado, e seguem em segundo plano: consulte o
  andamento pelo `id` até a `situacao` sair de `EM_ANDAMENTO`.
- **Dinheiro e frações** vêm como texto decimal (`"12500.40"`, `"0.1400"`), para não perder
  centavos.
- **Estimativa**: todo valor previsto pelo modelo vem marcado como tal, e o assistente nunca
  calcula número — ele só redige com os números do sistema, citando a fonte.

## Exemplo de uso, de ponta a ponta

Com o sistema no ar (`docker compose up -d`), em Python, com o `httpx` — o cliente guarda o
cookie da sessão entre as chamadas:

```python
import httpx

api = httpx.Client(base_url="http://localhost:8000")
r = api.post("/api/sessao", json={"login": "gestora", "senha": "uma frase longa de senha"})
r.raise_for_status()                                  # 201, e o cookie gih_sessao

emrisco = api.get("/api/parceiros", params={"segmento": "EM_RISCO", "tamanho": 5}).json()
print(emrisco["total"], [p["nome"] for p in emrisco["itens"]])

novo = api.post("/api/parceiros", json={"nome": "Ponto Azul 9", "status": "ATIVO"})
print(novo.status_code, novo.json())                # 201, ou 409 se o nome já existe

csv = api.get("/api/parceiros/exportacao.csv", params={"segmento": "EM_RISCO"})
open("em-risco.csv", "wb").write(csv.content)        # o mesmo recorte, em CSV

api.delete("/api/sessao")                            # 204: a sessão termina no servidor
```

O mesmo, com o `curl`, guardando o cookie num arquivo:

```bash
curl -c sessao.txt -H 'Content-Type: application/json' \
     -d '{"login":"gestora","senha":"uma frase longa de senha"}' http://localhost:8000/api/sessao
curl -b sessao.txt 'http://localhost:8000/api/parceiros?segmento=EM_RISCO&tamanho=5'
curl -b sessao.txt -X DELETE http://localhost:8000/api/sessao
```

## As áreas

| Área | O que tem | Rotas |
|---|---|---|
| Autenticação | Abrir e encerrar a sessão, saber quem está dentro, trocar a própria senha. | 4 |
| Usuários | As contas e os perfis de acesso (Administrador). | 6 |
| Parceiros | O cadastro dos parceiros da rede e das categorias; a ficha de cada um. | 12 |
| Importação | O relatório de desempenho de um período: a prévia e a gravação. | 5 |
| Painel | Os indicadores, o ranking, as séries, os segmentos e a mobilidade do Top N. | 7 |
| Configuração | Os limiares da segmentação (Administrador). | 2 |
| Modelo preditivo | O treino do modelo de previsão e as versões. | 4 |
| Campanha | O catálogo de ações e o plano de campanha calculado pelo otimizador. | 9 |
| Benchmark | O mesmo problema medido em Python, C++ serial, OpenMP e GPU. | 4 |
| Mensagens | A geração das mensagens para os parceiros e a fila de aprovação. | 11 |
| Portal do parceiro | O desempenho do próprio parceiro (perfil Parceiro). | 1 |
| Assistente | Perguntas em linguagem natural sobre os dados, com a fonte de cada número. | 2 |
| Auditoria | A trilha das ações sensíveis (Administrador). | 3 |
| Relatórios | Os relatórios da rede e o de operações, na tela e em CSV. | 9 |
| Ajuda | Os números das regras que a tela de ajuda cita, como estão valendo. | 1 |
| Sistema | A saúde do serviço. | 1 |

**81 operações.**

## Autenticação

Abrir e encerrar a sessão, saber quem está dentro, trocar a própria senha.

### `POST /api/sessao` — Entrar: abre a sessão

**Quem pode:** Pública: não exige sessão.

Abre a sessão (RF01).

A ordem aqui importa: bloqueio, depois conferência, depois renovação. E o
caminho de falha gasta o mesmo tempo do caminho de sucesso — ver
`gastar_tempo_de_conferencia`.

**Corpo** (`application/json`): `Credenciais`.

```json
{
  "login": "gestora",
  "senha": "uma frase longa de senha"
}
```

| Resposta | Quando |
|---|---|
| `201` | Criado: o corpo traz o registro novo. — `SessaoResposta` |
| `401` | Login ou senha errados — a mesma resposta para os dois, de propósito: ela não diz se o login existe (RNF11). — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `429` | Tentativas de entrada demais desta origem: espere 15 minutos. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `DELETE /api/sessao` — Sair: encerra a sessão no servidor

**Quem pode:** Qualquer perfil, com sessão aberta.

Encerra a sessão **no servidor** (RF02, H12).

Apagar o cookie sozinho não bastaria: quem já tem o token na mão continuaria
entrando. Por isso a revogação vem primeiro e o cookie depois.

| Resposta | Quando |
|---|---|
| `204` | Feito, sem corpo na resposta. |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/sessao/atual` — Quem está dentro, e as telas que pode abrir

**Quem pode:** Qualquer perfil, com sessão aberta.

Quem está autenticado. O frontend usa para decidir o que desenhar.

Decidir o que *desenhar*, não o que *permitir* — a permissão é verificada no
servidor a cada requisição (regra 2.5, RNF14).

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `UsuarioAtualResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/sessao/senha` — Trocar a própria senha

**Quem pode:** Qualquer perfil, com sessão aberta.

Troca a própria senha, exigindo a atual (RF07, H19).

**Corpo** (`application/json`): `TrocaSenha`.

```json
{
  "senha_atual": "uma frase longa de senha",
  "senha_nova": "outra frase longa, nova"
}
```

| Resposta | Quando |
|---|---|
| `204` | Feito, sem corpo na resposta. |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Usuários

As contas e os perfis de acesso (Administrador).

### `GET /api/usuarios` — Listar as contas, com filtros e busca

**Quem pode:** Administrador.

A lista, filtrada por situação e perfil, e com busca por nome ou login (RF52, H91).

A busca normaliza o termo pela mesma regra da de parceiros (`para_busca`):
sem maiúscula, sem acento, e com `%` e `_` tratados como texto, e não como
curinga.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `ativo` | query | boolean (opcional) | não | Filtra por situação. |
| `perfil` | query | Perfil (opcional) | não | Só as contas deste perfil. |
| `busca` | query | string (opcional) | não | Trecho do nome ou do login, sem maiúscula nem acento. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `lista de UsuarioResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/usuarios` — Criar uma conta

**Quem pode:** Administrador.

Cria a conta com a senha inicial, que passa pela regra de força (RF03, RF04). O perfil Parceiro exige o parceiro vinculado (RF56). Recusa com `409` o login que já existe.

**Corpo** (`application/json`): `NovoUsuario`.

```json
{
  "login": "analista.norte",
  "nome": "Analista da Regional Norte",
  "senha": "senha inicial longa",
  "perfil": "ANALISTA"
}
```

| Resposta | Quando |
|---|---|
| `201` | Criado: o corpo traz o registro novo. — `UsuarioResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/usuarios/parceiros` — Buscar um parceiro pelo nome, para a conta Parceiro

**Quem pode:** Administrador.

Acha um parceiro pelo nome, para vinculá-lo a uma conta de perfil Parceiro (RF56, H101).

**Não é a lista de parceiros**, que a matriz não dá ao Administrador (UC04):
a busca é obrigatória, devolve só o nome e a situação, e para em
`PARCEIROS_NA_BUSCA`. Sem ela, a conta do parceiro só se criava pela API.

Declarada antes de `/{usuario_id}`: depois dela, "parceiros" seria lido como
o identificador de um usuário.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `busca` | query | string | sim | Trecho do nome do parceiro. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `lista de ParceiroDoVinculo` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/usuarios/{usuario_id}` — Ler uma conta

**Quem pode:** Administrador.

A conta, com o perfil, a situação e o parceiro vinculado.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `usuario_id` | path | integer | sim | O identificador da conta. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `UsuarioDetalhe` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `PATCH /api/usuarios/{usuario_id}` — Editar uma conta: nome, perfil, vínculo e situação

**Quem pode:** Administrador.

Altera nome, perfil, vínculo de parceiro e situação.

Não existe apagar: a auditoria referencia o autor de cada ação, e remover a
linha deixaria a trilha apontando para o nada. Desativar resolve o problema
real — tirar o acesso — sem destruir o histórico (RF03, RF06).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `usuario_id` | path | integer | sim | O identificador da conta. |

**Corpo** (`application/json`): `EdicaoUsuario`.

```json
{
  "perfil": "GESTOR"
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `UsuarioResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/usuarios/{usuario_id}/senha` — Redefinir a senha de outra conta

**Quem pode:** Administrador.

O Administrador dá uma senha nova a outra conta (RF54, H93).

É a volta de quem esqueceu a senha: antes desta rota, a única saída era
criar outra conta para a mesma pessoa. A senha passa pela mesma validação de
força da criação, e **todas** as sessões da conta caem — diferente da troca
da própria senha, que preserva a sessão de quem trocou: aqui quem está
fazendo a operação não é o dono da conta.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `usuario_id` | path | integer | sim | O identificador da conta. |

**Corpo** (`application/json`): `RedefinicaoSenha`.

```json
{
  "senha_nova": "senha redefinida longa"
}
```

| Resposta | Quando |
|---|---|
| `204` | Feito, sem corpo na resposta. |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Parceiros

O cadastro dos parceiros da rede e das categorias; a ficha de cada um.

### `GET /api/parceiros` — Listar os parceiros, com busca, filtros e ordenação

**Quem pode:** Gestor e Analista.

Lista paginada, com busca, filtros e ordenação (RF14, RF23, RF24).

`selectinload` na categoria não é detalhe: sem ele, montar a resposta faria
uma consulta por linha para buscar o nome da categoria — o N+1 que funciona
com 100 parceiros e morre com 10.000, que é a carga do RNF04.

**A paginação não é enfeite.** Antes dela, medido com o gerador: 141 ms com
5.000 parceiros e 295 ms com 10.000, a única consulta do painel que crescia
com o tamanho da base (ver `docs/medicoes/`).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `busca` | query | string (opcional) | não | Trecho do nome. Ignora maiúsculas e acentuação. |
| `categoria_id` | query | integer (opcional) | não | Só os parceiros desta categoria. |
| `status` | query | StatusComercial (opcional) | não | Só os parceiros deste status comercial. |
| `ativo` | query | boolean (opcional) | não | Filtra por situação. |
| `sem_categoria` | query | boolean (opcional) | não | Só os pendentes: sem categoria confirmada — em branco ou só sugerida. |
| `segmento` | query | Segmento (opcional) | não | Segmento no período mais recente. |
| `ordenar_por` | query | Ordenacao | não | A coluna da ordenação. |
| `descendente` | query | boolean | não | Inverte a ordem. |
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaParceiros` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/parceiros` — Cadastrar um parceiro

**Quem pode:** Gestor e Analista.

Cadastra o parceiro (RF14). A categoria é opcional; sem ela, a tela sugere uma pelo nome (RN05). Recusa com `409` o nome que já existe, apontando o cadastro existente.

**Corpo** (`application/json`): `NovoParceiro`.

```json
{
  "nome": "Ponto Azul 9",
  "categoria_id": 3,
  "status": "ATIVO",
  "contato": "contato@exemplo.test"
}
```

| Resposta | Quando |
|---|---|
| `201` | Criado: o corpo traz o registro novo. — `ParceiroResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/parceiros/exportacao.csv` — Exportar a lista de parceiros em CSV

**Quem pode:** Gestor e Analista.

Exporta a visão filtrada em CSV (RF25, H38).

**Declarada antes de `/{parceiro_id}`**, e isso não é estilo: o FastAPI casa
as rotas na ordem em que foram registradas, e `exportacao.csv` entraria como
id de parceiro, devolvendo 422 em vez do arquivo.

Recebe **exatamente** os mesmos filtros da listagem, e os aplica pela mesma
função: exportar um recorte diferente do que está na tela é pior que não
exportar.

Sem paginação de propósito — é o arquivo inteiro do recorte — mas também sem
montar a lista em memória: as linhas saem em lotes, pelo `yield_per`, e o
gerador entrega cada uma conforme ela chega do banco.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `busca` | query | string (opcional) | não | Um trecho do nome; maiúscula e acento não importam. |
| `categoria_id` | query | integer (opcional) | não | Só os parceiros desta categoria. |
| `status` | query | StatusComercial (opcional) | não | Só os parceiros deste status comercial. |
| `ativo` | query | boolean (opcional) | não | Só os ativos (verdadeiro) ou só os inativos (falso). |
| `sem_categoria` | query | boolean (opcional) | não | Só os parceiros sem categoria. |
| `segmento` | query | Segmento (opcional) | não | Só os parceiros deste segmento (RN01). |
| `ordenar_por` | query | Ordenacao | não | A coluna da ordenação. |
| `descendente` | query | boolean | não | Do maior para o menor. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/parceiros/{parceiro_id}` — Ler um parceiro, com o desempenho mais recente

**Quem pode:** Gestor e Analista.

Um parceiro, com o desempenho do período mais recente.

O mesmo formato de um item da lista, pela mesma consulta. A tela de cadastro
mostra o segmento e o faturamento ao lado dos dados cadastrais: é o que liga
o registro à análise, e o que deixa o usuário ver o efeito de desativar ou
reclassificar alguém. Montar isso numa segunda consulta, diferente da lista,
faria as duas telas discordarem sobre o mesmo parceiro.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `parceiro_id` | path | integer | sim | O identificador do parceiro. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ParceiroComDesempenho` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `PATCH /api/parceiros/{parceiro_id}` — Editar um parceiro

**Quem pode:** Gestor e Analista.

Altera nome, categoria, status comercial, contato e situação (RF14).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `parceiro_id` | path | integer | sim | O identificador do parceiro. |

**Corpo** (`application/json`): `EdicaoParceiro`.

```json
{
  "contato": "(81) 3000-0000",
  "status": "PROSPECCAO"
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ParceiroResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `DELETE /api/parceiros/{parceiro_id}` — Excluir um parceiro sem histórico

**Quem pode:** Gestor e Analista.

Exclui o parceiro — **quando ele não tem histórico**.

Apagar um parceiro que já tem faturamento importado falsearia as séries dos
períodos fechados: o total da rede deixaria de bater com a soma das partes,
e ninguém perceberia, porque a tela continuaria parecendo correta.

Por isso a exclusão é condicional. Com vínculos, a resposta recusa dizendo
**quantos registros de cada tipo** impedem, e aponta a desativação — que
resolve o problema real, que é tirar o parceiro de circulação, sem destruir
o histórico (UC04, A4).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `parceiro_id` | path | integer | sim | O identificador do parceiro. |

| Resposta | Quando |
|---|---|
| `204` | Feito, sem corpo na resposta. |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/parceiros/{parceiro_id}/previsao` — A previsão do parceiro, ou por que não há

**Quem pode:** Gestor e Analista.

Faturamento previsto e risco do parceiro (RF28, H44) — ou o porquê de não haver.

Rota própria, com a previsão inteira e o porquê de não haver. A lista e a
exportação levam só o risco, e pela mesma junção da consulta delas (H80) —
e não por esta rota, que numa lista seria uma consulta por linha.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `parceiro_id` | path | integer | sim | O identificador do parceiro. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PrevisaoParceiro` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/parceiros/{parceiro_id}/campanha` — O parceiro no último plano de campanha

**Quem pode:** Gestor e Analista.

O parceiro no último plano de campanha viável (H81) — ou que ficou de fora dele.

É o caminho do cadastro para a campanha: quem abre o parceiro vê a ação que o
plano reserva para ele, e dali abre o plano. Rota própria, como a previsão: é
complemento do cadastro, e a lista não precisa dela.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `parceiro_id` | path | integer | sim | O identificador do parceiro. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `CampanhaDoParceiro` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/parceiros/{parceiro_id}/historico` — O histórico das alterações do cadastro

**Quem pode:** Gestor e Analista.

O que mudou no cadastro do parceiro, quando e por quem (RF50, H90).

Sai da trilha de auditoria — os eventos de cadastro com este parceiro como
alvo —, do mais recente para o mais antigo. **Só os do próprio parceiro**: a
trilha inteira continua sendo do Administrador (RF08), e por isso a origem e
os parâmetros crus não vêm aqui, só a frase. E a frase é só a mudança: o
nome do parceiro, que a trilha repete em cada linha, aqui é o título da página.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `parceiro_id` | path | integer | sim | O identificador do parceiro. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `lista de EventoDoParceiro` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/categorias/sugestao` — Sugerir a categoria pelo nome do parceiro

**Quem pode:** Gestor e Analista.

A categoria que a regra da RN05 sugere para um nome (RF15, H27).

Não grava nada: é o que o cadastro manual mostra enquanto a pessoa digita,
para ela usar, trocar ou ignorar. `categoria` nula quer dizer que o nome não
aponta uma categoria só — resultado aceitável, e não erro.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `nome` | query | string | sim | Nome do parceiro. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `SugestaoCategoria` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/categorias` — Listar as categorias

**Quem pode:** Gestor e Analista.

As categorias da rede, para o cadastro e para os filtros.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `ativa` | query | boolean (opcional) | não | Filtra por situação. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `lista de CategoriaResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/categorias` — Criar uma categoria

**Quem pode:** Gestor e Analista.

Cria uma categoria. Recusa com `409` o nome que já existe.

**Corpo** (`application/json`): `NovaCategoria`.

```json
{
  "nome": "Doceria"
}
```

| Resposta | Quando |
|---|---|
| `201` | Criado: o corpo traz o registro novo. — `CategoriaResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Importação

O relatório de desempenho de um período: a prévia e a gravação.

### `POST /api/importacoes/previa` — Prévia de um relatório colado, sem gravar

**Quem pode:** Gestor e Analista.

Mostra o que será gravado, sem gravar (RF11, H24).

**Corpo** (`application/json`): `PedidoImportacao`.

```json
{
  "periodo_inicio": "2026-09-21",
  "periodo_fim": "2026-09-27",
  "texto": "Parceiro;Faturamento;Pedidos\nPonto Azul 9;12500,40;312"
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PreviaImportacao` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/importacoes` — Importar um relatório colado

**Quem pode:** Gestor e Analista.

Grava as métricas do período (RF09, RF12, RF13, H21, H25).

A transação é a da requisição: qualquer falha reverte tudo, e o período
inteiro entra ou nada entra (UC03, E2). Isso vale também para a
substituição — apagar e gravar acontecem juntos ou não acontecem.

**Corpo** (`application/json`): `PedidoImportacao`.

```json
{
  "periodo_inicio": "2026-09-21",
  "periodo_fim": "2026-09-27",
  "texto": "Parceiro;Faturamento;Pedidos\nPonto Azul 9;12500,40;312",
  "substituir": false
}
```

| Resposta | Quando |
|---|---|
| `201` | Criado: o corpo traz o registro novo. — `ImportacaoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/importacoes` — Histórico das importações

**Quem pode:** Administrador, Gestor e Analista.

Histórico das importações, da mais recente para a mais antiga (RF13, H29).

`metricas_vigentes` é contado no banco, e não lido de `total_gravado`. Os
dois divergem de propósito depois de uma substituição: o total gravado
continua verdadeiro sobre o que aquela importação fez, enquanto o vigente
responde o que restou dela. Zero vigente é o rastro de um período trocado.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `autor` | query | integer (opcional) | não | Id de quem importou. |
| `de` | query | date (opcional) | não | Enviadas a partir deste dia. |
| `ate` | query | date (opcional) | não | Enviadas até este dia, inclusive. |
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaImportacoes` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/importacoes/arquivo/previa` — Prévia de um arquivo CSV, sem gravar

**Quem pode:** Gestor e Analista.

Prévia do arquivo, antes de gravar (RF11, H22, H24).

**Corpo** (`multipart/form-data`): `Body_previa_de_arquivo_api_importacoes_arquivo_previa_post`.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PreviaImportacao` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `413` | O arquivo passa do limite de tamanho. — `ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/importacoes/arquivo` — Importar um arquivo CSV

**Quem pode:** Gestor e Analista.

Importa a partir de arquivo (RF09, H22).

O período continua obrigatório, e pelo mesmo motivo de sempre: o relatório
não traz data, e importar sem ela corrompe a linha do tempo em silêncio
(RN03). Vir num arquivo não muda isso.

**Corpo** (`multipart/form-data`): `Body_importar_arquivo_api_importacoes_arquivo_post`.

| Resposta | Quando |
|---|---|
| `201` | Criado: o corpo traz o registro novo. — `ImportacaoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `413` | O arquivo passa do limite de tamanho. — `ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Painel

Os indicadores, o ranking, as séries, os segmentos e a mobilidade do Top N.

### `GET /api/painel/recortes` — Os períodos e as categorias do painel

**Quem pode:** Administrador, Gestor e Analista.

Os períodos e as categorias que o painel oferece (H82, UC05-A4).

Rota do painel, e não a de categorias: o Administrador lê o painel e não abre
o cadastro de parceiros, de onde a lista de categorias viria. Só as
categorias com parceiro — escolher uma vazia abriria um painel em branco.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `RecortesPainel` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/painel/indicadores` — Indicadores do período, com a variação

**Quem pode:** Administrador, Gestor e Analista.

Indicadores consolidados do período, com variação (RF17, H30) — da rede ou
de uma categoria (H82). A variação é contra o período anterior **no mesmo recorte**.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `periodo_id` | query | integer (opcional) | não | Padrão: o período mais recente. |
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `IndicadoresPainel` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/painel/ranking` — Ranking dos parceiros por faturamento

**Quem pode:** Administrador, Gestor e Analista.

Ranking por faturamento, com posição anterior e variação (RF18, H31).

**Esta rota é a fonte da posição.** A mobilidade do Top N (H35, RN02) vai ler
daqui, e nunca do segmento armazenado: um parceiro entre os N maiores mas em
queda fica gravado como EM_RISCO, e derivar a mobilidade do segmento faria o
painel anunciar que ele saiu do Top N enquanto continua lá.

Duas consultas, não N: a página, e as posições anteriores **apenas dos
parceiros dela**. A posição anterior é calculada sobre o ranking inteiro do
período anterior e só então filtrada — calculá-la sobre o recorte daria a
posição dentro da página, que não significa nada.

**Com categoria, a posição continua a da rede** (RN02, H82): a janela numera
o ranking inteiro na subconsulta, e o filtro entra por fora dela. Filtrar
antes renumeraria — a padaria que é a 40ª da rede viraria a 1ª, e a tabela
discordaria do cadastro dela e da mobilidade do Top N.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `periodo_id` | query | integer (opcional) | não | Padrão: o período mais recente. |
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaRanking` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/painel/series` — Série histórica da rede, de uma categoria ou de um parceiro

**Quem pode:** Administrador, Gestor e Analista.

Série histórica da rede, de uma categoria ou de um parceiro (RF19, H32, H82),
com a lacuna explícita onde não houve medição — ver `desempenho.serie_historica`.

Não há paginação: a quantidade de períodos é limitada pelo que foi
importado, e o RNF04 fixa o teto em 52. O recorte por data existe para quem
quiser menos, não para conter volume.

Com `periodo_id`, a série termina nele: quem escolhe um período no painel
quer saber como a rede vinha **até ali**, e não o que aconteceu depois.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `parceiro_id` | query | integer (opcional) | não | Padrão: a rede inteira. |
| `de` | query | date (opcional) | não | Períodos a partir deste dia. |
| `ate` | query | date (opcional) | não | Períodos que terminam até este dia. |
| `periodo_id` | query | integer (opcional) | não | A série vai até este período. Padrão: até o mais recente. |
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `SerieHistorica` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/painel/segmentos` — Quantos parceiros em cada segmento

**Quem pode:** Administrador, Gestor e Analista.

Quantos parceiros em cada segmento no período (RF20, H33).

Devolve **só os segmentos com parceiros**, ordenados do maior para o menor.
Preencher os seis com zero desenharia barras vazias que não dizem nada e
roubariam espaço das que dizem.

Período sem segmentação calculada devolve a lista vazia, e não seis zeros:
seis zeros afirmam uma distribuição plana que ninguém mediu.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `periodo_id` | query | integer (opcional) | não | Padrão: o período mais recente. |
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `DistribuicaoSegmentos` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/painel/mobilidade` — Quem entrou e quem saiu do Top N

**Quem pode:** Administrador, Gestor e Analista.

Quem entrou e quem saiu do Top N entre dois períodos (RF22, H35).

**RN02: isto lê o ranking, nunca o segmento armazenado.** Como Em Risco
vence Top na precedência de RN01, um parceiro entre os N maiores mas em
queda fica gravado como EM_RISCO. Derivar a mobilidade dali faria o painel
anunciar que ele saiu do Top N enquanto continua lá — e o erro passaria
despercebido, porque a tela continuaria plausível.

Uma consulta só, com junção externa completa dos dois rankings: quem está em
um lado e não no outro. Comparar as duas listas em Python exigiria trazer os
dois rankings inteiros para a aplicação.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `periodo_id` | query | integer (opcional) | não | Padrão: o período mais recente. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `MobilidadeTopN` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/painel/decisao` — A previsão e a campanha, resumidas para o painel

**Quem pode:** Gestor e Analista.

O que a previsão e a campanha dizem, dentro do painel (RF28, RF30 · H83, UC05-A5).

**Não tem `periodo_id`, de propósito.** A previsão parte do período em que o
modelo foi treinado, e o plano é o último calculado: nenhum dos dois muda com
o período que a pessoa escolhe olhar. A resposta diz de quando cada um é.

Quatro consultas agregadas, com 500 ou com 10.000 parceiros (RNF03).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `DecisaoPainel` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Configuração

Os limiares da segmentação (Administrador).

### `GET /api/configuracao/segmentacao` — Os limiares da segmentação em vigor

**Quem pode:** Administrador.

Os limiares em vigor.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ConfiguracaoSegmentacaoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `PUT /api/configuracao/segmentacao` — Alterar os limiares da segmentação

**Quem pode:** Administrador.

Altera os limiares e **reclassifica o período mais recente**.

Configuração que não se reflete na tela engana quem a mudou: o
administrador baixaria o Top N de 15 para 10, olharia o painel e veria as
mesmas quinze linhas marcadas como Top.

Só o período mais recente entra na requisição. Reprocessar a base inteira
levaria segundos com 10.000 parceiros e doze períodos — tempo demais para
uma chamada síncrona, e o RNF03 vale para o sistema todo. Os períodos
anteriores mantêm a classificação antiga até `reprocessar-segmentos` rodar,
e a resposta diz quantos foram reclassificados agora justamente para que
isso não passe despercebido.

A auditoria guarda **o valor anterior junto do novo**. "Alterou a
configuração" sem dizer o que era antes não responde à pergunta que a trilha
existe para responder.

**Corpo** (`application/json`): `LimiaresSegmentacao`.

```json
{
  "top_n": 15,
  "periodos_tendencia": 2,
  "periodos_novato": 3
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ConfiguracaoSegmentacaoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Modelo preditivo

O treino do modelo de previsão e as versões.

### `GET /api/modelo` — O modelo em uso e se dá para treinar agora

**Quem pode:** Administrador e Gestor.

A versão em uso, o último treino e se dá para treinar agora (UC07, passo 1).

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `EstadoModelo` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/modelo/treinos` — Treinar o modelo (em segundo plano)

**Quem pode:** Administrador e Gestor.

Dispara um treino (UC07, passos 2 a 5; H45).

Recusa com `409` e o motivo quando o histórico é curto demais (UC07-E1) ou
já há um treino rodando.

**O treino é gravado antes de a resposta sair**, com commit explícito: a
execução em segundo plano abre outra sessão e precisa encontrar a linha.

| Resposta | Quando |
|---|---|
| `202` | Aceito: a operação segue em segundo plano; consulte o andamento pelo `id`. — `TreinoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/modelo/treinos` — Histórico dos treinos

**Quem pode:** Administrador e Gestor.

O histórico de treinos, do mais recente para o mais antigo.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaTreinos` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/modelo/treinos/{treino_id}` — Acompanhar um treino

**Quem pode:** Administrador e Gestor.

Um treino — é o que a tela consulta enquanto ele roda.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `treino_id` | path | integer | sim | O identificador do treino. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `TreinoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Campanha

O catálogo de ações e o plano de campanha calculado pelo otimizador.

### `GET /api/campanha` — O que a tela da campanha precisa ao abrir

**Quem pode:** Gestor e Analista.

O que a tela de campanha precisa ao abrir (UC08, passo 1).

Quantos parceiros entram e quantos ficam fora, com o motivo (RN11); as
categorias para as cotas; o catálogo; os modos de execução que esta
instalação tem, e qual roda sem escolha (RF32); e se **quem pergunta** pode
calcular agora e editar o catálogo.

**O perfil entra na resposta** (regra 2.4): a tela esconde o botão pelo que
vem daqui, e não por um `if` sobre o perfil. Sem ele, o analista via
"Calcular plano" e recebia 403 ao clicar, e o gestor não via a edição do
catálogo (#190).

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `EstadoCampanha` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/otimizacoes` — Calcular um plano de campanha (em segundo plano)

**Quem pode:** Gestor.

Calcula o plano (UC08, passos 4 a 10; RF30, RF32).

Recusa com `409` sem modelo treinado (UC08-E1), sem ação ativa no catálogo
ou com outra otimização rodando. Campanha inviável **não** é recusada aqui:
ela é calculada, registrada como inviável e explicada (RN07, UC08-A1). Nem
modo indisponível: roda no primeiro modo disponível, e diz a troca (UC08-A4).

**Corpo** (`application/json`): `ParametrosCampanha-Input`.

```json
{
  "orcamento": "15000.00",
  "maximo_acoes": 30,
  "cota_cauda_longa": "0.30",
  "cotas_categoria": [
    {
      "categoria_id": 3,
      "minimo": "0.10"
    }
  ],
  "aplicacao_inicio": "2026-09-28",
  "aplicacao_fim": "2026-10-04"
}
```

| Resposta | Quando |
|---|---|
| `202` | Aceito: a operação segue em segundo plano; consulte o andamento pelo `id`. — `ExecucaoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/otimizacoes` — Histórico das execuções do otimizador

**Quem pode:** Administrador, Gestor e Analista.

O histórico de execuções, da mais recente para a mais antiga (RF34, H58).

Sem os itens do plano: cada execução vem com autor, data, parâmetros, modo,
tempo e resultado — o que o Administrador também vê. O plano, parceiro a
parceiro, só na consulta de uma execução, que é da campanha (UC08).

**Os filtros (RF51, H91).** O modo é o em que a execução **rodou**, e não o
pedido — quem pede GPU numa máquina sem placa roda no paralelo, e é isso
que a coluna mostra. O dia é o do relógio do servidor, como na trilha de
auditoria, e a data final inclui o dia inteiro.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `modo` | query | ModoExecucao (opcional) | não | O modo em que rodou. |
| `resultado` | query | ResultadoDaExecucao (opcional) | não | Só as execuções com este resultado. |
| `autor` | query | integer (opcional) | não | Id de quem calculou. |
| `de` | query | date (opcional) | não | Iniciadas a partir deste dia. |
| `ate` | query | date (opcional) | não | Iniciadas até este dia, inclusive. |
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaExecucoes` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/otimizacoes/comparacao` — Comparar dois planos lado a lado

**Quem pode:** Gestor e Analista.

Dois planos lado a lado, com o que difere (RF35, UC08-A3, H59).

**Declarada antes de `/otimizacoes/{execucao_id}`**, pelo mesmo motivo da
exportação de parceiros: o FastAPI casa as rotas na ordem, e "comparacao"
entraria como número de execução, devolvendo 422.

Do Gestor e do Analista, como abrir um plano: a comparação mostra os dois
planos inteiros. Só planos concluídos e viáveis se comparam.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `a` | query | integer | sim | O primeiro plano: a base da comparação. |
| `b` | query | integer | sim | O segundo plano: as diferenças são dele para o primeiro. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ComparacaoPlanos` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/otimizacoes/{execucao_id}` — Acompanhar uma execução, com o plano

**Quem pode:** Gestor e Analista.

Uma execução, com o plano: a tela consulta enquanto ela roda, e o
histórico a abre depois (H58).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `execucao_id` | path | integer | sim | O identificador da execução. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ExecucaoResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/otimizacoes/{execucao_id}/exportacao.csv` — Exportar os itens do plano em CSV

**Quem pode:** Gestor e Analista.

Os itens de um plano, em CSV (RF53, H91) — do Gestor e do Analista, como o plano.

As mesmas linhas, na mesma ordem, que a consulta da execução mostra
(`_itens`). O nome do parceiro, o da categoria e o da ação vieram de quem
cadastra, e passam pela proteção contra fórmula. Execução sem plano —
inviável, em andamento, ou que falhou — não tem o que exportar, e a resposta
diz isso em vez de mandar um arquivo só com o cabeçalho.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `execucao_id` | path | integer | sim | O identificador da execução. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/acoes-comerciais` — Listar o catálogo de ações

**Quem pode:** Gestor e Analista.

O catálogo, ativas e inativas: a inativa não entra na campanha, mas existe.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `lista de AcaoComercialResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/acoes-comerciais` — Criar uma ação no catálogo

**Quem pode:** Gestor.

Cria uma ação no catálogo: o custo e os dois efeitos da RN10, em fração (0,14 é 14%).

**Corpo** (`application/json`): `AcaoComercialEntrada`.

```json
{
  "nome": "Cupom de recompra",
  "custo_unitario": "35.00",
  "efeito_crescimento": "0.04",
  "efeito_retencao": "0.02"
}
```

| Resposta | Quando |
|---|---|
| `201` | Criado: o corpo traz o registro novo. — `AcaoComercialResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `PATCH /api/acoes-comerciais/{acao_id}` — Editar ou desativar uma ação do catálogo

**Quem pode:** Gestor.

Altera o custo, os efeitos ou a situação de uma ação. A inativa não entra nos próximos planos.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `acao_id` | path | integer | sim | O identificador da ação do catálogo. |

**Corpo** (`application/json`): `AcaoComercialEdicao`.

```json
{
  "custo_unitario": "40.00",
  "ativa": false
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `AcaoComercialResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Benchmark

O mesmo problema medido em Python, C++ serial, OpenMP e GPU.

### `GET /api/benchmark` — O que a tela do benchmark precisa ao abrir

**Quem pode:** Administrador e Gestor.

O que a tela de benchmark precisa ao abrir (UC09, passos 1 a 3).

Os modos que esta máquina tem, e por que falta cada um que falta (UC09-A1); o
benchmark em andamento, se houver; o último concluído, com o gráfico de
escalabilidade; e a base da estimativa de duração.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `EstadoBenchmark` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/benchmarks` — Rodar o benchmark (em segundo plano)

**Quem pode:** Administrador e Gestor.

Roda o benchmark (UC09, passos 4 a 8). Recusa com `409` se já há um rodando.

**Corpo** (`application/json`): `ParametrosBenchmark`.

```json
{
  "parceiros": 2000,
  "acoes": 5,
  "repeticoes": 3
}
```

| Resposta | Quando |
|---|---|
| `202` | Aceito: a operação segue em segundo plano; consulte o andamento pelo `id`. — `ExecucaoBenchmarkResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/benchmarks` — Histórico dos benchmarks

**Quem pode:** Administrador e Gestor.

O histórico dos benchmarks, do mais recente para o mais antigo (UC09, passo 8).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaBenchmarks` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/benchmarks/{execucao_id}` — Acompanhar um benchmark

**Quem pode:** Administrador e Gestor.

Um benchmark, com o gráfico de escalabilidade do número de ações dele: a tela
consulta enquanto ele roda, e o histórico o abre depois.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `execucao_id` | path | integer | sim | O identificador da execução. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ExecucaoBenchmarkResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Mensagens

A geração das mensagens para os parceiros e a fila de aprovação.

### `GET /api/mensagens/geracao` — Se o modelo de linguagem está no ar para gerar

**Quem pode:** Gestor e Analista.

O que a tela de mensagens mostra ao abrir: o assistente está no ar, e por que
não, quando não está (ADR-013); a geração em andamento, se houver; e a última.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `EstadoGeracao` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/mensagens/publico` — Prévia do público das mensagens, sem gerar

**Quem pode:** Gestor e Analista.

Quem entra, antes de gerar qualquer coisa (UC10, passos 1 e 2). Não grava nada.

**Corpo** (`application/json`): `PublicoMensagens`.

```json
{
  "tipo": "PLANO",
  "execucao_id": 12
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PreviaPublico` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/mensagens/lotes` — Gerar as mensagens de um público (em segundo plano)

**Quem pode:** Gestor e Analista.

Gera as mensagens do público (UC10, passos 3 a 6). Recusa com `409` se já há uma
geração em andamento, e com `422` o público vazio (E1) ou grande demais.

**Corpo** (`application/json`): `PublicoMensagens`.

```json
{
  "tipo": "FILTRO",
  "segmento": "EM_RISCO"
}
```

| Resposta | Quando |
|---|---|
| `202` | Aceito: a operação segue em segundo plano; consulte o andamento pelo `id`. — `LoteResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/mensagens/lotes/{lote_id}` — Acompanhar uma geração de mensagens

**Quem pode:** Gestor e Analista.

Um lote, com as mensagens prontas até agora e as falhas (UC10-A1, A2).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `lote_id` | path | integer | sim | O identificador da geração de mensagens. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `LoteResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/mensagens/lotes/{lote_id}/refazer` — Tentar de novo as mensagens que falharam

**Quem pode:** Gestor e Analista.

Tenta de novo as mensagens que falharam, ou que ficaram de fora quando a API
reiniciou (UC10-A2). As já geradas ficam como estão.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `lote_id` | path | integer | sim | O identificador da geração de mensagens. |

| Resposta | Quando |
|---|---|
| `202` | Aceito: a operação segue em segundo plano; consulte o andamento pelo `id`. — `LoteResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/mensagens` — A fila de aprovação e o histórico das mensagens

**Quem pode:** Gestor e Analista.

As mensagens de um estado: a fila (UC11, passos 1 e 2) e o histórico (RF40, H64).

As pendentes vêm da mais antiga para a mais nova: é a ordem em que chegaram à
fila, e a próxima a decidir é a primeira (passo 6). As decididas, da decisão
mais recente para a mais antiga, com quem decidiu, quando, o conteúdo final, o
texto redigido quando houve edição e o motivo da rejeição.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `estado` | query | EstadoMensagem | não | A fila são as pendentes. |
| `segmento` | query | Segmento (opcional) | não | O segmento do parceiro quando a mensagem foi gerada. |
| `lote_id` | query | integer (opcional) | não | As mensagens de uma geração. |
| `de` | query | date (opcional) | não | Decididas a partir deste dia, inclusive. |
| `ate` | query | date (opcional) | não | Decididas até este dia, inclusive. |
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaMensagens` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/mensagens/exportacao.csv` — Exportar as mensagens aprovadas em CSV

**Quem pode:** Gestor e Analista.

As mensagens aprovadas em CSV, prontas para envio (RF40, H64), com os filtros do
histórico. Com o contato do parceiro: é com ele que alguém vai enviar — o sistema
não envia nada (ADR-013).

Só as aprovadas: a rejeitada não vai a lugar nenhum, e a pendente ainda espera
a decisão (RN06).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `segmento` | query | Segmento (opcional) | não | O segmento do parceiro quando a mensagem foi gerada. |
| `de` | query | date (opcional) | não | Decididas a partir deste dia, inclusive. |
| `ate` | query | date (opcional) | não | Decididas até este dia, inclusive. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/mensagens/aprovacao-em-lote` — Aprovar várias mensagens de uma vez

**Quem pode:** Gestor.

Aprova as pendentes selecionadas (UC11-A3). Cada uma registra a própria decisão,
com autor e data, e entra na auditoria uma a uma; a que outra pessoa decidiu no
meio fica como estava, e a resposta diz qual.

**Corpo** (`application/json`): `AprovacaoEmLote`.

```json
{
  "ids": [
    101,
    102,
    103
  ]
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `ResultadoAprovacaoEmLote` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/mensagens/{mensagem_id}/aprovacao` — Aprovar uma mensagem

**Quem pode:** Gestor.

Aprova a mensagem (UC11, passos 4 e 5): ela fica pronta para envio, com o texto
editado, se houve edição. Recusa com `409` a que outra pessoa já decidiu (E1).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `mensagem_id` | path | integer | sim | O identificador da mensagem. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `MensagemResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/mensagens/{mensagem_id}/edicao` — Editar o texto de uma mensagem pendente

**Quem pode:** Gestor.

Troca o texto de uma mensagem pendente (UC11-A1). Ela continua pendente: a
edição não aprova. O texto redigido fica guardado para a auditoria, e a resposta
aponta os números do texto novo que não vieram dos dados.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `mensagem_id` | path | integer | sim | O identificador da mensagem. |

**Corpo** (`application/json`): `EdicaoMensagem`.

```json
{
  "texto": "Olá! Preparamos uma condição especial para a sua loja nesta semana."
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `MensagemResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/mensagens/{mensagem_id}/rejeicao` — Rejeitar uma mensagem

**Quem pode:** Gestor.

Rejeita a mensagem, com o motivo, se houver (UC11-A2). Recusa com `409` a que
outra pessoa já decidiu (E1).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `mensagem_id` | path | integer | sim | O identificador da mensagem. |

**Corpo** (`application/json`): `RejeicaoMensagem`.

```json
{
  "motivo": "Tom inadequado para o parceiro."
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `MensagemResposta` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Portal do parceiro

O desempenho do próprio parceiro (perfil Parceiro).

### `GET /api/meu-desempenho` — O desempenho do próprio parceiro

**Quem pode:** Parceiro.

O histórico do próprio parceiro: faturamento, pedidos e ticket médio por
período, e os do período mais recente contra o anterior (UC13, passos 1 a 3).

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `MeuDesempenho` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Assistente

Perguntas em linguagem natural sobre os dados, com a fonte de cada número.

### `GET /api/assistente` — Se o assistente está no ar, e os exemplos de pergunta

**Quem pode:** Gestor e Analista.

O que a tela mostra ao abrir: se o modelo está no ar, e os exemplos do catálogo.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `EstadoDoAssistente` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `POST /api/assistente/perguntas` — Perguntar ao assistente

**Quem pode:** Gestor e Analista.

A resposta a uma pergunta em linguagem natural (UC12, passos 1 a 4).

O modelo lê a pergunta e redige a resposta: com ele carregado, leva de 5 a 10 s;
a primeira pergunta depois de ele ficar parado paga o carregamento, perto de
45 s (ADR-013). A fonte é do código, e o modelo não a vê (H66).

**Corpo** (`application/json`): `PerguntaAssistente`.

```json
{
  "texto": "Qual foi o faturamento total da rede na última semana?"
}
```

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `RespostaAssistente` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Auditoria

A trilha das ações sensíveis (Administrador).

### `GET /api/auditoria` — Consultar a trilha de auditoria

**Quem pode:** Administrador.

Trilha filtrada por autor, ação, intervalo de datas e texto (RF08, RF49).

Paginada porque esta tabela só cresce: a mais movimentada do sistema recebe
uma linha por login, por importação e por decisão de mensagem. Devolver tudo
funcionaria na demonstração e travaria depois.

**O autor vem na mesma consulta**, pela junção — e não por uma busca a cada
linha. Ela é externa: a tentativa de entrada com login que não existe não tem
autor (UC14-A1), e precisa continuar na lista.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `autor` | query | integer (opcional) | não | Id do usuário que executou a ação. |
| `acao` | query | Acao (opcional) | não | Só os registros desta ação. |
| `de` | query | date (opcional) | não | Data inicial, inclusiva. |
| `ate` | query | date (opcional) | não | Data final, inclusiva. |
| `busca` | query | string (opcional) | não | Texto no que foi gravado ou em quem fez. |
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `PaginaAuditoria` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/auditoria/exportacao.csv` — Exportar a trilha de auditoria em CSV

**Quem pode:** Administrador.

A trilha em CSV, com **exatamente** o recorte da tela (RF49).

Os mesmos filtros, pela mesma função da lista: exportar um recorte diferente
do que está na tela é pior que não exportar. Sem paginação — é o arquivo
inteiro do recorte —, e as linhas saem em lotes, sem montar a lista antes.

O resumo e o login passam pela proteção contra fórmula: os dois trazem texto
que alguém digitou — um nome de parceiro, um login tentado.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `autor` | query | integer (opcional) | não | Id do usuário que executou a ação. |
| `acao` | query | Acao (opcional) | não | Só os registros desta ação. |
| `de` | query | date (opcional) | não | Data inicial, inclusiva. |
| `ate` | query | date (opcional) | não | Data final, inclusiva. |
| `busca` | query | string (opcional) | não | Texto no que foi gravado ou em quem fez. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/auditoria/acoes` — As ações que a trilha registra

**Quem pode:** Administrador.

As ações que existem, com o rótulo, para o filtro da interface.

Vem do enum, não de um `SELECT DISTINCT`: a lista precisa ser a mesma ainda
que uma ação nunca tenha ocorrido, senão o filtro some justo quando ninguém
fez aquilo — que é o caso mais interessante de procurar.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `lista de AcaoAuditavel` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Relatórios

Os relatórios da rede e o de operações, na tela e em CSV.

### `GET /api/relatorios/desempenho` — Relatório de desempenho do período

**Quem pode:** Gestor e Analista.

O desempenho de um período, por categoria e por segmento (RF44, H84).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `periodo_id` | query | integer (opcional) | não | Padrão: o período mais recente. |
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |
| `segmento` | query | Segmento (opcional) | não | Padrão: todos os segmentos. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `RelatorioDesempenho` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/desempenho/exportacao.csv` — Relatório de desempenho em CSV

**Quem pode:** Gestor e Analista.

O mesmo relatório, em CSV (RF48): as categorias, os segmentos e o total.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `periodo_id` | query | integer (opcional) | não | Padrão: o período mais recente. |
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |
| `segmento` | query | Segmento (opcional) | não | Padrão: todos os segmentos. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/risco` — Relatório dos parceiros em risco

**Quem pode:** Gestor e Analista.

Quem está em risco e quem o modelo prevê que caia (RF45, H85).

`risco_minimo` é um filtro de quem consulta, e não um limiar do sistema:
ninguém é "de risco" por passar dele, e sem ele o relatório traz todos.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |
| `segmento` | query | Segmento (opcional) | não | Padrão: todos os segmentos. |
| `risco_minimo` | query | number (opcional) | não | Só quem tem chance de queda a partir desta, de 0 a 1. |
| `pagina` | query | integer | não | A página da lista, a partir de 1. |
| `tamanho` | query | integer | não | Quantos itens por página. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `RelatorioRisco` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/risco/exportacao.csv` — Relatório de risco em CSV

**Quem pode:** Gestor e Analista.

O recorte inteiro, sem paginação, em fluxo (RF48) — uma linha por parceiro.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `categoria_id` | query | integer (opcional) | não | Padrão: a rede inteira. |
| `segmento` | query | Segmento (opcional) | não | Padrão: todos os segmentos. |
| `risco_minimo` | query | number (opcional) | não | Só quem tem chance de queda a partir desta, de 0 a 1. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/campanha` — Relatório de um plano de campanha

**Quem pode:** Gestor e Analista.

Onde a verba de um plano foi, por ação, por categoria e por segmento (RF46, H86).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `execucao_id` | query | integer (opcional) | não | Padrão: o último plano viável. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `RelatorioCampanha` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/campanha/planos` — Os planos que o relatório da campanha oferece

**Quem pode:** Gestor e Analista.

Os planos que o relatório oferece para escolher, do mais recente ao mais antigo.

Quem decide que execução tem plano é a API, e não a tela: a lista traz só as
concluídas e viáveis (RN07).

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `lista de PlanoResumido` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/campanha/exportacao.csv` — Relatório da campanha em CSV

**Quem pode:** Gestor e Analista.

O mesmo relatório, em CSV (RF48). Sem plano não há arquivo, e a resposta diz por quê.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `execucao_id` | query | integer (opcional) | não | Padrão: o último plano viável. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `404` | O registro pedido não existe. — `ErroSimples ou ErroComAjuda` |
| `409` | A regra de negócio recusa o pedido, e diz o que fazer. — `ErroComAjuda ou ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/operacoes` — Relatório das operações do sistema

**Quem pode:** Administrador.

O que foi feito no sistema, por tipo de ação, por usuário e por dia (RF47, H87).

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `de` | query | date (opcional) | não | Data inicial, inclusiva. |
| `ate` | query | date (opcional) | não | Data final, inclusiva. |
| `autor` | query | integer (opcional) | não | Id do usuário que executou a ação. |
| `acao` | query | Acao (opcional) | não | Só os registros desta ação. |

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `RelatorioOperacoes` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

### `GET /api/relatorios/operacoes/exportacao.csv` — Relatório das operações em CSV

**Quem pode:** Administrador.

O mesmo relatório, em CSV (RF48) — com todas as pessoas, que a tela resume.

| Parâmetro | Onde | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `de` | query | date (opcional) | não | Data inicial, inclusiva. |
| `ate` | query | date (opcional) | não | Data final, inclusiva. |
| `autor` | query | integer (opcional) | não | Id do usuário que executou a ação. |
| `acao` | query | Acao (opcional) | não | Só os registros desta ação. |

| Resposta | Quando |
|---|---|
| `200` | O arquivo CSV, com o separador `;` e o BOM do UTF-8. — `text/csv` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `422` | Um ou mais campos não passaram na validação; cada um diz o que corrigir. — `ErroDeCampos` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Ajuda

Os números das regras que a tela de ajuda cita, como estão valendo.

### `GET /api/ajuda/regras` — Os limiares das regras, como valem agora

**Quem pode:** Administrador, Gestor e Analista.

Os números das regras que a ajuda cita, como estão valendo agora.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `RegrasDaAjuda` |
| `401` | Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`. — `ErroSimples` |
| `403` | O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria. — `ErroSimples` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |

## Sistema

A saúde do serviço.

### `GET /api/health` — Saúde do serviço e do banco

**Quem pode:** Pública: não exige sessão.

Verificação de saúde. Público — não exige sessão.

| Resposta | Quando |
|---|---|
| `200` | Sucesso. — `object` |
| `500` | Falha inesperada. O detalhe fica no log, com o identificador. — `ErroInterno` |
