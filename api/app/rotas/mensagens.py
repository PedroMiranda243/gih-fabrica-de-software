"""A geração de mensagens — UC10, RF36 e RF37, história H60.

**Gestor e Analista**, pela matriz do UC10: quem gera a comunicação é o
Analista, e o Gestor também. O Administrador não: as mensagens falam de
parceiros e de planos, que ele não abre.

**A geração não roda dentro da requisição**, como a otimização: o `POST` grava
o lote, devolve `202` e gera depois da resposta. A tela acompanha pelo `GET` do
lote, que traz as mensagens prontas até ali — é o que a deixa mostrá-las uma a
uma, conforme ficam prontas (UC10-A1).

Aprovar é outra história, e de outro perfil (H62, RN06): aqui toda mensagem
nasce pendente.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auditoria, redator, servico_mensagens
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    MAXIMO_POR_LOTE,
    EstadoAssistente,
    EstadoGeracao,
    FalhaDoLote,
    FatoMensagem,
    LoteResposta,
    MensagemResposta,
    PreviaPublico,
    PublicoMensagens,
)
from app.modelos import AcaoComercial, ItemPlano, LoteMensagens, Mensagem, Parceiro, Perfil, Usuario

router = APIRouter(
    prefix="/api/mensagens",
    tags=["mensagens"],
    dependencies=[Depends(exigir(Perfil.GESTOR, Perfil.ANALISTA))],
)


def _recusa(recusa: servico_mensagens.MensagensRecusadas) -> HTTPException:
    return HTTPException(
        status_code=recusa.status,
        detail={"erro": recusa.erro, "ajuda": recusa.ajuda, **recusa.extra},
    )


def _mensagens(s: Session, lote_id: int) -> list[MensagemResposta]:
    linhas = s.execute(
        select(Mensagem, Parceiro.nome, AcaoComercial.nome)
        .join(Parceiro, Parceiro.id == Mensagem.parceiro_id)
        .outerjoin(ItemPlano, ItemPlano.id == Mensagem.item_plano_id)
        .outerjoin(AcaoComercial, AcaoComercial.id == ItemPlano.acao_id)
        .where(Mensagem.lote_id == lote_id)
        .order_by(Mensagem.id)
    )
    return [
        MensagemResposta(
            id=m.id,
            parceiro_id=m.parceiro_id,
            parceiro=nome,
            segmento=m.segmento,
            acao=acao,
            texto=m.texto_final or m.texto_gerado,
            texto_gerado=m.texto_gerado,
            estado=m.estado,
            redator=m.redator,
            modelo=m.modelo,
            motivo_redator=m.motivo_redator,
            fatos=[FatoMensagem(**f) for f in m.fatos],
            lote_id=m.lote_id,
            gerada_em=m.gerada_em,
        )
        for m, nome, acao in linhas
    ]


def _resposta(
    s: Session, lote: LoteMensagens | None, *, com_mensagens: bool = False
) -> LoteResposta | None:
    if lote is None:
        return None
    autor = s.get(Usuario, lote.usuario_id) if lote.usuario_id is not None else None
    return LoteResposta(
        id=lote.id,
        situacao=lote.situacao,
        autor=autor.nome if autor else None,
        publico=PublicoMensagens.model_validate(lote.publico),
        descricao=lote.publico.get("descricao", ""),
        iniciado_em=lote.iniciado_em,
        concluido_em=lote.concluido_em,
        total=len(lote.alvos),
        geradas=servico_mensagens.geradas(s, lote.id),
        pelo_modelo=servico_mensagens.pelo_modelo(s, lote.id),
        falhas=[FalhaDoLote(**f) for f in lote.falhas],
        modelo=lote.modelo,
        motivo=lote.motivo,
        mensagens=_mensagens(s, lote.id) if com_mensagens else None,
    )


@router.get("/geracao", response_model=EstadoGeracao)
def estado(s: Banco) -> EstadoGeracao:
    """O que a tela de mensagens mostra ao abrir: o assistente está no ar, e por que
    não, quando não está (ADR-013); a geração em andamento, se houver; e a última."""
    assistente = redator.atual().estado()
    return EstadoGeracao(
        assistente=EstadoAssistente(
            disponivel=assistente.disponivel, modelo=assistente.modelo, motivo=assistente.motivo
        ),
        em_andamento=_resposta(s, servico_mensagens.em_andamento(s)),
        ultimo=_resposta(s, servico_mensagens.ultimo(s)),
        maximo=MAXIMO_POR_LOTE,
    )


@router.post("/publico", response_model=PreviaPublico)
def previa(publico: PublicoMensagens, s: Banco) -> PreviaPublico:
    """Quem entra, antes de gerar qualquer coisa (UC10, passos 1 e 2). Não grava nada."""
    try:
        resolvido = servico_mensagens.resolver(s, publico)
    except servico_mensagens.MensagensRecusadas as recusa:
        raise _recusa(recusa) from None
    motivo = servico_mensagens.impedimento(resolvido)
    return PreviaPublico(
        descricao=resolvido.descricao,
        total=len(resolvido.parceiros),
        parceiros=resolvido.parceiros[:MAXIMO_POR_LOTE],
        excluidos=resolvido.excluidos,
        maximo=MAXIMO_POR_LOTE,
        pode_gerar=motivo is None,
        motivo=motivo,
    )


@router.post("/lotes", response_model=LoteResposta, status_code=status.HTTP_202_ACCEPTED)
def gerar(
    publico: PublicoMensagens,
    request: Request,
    tarefas: BackgroundTasks,
    s: Banco,
    autor: UsuarioAtual,
) -> LoteResposta:
    """Gera as mensagens do público (UC10, passos 3 a 6). Recusa com `409` se já há uma
    geração em andamento, e com `422` o público vazio (E1) ou grande demais."""
    try:
        lote = servico_mensagens.iniciar(s, publico, usuario_id=autor.id)
    except servico_mensagens.MensagensRecusadas as recusa:
        raise _recusa(recusa) from None
    # Gravado antes de a resposta sair: a geração abre outra sessão e precisa
    # encontrar a linha.
    s.commit()
    tarefas.add_task(servico_mensagens.executar, lote.id, origem=auditoria.origem_de(request))
    return _resposta(s, lote)


@router.get("/lotes/{lote_id}", response_model=LoteResposta)
def obter(lote_id: int, s: Banco) -> LoteResposta:
    """Um lote, com as mensagens prontas até agora e as falhas (UC10-A1, A2)."""
    lote = s.get(LoteMensagens, lote_id)
    if lote is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Geração de mensagens não encontrada."
        )
    return _resposta(s, lote, com_mensagens=True)


@router.post(
    "/lotes/{lote_id}/refazer",
    response_model=LoteResposta,
    status_code=status.HTTP_202_ACCEPTED,
)
def refazer(
    lote_id: int, request: Request, tarefas: BackgroundTasks, s: Banco, autor: UsuarioAtual
) -> LoteResposta:
    """Tenta de novo as mensagens que falharam, ou que ficaram de fora quando a API
    reiniciou (UC10-A2). As já geradas ficam como estão."""
    try:
        lote = servico_mensagens.refazer(s, lote_id)
    except servico_mensagens.MensagensRecusadas as recusa:
        raise _recusa(recusa) from None
    s.commit()
    tarefas.add_task(
        servico_mensagens.executar,
        lote.id,
        origem=auditoria.origem_de(request),
        usuario_id=autor.id,
    )
    return _resposta(s, lote)
