"""O modelo preditivo — UC07, RF27, histórias H42 a H45.

**Administrador e Gestor**, pela matriz do UC07 e pelo RF27. Treinar muda as
previsões que toda a equipe vê e que o otimizador vai usar; o Analista lê as
previsões no cadastro do parceiro (RF28), mas não troca o modelo.

**O treino não roda dentro da requisição** (`CLAUDE.md` §3, ADR-010). O `POST`
grava o treino em andamento, devolve `202` e agenda a execução para depois da
resposta. A tela acompanha pelo `GET` do treino até a situação mudar.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from gih_modelo import PERIODOS_MINIMOS
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auditoria, servico_previsao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    EstadoModelo,
    FaixaCalibracao,
    MetricasTreino,
    PaginaTreinos,
    PeriodoResposta,
    TreinoResposta,
    VolumeTreino,
)
from app.modelos import Perfil, Periodo, TreinoModelo, Usuario

router = APIRouter(
    prefix="/api/modelo",
    tags=["modelo preditivo"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR, Perfil.GESTOR))],
)


def _resposta(s: Session, treino: TreinoModelo | None) -> TreinoResposta | None:
    if treino is None:
        return None
    autor = s.get(Usuario, treino.usuario_id) if treino.usuario_id is not None else None
    detalhes = treino.detalhes or {}
    return TreinoResposta(
        id=treino.id,
        situacao=treino.situacao,
        autor=autor.nome if autor else None,
        iniciado_em=treino.iniciado_em,
        concluido_em=treino.concluido_em,
        periodo_base=PeriodoResposta.model_validate(s.get(Periodo, treino.periodo_base_id)),
        volume=VolumeTreino.model_validate(treino, from_attributes=True),
        metricas=MetricasTreino.model_validate(treino, from_attributes=True),
        curva=[FaixaCalibracao(**f) for f in detalhes.get("curva", [])],
        segundos=detalhes.get("segundos"),
        promovido=treino.promovido,
        versao=treino.versao,
        versao_em_uso=treino.versao_em_uso,
        motivo=treino.motivo,
    )


def _recusa(recusa: servico_previsao.TreinoRecusado) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"erro": recusa.erro, "ajuda": recusa.ajuda, **recusa.extra},
    )


@router.get("", response_model=EstadoModelo)
def estado(s: Banco) -> EstadoModelo:
    """A versão em uso, o último treino e se dá para treinar agora (UC07, passo 1)."""
    concluido = servico_previsao.ultimo_concluido(s)
    versao = concluido.versao_em_uso if concluido else None
    ultimo = s.scalar(select(TreinoModelo).order_by(TreinoModelo.id.desc()))
    andamento = servico_previsao.em_andamento(s)
    periodos = servico_previsao.periodos_com_dados(s)
    recente = servico_previsao.periodo_mais_recente(s)

    motivo = None
    if andamento is not None:
        motivo = "Há um treino em andamento."
    elif periodos < PERIODOS_MINIMOS:
        motivo = servico_previsao.recusa_por_historico(periodos).erro

    return EstadoModelo(
        versao_em_uso=versao,
        origem=(
            None
            if versao is None
            else "REFERENCIA" if servico_previsao.e_referencia(versao) else "MODELO"
        ),
        treino_da_versao=_resposta(s, servico_previsao.treino_da_versao(s, versao)),
        ultimo_treino=_resposta(s, ultimo),
        em_andamento=_resposta(s, andamento),
        periodos_na_base=periodos,
        periodos_minimos=PERIODOS_MINIMOS,
        periodo_mais_recente=PeriodoResposta.model_validate(recente) if recente else None,
        # Não é o do treino que produziu a versão: um treino que manteve a
        # rede-3 regravou as previsões dela a partir do período dele (UC07-A1).
        periodo_das_previsoes=(
            PeriodoResposta.model_validate(s.get(Periodo, concluido.periodo_base_id))
            if concluido
            else None
        ),
        desatualizado=bool(concluido and recente and recente.id != concluido.periodo_base_id),
        pode_treinar=motivo is None,
        motivo_bloqueio=motivo,
    )


@router.post("/treinos", response_model=TreinoResposta, status_code=status.HTTP_202_ACCEPTED)
def treinar(
    request: Request,
    tarefas: BackgroundTasks,
    s: Banco,
    autor: UsuarioAtual,
) -> TreinoResposta:
    """Dispara um treino (UC07, passos 2 a 5; H45).

    Recusa com `409` e o motivo quando o histórico é curto demais (UC07-E1) ou
    já há um treino rodando.

    **O treino é gravado antes de a resposta sair**, com commit explícito: a
    execução em segundo plano abre outra sessão e precisa encontrar a linha.
    """
    try:
        treino = servico_previsao.iniciar(s, usuario_id=autor.id)
    except servico_previsao.TreinoRecusado as recusa:
        raise _recusa(recusa) from None
    s.commit()
    tarefas.add_task(
        servico_previsao.executar, treino.id, origem=auditoria.origem_de(request)
    )
    return _resposta(s, treino)


@router.get("/treinos", response_model=PaginaTreinos)
def listar(
    s: Banco,
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(10, ge=1, le=50),
) -> PaginaTreinos:
    """O histórico de treinos, do mais recente para o mais antigo."""
    total = s.scalar(select(func.count()).select_from(TreinoModelo))
    treinos = s.scalars(
        select(TreinoModelo)
        .order_by(TreinoModelo.id.desc())
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    )
    return PaginaTreinos(
        itens=[_resposta(s, t) for t in treinos], total=total, pagina=pagina, tamanho=tamanho
    )


@router.get("/treinos/{treino_id}", response_model=TreinoResposta)
def obter(treino_id: int, s: Banco) -> TreinoResposta:
    """Um treino — é o que a tela consulta enquanto ele roda."""
    treino = s.get(TreinoModelo, treino_id)
    if treino is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Treino não encontrado.")
    return _resposta(s, treino)
