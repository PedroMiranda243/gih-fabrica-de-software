"""Tradução dos erros de validação para português (RNF20).

O FastAPI devolve os erros do Pydantic em inglês e num formato pensado para
quem escreve API, não para quem preenche formulário. O RNF20 pede a interface
integralmente em português e operável sem treinamento, e "Field required" em
cima de um campo não diz nem qual campo nem por que ele existe.

Alguns campos carregam explicação própria: dizer que o período é obrigatório é
menos útil que dizer **por que** ele é obrigatório — é o que separa um usuário
que corrige de um que tenta de novo do mesmo jeito.
"""
from __future__ import annotations

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Explicação de RN03, num lugar só. Repetir o texto nos dois campos faria as
# duas cópias divergirem na primeira vez que alguém reescrevesse uma delas.
POR_QUE_O_PERIODO = (
    "Sem o período, as métricas ficam órfãs na linha do tempo e a segmentação por tendência "
    "classifica errado sem emitir erro (RN03). Não existe valor padrão: informe a data inicial "
    "e a data final do relatório."
)

AJUDA_POR_CAMPO = {
    "periodo_inicio": POR_QUE_O_PERIODO,
    "periodo_fim": POR_QUE_O_PERIODO,
}

MENSAGENS = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Valor curto demais.",
    "string_too_long": "Valor longo demais.",
    "string_pattern_mismatch": "Formato inválido.",
    "int_parsing": "Informe um número inteiro.",
    "decimal_parsing": "Informe um número.",
    "date_from_datetime_parsing": "Informe uma data válida, no formato AAAA-MM-DD.",
    "date_parsing": "Informe uma data válida, no formato AAAA-MM-DD.",
    "greater_than_equal": "Valor abaixo do mínimo permitido.",
    "less_than_equal": "Valor acima do máximo permitido.",
}


def nome_do_campo(loc: tuple) -> str:
    """O último trecho utilizável do caminho do erro.

    O Pydantic devolve `("body", "periodo_inicio")`; o que interessa ao usuário
    é `periodo_inicio`. Em erro de modelo inteiro sobra só `("body",)`, e aí o
    campo é a requisição em si.
    """
    partes = [str(p) for p in loc if p not in {"body", "query", "path"}]
    return ".".join(partes) if partes else "requisição"


async def erro_de_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
    campos = []
    for e in exc.errors():
        campo = nome_do_campo(e["loc"])
        # `value_error` vem de validador escrito por nós, e a mensagem dele já
        # está em português — traduzir por cima apagaria o que foi explicado.
        if e["type"] == "value_error":
            mensagem = e["msg"].removeprefix("Value error, ")
        else:
            mensagem = MENSAGENS.get(e["type"], e["msg"])

        item = {"campo": campo, "mensagem": mensagem}
        if campo in AJUDA_POR_CAMPO:
            item["ajuda"] = AJUDA_POR_CAMPO[campo]
        campos.append(item)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"erro": "Alguns campos precisam de correção.", "campos": campos},
    )
