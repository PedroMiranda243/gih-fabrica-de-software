"""Aplicação FastAPI do Growth Intelligence Hub.

`/api/health` e a abertura de sessão são os únicos pontos públicos. Todo o
resto exige sessão válida, e a autorização por perfil é verificada no servidor
a cada requisição (RF05, RNF14) — ver `app/dependencias.py`.
"""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db import sessao
from app.erros import erro_de_validacao
from app.rotas import auditoria, autenticacao, categorias, importacoes, parceiros, usuarios

log = logging.getLogger("gih")

app = FastAPI(
    title="Growth Intelligence Hub",
    description="API do painel de inteligência de crescimento para redes de parceiros.",
    version="0.2.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


# As rotas entram aqui, e a ordem não importa: cada módulo declara o próprio
# prefixo e a própria exigência de perfil.
app.include_router(autenticacao.router)
app.include_router(usuarios.router)
app.include_router(parceiros.router)
app.include_router(categorias.router)
app.include_router(importacoes.router)
app.include_router(auditoria.router)


# Erro de validacao em portugues, com a explicacao do campo quando ela existe
# (RNF20). O padrao do FastAPI responde em ingles e num formato pensado para
# quem escreve API, nao para quem preenche formulario.
app.add_exception_handler(RequestValidationError, erro_de_validacao)


@app.exception_handler(Exception)
async def erro_nao_tratado(request: Request, exc: Exception) -> JSONResponse:
    """Mensagem genérica ao cliente, detalhe apenas no log (RNF18).

    O identificador de correlação vai nos dois lados para que uma reclamação de
    usuário possa ser ligada ao evento no servidor sem expor a pilha (RNF19).
    """
    correlacao = uuid.uuid4().hex[:12]
    log.exception("[%s] %s %s", correlacao, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "erro": "Não foi possível concluir a operação.",
            "correlacao": correlacao,
        },
    )


@app.get("/api/health", tags=["sistema"])
def health() -> dict:
    """Verificação de saúde. Público — não exige sessão."""
    try:
        with sessao() as s:
            s.execute(text("SELECT 1"))
        banco = "ok"
    except Exception:
        # A saúde do banco é informação de diagnóstico, não erro da requisição:
        # responder 200 com banco="indisponível" permite ao orquestrador
        # distinguir "API no ar, banco fora" de "API fora".
        log.warning("Banco indisponível na verificação de saúde", exc_info=True)
        banco = "indisponível"

    return {"status": "ok", "banco": banco, "versao": app.version}
