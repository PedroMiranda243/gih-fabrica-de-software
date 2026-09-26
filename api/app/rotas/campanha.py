"""A campanha — UC08, RF29 a RF32 e RF34, histórias H48 a H52, H55 e H58.

**Gestor calcula; Analista consulta**, pela matriz do UC08. O plano decide onde
vai a verba, e quem responde por isso é o Gestor; o Analista lê o plano e o
catálogo, mas não os muda. O Administrador cuida de acesso, e não de campanha:
**vê o histórico das execuções** (RF34) — autor, data, parâmetros, modo, tempo e
resultado —, mas não abre o plano de cada parceiro. Decisão de 26/09/2026,
registrada no `docs/03`.

**A busca não roda dentro da requisição** (`CLAUDE.md` §3, ADR-011), como o
treino do modelo: o `POST` grava a execução em andamento, devolve `202` e
agenda a busca para depois da resposta. A tela acompanha pelo `GET` da execução.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auditoria, servico_otimizacao, servico_previsao
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    AcaoComercialEdicao,
    AcaoComercialEntrada,
    AcaoComercialResposta,
    CategoriaCampanha,
    CotaEmContagem,
    EstadoCampanha,
    ExcluidosCampanha,
    ExecucaoResposta,
    ItemPlanoResposta,
    ModoCampanha,
    PaginaExecucoes,
    ParametrosCampanha,
    PeriodoResposta,
)
from app.modelos import (
    AcaoComercial,
    Categoria,
    ExecucaoOtimizador,
    HistoricoSegmento,
    ItemPlano,
    ModoExecucao,
    OrigemCategoria,
    Parceiro,
    Perfil,
    Periodo,
    PlanoCampanha,
    Usuario,
)
from app.servico_segmentacao import limiares_vigentes

router = APIRouter(
    prefix="/api",
    tags=["campanha"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)

catalogo = APIRouter(
    prefix="/api/acoes-comerciais",
    tags=["campanha"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)

# O histórico tem roteador próprio: a trava do roteador da campanha vale para
# todas as rotas dele, e o Administrador entra só nesta.
historico = APIRouter(
    prefix="/api/otimizacoes",
    tags=["campanha"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA, Perfil.ADMINISTRADOR))],
)

SO_GESTOR = [Depends(exigir(Perfil.GESTOR))]


# ------------------------------------------------------------ as respostas
def _itens(s: Session, execucao: ExecucaoOtimizador) -> list[ItemPlanoResposta]:
    plano = s.scalar(select(PlanoCampanha).where(PlanoCampanha.execucao_id == execucao.id))
    if plano is None:
        return []
    na_cauda = set((execucao.detalhes or {}).get("na_cauda", []))
    linhas = s.execute(
        select(
            ItemPlano,
            Parceiro.nome,
            Parceiro.origem_categoria,
            Categoria.nome,
            AcaoComercial.nome,
            HistoricoSegmento.segmento,
        )
        .join(Parceiro, Parceiro.id == ItemPlano.parceiro_id)
        .join(AcaoComercial, AcaoComercial.id == ItemPlano.acao_id)
        .outerjoin(Categoria, Categoria.id == Parceiro.categoria_id)
        .outerjoin(
            HistoricoSegmento,
            (HistoricoSegmento.parceiro_id == Parceiro.id)
            & (HistoricoSegmento.periodo_id == execucao.periodo_base_id),
        )
        .where(ItemPlano.plano_id == plano.id)
        .order_by(ItemPlano.uplift_esperado.desc(), Parceiro.nome)
    )
    return [
        ItemPlanoResposta(
            parceiro_id=item.parceiro_id,
            parceiro=nome,
            segmento=segmento,
            categoria=categoria if origem == OrigemCategoria.MANUAL else None,
            cauda_longa=item.parceiro_id in na_cauda,
            acao_id=item.acao_id,
            acao=acao,
            custo=item.custo,
            ganho=item.uplift_esperado,
        )
        for item, nome, origem, categoria, acao, segmento in linhas
    ]


def _resposta(
    s: Session, execucao: ExecucaoOtimizador | None, *, com_itens: bool = False
) -> ExecucaoResposta | None:
    if execucao is None:
        return None
    autor = s.get(Usuario, execucao.usuario_id) if execucao.usuario_id is not None else None
    detalhes = execucao.detalhes or {}
    return ExecucaoResposta(
        id=execucao.id,
        situacao=execucao.situacao,
        autor=autor.nome if autor else None,
        modo=execucao.modo,
        substituicao=detalhes.get("substituicao"),
        threads=(
            detalhes.get("busca", {}).get("threads")
            if execucao.modo == ModoExecucao.CPU_PARALELO
            else None
        ),
        iniciada_em=execucao.iniciada_em,
        concluida_em=execucao.concluida_em,
        parametros=ParametrosCampanha.model_validate(execucao.parametros),
        periodo_base=PeriodoResposta.model_validate(s.get(Periodo, execucao.periodo_base_id)),
        modelo_versao=execucao.modelo_versao,
        viavel=execucao.viavel,
        restricao_violada=execucao.restricao_violada,
        motivo=execucao.motivo,
        ajuda=detalhes.get("ajuda"),
        uplift_total=execucao.uplift_total,
        custo_total=execucao.custo_total,
        tempo_ms=execucao.tempo_ms,
        parcial=execucao.parcial,
        acoes=detalhes.get("acoes"),
        elegiveis=detalhes.get("elegiveis"),
        excluidos=(
            ExcluidosCampanha(**detalhes["excluidos"]) if "excluidos" in detalhes else None
        ),
        cotas=[CotaEmContagem(**c) for c in detalhes.get("cotas", [])],
        folga_orcamento=detalhes.get("folga_orcamento"),
        folga_acoes=detalhes.get("folga_acoes"),
        ganho_guloso=detalhes.get("ganho_guloso"),
        itens=_itens(s, execucao) if com_itens else None,
    )


def _recusa(recusa: servico_otimizacao.OtimizacaoRecusada) -> HTTPException:
    return HTTPException(
        status_code=recusa.status,
        detail={"erro": recusa.erro, "ajuda": recusa.ajuda, **recusa.extra},
    )


# ------------------------------------------------------------ a campanha
@router.get("/campanha", response_model=EstadoCampanha)
def estado(s: Banco) -> EstadoCampanha:
    """O que a tela de campanha precisa ao abrir (UC08, passo 1).

    Quantos parceiros entram e quantos ficam fora, com o motivo (RN11); as
    categorias para as cotas; o catálogo; os modos de execução que esta
    instalação tem, e qual roda sem escolha (RF32); e se dá para calcular agora.
    """
    concluido = servico_previsao.ultimo_concluido(s)
    elegiveis, excluidos = [], None
    if concluido is not None:
        elegiveis = servico_otimizacao.elegiveis(
            s, concluido.periodo_base_id, concluido.versao_em_uso
        )
        excluidos = ExcluidosCampanha(
            **servico_otimizacao.excluidos(s, concluido.periodo_base_id, concluido.versao_em_uso)
        )

    por_categoria: dict[int, int] = {}
    for e in elegiveis:
        if e.categoria_id is not None:
            por_categoria[e.categoria_id] = por_categoria.get(e.categoria_id, 0) + 1
    recusa = servico_otimizacao.bloqueio(s)
    modos = servico_otimizacao.modos()
    return EstadoCampanha(
        modelo_versao=concluido.versao_em_uso if concluido else None,
        periodo_base=(
            PeriodoResposta.model_validate(s.get(Periodo, concluido.periodo_base_id))
            if concluido
            else None
        ),
        top_n=limiares_vigentes(s).top_n,
        elegiveis=len(elegiveis),
        excluidos=excluidos,
        sem_categoria=sum(1 for e in elegiveis if e.categoria_id is None),
        categorias=[
            CategoriaCampanha(id=c.id, nome=c.nome, elegiveis=por_categoria.get(c.id, 0))
            for c in s.scalars(
                select(Categoria).where(Categoria.ativa.is_(True)).order_by(Categoria.nome)
            )
        ],
        acoes=[
            AcaoComercialResposta.model_validate(a)
            for a in s.scalars(select(AcaoComercial).order_by(AcaoComercial.id))
        ],
        em_andamento=_resposta(s, servico_otimizacao.em_andamento(s)),
        ultima=_resposta(s, servico_otimizacao.ultima_concluida(s), com_itens=True),
        pode_executar=recusa is None,
        motivo_bloqueio=recusa.erro if recusa else None,
        modos=[ModoCampanha(modo=m.modo, disponivel=m.disponivel, motivo=m.motivo) for m in modos],
        modo_automatico=servico_otimizacao.escolher(None, modos)[0],
    )


@router.post(
    "/otimizacoes",
    response_model=ExecucaoResposta,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=SO_GESTOR,
)
def calcular(
    parametros: ParametrosCampanha,
    request: Request,
    tarefas: BackgroundTasks,
    s: Banco,
    autor: UsuarioAtual,
) -> ExecucaoResposta:
    """Calcula o plano (UC08, passos 4 a 10; RF30, RF32).

    Recusa com `409` sem modelo treinado (UC08-E1), sem ação ativa no catálogo
    ou com outra otimização rodando. Campanha inviável **não** é recusada aqui:
    ela é calculada, registrada como inviável e explicada (RN07, UC08-A1). Nem
    modo indisponível: roda no mais rápido que houver, e diz a troca (UC08-A4).
    """
    try:
        execucao = servico_otimizacao.iniciar(s, parametros, usuario_id=autor.id)
    except servico_otimizacao.OtimizacaoRecusada as recusa:
        raise _recusa(recusa) from None
    # Gravada antes de a resposta sair: a busca abre outra sessão e precisa
    # encontrar a linha.
    s.commit()
    tarefas.add_task(
        servico_otimizacao.executar, execucao.id, origem=auditoria.origem_de(request)
    )
    return _resposta(s, execucao)


@historico.get("", response_model=PaginaExecucoes)
def listar(
    s: Banco,
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(10, ge=1, le=50),
) -> PaginaExecucoes:
    """O histórico de execuções, da mais recente para a mais antiga (RF34, H58).

    Sem os itens do plano: cada execução vem com autor, data, parâmetros, modo,
    tempo e resultado — o que o Administrador também vê. O plano, parceiro a
    parceiro, só na consulta de uma execução, que é da campanha (UC08).
    """
    total = s.scalar(select(func.count()).select_from(ExecucaoOtimizador))
    execucoes = s.scalars(
        select(ExecucaoOtimizador)
        .order_by(ExecucaoOtimizador.id.desc())
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    )
    return PaginaExecucoes(
        itens=[_resposta(s, e) for e in execucoes], total=total, pagina=pagina, tamanho=tamanho
    )


@router.get("/otimizacoes/{execucao_id}", response_model=ExecucaoResposta)
def obter(execucao_id: int, s: Banco) -> ExecucaoResposta:
    """Uma execução, com o plano: a tela consulta enquanto ela roda, e o
    histórico a abre depois (H58)."""
    execucao = s.get(ExecucaoOtimizador, execucao_id)
    if execucao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Otimização não encontrada.")
    return _resposta(s, execucao, com_itens=True)


# ------------------------------------------------------------ o catálogo
def _nome_em_uso(nome: str) -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT,
        detail={
            "erro": f"Já existe uma ação com o nome {nome}.",
            "ajuda": "Escolha outro nome, ou edite a ação que já existe.",
        },
    )


def _como_dict(acao: AcaoComercial) -> dict:
    return AcaoComercialResposta.model_validate(acao).model_dump(mode="json")


@catalogo.get("", response_model=list[AcaoComercialResposta])
def listar_acoes(s: Banco) -> list[AcaoComercial]:
    """O catálogo, ativas e inativas: a inativa não entra na campanha, mas existe."""
    return list(s.scalars(select(AcaoComercial).order_by(AcaoComercial.id)))


@catalogo.post(
    "",
    response_model=AcaoComercialResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=SO_GESTOR,
)
def criar_acao(
    dados: AcaoComercialEntrada, request: Request, s: Banco, autor: UsuarioAtual
) -> AcaoComercial:
    acao = AcaoComercial(**dados.model_dump())
    s.add(acao)
    try:
        s.flush()
    except IntegrityError:
        # O nome é único no banco: deixar o banco recusar é o único jeito sem
        # corrida entre a conferência e a gravação.
        s.rollback()
        raise _nome_em_uso(dados.nome) from None
    auditoria.registrar(
        Acao.ACAO_COMERCIAL_CRIADA,
        usuario_id=autor.id,
        detalhes=_como_dict(acao),
        origem=auditoria.origem_de(request),
    )
    return acao


@catalogo.patch("/{acao_id}", response_model=AcaoComercialResposta, dependencies=SO_GESTOR)
def editar_acao(
    acao_id: int, dados: AcaoComercialEdicao, request: Request, s: Banco, autor: UsuarioAtual
) -> AcaoComercial:
    acao = s.get(AcaoComercial, acao_id)
    if acao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ação não encontrada.")
    antes = _como_dict(acao)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(acao, campo, valor)
    try:
        s.flush()
    except IntegrityError:
        s.rollback()
        raise _nome_em_uso(dados.nome) from None
    auditoria.registrar(
        Acao.ACAO_COMERCIAL_EDITADA,
        usuario_id=autor.id,
        detalhes={"antes": antes, "depois": _como_dict(acao)},
        origem=auditoria.origem_de(request),
    )
    return acao
