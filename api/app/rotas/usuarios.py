"""Gestão de usuários e perfis (RF03, RF04 · histórias H15 e H16).

Tudo aqui é exclusivo do Administrador, e a restrição está declarada na rota —
não como `if` no corpo da função, onde esquecer um é silencioso (regra 2.5).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auditoria, seguranca, sessoes
from app.auditoria import Acao
from app.dependencias import Banco, UsuarioAtual, exigir
from app.esquemas import (
    EdicaoUsuario,
    NovoUsuario,
    ParceiroDoVinculo,
    RedefinicaoSenha,
    UsuarioDetalhe,
    UsuarioResposta,
)
from app.modelos import Parceiro, Perfil, Usuario
from app.seguranca import SenhaFraca
from app.sessoes import Motivo
from app.texto import para_busca

router = APIRouter(
    prefix="/api/usuarios",
    tags=["usuários"],
    dependencies=[Depends(exigir(Perfil.ADMINISTRADOR))],
)


# As vogais acentuadas e o cê-cedilha do português, para a busca ignorar o
# acento do que está **gravado**. O parceiro tem uma coluna normalizada para
# isso, com índice (RNF04: são dez mil); os usuários são dezenas, e traduzir na
# consulta dispensa a coluna e a migração.
_COM_ACENTO = "áàâãäéèêëíìîïóòôõöúùûüçñ"
_SEM_ACENTO = "aaaaaeeeeiiiiooooouuuucn"


def _para_comparar(coluna):
    return func.translate(func.lower(coluna), _COM_ACENTO, _SEM_ACENTO)


@router.get("", response_model=list[UsuarioResposta])
def listar(
    s: Banco,
    ativo: Annotated[bool | None, Query(description="Filtra por situação.")] = None,
    perfil: Annotated[Perfil | None, Query()] = None,
    busca: Annotated[
        str | None,
        Query(max_length=120, description="Trecho do nome ou do login, sem maiúscula nem acento."),
    ] = None,
) -> list[Usuario]:
    """A lista, filtrada por situação e perfil, e com busca por nome ou login (RF52, H91).

    A busca normaliza o termo pela mesma regra da de parceiros (`para_busca`):
    sem maiúscula, sem acento, e com `%` e `_` tratados como texto, e não como
    curinga.
    """
    consulta = select(Usuario).order_by(Usuario.nome)
    if ativo is not None:
        consulta = consulta.where(Usuario.ativo.is_(ativo))
    if perfil is not None:
        consulta = consulta.where(Usuario.perfil == perfil)
    termo = (busca or "").strip()
    if termo:
        padrao = f"%{para_busca(termo)}%"
        consulta = consulta.where(
            or_(
                _para_comparar(Usuario.nome).like(padrao, escape="\\"),
                _para_comparar(Usuario.login).like(padrao, escape="\\"),
            )
        )
    return list(s.scalars(consulta))


# Quantos parceiros a busca do vínculo devolve. É para achar um pelo nome, e não
# para percorrer a rede: quem digita mais, acha.
PARCEIROS_NA_BUSCA = 20


@router.get("/parceiros", response_model=list[ParceiroDoVinculo])
def parceiros_para_o_vinculo(
    s: Banco,
    busca: Annotated[
        str,
        Query(min_length=2, max_length=120, description="Trecho do nome do parceiro."),
    ],
) -> list[Parceiro]:
    """Acha um parceiro pelo nome, para vinculá-lo a uma conta de perfil Parceiro (RF56, H101).

    **Não é a lista de parceiros**, que a matriz não dá ao Administrador (UC04):
    a busca é obrigatória, devolve só o nome e a situação, e para em
    `PARCEIROS_NA_BUSCA`. Sem ela, a conta do parceiro só se criava pela API.

    Declarada antes de `/{usuario_id}`: depois dela, "parceiros" seria lido como
    o identificador de um usuário.
    """
    padrao = f"%{para_busca(busca.strip())}%"
    return list(
        s.scalars(
            select(Parceiro)
            .where(Parceiro.nome_normalizado.like(padrao, escape="\\"))
            .order_by(Parceiro.nome)
            .limit(PARCEIROS_NA_BUSCA)
        )
    )


@router.get("/{usuario_id}", response_model=UsuarioDetalhe)
def obter(usuario_id: int, s: Banco) -> UsuarioDetalhe:
    usuario = _buscar(s, usuario_id)
    parceiro = s.get(Parceiro, usuario.parceiro_id) if usuario.parceiro_id else None
    return UsuarioDetalhe(
        **UsuarioResposta.model_validate(usuario).model_dump(),
        parceiro=ParceiroDoVinculo.model_validate(parceiro) if parceiro else None,
    )


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
        raise _erro_do_campo("senha", str(e), "********") from e
    parceiro = _parceiro_do_vinculo(s, dados.parceiro_id)

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
        # Só a restrição do login vira "login em uso". Até a #227, toda violação
        # virava: um parceiro inexistente no vínculo respondia que o login já
        # existia, e a pessoa trocava um login que estava certo.
        if not _e_do_login(e):
            raise
        raise _login_em_uso(s, dados.login) from e

    detalhes = {"alvo": usuario.id, "login": usuario.login, "perfil": str(usuario.perfil)}
    if parceiro is not None:
        detalhes["parceiro"] = parceiro.nome
    auditoria.registrar(
        Acao.USUARIO_CRIADO,
        usuario_id=autor.id,
        detalhes=detalhes,
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

    # O nome do parceiro de antes, lido agora: depois da troca, a trilha não
    # teria mais de onde tirar o que era (RF06).
    antes = s.get(Parceiro, usuario.parceiro_id) if usuario.parceiro_id else None
    anterior["parceiro_nome"] = antes.nome if antes else None

    perfil_novo = dados.perfil if dados.perfil is not None else usuario.perfil
    ativo_novo = dados.ativo if dados.ativo is not None else usuario.ativo
    _proteger_ultimo_administrador(s, usuario, perfil_novo, ativo_novo)
    _parceiro_do_vinculo(s, dados.parceiro_id)

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
        raise _erro_do_campo(
            "parceiro_id", "O perfil Parceiro exige um parceiro vinculado.", None
        )

    s.flush()

    # Desativar precisa ter efeito agora, não no fim da sessão em curso.
    if anterior["ativo"] and not usuario.ativo:
        sessoes.revogar_do_usuario(s, usuario.id, Motivo.USUARIO_DESATIVADO)

    depois = s.get(Parceiro, usuario.parceiro_id) if usuario.parceiro_id else None
    _auditar_edicao(
        usuario, anterior, autor_id=autor.id, origem=origem,
        parceiro_nome=depois.nome if depois else None,
    )
    return usuario


@router.post("/{usuario_id}/senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(
    usuario_id: int,
    dados: RedefinicaoSenha,
    request: Request,
    s: Banco,
    autor: UsuarioAtual,
) -> Response:
    """O Administrador dá uma senha nova a outra conta (RF54, H93).

    É a volta de quem esqueceu a senha: antes desta rota, a única saída era
    criar outra conta para a mesma pessoa. A senha passa pela mesma validação de
    força da criação, e **todas** as sessões da conta caem — diferente da troca
    da própria senha, que preserva a sessão de quem trocou: aqui quem está
    fazendo a operação não é o dono da conta.
    """
    usuario = _buscar(s, usuario_id)
    if usuario.id == autor.id:
        # A própria senha tem o caminho dela, que exige a atual. Aceitar aqui
        # faria de uma sessão esquecida aberta o bastante para tomar a conta.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "erro": "Esta é a sua própria conta.",
                "ajuda": "Troque a sua senha em Minha conta, que pede a senha atual.",
            },
        )

    try:
        seguranca.validar_forca(dados.senha_nova, usuario.login)
    except SenhaFraca as e:
        raise _erro_do_campo("senha_nova", str(e), "********") from e

    usuario.senha_hash = seguranca.gerar_hash(dados.senha_nova)
    derrubadas = sessoes.revogar_do_usuario(s, usuario.id, Motivo.SENHA_REDEFINIDA)

    auditoria.registrar(
        Acao.SENHA_REDEFINIDA,
        usuario_id=autor.id,
        detalhes={"alvo": usuario.id, "login": usuario.login, "sessoes_encerradas": derrubadas},
        origem=auditoria.origem_de(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _parceiro_do_vinculo(s: Session, parceiro_id: int | None) -> Parceiro | None:
    """O parceiro que a conta vai apontar — ou a recusa, no campo, se ele não existe.

    Sem esta conferência o banco recusava pela chave estrangeira, e a recusa
    saía como "login em uso" na criação e como erro 500 na edição (#227).
    """
    if parceiro_id is None:
        return None
    parceiro = s.get(Parceiro, parceiro_id)
    if parceiro is None:
        raise _erro_do_campo("parceiro_id", "Parceiro não encontrado.", parceiro_id)
    return parceiro


def _e_do_login(erro: IntegrityError) -> bool:
    """A violação é a do login único? O nome da restrição vem do próprio banco."""
    restricao = getattr(getattr(erro.orig, "diag", None), "constraint_name", None) or ""
    return "login" in restricao


def _erro_do_campo(campo: str, mensagem: str, entrada) -> RequestValidationError:
    """Recusa que pertence a um campo sai como os outros erros de campo.

    Mesmo arranjo de `_categoria_existe` em `rotas/parceiros.py`: passando pelo
    tradutor de `app/erros.py`, a tela recebe o formato de sempre e marca o
    campo certo, em vez de um aviso solto no topo.
    """
    return RequestValidationError(
        [{"type": "value_error", "loc": ("body", campo), "msg": f"Value error, {mensagem}",
          "input": entrada}]
    )


def _login_em_uso(s: Session, login: str) -> HTTPException:
    """Login repetido (UC02, E1) — e **qual** conta já o usa.

    O caso comum não é coincidência de nomes: é a conta antiga, desativada, de
    quem voltou. Apontar a conta é o que leva a reativá-la em vez de tentar
    outro login para a mesma pessoa.
    """
    existente = s.scalar(select(Usuario).where(Usuario.login == login))
    detalhe = {
        "erro": f"Já existe um usuário com o login {login!r}.",
        "ajuda": (
            "Escolha outro login. Se a conta é da mesma pessoa e está desativada, "
            "reative-a em vez de criar outra."
        ),
    }
    if existente is not None:
        detalhe["existente"] = {
            "id": existente.id,
            "login": existente.login,
            "nome": existente.nome,
            "ativo": existente.ativo,
        }
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detalhe)


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
            detail={
                "erro": "Este é o último administrador ativo.",
                "ajuda": (
                    "Sem ele, ninguém mais conseguiria gerenciar usuários. Promova outro usuário "
                    "a Administrador antes de desativar este ou mudar o perfil dele."
                ),
            },
        )


def _auditar_edicao(
    usuario: Usuario, anterior: dict, *, autor_id: int, origem: str, parceiro_nome: str | None
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
                # O nome de antes e o de depois, e não só os identificadores: a
                # trilha diz de quem a conta era sem depender do cadastro de hoje.
                "parceiro_de_nome": anterior["parceiro_nome"],
                "parceiro_para_nome": parceiro_nome,
            },
            origem=origem,
        )
