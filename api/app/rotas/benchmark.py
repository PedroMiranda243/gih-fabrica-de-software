"""O benchmark — UC09, RF33, história H57.

**Gestor e Administrador**, pela matriz do UC09: o benchmark mede a máquina, e
não a campanha — não mostra parceiro nem plano, só tempos e o ganho de um
problema sintético. O Analista não o tem.

**A medição não roda dentro da requisição**, como a otimização: o `POST` grava o
benchmark em andamento, devolve `202` e mede depois da resposta. A tela
acompanha pelo `GET` do benchmark, que traz o andamento.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auditoria, servico_benchmark
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    AmbienteBenchmark,
    DisponibilidadeBenchmark,
    EscalabilidadeBenchmark,
    EstadoBenchmark,
    ExecucaoBenchmarkResposta,
    PaginaBenchmarks,
    ParametrosBenchmark,
    ProgressoBenchmark,
)
from app.modelos import ExecucaoBenchmark, Perfil, Usuario

router = APIRouter(
    prefix="/api",
    tags=["benchmark"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ADMINISTRADOR))],
)


def _resposta(
    s: Session, execucao: ExecucaoBenchmark | None, *, com_escalabilidade: bool = False
) -> ExecucaoBenchmarkResposta | None:
    if execucao is None:
        return None
    autor = s.get(Usuario, execucao.usuario_id) if execucao.usuario_id is not None else None
    resumo = servico_benchmark.resumir(execucao)
    series = servico_benchmark.escalabilidade(s, execucao.acoes) if com_escalabilidade else None
    return ExecucaoBenchmarkResposta(
        id=execucao.id,
        situacao=execucao.situacao,
        autor=autor.nome if autor else None,
        iniciada_em=execucao.iniciada_em,
        concluida_em=execucao.concluida_em,
        parametros=ParametrosBenchmark(
            parceiros=execucao.parceiros, acoes=execucao.acoes, repeticoes=execucao.repeticoes
        ),
        progresso=ProgressoBenchmark(**execucao.progresso) if execucao.progresso else None,
        colunas=resumo,
        ambiente=(
            AmbienteBenchmark(
                threads=execucao.ambiente.get("threads"),
                gpu=execucao.ambiente.get("gpu"),
                compilador=execucao.ambiente.get("compilador"),
            )
            if execucao.ambiente
            else None
        ),
        disputada=execucao.disputada,
        motivo=execucao.motivo,
        explicacao_gpu=(
            servico_benchmark.explicar_gpu(execucao, resumo, series or []) if resumo else None
        ),
        escalabilidade=(
            EscalabilidadeBenchmark(acoes=execucao.acoes, series=series)
            if series is not None
            else None
        ),
    )


def _recusa(recusa: servico_benchmark.BenchmarkRecusado) -> HTTPException:
    return HTTPException(
        status_code=recusa.status,
        detail={"erro": recusa.erro, "ajuda": recusa.ajuda, **recusa.extra},
    )


@router.get("/benchmark", response_model=EstadoBenchmark)
def estado(s: Banco) -> EstadoBenchmark:
    """O que a tela de benchmark precisa ao abrir (UC09, passos 1 a 3).

    Os modos que esta máquina tem, e por que falta cada um que falta (UC09-A1); o
    benchmark em andamento, se houver; o último concluído, com o gráfico de
    escalabilidade; e a base da estimativa de duração.
    """
    disponiveis, _ = servico_benchmark.colunas()
    rodando = servico_benchmark.em_andamento(s)
    return EstadoBenchmark(
        colunas=[
            DisponibilidadeBenchmark(
                coluna=d.coluna, disponivel=d.disponivel, motivo=d.motivo, detalhe=d.detalhe
            )
            for d in disponiveis
        ],
        padrao=servico_benchmark.PADRAO,
        em_andamento=_resposta(s, rodando),
        ultima=_resposta(s, servico_benchmark.ultima_concluida(s), com_escalabilidade=True),
        pode_executar=rodando is None,
        motivo_bloqueio="Já existe um benchmark em andamento." if rodando else None,
        python_s_por_parceiro=servico_benchmark.python_s_por_parceiro(s),
    )


@router.post(
    "/benchmarks",
    response_model=ExecucaoBenchmarkResposta,
    status_code=status.HTTP_202_ACCEPTED,
)
def rodar(
    parametros: ParametrosBenchmark,
    request: Request,
    tarefas: BackgroundTasks,
    s: Banco,
    autor: UsuarioAtual,
) -> ExecucaoBenchmarkResposta:
    """Roda o benchmark (UC09, passos 4 a 8). Recusa com `409` se já há um rodando."""
    try:
        execucao = servico_benchmark.iniciar(s, parametros, usuario_id=autor.id)
    except servico_benchmark.BenchmarkRecusado as recusa:
        raise _recusa(recusa) from None
    # Gravado antes de a resposta sair: a medição abre outra sessão e precisa
    # encontrar a linha.
    s.commit()
    tarefas.add_task(servico_benchmark.executar, execucao.id, origem=auditoria.origem_de(request))
    return _resposta(s, execucao)


@router.get("/benchmarks", response_model=PaginaBenchmarks)
def listar(
    s: Banco,
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(10, ge=1, le=50),
) -> PaginaBenchmarks:
    """O histórico dos benchmarks, do mais recente para o mais antigo (UC09, passo 8)."""
    total = s.scalar(select(func.count()).select_from(ExecucaoBenchmark))
    execucoes = s.scalars(
        select(ExecucaoBenchmark)
        .order_by(ExecucaoBenchmark.id.desc())
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    )
    return PaginaBenchmarks(
        itens=[_resposta(s, e) for e in execucoes], total=total, pagina=pagina, tamanho=tamanho
    )


@router.get("/benchmarks/{execucao_id}", response_model=ExecucaoBenchmarkResposta)
def obter(execucao_id: int, s: Banco) -> ExecucaoBenchmarkResposta:
    """Um benchmark, com o gráfico de escalabilidade do número de ações dele: a tela
    consulta enquanto ele roda, e o histórico o abre depois."""
    execucao = s.get(ExecucaoBenchmark, execucao_id)
    if execucao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Benchmark não encontrado.")
    return _resposta(s, execucao, com_escalabilidade=True)
