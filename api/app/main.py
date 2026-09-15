"""Aplicação FastAPI do Growth Intelligence Hub.

Esqueleto da API. Por enquanto expõe apenas a verificação de saúde, que é o
único endpoint público do sistema — todos os demais exigirão sessão (RF05).
"""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db import sessao

log = logging.getLogger("gih")

app = FastAPI(
    title="Growth Intelligence Hub",
    description="API do painel de inteligência de crescimento para redes de parceiros.",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


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
