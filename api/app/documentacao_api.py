"""A documentação da API para quem a usa (H107).

O FastAPI gera o OpenAPI das rotas, mas só com o que o código já diz: o resumo
sai do nome da função ("Listar", sete vezes), a autenticação não aparece, o 422
documentado é o padrão dele — e a API devolve outro formato —, e nenhum erro de
regra (404, 409, 413, 429) é citado. Este módulo completa o documento num lugar
só, sem tocar no comportamento de nenhuma rota:

- o resumo em português de cada operação, e a descrição de cada área (tag);
- os perfis que podem chamar cada rota, lidos da própria rota
  (`perfis_da_rota`), e não copiados à mão;
- o cookie de sessão como esquema de segurança, com o 401 e o 403;
- os quatro formatos de erro como são, e os erros de regra de cada rota;
- a descrição dos parâmetros repetidos, os exemplos de entrada e o `text/csv`
  das exportações.

`api/tests/test_documentacao_api.py` reprova a rota nova sem resumo, sem
descrição ou sem exemplo, e o exemplo que o próprio esquema recusaria.
"""
from __future__ import annotations

import copy
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field

from app.config import config
from app.dependencias import perfis_da_rota
from app.modelos import Perfil

VERSAO = "1.0.0-rc.1"

DESCRICAO = """
A API do **Growth Intelligence Hub**: recebe os relatórios de desempenho de uma rede de parceiros
e devolve o painel, a previsão, o plano de campanha otimizado e as mensagens para cada parceiro.
A interface web usa estas mesmas rotas.

## Autenticação

A sessão vive num **cookie** (`gih_sessao`, `HttpOnly`, `SameSite=Lax`), e nunca num token que o
cliente guarda:

1. `POST /api/sessao` com `{"login": "...", "senha": "..."}` abre a sessão e devolve o cookie;
2. as chamadas seguintes mandam o cookie de volta (o navegador faz isso sozinho; com `httpx` ou
   `requests`, use um cliente com sessão);
3. `DELETE /api/sessao` encerra a sessão **no servidor**.

A sessão dura 8 horas por padrão. Cinco tentativas de entrada erradas da mesma origem bloqueiam
novas tentativas por 15 minutos (`429`). Nesta página (Swagger), entre por `POST /api/sessao` com
"Try it out": o navegador guarda o cookie, e as outras rotas passam a responder.

## Perfis

Cada rota diz, na descrição, os **perfis** que podem chamá-la: Administrador, Gestor, Analista e
Parceiro. A permissão é conferida **no servidor**, em toda chamada: o perfil sem permissão recebe
`403`, e a tentativa fica na trilha de auditoria.

## Erros

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

## Convenções

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
""".strip()

AREAS = [
    ("autenticação", "Abrir e encerrar a sessão, saber quem está dentro, trocar a própria senha."),
    ("usuários", "As contas e os perfis de acesso (Administrador)."),
    ("parceiros", "O cadastro dos parceiros da rede e das categorias; a ficha de cada um."),
    ("importação", "O relatório de desempenho de um período: a prévia e a gravação."),
    ("painel", "Os indicadores, o ranking, as séries, os segmentos e a mobilidade do Top N."),
    ("configuração", "Os limiares da segmentação (Administrador)."),
    ("modelo preditivo", "O treino do modelo de previsão e as versões."),
    ("campanha", "O catálogo de ações e o plano de campanha calculado pelo otimizador."),
    ("benchmark", "O mesmo problema medido em Python, C++ serial, OpenMP e GPU."),
    ("mensagens", "A geração das mensagens para os parceiros e a fila de aprovação."),
    ("portal do parceiro", "O desempenho do próprio parceiro (perfil Parceiro)."),
    ("assistente", "Perguntas em linguagem natural sobre os dados, com a fonte de cada número."),
    ("auditoria", "A trilha das ações sensíveis (Administrador)."),
    ("relatórios", "Os relatórios da rede e o de operações, na tela e em CSV."),
    ("ajuda", "Os números das regras que a tela de ajuda cita, como estão valendo."),
    ("sistema", "A saúde do serviço."),
]

RESUMOS: dict[tuple[str, str], str] = {
    ("POST", "/api/sessao"): "Entrar: abre a sessão",
    ("DELETE", "/api/sessao"): "Sair: encerra a sessão no servidor",
    ("GET", "/api/sessao/atual"): "Quem está dentro, e as telas que pode abrir",
    ("POST", "/api/sessao/senha"): "Trocar a própria senha",
    ("GET", "/api/usuarios"): "Listar as contas, com filtros e busca",
    ("GET", "/api/usuarios/parceiros"): "Buscar um parceiro pelo nome, para a conta Parceiro",
    ("GET", "/api/usuarios/{usuario_id}"): "Ler uma conta",
    ("POST", "/api/usuarios"): "Criar uma conta",
    ("PATCH", "/api/usuarios/{usuario_id}"): "Editar uma conta: nome, perfil, vínculo e situação",
    ("POST", "/api/usuarios/{usuario_id}/senha"): "Redefinir a senha de outra conta",
    ("GET", "/api/parceiros"): "Listar os parceiros, com busca, filtros e ordenação",
    ("GET", "/api/parceiros/exportacao.csv"): "Exportar a lista de parceiros em CSV",
    ("GET", "/api/parceiros/{parceiro_id}"): "Ler um parceiro, com o desempenho mais recente",
    ("GET", "/api/parceiros/{parceiro_id}/previsao"): "A previsão do parceiro, ou por que não há",
    ("GET", "/api/parceiros/{parceiro_id}/campanha"): "O parceiro no último plano de campanha",
    ("GET", "/api/parceiros/{parceiro_id}/historico"): "O histórico das alterações do cadastro",
    ("POST", "/api/parceiros"): "Cadastrar um parceiro",
    ("PATCH", "/api/parceiros/{parceiro_id}"): "Editar um parceiro",
    ("DELETE", "/api/parceiros/{parceiro_id}"): "Excluir um parceiro sem histórico",
    ("GET", "/api/categorias/sugestao"): "Sugerir a categoria pelo nome do parceiro",
    ("GET", "/api/categorias"): "Listar as categorias",
    ("POST", "/api/categorias"): "Criar uma categoria",
    ("POST", "/api/importacoes/previa"): "Prévia de um relatório colado, sem gravar",
    ("POST", "/api/importacoes"): "Importar um relatório colado",
    ("POST", "/api/importacoes/arquivo/previa"): "Prévia de um arquivo CSV, sem gravar",
    ("POST", "/api/importacoes/arquivo"): "Importar um arquivo CSV",
    ("GET", "/api/importacoes"): "Histórico das importações",
    ("GET", "/api/painel/recortes"): "Os períodos e as categorias do painel",
    ("GET", "/api/painel/indicadores"): "Indicadores do período, com a variação",
    ("GET", "/api/painel/ranking"): "Ranking dos parceiros por faturamento",
    ("GET", "/api/painel/series"): "Série histórica da rede, de uma categoria ou de um parceiro",
    ("GET", "/api/painel/segmentos"): "Quantos parceiros em cada segmento",
    ("GET", "/api/painel/mobilidade"): "Quem entrou e quem saiu do Top N",
    ("GET", "/api/painel/decisao"): "A previsão e a campanha, resumidas para o painel",
    ("GET", "/api/configuracao/segmentacao"): "Os limiares da segmentação em vigor",
    ("PUT", "/api/configuracao/segmentacao"): "Alterar os limiares da segmentação",
    ("GET", "/api/modelo"): "O modelo em uso e se dá para treinar agora",
    ("POST", "/api/modelo/treinos"): "Treinar o modelo (em segundo plano)",
    ("GET", "/api/modelo/treinos"): "Histórico dos treinos",
    ("GET", "/api/modelo/treinos/{treino_id}"): "Acompanhar um treino",
    ("GET", "/api/campanha"): "O que a tela da campanha precisa ao abrir",
    ("POST", "/api/otimizacoes"): "Calcular um plano de campanha (em segundo plano)",
    ("GET", "/api/otimizacoes/comparacao"): "Comparar dois planos lado a lado",
    ("GET", "/api/otimizacoes/{execucao_id}"): "Acompanhar uma execução, com o plano",
    ("GET", "/api/otimizacoes/{execucao_id}/exportacao.csv"): "Exportar os itens do plano em CSV",
    ("GET", "/api/acoes-comerciais"): "Listar o catálogo de ações",
    ("POST", "/api/acoes-comerciais"): "Criar uma ação no catálogo",
    ("PATCH", "/api/acoes-comerciais/{acao_id}"): "Editar ou desativar uma ação do catálogo",
    ("GET", "/api/otimizacoes"): "Histórico das execuções do otimizador",
    ("GET", "/api/benchmark"): "O que a tela do benchmark precisa ao abrir",
    ("POST", "/api/benchmarks"): "Rodar o benchmark (em segundo plano)",
    ("GET", "/api/benchmarks"): "Histórico dos benchmarks",
    ("GET", "/api/benchmarks/{execucao_id}"): "Acompanhar um benchmark",
    ("GET", "/api/mensagens/geracao"): "Se o modelo de linguagem está no ar para gerar",
    ("POST", "/api/mensagens/publico"): "Prévia do público das mensagens, sem gerar",
    ("POST", "/api/mensagens/lotes"): "Gerar as mensagens de um público (em segundo plano)",
    ("GET", "/api/mensagens/lotes/{lote_id}"): "Acompanhar uma geração de mensagens",
    ("POST", "/api/mensagens/lotes/{lote_id}/refazer"): "Tentar de novo as mensagens que falharam",
    ("GET", "/api/mensagens"): "A fila de aprovação e o histórico das mensagens",
    ("GET", "/api/mensagens/exportacao.csv"): "Exportar as mensagens aprovadas em CSV",
    ("POST", "/api/mensagens/aprovacao-em-lote"): "Aprovar várias mensagens de uma vez",
    ("POST", "/api/mensagens/{mensagem_id}/aprovacao"): "Aprovar uma mensagem",
    ("POST", "/api/mensagens/{mensagem_id}/edicao"): "Editar o texto de uma mensagem pendente",
    ("POST", "/api/mensagens/{mensagem_id}/rejeicao"): "Rejeitar uma mensagem",
    ("GET", "/api/meu-desempenho"): "O desempenho do próprio parceiro",
    ("GET", "/api/assistente"): "Se o assistente está no ar, e os exemplos de pergunta",
    ("POST", "/api/assistente/perguntas"): "Perguntar ao assistente",
    ("GET", "/api/auditoria"): "Consultar a trilha de auditoria",
    ("GET", "/api/auditoria/exportacao.csv"): "Exportar a trilha de auditoria em CSV",
    ("GET", "/api/auditoria/acoes"): "As ações que a trilha registra",
    ("GET", "/api/relatorios/desempenho"): "Relatório de desempenho do período",
    ("GET", "/api/relatorios/desempenho/exportacao.csv"): "Relatório de desempenho em CSV",
    ("GET", "/api/relatorios/risco"): "Relatório dos parceiros em risco",
    ("GET", "/api/relatorios/risco/exportacao.csv"): "Relatório de risco em CSV",
    ("GET", "/api/relatorios/campanha"): "Relatório de um plano de campanha",
    ("GET", "/api/relatorios/campanha/planos"): "Os planos que o relatório da campanha oferece",
    ("GET", "/api/relatorios/campanha/exportacao.csv"): "Relatório da campanha em CSV",
    ("GET", "/api/relatorios/operacoes"): "Relatório das operações do sistema",
    ("GET", "/api/relatorios/operacoes/exportacao.csv"): "Relatório das operações em CSV",
    ("GET", "/api/ajuda/regras"): "Os limiares das regras, como valem agora",
    ("GET", "/api/health"): "Saúde do serviço e do banco",
}

# As sete operações que não tinham descrição no código.
DESCRICOES: dict[tuple[str, str], str] = {
    ("GET", "/api/usuarios/{usuario_id}"): (
        "A conta, com o perfil, a situação e o parceiro vinculado."
    ),
    ("POST", "/api/usuarios"): (
        "Cria a conta com a senha inicial, que passa pela regra de força (RF03, RF04). O perfil "
        "Parceiro exige o parceiro vinculado (RF56). Recusa com `409` o login que já existe."
    ),
    ("POST", "/api/parceiros"): (
        "Cadastra o parceiro (RF14). A categoria é opcional; sem ela, a tela sugere uma pelo nome "
        "(RN05). Recusa com `409` o nome que já existe, apontando o cadastro existente."
    ),
    ("GET", "/api/categorias"): "As categorias da rede, para o cadastro e para os filtros.",
    ("POST", "/api/categorias"): "Cria uma categoria. Recusa com `409` o nome que já existe.",
    ("POST", "/api/acoes-comerciais"): (
        "Cria uma ação no catálogo: o custo e os dois efeitos da RN10, em fração (0,14 é 14%)."
    ),
    ("PATCH", "/api/acoes-comerciais/{acao_id}"): (
        "Altera o custo, os efeitos ou a situação de uma ação. A inativa não entra nos "
        "próximos planos."
    ),
}

PARAMETROS: dict[str, str] = {
    "pagina": "A página da lista, a partir de 1.",
    "tamanho": "Quantos itens por página.",
    "busca": "Um trecho do nome; maiúscula e acento não importam.",
    "ordenar_por": "A coluna da ordenação.",
    "descendente": "Do maior para o menor.",
    "categoria_id": "Só os parceiros desta categoria.",
    "sem_categoria": "Só os parceiros sem categoria.",
    "segmento": "Só os parceiros deste segmento (RN01).",
    "status": "Só os parceiros deste status comercial.",
    "ativo": "Só os ativos (verdadeiro) ou só os inativos (falso).",
    "perfil": "Só as contas deste perfil.",
    "acao": "Só os registros desta ação.",
    "resultado": "Só as execuções com este resultado.",
    "usuario_id": "O identificador da conta.",
    "parceiro_id": "O identificador do parceiro.",
    "execucao_id": "O identificador da execução.",
    "treino_id": "O identificador do treino.",
    "lote_id": "O identificador da geração de mensagens.",
    "mensagem_id": "O identificador da mensagem.",
    "acao_id": "O identificador da ação do catálogo.",
}

EXEMPLOS: dict[tuple[str, str], dict[str, Any]] = {
    ("POST", "/api/sessao"): {"login": "gestora", "senha": "uma frase longa de senha"},
    ("POST", "/api/sessao/senha"): {
        "senha_atual": "uma frase longa de senha",
        "senha_nova": "outra frase longa, nova",
    },
    ("POST", "/api/usuarios"): {
        "login": "analista.norte",
        "nome": "Analista da Regional Norte",
        "senha": "senha inicial longa",
        "perfil": "ANALISTA",
    },
    ("PATCH", "/api/usuarios/{usuario_id}"): {"perfil": "GESTOR"},
    ("POST", "/api/usuarios/{usuario_id}/senha"): {"senha_nova": "senha redefinida longa"},
    ("POST", "/api/parceiros"): {
        "nome": "Ponto Azul 9",
        "categoria_id": 3,
        "status": "ATIVO",
        "contato": "contato@exemplo.test",
    },
    ("PATCH", "/api/parceiros/{parceiro_id}"): {
        "contato": "(81) 3000-0000",
        "status": "PROSPECCAO",
    },
    ("POST", "/api/categorias"): {"nome": "Doceria"},
    ("POST", "/api/importacoes/previa"): {
        "periodo_inicio": "2026-09-21",
        "periodo_fim": "2026-09-27",
        "texto": "Parceiro;Faturamento;Pedidos\nPonto Azul 9;12500,40;312",
    },
    ("POST", "/api/importacoes"): {
        "periodo_inicio": "2026-09-21",
        "periodo_fim": "2026-09-27",
        "texto": "Parceiro;Faturamento;Pedidos\nPonto Azul 9;12500,40;312",
        "substituir": False,
    },
    ("PUT", "/api/configuracao/segmentacao"): {
        "top_n": 15,
        "periodos_tendencia": 2,
        "periodos_novato": 3,
    },
    ("POST", "/api/otimizacoes"): {
        "orcamento": "15000.00",
        "maximo_acoes": 30,
        "cota_cauda_longa": "0.30",
        "cotas_categoria": [{"categoria_id": 3, "minimo": "0.10"}],
        "aplicacao_inicio": "2026-09-28",
        "aplicacao_fim": "2026-10-04",
    },
    ("POST", "/api/acoes-comerciais"): {
        "nome": "Cupom de recompra",
        "custo_unitario": "35.00",
        "efeito_crescimento": "0.04",
        "efeito_retencao": "0.02",
    },
    ("PATCH", "/api/acoes-comerciais/{acao_id}"): {"custo_unitario": "40.00", "ativa": False},
    ("POST", "/api/benchmarks"): {"parceiros": 2000, "acoes": 5, "repeticoes": 3},
    ("POST", "/api/mensagens/publico"): {"tipo": "PLANO", "execucao_id": 12},
    ("POST", "/api/mensagens/lotes"): {"tipo": "FILTRO", "segmento": "EM_RISCO"},
    ("POST", "/api/mensagens/aprovacao-em-lote"): {"ids": [101, 102, 103]},
    ("POST", "/api/mensagens/{mensagem_id}/edicao"): {
        "texto": "Olá! Preparamos uma condição especial para a sua loja nesta semana."
    },
    ("POST", "/api/mensagens/{mensagem_id}/rejeicao"): {
        "motivo": "Tom inadequado para o parceiro."
    },
    ("POST", "/api/assistente/perguntas"): {
        "texto": "Qual foi o faturamento total da rede na última semana?"
    },
}

# Os erros de regra de cada rota, além do 401, do 403 e do 422, que valem para todas.
ERROS: dict[tuple[str, str], tuple[int, ...]] = {
    ("POST", "/api/sessao"): (401, 429),
    ("GET", "/api/usuarios/{usuario_id}"): (404,),
    ("POST", "/api/usuarios"): (409,),
    ("PATCH", "/api/usuarios/{usuario_id}"): (404, 409),
    ("POST", "/api/usuarios/{usuario_id}/senha"): (404, 409),
    ("GET", "/api/parceiros/{parceiro_id}"): (404,),
    ("GET", "/api/parceiros/{parceiro_id}/previsao"): (404,),
    ("GET", "/api/parceiros/{parceiro_id}/campanha"): (404,),
    ("GET", "/api/parceiros/{parceiro_id}/historico"): (404,),
    ("POST", "/api/parceiros"): (409,),
    ("PATCH", "/api/parceiros/{parceiro_id}"): (404, 409),
    ("DELETE", "/api/parceiros/{parceiro_id}"): (404, 409),
    ("POST", "/api/categorias"): (409,),
    ("POST", "/api/importacoes"): (409,),
    ("POST", "/api/importacoes/arquivo/previa"): (413,),
    ("POST", "/api/importacoes/arquivo"): (409, 413),
    ("GET", "/api/painel/indicadores"): (404,),
    ("GET", "/api/painel/ranking"): (404,),
    ("GET", "/api/painel/series"): (404,),
    ("GET", "/api/painel/segmentos"): (404,),
    ("GET", "/api/painel/mobilidade"): (404,),
    ("GET", "/api/painel/decisao"): (404,),
    ("POST", "/api/modelo/treinos"): (409,),
    ("GET", "/api/modelo/treinos/{treino_id}"): (404,),
    ("POST", "/api/otimizacoes"): (409,),
    ("GET", "/api/otimizacoes/comparacao"): (404,),
    ("GET", "/api/otimizacoes/{execucao_id}"): (404,),
    ("GET", "/api/otimizacoes/{execucao_id}/exportacao.csv"): (404, 409),
    ("POST", "/api/acoes-comerciais"): (409,),
    ("PATCH", "/api/acoes-comerciais/{acao_id}"): (404, 409),
    ("POST", "/api/benchmarks"): (409,),
    ("GET", "/api/benchmarks/{execucao_id}"): (404,),
    ("POST", "/api/mensagens/publico"): (404,),
    ("POST", "/api/mensagens/lotes"): (404, 409),
    ("GET", "/api/mensagens/lotes/{lote_id}"): (404,),
    ("POST", "/api/mensagens/lotes/{lote_id}/refazer"): (404, 409),
    ("POST", "/api/mensagens/aprovacao-em-lote"): (404,),
    ("POST", "/api/mensagens/{mensagem_id}/aprovacao"): (404, 409),
    ("POST", "/api/mensagens/{mensagem_id}/edicao"): (404, 409),
    ("POST", "/api/mensagens/{mensagem_id}/rejeicao"): (404, 409),
    ("GET", "/api/relatorios/desempenho"): (404,),
    ("GET", "/api/relatorios/desempenho/exportacao.csv"): (404,),
    ("GET", "/api/relatorios/risco/exportacao.csv"): (409,),
    ("GET", "/api/relatorios/campanha"): (404,),
    ("GET", "/api/relatorios/campanha/exportacao.csv"): (404, 409),
}

# Onde o código de erro quer dizer outra coisa que o padrão da tabela abaixo.
ERRO_DA_ROTA = {
    (("POST", "/api/sessao"), 401): (
        "Login ou senha errados — a mesma resposta para os dois, de propósito: ela não diz se o "
        "login existe (RNF11)."
    ),
}
# E onde a mensagem também é outra: o exemplo da tabela abaixo mentiria ali.
MENSAGEM_DA_ROTA = {
    (("POST", "/api/sessao"), 401): "Login ou senha inválidos.",
}

# As rotas que não exigem sessão.
PUBLICAS = {("POST", "/api/sessao"), ("GET", "/api/health")}


# ---------------------------------------------------------------- os formatos de erro
class CampoComErro(BaseModel):
    campo: str = Field(description="O nome do campo, como no corpo ou na query.")
    mensagem: str = Field(description="O que está errado, em português.")
    ajuda: str | None = Field(default=None, description="Como corrigir, quando há o que dizer.")


class ErroDeCampos(BaseModel):
    """O `422`: um ou mais campos não passaram na validação."""

    erro: str = Field(examples=["Alguns campos precisam de correção."])
    campos: list[CampoComErro]


class ErroSimples(BaseModel):
    """`401`, `403`, `429` e parte dos `404`: só a mensagem."""

    detail: str = Field(examples=["Seu perfil não permite esta operação."])


class RecusaComAjuda(BaseModel):
    erro: str = Field(description="O que foi recusado, e por quê.")
    ajuda: str | None = Field(default=None, description="O que fazer para seguir.")


class ErroComAjuda(BaseModel):
    """`409`, `413` e parte dos `404`: a recusa da regra, com o que fazer. Algumas trazem
    campos a mais, como o registro que já existe."""

    detail: RecusaComAjuda


class ErroInterno(BaseModel):
    """`500`: a falha inesperada. O detalhe técnico fica no log, com este identificador."""

    erro: str = Field(examples=["Não foi possível concluir a operação."])
    correlacao: str = Field(description="O identificador da falha no log do servidor.")


ESQUEMAS_DE_ERRO = (
    CampoComErro, ErroDeCampos, ErroSimples, RecusaComAjuda, ErroComAjuda, ErroInterno
)


def _ref(modelo: type[BaseModel]) -> dict:
    return {"$ref": f"#/components/schemas/{modelo.__name__}"}


def _resposta(descricao: str, *modelos: type[BaseModel], exemplo: str | None = None) -> dict:
    esquema = _ref(modelos[0]) if len(modelos) == 1 else {"oneOf": [_ref(m) for m in modelos]}
    conteudo: dict[str, Any] = {"schema": esquema}
    if exemplo is not None:
        conteudo["example"] = {"detail": exemplo}
    return {"description": descricao, "content": {"application/json": conteudo}}


# O que a API responde de verdade em cada um: o esquema `ErroSimples` é o mesmo nos
# três, e o exemplo dele, um só — era o do 403 que aparecia no 401 (o teste da
# documentação confere estes textos contra as respostas da API).
MENSAGEM_401 = "Sessão inválida ou expirada."
MENSAGEM_403 = "Seu perfil não permite esta operação."
MENSAGEM_429 = "Muitas tentativas. Aguarde alguns minutos antes de tentar de novo."

RESPOSTAS_DE_ERRO = {
    401: _resposta(
        "Sem sessão, ou a sessão terminou: entre de novo em `POST /api/sessao`.", ErroSimples,
        exemplo=MENSAGEM_401,
    ),
    403: _resposta(
        "O perfil desta sessão não pode fazer isto. A tentativa fica na trilha de auditoria.",
        ErroSimples, exemplo=MENSAGEM_403,
    ),
    404: _resposta("O registro pedido não existe.", ErroSimples, ErroComAjuda),
    409: _resposta(
        "A regra de negócio recusa o pedido, e diz o que fazer.", ErroComAjuda, ErroSimples
    ),
    413: _resposta("O arquivo passa do limite de tamanho.", ErroComAjuda),
    422: _resposta(
        "Um ou mais campos não passaram na validação; cada um diz o que corrigir.", ErroDeCampos
    ),
    429: _resposta(
        "Tentativas de entrada demais desta origem: espere 15 minutos.", ErroSimples,
        exemplo=MENSAGEM_429,
    ),
    500: _resposta("Falha inesperada. O detalhe fica no log, com o identificador.", ErroInterno),
}

# O texto padrão do FastAPI para o sucesso é "Successful Response", em inglês e o mesmo para tudo.
SUCESSO = {
    "200": "Sucesso.",
    "201": "Criado: o corpo traz o registro novo.",
    "202": "Aceito: a operação segue em segundo plano; consulte o andamento pelo `id`.",
    "204": "Feito, sem corpo na resposta.",
}

NOMES_DOS_PERFIS = {
    Perfil.ADMINISTRADOR: "Administrador",
    Perfil.GESTOR: "Gestor",
    Perfil.ANALISTA: "Analista",
    Perfil.PARCEIRO: "Parceiro",
}


def _quem_pode(rota: APIRoute, chave: tuple[str, str]) -> str:
    if chave in PUBLICAS:
        return "Pública: não exige sessão."
    perfis = perfis_da_rota(rota)
    if not perfis:
        return "Qualquer perfil, com sessão aberta."
    nomes = [NOMES_DOS_PERFIS[p] for p in Perfil if p in perfis]
    return f"{', '.join(nomes[:-1])} e {nomes[-1]}." if len(nomes) > 1 else f"{nomes[0]}."


def documentar(app: FastAPI) -> dict[str, Any]:
    """O OpenAPI do FastAPI, completado com o que este módulo sabe de cada rota."""
    if app.openapi_schema:
        return app.openapi_schema
    esquema = get_openapi(
        title=app.title,
        version=app.version,
        description=DESCRICAO,
        routes=app.routes,
        tags=[{"name": nome, "description": texto} for nome, texto in AREAS],
    )
    componentes = esquema.setdefault("components", {})
    esquemas = componentes.setdefault("schemas", {})
    for modelo in ESQUEMAS_DE_ERRO:
        esquemas[modelo.__name__] = modelo.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
    # O 422 do FastAPI não é o que a API devolve (app/erros.py): sai do documento.
    esquemas.pop("HTTPValidationError", None)
    esquemas.pop("ValidationError", None)
    componentes["securitySchemes"] = {
        "sessao": {
            "type": "apiKey",
            "in": "cookie",
            "name": config.sessao_cookie,
            "description": "O cookie que `POST /api/sessao` devolve. O navegador o manda sozinho.",
        }
    }

    for rota in app.routes:
        if not isinstance(rota, APIRoute):
            continue
        for metodo in rota.methods - {"HEAD"}:
            chave = (metodo, rota.path)
            op = esquema["paths"][rota.path][metodo.lower()]
            op["summary"] = RESUMOS.get(chave, op.get("summary", ""))
            descricao = (op.get("description") or DESCRICOES.get(chave, "")).strip()
            op["description"] = f"**Quem pode:** {_quem_pode(rota, chave)}\n\n{descricao}".strip()

            # O cookie aparece como esquema de segurança, e não como parâmetro solto.
            op["parameters"] = [p for p in op.get("parameters", []) if p.get("in") != "cookie"]
            for parametro in op["parameters"]:
                if not parametro.get("description") and parametro["name"] in PARAMETROS:
                    parametro["description"] = PARAMETROS[parametro["name"]]
            if not op["parameters"]:
                del op["parameters"]

            if chave in EXEMPLOS:
                conteudo = op["requestBody"]["content"]["application/json"]
                conteudo["example"] = EXEMPLOS[chave]

            respostas = op.setdefault("responses", {})
            if any(trecho in rota.path for trecho in ("exportacao.csv",)):
                for codigo, resposta in respostas.items():
                    if codigo.startswith("2"):
                        resposta["content"] = {"text/csv": {"schema": {"type": "string"}}}
                        resposta["description"] = (
                            "O arquivo CSV, com o separador `;` e o BOM do UTF-8."
                        )
            codigos = list(ERROS.get(chave, ()))
            if chave not in PUBLICAS:
                op["security"] = [{"sessao": []}]
                codigos.append(401)
                if perfis_da_rota(rota):
                    codigos.append(403)
            # O 422 que o FastAPI pôs por causa do cookie, tirado acima, não vale mais.
            respostas.pop("422", None)
            if op.get("requestBody") or op.get("parameters"):
                codigos.append(422)
            codigos.append(500)
            for codigo in sorted(set(codigos)):
                # Cópia inteira: o exemplo mora dentro do `content`, e trocá-lo numa
                # cópia rasa o trocaria em toda rota.
                respostas[str(codigo)] = copy.deepcopy(RESPOSTAS_DE_ERRO[codigo])
                if (chave, codigo) in ERRO_DA_ROTA:
                    respostas[str(codigo)]["description"] = ERRO_DA_ROTA[(chave, codigo)]
                if (chave, codigo) in MENSAGEM_DA_ROTA:
                    respostas[str(codigo)]["content"]["application/json"]["example"] = {
                        "detail": MENSAGEM_DA_ROTA[(chave, codigo)]
                    }
            for codigo, resposta in respostas.items():
                if resposta.get("description") == "Successful Response":
                    resposta["description"] = SUCESSO.get(codigo, "Sucesso.")
            op["responses"] = dict(sorted(respostas.items()))

    app.openapi_schema = esquema
    return esquema
