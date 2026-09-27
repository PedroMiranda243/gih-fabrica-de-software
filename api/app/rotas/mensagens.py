"""As mensagens: a geração (UC10, H60) e a fila de aprovação (UC11, H61 a H63).

**Gestor e Analista**, pela matriz do UC10: quem gera a comunicação é o
Analista, e o Gestor também. O Administrador não: as mensagens falam de
parceiros e de planos, que ele não abre.

**Decidir é só do Gestor** (RN06, UC11-A4). As rotas de aprovar, editar e
rejeitar exigem o perfil no servidor, além do Gestor e Analista do roteador; o
Analista que tentar recebe 403, e a tentativa entra na auditoria pelo próprio
`exigir`. Ele vê a fila, mas não decide.

**A geração não roda dentro da requisição**, como a otimização: o `POST` grava
o lote, devolve `202` e gera depois da resposta. A tela acompanha pelo `GET` do
lote, que traz as mensagens prontas até ali — é o que a deixa mostrá-las uma a
uma, conforme ficam prontas (UC10-A1).

Aprovar é outra história, e de outro perfil (H62, RN06): aqui toda mensagem
nasce pendente.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app import auditoria, redator, servico_aprovacao, servico_mensagens
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    MAXIMO_POR_LOTE,
    AprovacaoEmLote,
    DecisaoJaRegistrada,
    EdicaoMensagem,
    EstadoAssistente,
    EstadoGeracao,
    FalhaDoLote,
    FatoMensagem,
    LoteResposta,
    MensagemResposta,
    PaginaMensagens,
    PreviaPublico,
    PublicoMensagens,
    RejeicaoMensagem,
    ResultadoAprovacaoEmLote,
)
from app.guarda_numerica import numeros_sem_origem
from app.modelos import (
    AcaoComercial,
    Categoria,
    EstadoMensagem,
    ItemPlano,
    LoteMensagens,
    Mensagem,
    OrigemCategoria,
    Parceiro,
    Perfil,
    Segmento,
    Usuario,
)

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


_DECISOR = aliased(Usuario)


def _consulta():
    """A mensagem com o que a fila mostra dela (UC11, passo 2): o parceiro, a
    categoria confirmada, a ação do plano e quem decidiu."""
    return (
        select(
            Mensagem,
            Parceiro.nome,
            Categoria.nome,
            Parceiro.origem_categoria,
            AcaoComercial.nome,
            _DECISOR.nome,
        )
        .join(Parceiro, Parceiro.id == Mensagem.parceiro_id)
        .outerjoin(Categoria, Categoria.id == Parceiro.categoria_id)
        .outerjoin(ItemPlano, ItemPlano.id == Mensagem.item_plano_id)
        .outerjoin(AcaoComercial, AcaoComercial.id == ItemPlano.acao_id)
        .outerjoin(_DECISOR, _DECISOR.id == Mensagem.decidida_por_id)
    )


def _para_resposta(linha) -> MensagemResposta:
    m, nome, categoria, origem, acao, decisor = linha
    texto = m.texto_final or m.texto_gerado
    editada = m.texto_final is not None and m.texto_final != m.texto_gerado
    return MensagemResposta(
        id=m.id,
        parceiro_id=m.parceiro_id,
        parceiro=nome,
        segmento=m.segmento,
        acao=acao,
        texto=texto,
        texto_gerado=m.texto_gerado,
        estado=m.estado,
        redator=m.redator,
        modelo=m.modelo,
        motivo_redator=m.motivo_redator,
        fatos=[FatoMensagem(**f) for f in m.fatos],
        lote_id=m.lote_id,
        gerada_em=m.gerada_em,
        categoria=categoria if origem == OrigemCategoria.MANUAL else None,
        editada=editada,
        # Só o texto do gestor precisa do aviso: o do modelo passou pela guarda, e o
        # do modelo fixo só tem os números dos fatos.
        numeros_fora_dos_fatos=numeros_sem_origem(texto, m.fatos) if editada else [],
        decidida_por=decisor,
        decidida_em=m.decidida_em,
        motivo_rejeicao=m.motivo_rejeicao,
    )


def _uma(s: Session, mensagem_id: int) -> MensagemResposta:
    return _para_resposta(s.execute(_consulta().where(Mensagem.id == mensagem_id)).one())


def _mensagens(s: Session, lote_id: int) -> list[MensagemResposta]:
    linhas = s.execute(_consulta().where(Mensagem.lote_id == lote_id).order_by(Mensagem.id))
    return [_para_resposta(linha) for linha in linhas]


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


# --------------------------------------------------------- a fila (UC11, H61)
@router.get("", response_model=PaginaMensagens)
def listar(
    s: Banco,
    estado: Annotated[EstadoMensagem, Query(description="A fila são as pendentes.")] = (
        EstadoMensagem.PENDENTE
    ),
    segmento: Annotated[
        Segmento | None, Query(description="O segmento do parceiro quando a mensagem foi gerada.")
    ] = None,
    lote_id: Annotated[int | None, Query(description="As mensagens de uma geração.")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaMensagens:
    """As mensagens de um estado (UC11, passos 1 e 2).

    As pendentes vêm da mais antiga para a mais nova: é a ordem em que chegaram à
    fila, e a próxima a decidir é a primeira (passo 6). As decididas, da decisão
    mais recente para a mais antiga.
    """
    filtros = [Mensagem.estado == estado]
    if segmento is not None:
        filtros.append(Mensagem.segmento == segmento)
    if lote_id is not None:
        filtros.append(Mensagem.lote_id == lote_id)
    total = s.scalar(select(func.count()).select_from(Mensagem).where(*filtros))
    ordem = (
        (Mensagem.id.asc(),)
        if estado == EstadoMensagem.PENDENTE
        else (Mensagem.decidida_em.desc(), Mensagem.id.desc())
    )
    linhas = s.execute(
        _consulta().where(*filtros).order_by(*ordem).offset((pagina - 1) * tamanho).limit(tamanho)
    )
    return PaginaMensagens(
        itens=[_para_resposta(linha) for linha in linhas],
        total=total,
        pagina=pagina,
        tamanho=tamanho,
    )


# -------------------------------------------------- a decisão (UC11, H62, H63)
def _recusa_da_decisao(recusa: servico_aprovacao.DecisaoRecusada) -> HTTPException:
    return HTTPException(
        status_code=recusa.status,
        detail={"erro": recusa.erro, "ajuda": recusa.ajuda, **recusa.extra},
    )


SO_GESTOR = [Depends(exigir(Perfil.GESTOR))]


@router.post(
    "/aprovacao-em-lote", response_model=ResultadoAprovacaoEmLote, dependencies=SO_GESTOR
)
def aprovar_em_lote(
    pedido: AprovacaoEmLote, request: Request, s: Banco, autor: UsuarioAtual
) -> ResultadoAprovacaoEmLote:
    """Aprova as pendentes selecionadas (UC11-A3). Cada uma registra a própria decisão,
    com autor e data, e entra na auditoria uma a uma; a que outra pessoa decidiu no
    meio fica como estava, e a resposta diz qual."""
    resultado = servico_aprovacao.aprovar_em_lote(s, pedido.ids, usuario_id=autor.id)
    s.flush()
    origem = auditoria.origem_de(request)
    parceiros = dict(
        s.execute(
            select(Mensagem.id, Mensagem.parceiro_id).where(Mensagem.id.in_(resultado.aprovadas))
        ).all()
    )
    for mensagem_id in resultado.aprovadas:
        auditoria.registrar(
            Acao.MENSAGEM_APROVADA,
            usuario_id=autor.id,
            detalhes={"mensagem": mensagem_id, "parceiro": parceiros[mensagem_id], "em_lote": True},
            origem=origem,
        )
    return ResultadoAprovacaoEmLote(
        aprovadas=resultado.aprovadas,
        ja_decididas=[
            DecisaoJaRegistrada(
                mensagem_id=d.mensagem_id,
                estado=d.estado,
                decidida_por=d.decidida_por,
                decidida_em=d.decidida_em,
            )
            for d in resultado.ja_decididas
        ],
        nao_encontradas=resultado.nao_encontradas,
    )


@router.post("/{mensagem_id}/aprovacao", response_model=MensagemResposta, dependencies=SO_GESTOR)
def aprovar(mensagem_id: int, request: Request, s: Banco, autor: UsuarioAtual) -> MensagemResposta:
    """Aprova a mensagem (UC11, passos 4 e 5): ela fica pronta para envio, com o texto
    editado, se houve edição. Recusa com `409` a que outra pessoa já decidiu (E1)."""
    try:
        mensagem = servico_aprovacao.aprovar(s, mensagem_id, usuario_id=autor.id)
    except servico_aprovacao.DecisaoRecusada as recusa:
        raise _recusa_da_decisao(recusa) from None
    s.flush()
    resposta = _uma(s, mensagem_id)
    auditoria.registrar(
        Acao.MENSAGEM_APROVADA,
        usuario_id=autor.id,
        detalhes={
            "mensagem": mensagem.id,
            "parceiro": mensagem.parceiro_id,
            "editada": resposta.editada,
        },
        origem=auditoria.origem_de(request),
    )
    return resposta


@router.post("/{mensagem_id}/edicao", response_model=MensagemResposta, dependencies=SO_GESTOR)
def editar(
    mensagem_id: int, pedido: EdicaoMensagem, request: Request, s: Banco, autor: UsuarioAtual
) -> MensagemResposta:
    """Troca o texto de uma mensagem pendente (UC11-A1). Ela continua pendente: a
    edição não aprova. O texto redigido fica guardado para a auditoria, e a resposta
    aponta os números do texto novo que não vieram dos dados."""
    try:
        servico_aprovacao.editar(s, mensagem_id, pedido.texto)
    except servico_aprovacao.DecisaoRecusada as recusa:
        raise _recusa_da_decisao(recusa) from None
    s.flush()
    resposta = _uma(s, mensagem_id)
    auditoria.registrar(
        Acao.MENSAGEM_EDITADA,
        usuario_id=autor.id,
        detalhes={
            "mensagem": mensagem_id,
            "parceiro": resposta.parceiro_id,
            "numeros_fora_dos_fatos": resposta.numeros_fora_dos_fatos,
        },
        origem=auditoria.origem_de(request),
    )
    return resposta


@router.post("/{mensagem_id}/rejeicao", response_model=MensagemResposta, dependencies=SO_GESTOR)
def rejeitar(
    mensagem_id: int,
    pedido: RejeicaoMensagem,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> MensagemResposta:
    """Rejeita a mensagem, com o motivo, se houver (UC11-A2). Recusa com `409` a que
    outra pessoa já decidiu (E1)."""
    try:
        mensagem = servico_aprovacao.rejeitar(
            s, mensagem_id, usuario_id=autor.id, motivo=pedido.motivo
        )
    except servico_aprovacao.DecisaoRecusada as recusa:
        raise _recusa_da_decisao(recusa) from None
    s.flush()
    auditoria.registrar(
        Acao.MENSAGEM_REJEITADA,
        usuario_id=autor.id,
        detalhes={
            "mensagem": mensagem.id,
            "parceiro": mensagem.parceiro_id,
            "motivo": mensagem.motivo_rejeicao,
        },
        origem=auditoria.origem_de(request),
    )
    return _uma(s, mensagem_id)
