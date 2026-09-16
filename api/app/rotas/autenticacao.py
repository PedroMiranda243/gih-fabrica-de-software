"""Autenticação: abrir sessão, encerrar sessão e trocar a própria senha.

Histórias H11, H12, H13, H14 e H19. Requisitos RF01, RF02, RF07, RNF09, RNF10
e RNF11.
"""
from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sqlalchemy import select

from app import auditoria, bloqueio, seguranca, sessoes
from app.auditoria import Acao
from app.config import config
from app.dependencias import Banco, SessaoAtual, UsuarioAtual
from app.esquemas import Credenciais, SessaoResposta, TrocaSenha, UsuarioResposta
from app.modelos import Usuario
from app.seguranca import SenhaFraca
from app.sessoes import Motivo

router = APIRouter(prefix="/api/sessao", tags=["autenticação"])

# Resposta única para credencial inválida. O RNF11 exige que login inexistente e
# senha errada sejam indistinguíveis — mesma mensagem, mesmo código. Duas
# mensagens diferentes entregam a lista de logins válidos de graça.
CREDENCIAL_INVALIDA = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Login ou senha inválidos.",
)


def _gravar_cookie(resposta: Response, token: str) -> None:
    """Cookie de sessão conforme o RNF10.

    `HttpOnly` tira o token do alcance de JavaScript, o que limita o estrago de
    um XSS. `SameSite=Lax` barra o envio em requisição vinda de outro site, que
    é a defesa contra CSRF neste desenho. `Secure` depende de HTTPS e por isso é
    configurável — em produção ele precisa estar ligado.
    """
    resposta.set_cookie(
        key=config.sessao_cookie,
        value=token,
        httponly=True,
        samesite="lax",
        secure=config.cookie_seguro,
        max_age=config.sessao_duracao_horas * 3600,
        path="/",
    )


@router.post("", response_model=SessaoResposta, status_code=status.HTTP_201_CREATED)
def autenticar(
    credenciais: Credenciais,
    request: Request,
    resposta: Response,
    s: Banco,
    cookie_atual: Annotated[str | None, Cookie(alias=config.sessao_cookie)] = None,
) -> SessaoResposta:
    """Abre a sessão (RF01).

    A ordem aqui importa: bloqueio, depois conferência, depois renovação. E o
    caminho de falha gasta o mesmo tempo do caminho de sucesso — ver
    `gastar_tempo_de_conferencia`.
    """
    origem = auditoria.origem_de(request)
    login = credenciais.login.strip().casefold()

    if bloqueio.esta_bloqueada(origem):
        auditoria.registrar(Acao.LOGIN_BLOQUEADO, detalhes={"login": login}, origem=origem)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Aguarde alguns minutos antes de tentar de novo.",
        )

    usuario = s.scalar(select(Usuario).where(Usuario.login == login))

    if usuario is None or not usuario.ativo:
        # Confere contra um hash descartável para não responder mais rápido
        # quando o usuário não existe (RNF11).
        seguranca.gastar_tempo_de_conferencia()
        _recusar(login, origem, usuario_id=usuario.id if usuario else None)

    if not seguranca.conferir_senha(credenciais.senha, usuario.senha_hash):
        _recusar(login, origem, usuario_id=usuario.id)

    # H13 — fixação de sessão: quem chega com um identificador na mão não fica
    # com ele depois de autenticar. O antigo morre aqui.
    if cookie_atual:
        anterior = sessoes.validar(s, cookie_atual)
        if anterior is not None:
            sessoes.revogar(s, anterior, Motivo.NOVO_LOGIN)

    token, sessao = sessoes.criar(
        s,
        usuario,
        origem=origem,
        agente=request.headers.get("user-agent"),
    )
    _gravar_cookie(resposta, token)

    bloqueio.registrar_tentativa(login, origem, sucesso=True)
    auditoria.registrar(Acao.LOGIN_SUCESSO, usuario_id=usuario.id, origem=origem)

    return SessaoResposta(
        usuario=UsuarioResposta.model_validate(usuario),
        expira_em=sessao.expira_em,
    )


def _recusar(login: str, origem: str, *, usuario_id: int | None) -> NoReturn:
    """Registra a falha e recusa. Nunca retorna — sempre levanta."""
    bloqueio.registrar_tentativa(login, origem, sucesso=False)
    auditoria.registrar(
        Acao.LOGIN_FALHA,
        usuario_id=usuario_id,
        detalhes={"login": login},
        origem=origem,
    )
    raise CREDENCIAL_INVALIDA


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def encerrar(
    request: Request,
    s: Banco,
    sessao: SessaoAtual,
) -> Response:
    """Encerra a sessão **no servidor** (RF02, H12).

    Apagar o cookie sozinho não bastaria: quem já tem o token na mão continuaria
    entrando. Por isso a revogação vem primeiro e o cookie depois.
    """
    sessoes.revogar(s, sessao, Motivo.LOGOUT)
    auditoria.registrar(
        Acao.LOGOUT,
        usuario_id=sessao.usuario_id,
        origem=auditoria.origem_de(request),
    )
    # O cookie é apagado na própria resposta devolvida. Injetar um `Response` e
    # devolver outro perderia o cabeçalho: o FastAPI só funde os dois quando a
    # rota **não** devolve uma Response pronta.
    resposta = Response(status_code=status.HTTP_204_NO_CONTENT)
    resposta.delete_cookie(config.sessao_cookie, path="/")
    return resposta


@router.get("/atual", response_model=UsuarioResposta)
def quem_sou(usuario: UsuarioAtual) -> Usuario:
    """Quem está autenticado. O frontend usa para decidir o que desenhar.

    Decidir o que *desenhar*, não o que *permitir* — a permissão é verificada no
    servidor a cada requisição (regra 2.5, RNF14).
    """
    return usuario


@router.post("/senha", status_code=status.HTTP_204_NO_CONTENT)
def trocar_senha(
    dados: TrocaSenha,
    request: Request,
    s: Banco,
    sessao: SessaoAtual,
    usuario: UsuarioAtual,
) -> Response:
    """Troca a própria senha, exigindo a atual (RF07, H19)."""
    if not seguranca.conferir_senha(dados.senha_atual, usuario.senha_hash):
        # Aqui não há o que esconder — o usuário já está autenticado, então
        # dizer que a senha atual está errada não entrega informação a ninguém.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha atual está incorreta.",
        )

    try:
        seguranca.validar_forca(dados.senha_nova, usuario.login)
    except SenhaFraca as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    usuario.senha_hash = seguranca.gerar_hash(dados.senha_nova)

    # As outras sessões caem: se a troca foi por suspeita de acesso indevido,
    # deixar as demais abertas anula o motivo de ter trocado. A que fez a troca
    # continua, senão o usuário se desloga sozinho ao se proteger.
    derrubadas = sessoes.revogar_do_usuario(
        s, usuario.id, Motivo.SENHA_ALTERADA, preservar_id=sessao.id
    )

    auditoria.registrar(
        Acao.SENHA_ALTERADA,
        usuario_id=usuario.id,
        detalhes={"sessoes_encerradas": derrubadas},
        origem=auditoria.origem_de(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
