"""Gestão de usuários e perfis (RF03, RF04 · histórias H15 e H16).

Tudo aqui é exclusivo do Administrador, e a restrição está declarada na rota —
não como `if` no corpo da função, onde esquecer um é silencioso (regra 2.5).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auditoria, seguranca, sessoes
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import EdicaoUsuario, NovoUsuario, UsuarioResposta
from app.modelos import Perfil, Usuario
from app.seguranca import SenhaFraca
from app.sessoes import Motivo

router = APIRouter(
    prefix="/api/usuarios",
    tags=["usuários"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR))],
)


@router.get("", response_model=list[UsuarioResposta])
def listar(
    s: Banco,
    ativo: Annotated[bool | None, Query(description="Filtra por situação.")] = None,
    perfil: Annotated[Perfil | None, Query()] = None,
) -> list[Usuario]:
    consulta = select(Usuario).order_by(Usuario.nome)
    if ativo is not None:
        consulta = consulta.where(Usuario.ativo.is_(ativo))
    if perfil is not None:
        consulta = consulta.where(Usuario.perfil == perfil)
    return list(s.scalars(consulta))


@router.get("/{usuario_id}", response_model=UsuarioResposta)
def obter(usuario_id: int, s: Banco) -> Usuario:
    return _buscar(s, usuario_id)


@router.post("", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def criar(
    dados: NovoUsuario,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Usuario:
    try:
        seguranca.validar_forca(dados.senha, dados.login)
    except SenhaFraca as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    usuario = Usuario(
        login=dados.login,
        nome=dados.nome,
        senha_hash=seguranca.gerar_hash(dados.senha),
        perfil=dados.perfil,
        parceiro_id=dados.parceiro_id,
        ativo=True,
    )
    s.add(usuario)

    try:
        s.flush()
    except IntegrityError as e:
        # O login é único no banco. Conferir antes com um SELECT deixaria uma
        # janela entre a conferência e a gravação — deixar o banco recusar é o
        # único jeito sem corrida.
        s.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com este login.",
        ) from e

    auditoria.registrar(
        Acao.USUARIO_CRIADO,
        usuario_id=autor.id,
        detalhes={"alvo": usuario.id, "login": usuario.login, "perfil": str(usuario.perfil)},
        origem=auditoria.origem_de(request),
    )
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioResposta)
def editar(
    usuario_id: int,
    dados: EdicaoUsuario,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Usuario:
    """Altera nome, perfil, vínculo de parceiro e situação.

    Não existe apagar: a auditoria referencia o autor de cada ação, e remover a
    linha deixaria a trilha apontando para o nada. Desativar resolve o problema
    real — tirar o acesso — sem destruir o histórico (RF03, RF06).
    """
    usuario = _buscar(s, usuario_id)
    origem = auditoria.origem_de(request)
    anterior = {
        "nome": usuario.nome,
        "perfil": str(usuario.perfil),
        "parceiro_id": usuario.parceiro_id,
        "ativo": usuario.ativo,
    }

    perfil_novo = dados.perfil if dados.perfil is not None else usuario.perfil
    ativo_novo = dados.ativo if dados.ativo is not None else usuario.ativo
    _proteger_ultimo_administrador(s, usuario, perfil_novo, ativo_novo)

    if dados.nome is not None:
        usuario.nome = dados.nome

    # O vínculo acompanha o perfil: quem deixa de ser Parceiro perde o vínculo,
    # senão o CHECK do banco recusa e o usuário recebe um 500 sem explicação.
    if dados.perfil is not None:
        usuario.perfil = dados.perfil
        if dados.perfil != Perfil.PARCEIRO:
            usuario.parceiro_id = None
    if dados.parceiro_id is not None:
        usuario.parceiro_id = dados.parceiro_id
    if dados.ativo is not None:
        usuario.ativo = dados.ativo

    if usuario.perfil == Perfil.PARCEIRO and usuario.parceiro_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O perfil Parceiro exige um parceiro vinculado.",
        )

    s.flush()

    # Desativar precisa ter efeito agora, não no fim da sessão em curso.
    if anterior["ativo"] and not usuario.ativo:
        sessoes.revogar_do_usuario(s, usuario.id, Motivo.USUARIO_DESATIVADO)

    _auditar_edicao(usuario, anterior, autor_id=autor.id, origem=origem)
    return usuario


def _buscar(s: Session, usuario_id: int) -> Usuario:
    usuario = s.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado."
        )
    return usuario


def _proteger_ultimo_administrador(
    s: Session, usuario: Usuario, perfil_novo: Perfil, ativo_novo: bool
) -> None:
    """Impede que a última conta de Administrador ativa seja perdida.

    Sem isto, uma edição distraída deixa o sistema sem ninguém capaz de criar
    usuários — e o RF03 vira impossível de cumprir sem mexer no banco à mão.

    **Não é regra de negócio de `docs/`, é trava de segurança.** Está registrada
    na issue da H15 para a equipe confirmar ou remover.
    """
    perdendo = usuario.perfil == Perfil.ADMINISTRADOR and usuario.ativo
    continuando = perfil_novo == Perfil.ADMINISTRADOR and ativo_novo
    if not perdendo or continuando:
        return

    restantes = s.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(
            Usuario.perfil == Perfil.ADMINISTRADOR,
            Usuario.ativo.is_(True),
            Usuario.id != usuario.id,
        )
    )
    if not restantes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este é o último administrador ativo — promova outro antes de alterá-lo.",
        )


def _auditar_edicao(
    usuario: Usuario, anterior: dict, *, autor_id: int, origem: str
) -> None:
    """Uma ação por tipo de mudança, para o filtro da H18 ser útil.

    Registrar tudo como "usuário editado" faria a consulta por troca de perfil
    devolver toda alteração de nome junto.
    """
    alvo = {"alvo": usuario.id, "login": usuario.login}

    if str(usuario.perfil) != anterior["perfil"]:
        auditoria.registrar(
            Acao.PERFIL_ALTERADO,
            usuario_id=autor_id,
            detalhes={**alvo, "de": anterior["perfil"], "para": str(usuario.perfil)},
            origem=origem,
        )

    if usuario.ativo != anterior["ativo"]:
        acao = Acao.USUARIO_REATIVADO if usuario.ativo else Acao.USUARIO_DESATIVADO
        auditoria.registrar(acao, usuario_id=autor_id, detalhes=alvo, origem=origem)

    mudou_dados = usuario.nome != anterior["nome"] or usuario.parceiro_id != anterior["parceiro_id"]
    if mudou_dados:
        auditoria.registrar(
            Acao.USUARIO_EDITADO,
            usuario_id=autor_id,
            detalhes={
                **alvo,
                "nome_de": anterior["nome"],
                "nome_para": usuario.nome,
                "parceiro_de": anterior["parceiro_id"],
                "parceiro_para": usuario.parceiro_id,
            },
            origem=origem,
        )
