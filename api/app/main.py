"""Aplicação FastAPI do Growth Intelligence Hub.

`/api/health` e a abertura de sessão são os únicos pontos públicos. Todo o
resto exige sessão válida, e a autorização por perfil é verificada no servidor
a cada requisição (RF05, RNF14) — ver `app/dependencias.py`.
"""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import servico_benchmark, servico_mensagens, servico_otimizacao, servico_previsao
from app.db import sessao
from app.erros import erro_de_validacao
from app.rotas import (
    ajuda,
    assistente,
    auditoria,
    autenticacao,
    benchmark,
    campanha,
    categorias,
    configuracao,
    importacoes,
    mensagens,
    meu_desempenho,
    modelo,
    painel,
    parceiros,
    relatorios,
    usuarios,
)

log = logging.getLogger("gih")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Na subida, fecha os treinos, as otimizações e os benchmarks que um reinício
    deixou em andamento.

    Sem isto, a trava do um por vez ficaria presa para sempre, e as telas do
    modelo, da campanha, do benchmark e das mensagens recusariam todo pedido
    novo (ADR-010, ADR-011). Banco
    fora do ar não impede a subida: a verificação de saúde é quem diz isso, e a
    API volta a funcionar quando o banco voltar.
    """
    try:
        with sessao() as s:
            interrompidos = servico_previsao.recuperar_interrompidos(s)
            interrompidas = servico_otimizacao.recuperar_interrompidas(s)
            benchmarks = servico_benchmark.recuperar_interrompidos(s)
            lotes = servico_mensagens.recuperar_interrompidos(s)
        if interrompidos:
            log.warning("%d treino(s) interrompido(s) marcado(s) como falho(s)", interrompidos)
        if interrompidas:
            log.warning("%d otimização(ões) interrompida(s) marcada(s) como falha", interrompidas)
        if benchmarks:
            log.warning("%d benchmark(s) interrompido(s) marcado(s) como falho(s)", benchmarks)
        if lotes:
            log.warning("%d geração(ões) de mensagens interrompida(s)", lotes)
    except Exception:
        log.exception("Não foi possível conferir o que ficou em andamento")
    yield


app = FastAPI(
    lifespan=ciclo_de_vida,
    title="Growth Intelligence Hub",
    description="API do painel de inteligência de crescimento para redes de parceiros.",
    version="0.2.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


class SemAdivinharOTipo:
    """`X-Content-Type-Options: nosniff` em toda resposta (RNF12, H70).

    A API devolve JSON com o que o usuário digitou — nome de parceiro, de
    categoria, de ação. Sem este cabeçalho, um navegador pode "adivinhar" que um
    JSON com `<script>` dentro é HTML e executá-lo, se alguém o abrir direto. Com
    ele, vale o tipo declarado, e JSON nunca é página.

    Um middleware ASGI, e não o `@app.middleware("http")`: aquele envolve a
    resposta inteira, e atrapalha a exportação em fluxo e as tarefas de fundo.
    Este só acrescenta o cabeçalho quando a resposta começa.
    """

    def __init__(self, aplicacao) -> None:
        self.aplicacao = aplicacao

    async def __call__(self, escopo, receber, enviar):
        if escopo["type"] != "http":
            await self.aplicacao(escopo, receber, enviar)
            return

        async def com_cabecalho(mensagem):
            if mensagem["type"] == "http.response.start":
                mensagem.setdefault("headers", [])
                mensagem["headers"].append((b"x-content-type-options", b"nosniff"))
            await enviar(mensagem)

        await self.aplicacao(escopo, receber, com_cabecalho)


app.add_middleware(SemAdivinharOTipo)


# As rotas entram aqui, e a ordem não importa: cada módulo declara o próprio
# prefixo e a própria exigência de perfil.
app.include_router(autenticacao.router)
app.include_router(usuarios.router)
app.include_router(parceiros.router)
app.include_router(categorias.router)
app.include_router(importacoes.router)
app.include_router(painel.router)
app.include_router(configuracao.router)
app.include_router(modelo.router)
app.include_router(campanha.router)
app.include_router(campanha.catalogo)
app.include_router(campanha.historico)
app.include_router(benchmark.router)
app.include_router(mensagens.router)
app.include_router(meu_desempenho.router)
app.include_router(assistente.router)
app.include_router(auditoria.router)
app.include_router(relatorios.router)
app.include_router(ajuda.router)


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
